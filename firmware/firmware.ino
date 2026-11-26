// Claude Code Companion: firmware do Seeed XIAO ESP32-C3.
// O corpo é o mascote do Claude Code; os olhos são as duas janelinhas dele, com LEDs atrás de um difusor branco.
// Os olhos e o buzzer mostram o que o Claude Code está fazendo. Os comandos chegam por BLE, do plugin ou do portal, e
// pela serial (Wokwi e testes): um comando de texto por escrita ou por linha. O protocolo está em docs/protocolo.md;
// shared/protocol.ts e plugin/bin/companion usam os mesmos UUIDs e estados (há teste).
#include <Adafruit_NeoPixel.h>
#include <BLE2902.h>
#include <BLEDevice.h>
#include <Preferences.h>
#include <esp_sleep.h>

#define FW_VERSION "1.0.0"
#define BLE_NAME "Claude Companion"
#define SERVICE_UUID "5d1e0000-23fd-4dbe-89ca-ba268b36c947"
#define COMMAND_UUID "5d1e0001-23fd-4dbe-89ca-ba268b36c947"
#define STATUS_UUID "5d1e0002-23fd-4dbe-89ca-ba268b36c947"

// Pinos pelo número do GPIO, o impresso na ESP32-C3 SuperMini (no XIAO: 5 = D3, 6 = D4). Ligações em docs/hardware.md.
// LEDs fora dos GPIO20 e 21 (UART0, onde o boot escreve o log) e dos GPIO8 e 9 (strapping).
#define LEFT_EYE_PIN 5   // o olho esquerdo de quem olha de frente
#define RIGHT_EYE_PIN 6
#define EYE_PIXELS 2     // por olho: a janelinha do mascote tem um pixel de largura por dois de altura
#define BUZZER_PIN 4
#define BUTTON_PIN 3     // só os GPIO0 a 5 acordam o C3 do deep sleep
#define BATTERY_PIN 2    // divisor 1:1 a partir do BAT+; sem bateria, no 3V3
#define LED_EN_PIN 10    // liga a alimentação dos LEDs; solto no deep sleep, o pull-down do MOSFET corta

const uint32_t HOLD_MS = 1000;   // segurar o botão para ligar e para desligar
const int LOW_BATTERY_MV = 3300; // abaixo disso, desliga sozinho para poupar a bateria

enum State { IDLE, THINKING, DONE, QUESTION, ERROR, STATE_COUNT };
const char *STATE_NAMES[STATE_COUNT] = {"idle", "thinking", "done", "question", "error"};

struct Rgb {
  uint8_t r, g, b;
};
const Rgb YELLOW = {255, 190, 0}, ORANGE = {255, 72, 0}, GREEN = {0, 230, 90}, BLUE = {30, 110, 255},
          RED = {255, 16, 16}, WHITE = {255, 255, 255};

// Melodias: {frequência em Hz, duração em ms}; 0 Hz é pausa e {0, 0} encerra
struct Note {
  uint16_t hz, ms;
};
const Note SND_ON[] = {{523, 70}, {659, 70}, {784, 70}, {1047, 160}, {0, 0}};
const Note SND_OFF[] = {{1047, 70}, {784, 70}, {659, 70}, {523, 220}, {0, 0}};
const Note SND_DONE[] = {{1319, 70}, {0, 30}, {1760, 160}, {0, 0}};
const Note SND_ERROR[] = {{330, 120}, {0, 40}, {220, 280}, {0, 0}};
const Note SND_BEEP[] = {{1047, 60}, {0, 0}};
const Rgb PARTY[] = {RED, ORANGE, GREEN, BLUE, {190, 0, 255}, WHITE};
#include "songs.h"

Adafruit_NeoPixel eyes[2] = {{EYE_PIXELS, LEFT_EYE_PIN, NEO_GRB + NEO_KHZ800},
                             {EYE_PIXELS, RIGHT_EYE_PIN, NEO_GRB + NEO_KHZ800}};
Preferences prefs;

State state = IDLE;
uint8_t volume = 60, brightness = 40;  // 0 a 100, guardados na flash
int batteryMv = 0, batteryPct = -1;    // -1: sem bateria (só USB, ou no Wokwi)

