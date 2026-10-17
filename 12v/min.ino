// Arduino Nano 33 IoT; matches the D3/D5/D6 MOSFET wiring in min.svg.
// Normally-open pushbutton: D2 to GND. The onboard RESET button restarts
// the sketch in full brightness. No additional libraries are required.
#include <Arduino.h>
#include <math.h>

#if !defined(ARDUINO_SAMD_NANO_33_IOT)
#error "Select Arduino Nano 33 IoT (Arduino SAMD Boards) before compiling."
#endif

constexpr uint8_t RED_PIN = 3;
constexpr uint8_t GREEN_PIN = 5;
constexpr uint8_t BLUE_PIN = 6;
constexpr uint8_t BUTTON_PIN = 2;

// Warm, dim RGB mix; adjust each value from 0 (off) to 255 (full).
constexpr uint8_t MOOD_RED = 64;
constexpr uint8_t MOOD_GREEN = 32;
constexpr uint8_t MOOD_BLUE = 16;
constexpr uint32_t RAINBOW_PERIOD_MS = 5000;
constexpr uint32_t BRIGHTNESS_PERIOD_MS = 9000;  // Full -> off -> full.
constexpr uint32_t FRAME_INTERVAL_MS = 20;
constexpr uint32_t DEBOUNCE_MS = 30;
constexpr float TWO_PI_F = 6.28318530718f;

enum Mode : uint8_t { FULL, MOOD, TRIPPY };
Mode mode = FULL;
int rawButton = HIGH;
int stableButton = HIGH;
uint32_t buttonChangedAt = 0;
uint32_t lastFrameAt = 0;
uint32_t rainbowPhaseMs = 0;
uint32_t brightnessPhaseMs = 0;

void writeChannel(uint8_t pin, uint8_t value) {
  if (value == 0 || value == 255) {
    // SAMD PWM's maximum duty is slightly below 100%. Drive the endpoints
    // directly for true off/full; pinMode also disconnects any active PWM.
    digitalWrite(pin, value == 255 ? HIGH : LOW);
    pinMode(pin, OUTPUT);
  } else {
    analogWrite(pin, value);  // Reconnects PWM after a direct off/full output.
  }
}

void writeRgb(uint8_t red, uint8_t green, uint8_t blue) {
  // Low-side N-channel MOSFETs: HIGH means on; do not invert these values.
  writeChannel(RED_PIN, red);
  writeChannel(GREEN_PIN, green);
  writeChannel(BLUE_PIN, blue);
}

void renderMode() {
  if (mode == FULL) {
    writeRgb(255, 255, 255);
    return;
  }
  if (mode == MOOD) {
    writeRgb(MOOD_RED, MOOD_GREEN, MOOD_BLUE);
    return;
  }

  // Smooth, independent breathing: full at 0 s, off at 4.5 s, full at 9 s.
  const float brightness = 0.5f + 0.5f * cosf(
      TWO_PI_F * brightnessPhaseMs / BRIGHTNESS_PERIOD_MS);
  const uint8_t peak = static_cast<uint8_t>(255.0f * brightness + 0.5f);

  // Six linear hue segments: red, yellow, green, cyan, blue, magenta, red.
  const uint32_t hue = rainbowPhaseMs * 6;
  const uint8_t segment = hue / RAINBOW_PERIOD_MS;
  const uint32_t fraction = hue % RAINBOW_PERIOD_MS;
  const uint8_t rising = (peak * fraction + RAINBOW_PERIOD_MS / 2) /
                         RAINBOW_PERIOD_MS;
  const uint8_t falling = peak - rising;
  switch (segment) {
    case 0: writeRgb(peak, rising, 0); break;
    case 1: writeRgb(falling, peak, 0); break;
    case 2: writeRgb(0, peak, rising); break;
    case 3: writeRgb(0, falling, peak); break;
    case 4: writeRgb(rising, 0, peak); break;
    default: writeRgb(peak, 0, falling); break;
  }
}

void advanceMode(uint32_t now) {
  switch (mode) {
    case FULL: mode = MOOD; break;
    case MOOD: mode = TRIPPY; break;
    case TRIPPY: mode = FULL; break;
  }
  // Trippy always begins at full red, with both cycles starting together.
  rainbowPhaseMs = 0;
  brightnessPhaseMs = 0;
  lastFrameAt = now;
  renderMode();
}

void updateButton(uint32_t now) {
  const int reading = digitalRead(BUTTON_PIN);
  if (reading != rawButton) {
    rawButton = reading;
    buttonChangedAt = now;
  }
  if (rawButton != stableButton && now - buttonChangedAt >= DEBOUNCE_MS) {
    stableButton = rawButton;
    if (stableButton == LOW) {
      advanceMode(now);  // One change per press; holding does not repeat.
    }
  }
}

void setup() {
  // Establish LOW on all gates before enabling any light output.
  writeRgb(0, 0, 0);
  analogWriteResolution(8);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  // A button held during power-up must be released before it can advance.
  rawButton = stableButton = digitalRead(BUTTON_PIN);
  buttonChangedAt = lastFrameAt = millis();
  renderMode();
}

void loop() {
  const uint32_t now = millis();
  updateButton(now);
  const uint32_t elapsed = now - lastFrameAt;
  if (mode == TRIPPY && elapsed >= FRAME_INTERVAL_MS) {
    // Advance separate phases with unsigned elapsed time, including across
    // millis() rollover. No delay(): the button stays responsive while fading.
    rainbowPhaseMs = (rainbowPhaseMs + elapsed % RAINBOW_PERIOD_MS) %
                     RAINBOW_PERIOD_MS;
    brightnessPhaseMs = (brightnessPhaseMs + elapsed % BRIGHTNESS_PERIOD_MS) %
                        BRIGHTNESS_PERIOD_MS;
    lastFrameAt = now;
    renderMode();
  }
}
