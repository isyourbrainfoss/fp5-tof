/* Minimal Arduino shim for ST VL53L3CX API on Linux. */
#ifndef FP5_ARDUINO_SHIM_H
#define FP5_ARDUINO_SHIM_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define LED_BUILTIN 13

typedef uint8_t byte;

static inline void delay(unsigned int ms)
{
	usleep((useconds_t)ms * 1000U);
}

static inline void pinMode(int pin, int mode)
{
	(void)pin;
	(void)mode;
}

static inline void digitalWrite(int pin, int val)
{
	(void)pin;
	(void)val;
}

static inline unsigned long millis(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (unsigned long)ts.tv_sec * 1000UL + (unsigned long)ts.tv_nsec / 1000000UL;
}

class DummySerial {
public:
	void print(int) {}
	void print(unsigned int) {}
	void print(const char *) {}
	void println(int) {}
	void println(unsigned int) {}
	void println(const char *) {}
};

static DummySerial Serial;

#endif