BLECharacteristic *statusChar = nullptr;
struct Line {
  char text[32];
};
QueueHandle_t inbox;  // comandos do BLE; o callback roda na task do Bluetooth e o loop é quem mexe nos LEDs

// ---------------- Som ----------------
const Note *song = nullptr;
uint32_t noteEnd = 0;
const Note *music = nullptr;  // começo da música tocando: os olhos piscam com as notas e os sons de estado ficam quietos

void buzz(uint16_t hz) {
  if (!hz || !volume) {
    ledcWrite(BUZZER_PIN, 0);
    return;
  }
  ledcWriteTone(BUZZER_PIN, hz * 2);  // uma oitava acima, onde o piezo soa mais alto
  ledcWrite(BUZZER_PIN, 1 + volume * volume * 511 / 10000);  // ciclo de trabalho até 50%: o tom usa 10 bits
}

void play(const Note *s) {
  song = s;
  noteEnd = 0;
  music = nullptr;
}

void playMusic(const Note *s) {
  play(s);
  music = s;
}

void soundTick(uint32_t now) {
  if (!song) return;
  if ((int32_t)(now - noteEnd) < 0) {
    if (music && (int32_t)(now - noteEnd) >= -20) buzz(0);  // separa notas repetidas
    return;
  }
  if (!song->ms) {
    buzz(0);
    song = nullptr;
    music = nullptr;
    return;
  }
  buzz(song->hz);
  noteEnd = now + song->ms;
  song++;
}

// Espera tocando o som: para as animações de ligar e desligar
void wait(uint32_t ms) {
  uint32_t end = millis() + ms;
  while ((int32_t)(end - millis()) > 0) {
    soundTick(millis());
    delay(1);
  }
}

// ---------------- Olhos ----------------
float breathe(uint32_t t, uint32_t period) { return (1 - cosf(TWO_PI * (t % period) / period)) / 2; }

// Linear de propósito: com gama, o repouso (nível baixo) e o brilho em 40% somem
uint32_t rgb(Rgb c, float level) { return Adafruit_NeoPixel::Color(c.r * level, c.g * level, c.b * level); }

// Cor no instante t (ms). O olho inteiro muda junto: com o difusor, LEDs em fases diferentes virariam uma cor só.
uint32_t colorAt(uint32_t t) {
  switch (state) {
    case THINKING: {  // alterna entre amarelo e laranja vibrante
      float k = (sinf(TWO_PI * t / 1200.0f) + 1) / 2;
      Rgb c = {uint8_t(YELLOW.r + (ORANGE.r - YELLOW.r) * k), uint8_t(YELLOW.g + (ORANGE.g - YELLOW.g) * k),
               uint8_t(YELLOW.b + (ORANGE.b - YELLOW.b) * k)};
      return rgb(c, 1);
    }
    case DONE:
      return rgb(GREEN, 1);
    case QUESTION:
      return rgb(BLUE, 0.35f + 0.65f * breathe(t, 1600));
    case ERROR:
      return rgb(RED, 1);
    default:  // repouso: apagado, e o difusor fica branco
      return 0;
  }
}

void fillAll(uint32_t c) {
  for (auto &eye : eyes) {
    eye.fill(c);
    eye.show();
  }
}

void showFrame(uint32_t t) {
  if (!music || song == music) return fillAll(colorAt(t));
  int i = song - music - 1;  // a nota que está soando
  bool lit = music[i].hz && (int32_t)(noteEnd - t) > 20;
  for (int e = 0; e < 2; e++) {
    eyes[e].fill(lit ? rgb(PARTY[(i + e * 3) % 6], 1) : 0);
    eyes[e].show();
  }
}

void setRow(int row, uint32_t c) {  // a mesma linha nos dois olhos
  for (auto &eye : eyes) {
    eye.setPixelColor(row, c);
    eye.show();
  }
}

void applyBrightness() {
  for (auto &eye : eyes) eye.setBrightness(map(brightness, 0, 100, 0, 255));
}

