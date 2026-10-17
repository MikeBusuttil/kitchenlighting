// Run from the repository root:
// g++ -std=c++11 -Wall -Wextra -Werror -I12v/tests 12v/tests/test_min.cpp -o /tmp/test_min
// /tmp/test_min
// The stub models SAMD pin ownership: digitalWrite does not disconnect PWM;
// pinMode does, and analogWrite reconnects it. Timing and outputs are simulated,
// not electrical behavior or the real board's bootloader.
#include <array>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <string>
#include "Arduino.h"

namespace simulated {
struct Pin {
  int mode = 0;
  int latch = LOW;
  bool pwm = false;
  int duty = 0;
};
std::array<Pin, 8> pins;
uint32_t now = 0;
int button = HIGH;
int resolution = 0;

void require(bool condition, const std::string& message) {
  if (!condition) throw std::runtime_error(message);
}

Pin& outputPin(uint8_t pin) {
  require(pin == 3 || pin == 5 || pin == 6, "Unexpected output pin");
  return pins.at(pin);
}
}  // namespace simulated

uint32_t millis() { return simulated::now; }
int digitalRead(uint8_t pin) {
  simulated::require(pin == 2, "Button must use D2");
  return simulated::button;
}
void digitalWrite(uint8_t pin, int value) {
  simulated::outputPin(pin).latch = value;
}
void pinMode(uint8_t pin, int mode) {
  auto& state = simulated::pins.at(pin);
  state.mode = mode;
  state.pwm = false;
}
void analogWrite(uint8_t pin, int value) {
  auto& state = simulated::outputPin(pin);
  simulated::require(value >= 0 && value <= 255, "PWM value outside 8 bits");
  state.pwm = true;
  state.duty = value;
}
void analogWriteResolution(int bits) { simulated::resolution = bits; }

#define ARDUINO_SAMD_NANO_33_IOT
#include "../min.ino"

