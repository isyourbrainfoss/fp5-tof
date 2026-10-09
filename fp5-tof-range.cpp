/*
 * Userspace VL53L3CX ranger for Fairphone 5 (i2c-9 0x29).
 * Uses ST VL53LX API (BSD-3-Clause, lab/tof/vendor/VL53L3CX).
 * Never requests NFC reset GPIO 38. Power/XSHUT are the caller's job
 * (tof-rail.ko + gpioset gpiochip4 49=1).
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "Arduino.h"
#include "Wire.h"
#include "vl53lx_class.h"

int main(int argc, char **argv)
{
	const char *dev = "/dev/i2c-9";
	int loops = 12;
	int i;
	int follow = 0;

	setvbuf(stdout, NULL, _IOLBF, 0);

	for (i = 1; i < argc; i++) {
		if (strcmp(argv[i], "--follow") == 0 || strcmp(argv[i], "-f") == 0)
			follow = 1;
		else if (argv[i][0] != '-')
			break;
	}
	if (i < argc)
		dev = argv[i++];
	if (i < argc)
		loops = atoi(argv[i]);
	if (follow)
		loops = -1;
	if (!follow && loops < 1)
		loops = 1;

	TwoWire wire(dev);
	wire.begin();

	VL53LX sensor(&wire, -1);
	sensor.begin();

	int st = sensor.InitSensor(0x52);
	if (st != 0) {
		fprintf(stderr, "INIT_FAIL status=%d\n", st);
		return 2;
	}
	st = sensor.VL53LX_StartMeasurement();
	if (st != 0) {
		fprintf(stderr, "START_FAIL status=%d\n", st);
		return 3;
	}

	int got_valid = 0;
	for (i = 0; follow || i < loops; i++) {
		uint8_t ready = 0;
		int t;

		for (t = 0; t < 80; t++) {
			st = sensor.VL53LX_GetMeasurementDataReady(&ready);
			if (st == 0 && ready)
				break;
			delay(5);
		}
		if (!ready) {
			printf("RANGE wait_timeout loop=%d\n", i);
			continue;
		}

		VL53LX_MultiRangingData_t d;
		memset(&d, 0, sizeof(d));
		st = sensor.VL53LX_GetMultiRangingData(&d);
		if (st != 0) {
			printf("RANGE get_fail status=%d loop=%d\n", st, i);
			continue;
		}

		printf("RANGE objs=%u stream=%u\n",
		       d.NumberOfObjectsFound, d.StreamCount);
		int j;
		for (j = 0; j < d.NumberOfObjectsFound; j++) {
			int16_t mm = d.RangeData[j].RangeMilliMeter;
			uint8_t rs = d.RangeData[j].RangeStatus;
			printf("RANGE mm=%d status=%u obj=%d\n",
			       (int)mm, (unsigned)rs, j);
			/* 8191 = no target in ST API; 0 status = valid */
			if (rs == 0 && mm > 0 && mm < 8191)
				got_valid = 1;
		}

		sensor.VL53LX_ClearInterruptAndStartMeasurement();
	}

	return got_valid ? 0 : 4;
}
