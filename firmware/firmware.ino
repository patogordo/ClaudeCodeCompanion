// Claude Code Companion: firmware do Seeed XIAO ESP32-C3.
// O corpo é o mascote do Claude Code; os olhos são as duas janelinhas dele, com LEDs atrás de um difusor branco.
// Os olhos e o buzzer mostram o que o Claude Code está fazendo. Os comandos chegam por BLE, do plugin ou do portal, e
// pela serial (Wokwi e testes): um comando de texto por escrita ou por linha. O protocolo está em docs/protocolo.md;
// shared/protocol.ts e plugin/bin/companion usam os mesmos UUIDs e estados (há teste).
#include <Adafruit_NeoPixel.h>
#include <BLE2902.h>
#include <BLEDevice.h>
#include <Preferences.h>
#include <Wire.h>
#include <esp_sleep.h>

#define FW_VERSION "1.0.0"
#define BLE_NAME "Claude Companion"
#define SERVICE_UUID "5d1e0000-23fd-4dbe-89ca-ba268b36c947"
#define COMMAND_UUID "5d1e0001-23fd-4dbe-89ca-ba268b36c947"
#define STATUS_UUID "5d1e0002-23fd-4dbe-89ca-ba268b36c947"

// Pinos: use os nomes Dx (no XIAO, "7" é o GPIO7, que é o D5). Pinagem e ligações em docs/hardware.md.
// LEDs fora de D6 e D7 (UART0, onde o boot escreve o log) e de D8 e D9 (strapping: um LED apagado no dado puxaria o
// GPIO9 para baixo no boot).
#define LED_PIN D3  // um fio só: olho esquerdo (cima, baixo) → olho direito (cima, baixo) → superpoder da cabeça
#define EYE_PIXELS 2  // por olho: a janelinha do mascote tem um pixel de largura por dois de altura
#define HAT_PIXELS 16  // dados a mais saem pelo fim da corrente sem problema: cabe chapéu de até 16 LEDs
#define BUZZER_PIN D2
#define BUTTON_PIN D1   // GPIO3: só os GPIO0 a 5 acordam o C3 do deep sleep
#define BATTERY_PIN A0  // divisor 1:1 a partir do BAT+
#define LED_EN_PIN D10  // liga a alimentação dos LEDs; solto no deep sleep, o pull-down do MOSFET corta
// Superpoder das costas: I2C (Qwiic/STEMMA QT) em D4 (SDA) e D5 (SCL), os pinos padrão do Wire.

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

Adafruit_NeoPixel leds(2 * EYE_PIXELS + HAT_PIXELS, LED_PIN, NEO_GRB + NEO_KHZ800);
const int HAT = 2 * EYE_PIXELS;  // onde o chapéu começa na corrente; o LED da linha r do olho e é e * EYE_PIXELS + r
Preferences prefs;

State state = IDLE;
uint8_t volume = 60, brightness = 40;  // 0 a 100, guardados na flash
int batteryMv = 0, batteryPct = -1;    // -1: sem bateria (só USB, ou no Wokwi)
uint8_t i2cFound[8];
int i2cCount = 0;

BLECharacteristic *statusChar = nullptr;
struct Line {
  char text[32];
};
QueueHandle_t inbox;  // comandos do BLE; o callback roda na task do Bluetooth e o loop é quem mexe nos LEDs

// ---------------- Som ----------------
const Note *song = nullptr;
uint32_t noteEnd = 0;

void buzz(uint16_t hz) {
  if (!hz || !volume) {
    ledcWrite(BUZZER_PIN, 0);
    return;
  }
  ledcWriteTone(BUZZER_PIN, hz);
  ledcWrite(BUZZER_PIN, 1 + volume * volume * 127 / 10000);  // o volume é o ciclo de trabalho (até 50%)
}

void play(const Note *s) {
  song = s;
  noteEnd = 0;
}

void soundTick(uint32_t now) {
  if (!song || (int32_t)(now - noteEnd) < 0) return;
  if (!song->ms) {
    buzz(0);
    song = nullptr;
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

// Cor no instante t (ms). pos (0 a 1) é a posição: os olhos usam 0 e o olho inteiro muda junto (com o difusor, LEDs
// em fases diferentes virariam uma cor só); o chapéu usa a posição de cada LED, e a cor corre por ele.
uint32_t colorAt(float pos, uint32_t t) {
  switch (state) {
    case THINKING: {  // alterna entre amarelo e laranja vibrante
      float k = (sinf(TWO_PI * (t / 1200.0f + pos)) + 1) / 2;
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
  leds.fill(c);
  leds.show();
}

void showFrame(uint32_t t) {
  leds.fill(colorAt(0, t), 0, 2 * EYE_PIXELS);
  for (int i = 0; i < HAT_PIXELS; i++) leds.setPixelColor(HAT + i, colorAt((float)i / HAT_PIXELS, t));
  leds.show();
}

void setRow(int row, uint32_t c) {  // a mesma linha nos dois olhos
  for (int eye = 0; eye < 2; eye++) leds.setPixelColor(eye * EYE_PIXELS + row, c);
  leds.show();
}

void applyBrightness() { leds.setBrightness(map(brightness, 0, 100, 0, 255)); }

// Ao ligar: os olhos abrem em branco (de baixo para cima), piscam duas vezes e se apagam devagar até o repouso
void bootAnimation() {
  play(SND_ON);
  uint32_t c = rgb(WHITE, 1);
  leds.fill(c, HAT, HAT_PIXELS);  // o chapéu acende junto
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
  String i2c;
  for (int i = 0; i < i2cCount; i++) i2c += (i ? "," : "") + String(i2cFound[i]);
  char buf[200];
  snprintf(buf, sizeof buf, "{\"fw\":\"%s\",\"state\":\"%s\",\"vol\":%d,\"bri\":%d,\"bat\":%d,\"mv\":%d,\"i2c\":[%s]}",
           FW_VERSION, STATE_NAMES[state], volume, brightness, batteryPct, batteryMv, i2c.c_str());
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
  if (s == DONE) play(SND_DONE);
  if (s == ERROR) play(SND_ERROR);
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
    if (now - downAt > 30) setState(IDLE);  // toque curto: volta ao repouso
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
    play(SND_BEEP);
  } else if (name == "bri" && arg >= 0) {
    brightness = constrain(arg, 5L, 100L);
    prefs.putUChar("bri", brightness);
    applyBrightness();
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
  leds.begin();
  applyBrightness();

  inbox = xQueueCreate(8, sizeof(Line));
  Wire.begin();
  for (uint8_t a = 8; a < 120 && i2cCount < 8; a++) {  // o que estiver ligado no superpoder das costas
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) i2cFound[i2cCount++] = a;
  }
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