// Ao ligar: os olhos abrem em branco (de baixo para cima), piscam duas vezes e se apagam devagar até o repouso
void bootAnimation() {
  play(SND_ON);
  uint32_t c = rgb(WHITE, 1);
  for (int row = EYE_PIXELS - 1; row >= 0; row--) {
    setRow(row, c);
    wait(150);
  }
  for (int blink = 0; blink < 2; blink++) {
    fillAll(0);
    wait(90);
    fillAll(c);
    wait(160);
  }
  wait(300);
  for (int level = 10; level >= 0; level--) {
    fillAll(rgb(WHITE, level / 10.0f));
    wait(40);
  }
}

// ---------------- Estado e status ----------------
void handle(String cmd);
String statusJson() {
  char buf[200];
  snprintf(buf, sizeof buf, "{\"fw\":\"%s\",\"state\":\"%s\",\"vol\":%d,\"bri\":%d,\"bat\":%d,\"mv\":%d,\"i2c\":[]}",
           FW_VERSION, STATE_NAMES[state], volume, brightness, batteryPct, batteryMv);
  return buf;
}

// Avisa a mudança nos dois caminhos: notificação no BLE e uma linha na serial (a ponte do simulador guarda a última)
void publishStatus() {
  String json = statusJson();
  Serial.println(json);
  if (!statusChar) return;
  statusChar->setValue(json.c_str());
  statusChar->notify();
}

// Junta os caracteres até o fim da linha, sem esperar: um comando que chega picotado não vira dois
void readSerial() {
  static String line;
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (line.length()) handle(line);
      line = "";
    } else if (line.length() < 31) {
      line += c;
    }
  }
}

void setState(State s) {
  if (s == DONE && !music) play(SND_DONE);
  if (s == ERROR && !music) play(SND_ERROR);
  state = s;
  publishStatus();
}

// ---------------- Energia ----------------
void sleepNow() {
  digitalWrite(LED_EN_PIN, LOW);
  esp_deep_sleep_enable_gpio_wakeup(1ULL << BUTTON_PIN, ESP_GPIO_WAKEUP_GPIO_LOW);
  esp_deep_sleep_start();
}

// Ao desligar: os olhos acendem em branco, a pálpebra fecha (apaga de cima para baixo) e o C3 dorme até o botão
void powerOff() {
  Serial.println("desligando");
  play(SND_OFF);
  fillAll(rgb(WHITE, 1));
  wait(120);
  for (int row = 0; row < EYE_PIXELS; row++) {
    setRow(row, 0);
    wait(150);
  }
  fillAll(0);
  wait(250);
  buzz(0);
  while (digitalRead(BUTTON_PIN) == LOW) delay(10);  // soltar antes de dormir, senão acorda na hora
  sleepNow();
}

void readBattery() {
  uint32_t sum = 0;
  for (int i = 0; i < 8; i++) sum += analogReadMilliVolts(BATTERY_PIN);
  batteryMv = sum / 8 * 2;  // divisor 1:1
  // shortcut: curva linear de LiPo entre 3,3 V e 4,15 V; troque por uma tabela se a porcentagem incomodar
  batteryPct = batteryMv < 2500 ? -1 : constrain(map(batteryMv, LOW_BATTERY_MV, 4150, 0, 100), 0, 100);
}

void checkBattery() {
  static int lowReadings = 0;
  int before = batteryPct;
  readBattery();
  lowReadings = batteryPct >= 0 && batteryMv < LOW_BATTERY_MV ? lowReadings + 1 : 0;
  if (lowReadings >= 3) powerOff();  // três leituras seguidas, para não desligar por um pico
  if (batteryPct != before) publishStatus();
}

void checkButton(uint32_t now) {
  static uint32_t downAt = 0;
  bool down = digitalRead(BUTTON_PIN) == LOW;
  if (down && !downAt) downAt = now | 1;
  if (down && now - downAt >= HOLD_MS) powerOff();
  if (!down && downAt) {
    if (now - downAt > 30) {  // toque curto: para a música e volta ao repouso
      if (music) {
        play(nullptr);
        buzz(0);
      }
      setState(IDLE);
    }
    downAt = 0;
  }
}

