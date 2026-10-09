#include "Wire.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>

TwoWire::TwoWire(const char *dev)
	: path_(dev), fd_(-1), addr7_(0), rx_off_(0)
{
}

TwoWire::~TwoWire()
{
	end();
}

void TwoWire::begin()
{
	if (fd_ >= 0)
		return;
	fd_ = open(path_.c_str(), O_RDWR);
	if (fd_ < 0)
		perror(path_.c_str());
}

void TwoWire::end()
{
	if (fd_ >= 0) {
		close(fd_);
		fd_ = -1;
	}
}

void TwoWire::beginTransmission(uint8_t addr7)
{
	addr7_ = addr7;
	tx_.clear();
}

size_t TwoWire::write(uint8_t b)
{
	tx_.push_back(b);
	return 1;
}

size_t TwoWire::write(const uint8_t *data, size_t n)
{
	tx_.insert(tx_.end(), data, data + n);
	return n;
}

int TwoWire::i2c_write(const uint8_t *data, size_t n)
{
	struct i2c_msg msg;
	struct i2c_rdwr_ioctl_data rdwr;

	memset(&msg, 0, sizeof(msg));
	msg.addr = addr7_;
	msg.flags = 0;
	msg.len = (uint16_t)n;
	msg.buf = const_cast<uint8_t *>(data);
	rdwr.msgs = &msg;
	rdwr.nmsgs = 1;
	if (ioctl(fd_, I2C_RDWR, &rdwr) < 0)
		return -errno;
	return 0;
}

int TwoWire::i2c_write_read(const uint8_t *w, size_t wn, uint8_t *r, size_t rn)
{
	struct i2c_msg msgs[2];
	struct i2c_rdwr_ioctl_data rdwr;

	memset(msgs, 0, sizeof(msgs));
	msgs[0].addr = addr7_;
	msgs[0].flags = 0;
	msgs[0].len = (uint16_t)wn;
	msgs[0].buf = const_cast<uint8_t *>(w);
	msgs[1].addr = addr7_;
	msgs[1].flags = I2C_M_RD;
	msgs[1].len = (uint16_t)rn;
	msgs[1].buf = r;
	rdwr.msgs = msgs;
	rdwr.nmsgs = 2;
	if (ioctl(fd_, I2C_RDWR, &rdwr) < 0)
		return -errno;
	return 0;
}

uint8_t TwoWire::endTransmission(bool sendStop)
{
	if (fd_ < 0)
		return 1;
	if (sendStop) {
		int rc = i2c_write(tx_.data(), tx_.size());
		tx_.clear();
		return rc ? 1 : 0;
	}
	/* repeated start: keep tx_ as register prefix for requestFrom */
	return 0;
}

uint8_t TwoWire::requestFrom(uint8_t addr7, uint8_t n)
{
	addr7_ = addr7;
	rx_.assign(n, 0);
	rx_off_ = 0;
	int rc = i2c_write_read(tx_.data(), tx_.size(), rx_.data(), n);
	tx_.clear();
	if (rc) {
		rx_.clear();
		return 0;
	}
	return n;
}

int TwoWire::available()
{
	return (int)(rx_.size() - rx_off_);
}

int TwoWire::read()
{
	if (rx_off_ >= rx_.size())
		return -1;
	return rx_[rx_off_++];
}
