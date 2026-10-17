#pragma once

#include <stdint.h>

constexpr int LOW = 0;
constexpr int HIGH = 1;
constexpr int OUTPUT = 1;
constexpr int INPUT_PULLUP = 2;

uint32_t millis();
int digitalRead(uint8_t pin);
void digitalWrite(uint8_t pin, int value);
void pinMode(uint8_t pin, int mode);
void analogWrite(uint8_t pin, int value);
void analogWriteResolution(int bits);
