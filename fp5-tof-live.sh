#!/bin/sh
# Power VTOF + XSHUT 49, then run fp5-tof-range --follow.
# Never touches NFC reset GPIO 38. Cleanup on exit.
set -eu
RANGER="${FP5_TOF_RANGE:-/usr/local/bin/fp5-tof-range}"
KO="${FP5_TOF_RAIL_KO:-/usr/local/lib/fp5-tof/tof-rail.ko}"
CHIP="${FP5_TOF_GPIOCHIP:-/dev/gpiochip4}"
XSHUT="${FP5_TOF_XSHUT:-49}"
DEV="${1:-/dev/i2c-9}"

if [ ! -x "$RANGER" ]; then
	echo "no ranger at $RANGER" >&2
	exit 1
fi

XSHUT_PID=""
cleanup() {
	if [ -n "$XSHUT_PID" ]; then
		kill "$XSHUT_PID" 2>/dev/null || true
	fi
	pkill -x gpioset 2>/dev/null || true
	rmmod tof-rail 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [ -f "$KO" ]; then
	insmod "$KO" 2>/dev/null || true
fi
# Hold XSHUT high (ACTIVE_LOW reset released). Do not request GPIO 38.
gpioset -c "$CHIP" "$XSHUT"=1 &
XSHUT_PID=$!
sleep 0.4
"$RANGER" --follow "$DEV"
