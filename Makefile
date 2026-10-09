# Native aarch64 (on-phone g++) or host clang. Phone: musl.
CXX ?= g++
SHIM := linux-shim
VENDOR := third_party/VL53L3CX/src
CXXFLAGS ?= -O2 -std=c++17 -I$(SHIM) -I$(VENDOR) -Wno-unused-parameter -Wno-unused-variable -Wno-sign-compare -fno-exceptions -fno-rtti

.PHONY: all clean range

all: fp5-tof-range

fp5-tof-range: fp5-tof-range.cpp $(SHIM)/Wire.cpp $(VENDOR)/vl53lx_class.cpp
	$(CXX) $(CXXFLAGS) -o $@ fp5-tof-range.cpp $(SHIM)/Wire.cpp $(VENDOR)/vl53lx_class.cpp

clean:
	rm -f fp5-tof-range
