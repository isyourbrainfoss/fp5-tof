#ifndef FP5_WIRE_SHIM_H
#define FP5_WIRE_SHIM_H

#include <stdint.h>
#include <vector>
#include <string>

class TwoWire {
public:
	explicit TwoWire(const char *dev = "/dev/i2c-9");
	~TwoWire();
	void begin();
	void end();
	void beginTransmission(uint8_t addr7);
	size_t write(uint8_t b);
	size_t write(const uint8_t *data, size_t n);
	uint8_t endTransmission(bool sendStop = true);
	uint8_t requestFrom(uint8_t addr7, uint8_t n);
	int available();
	int read();

private:
	std::string path_;
	int fd_;
	uint8_t addr7_;
	std::vector<uint8_t> tx_;
	std::vector<uint8_t> rx_;
	size_t rx_off_;
	int i2c_write(const uint8_t *data, size_t n);
	int i2c_write_read(const uint8_t *w, size_t wn, uint8_t *r, size_t rn);
};

#endif