// ---------------- Comandos ----------------
void handle(String cmd) {
  cmd.trim();
  cmd.toLowerCase();
  if (!cmd.length()) return;
  int sp = cmd.indexOf(' ');
  String name = sp < 0 ? cmd : cmd.substring(0, sp);
  long arg = sp > 0 && isDigit(cmd[sp + 1]) ? cmd.substring(sp + 1).toInt() : -1;

  for (int s = 0; s < STATE_COUNT; s++) {
    if (name == STATE_NAMES[s]) return setState((State)s);
  }
  if (name == "vol" && arg >= 0) {
    volume = min(arg, 100L);
    prefs.putUChar("vol", volume);
    if (!music) play(SND_BEEP);
  } else if (name == "bri" && arg >= 0) {
    brightness = constrain(arg, 5L, 100L);
    prefs.putUChar("bri", brightness);
    applyBrightness();
  } else if (name == "music") {  // music N (1 a SONG_COUNT); sem número, a primeira
    if (arg < 0) arg = 1;
    if (arg >= 1 && arg <= SONG_COUNT) playMusic(SONG_LIST[arg - 1]);
    return;
  } else if (name == "off") {
    return powerOff();
  } else if (name == "status") {
    Serial.println(statusJson());
    return;
  } else {
    Serial.printf("comando desconhecido: %s\n", cmd.c_str());
    return;
  }
  publishStatus();
}

// ---------------- BLE ----------------
class CommandWrite : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) override {
    Line line = {};
    strncpy(line.text, c->getValue().c_str(), sizeof line.text - 1);
    xQueueSend(inbox, &line, 0);
  }
};

class Connections : public BLEServerCallbacks {
  // continua anunciando: o plugin e o portal podem ficar conectados ao mesmo tempo
  void onConnect(BLEServer *) override { BLEDevice::startAdvertising(); }
  void onDisconnect(BLEServer *) override { BLEDevice::startAdvertising(); }
};

void startBle() {
  BLEDevice::init(BLE_NAME);
  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new Connections());
  BLEService *service = server->createService(SERVICE_UUID);
  BLECharacteristic *command = service->createCharacteristic(
      COMMAND_UUID, BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
  command->setCallbacks(new CommandWrite());
  statusChar = service->createCharacteristic(STATUS_UUID,
                                             BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  statusChar->addDescriptor(new BLE2902());
  statusChar->setValue(statusJson().c_str());
  service->start();
  BLEAdvertising *adv = BLEDevice::getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setScanResponse(true);
  BLEDevice::startAdvertising();
}

// ---------------- Setup e loop ----------------
void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  if (esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_GPIO) {
    // acordou pelo botão: só liga se ele continuar apertado (um esbarrão não liga)
    uint32_t start = millis();
    while (digitalRead(BUTTON_PIN) == LOW && millis() - start < HOLD_MS) delay(5);
    if (digitalRead(BUTTON_PIN) == HIGH) sleepNow();
  }

  pinMode(LED_EN_PIN, OUTPUT);
  digitalWrite(LED_EN_PIN, HIGH);
  ledcAttach(BUZZER_PIN, 1000, 8);
  ledcWrite(BUZZER_PIN, 0);
  prefs.begin("companion");
  volume = prefs.getUChar("vol", volume);
  brightness = prefs.getUChar("bri", brightness);
  for (auto &eye : eyes) eye.begin();
  applyBrightness();

  inbox = xQueueCreate(8, sizeof(Line));
  readBattery();
  startBle();

  bootAnimation();
  while (digitalRead(BUTTON_PIN) == LOW) delay(10);  // o mesmo aperto que ligou não desliga
  Serial.println(statusJson());
}

void loop() {
  uint32_t now = millis();
  Line line;
  while (xQueueReceive(inbox, &line, 0)) handle(line.text);
  readSerial();
  checkButton(now);
  soundTick(now);

  static uint32_t lastFrame = 0, lastBattery = 0;
  if (now - lastFrame >= 20) {
    lastFrame = now;
    showFrame(now);
  }
  if (now - lastBattery >= 10000) {
    lastBattery = now;
    checkBattery();
  }
}