namespace {
using simulated::require;
using Rgb = std::array<int, 3>;

Rgb output() {
  Rgb result;
  const int pins[] = {3, 5, 6};
  for (int i = 0; i < 3; ++i) {
    const auto& state = simulated::pins[pins[i]];
    require(state.mode == OUTPUT, "RGB pin is not an output");
    result[i] = state.pwm ? state.duty : (state.latch == HIGH ? 255 : 0);
  }
  return result;
}

void expectRgb(const Rgb& expected, const std::string& message, int tolerance = 0) {
  const Rgb actual = output();
  for (int i = 0; i < 3; ++i) {
    require(std::abs(actual[i] - expected[i]) <= tolerance,
            message + ": channel " + std::to_string(i) + " was " +
            std::to_string(actual[i]) + ", expected " + std::to_string(expected[i]));
  }
}

void expectGpio(const std::string& message) {
  for (int pin : {3, 5, 6}) require(!simulated::pins[pin].pwm, message);
}

void tick(uint32_t elapsed) {
  simulated::now += elapsed;
  loop();
}

void setButton(int level) {
  simulated::button = level;
  loop();
}

void release() {
  setButton(HIGH);
  tick(30);
}

void press() {
  setButton(LOW);
  tick(30);
}

void boot(uint32_t now = 0, int button = HIGH) {
  simulated::pins = {};
  simulated::now = now;
  simulated::button = button;
  simulated::resolution = 0;
  // Reset globals to emulate a fresh MCU boot between independent scenarios.
  mode = FULL;
  rawButton = stableButton = HIGH;
  buttonChangedAt = lastFrameAt = rainbowPhaseMs = brightnessPhaseMs = 0;
  setup();
  expectRgb({255, 255, 255}, "Boot must start at full white");
  expectGpio("Full brightness must use constant HIGH, not PWM");
  require(simulated::resolution == 8, "Expected 8-bit PWM resolution");
  require(simulated::pins[2].mode == INPUT_PULLUP, "Button needs its pull-up");
}

uint32_t enterTrippy() {
  press();
  release();
  press();
  const uint32_t enteredAt = simulated::now;
  expectRgb({255, 0, 0}, "Trippy starts at full red");
  expectGpio("PWM must disconnect at full and off endpoints");
  release();
  return enteredAt;
}

void atPhase(uint32_t enteredAt, uint32_t elapsed) {
  simulated::now = enteredAt + elapsed;
  loop();
}

void testButtonAndModes() {
  boot();
  setButton(LOW);
  tick(10);
  setButton(HIGH);
  tick(5);
  setButton(LOW);
  tick(29);
  expectRgb({255, 255, 255}, "Bounce must not count as a press");
  tick(1);
  expectRgb({64, 32, 16}, "First debounced press selects warm mood");
  for (int pin : {3, 5, 6}) require(simulated::pins[pin].pwm, "Mood uses PWM");
  tick(10000);
  expectRgb({64, 32, 16}, "Holding the button must not repeat");
  setButton(HIGH);
  tick(10);
  setButton(LOW);
  tick(30);
  expectRgb({64, 32, 16}, "Release bounce must not create a second press");
  release();
  press();
  expectRgb({255, 0, 0}, "Second press selects trippy");
  expectGpio("Changing from mood must disconnect PWM at endpoints");
  release();
  press();
  expectRgb({255, 255, 255}, "Third press returns to full white");
  expectGpio("Returning to full must disable PWM on every RGB pin");
  release();
  press();
  expectRgb({64, 32, 16}, "Mode sequence repeats");
}

void testHeldAtBoot() {
  boot(100, LOW);
  tick(10000);
  expectRgb({255, 255, 255}, "Button held during boot must not advance");
  release();
  press();
  expectRgb({64, 32, 16}, "Release and new press after boot must advance once");
}

void testRainbowAndBreathing(uint32_t start) {
  boot(start);
  const uint32_t enteredAt = enterTrippy();
  // Check observable colors throughout the rainbow, including independent
  // dimming. A one-step tolerance allows channel rounding at hue boundaries.
  atPhase(enteredAt, 833);
  expectRgb({234, 234, 0}, "Yellow near one sixth of the rainbow", 1);
  require(simulated::pins[3].pwm && simulated::pins[5].pwm,
          "Intermediate colors must reconnect PWM after GPIO endpoints");
  atPhase(enteredAt, 1667);
  expectRgb({0, 178, 0}, "Green near one third of the rainbow", 1);
  atPhase(enteredAt, 2500);
  expectRgb({0, 105, 105}, "Cyan halfway through the rainbow", 1);
  atPhase(enteredAt, 3333);
  expectRgb({0, 0, 40}, "Blue near two thirds of the rainbow", 1);
  atPhase(enteredAt, 4167);
  expectRgb({3, 0, 3}, "Magenta near five sixths of the rainbow", 1);
  atPhase(enteredAt, 4500);
  expectRgb({0, 0, 0}, "Brightness reaches off at 4.5 seconds");
  expectGpio("Off must use constant LOW on all channels");
  atPhase(enteredAt, 5000);
  expectRgb({8, 0, 0}, "Hue repeats after 5 seconds while brightness remains low", 1);
  atPhase(enteredAt, 9000);
  expectRgb({204, 0, 255}, "Brightness returns to full after 9 seconds at a different hue");
  require(!simulated::pins[6].pwm, "Full blue must be constant HIGH");
  atPhase(enteredAt, 45000);
  expectRgb({255, 0, 0}, "Both independent cycles repeat after 45 seconds");
  // A press is processed during animation without waiting for either cycle.
  atPhase(enteredAt, 46000);
  setButton(LOW);
  tick(29);
  require(output() != Rgb{255, 255, 255}, "Press accepted before debounce");
  tick(1);
  expectRgb({255, 255, 255}, "Button remains responsive while trippy animates");
}

void testDebounceRollover() {
  boot(UINT32_MAX - 10);
  setButton(LOW);
  tick(29);
  expectRgb({255, 255, 255}, "Rollover must not shorten debounce");
  tick(1);
  expectRgb({64, 32, 16}, "Press must be accepted across millis rollover");
}
}  // namespace

int main() {
  try {
    testButtonAndModes();
    testHeldAtBoot();
    testRainbowAndBreathing(0);
    // Trippy begins 10 ms before rollover; run the same output checks after it.
    testRainbowAndBreathing(UINT32_MAX - 100);
    testDebounceRollover();
    std::cout << "PASS: modes, debounce, startup hold, PWM endpoints, animation, rollover\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "FAIL: " << error.what() << '\n';
    return 1;
  }
}
