# Fairphone 5 — VL53L3 time of flight

Userspace ranger for the rear time-of-flight sensor on Fairphone 5
(Qualcomm SM7325 / sc7280, postmarketOS). The part answers at I2C
`0x29` on bus 9. `IDENTIFICATION__MODEL_ID` is `0xEAAA`, so this is a
VL53L3CX, not a VL53L1X (`0xEACC`).

It is not the STK33562 light and proximity sensor. That part is a
separate device and is not what this tree talks to.

Status: **experimental**. Not upstream. Not an official Fairphone or
distribution package. There is no IIO driver here. The binding and the
board snippet are local drafts and have not been mailed.

## Where this stands

On 2026-08-24 `fp5-tof-range` printed `RANGE mm=11..14 status=0` at a
close target. The kernel was `7.2.0-nfc-test+`. `tof-rail` had enabled
the `VTOF_LDO_2P8` regulator and XSHUT (TLMM 49) was held high. The ToF
node was spliced into the hybrid boot image
`boot-voice2-imx800-cma128-tof.img`.

The same ranger later read about half a metre (`mm=498..507`) and about
2.1 m (`mm=2090..2146`) on 2026-08-25. Those captures are the fixtures
under `tests/fixtures/`.

Mainline `drivers/iio/proximity/vl53l1x-i2c.c` does not range this
silicon. Its model id is `0xEACC`, and on this part the L1X range
register `0x0096` stays `0x0000`. Accepting `0xEAAA` in that driver is
not enough: the L1X config blob does not range an L3. The compatible
for a future series is `st,vl53l3cx`.

## Repository layout

```
fp5-tof-range.cpp   ST ULD ranger (millimetres on stdout)
fp5-tof-live.sh     enable the rail, hold XSHUT, run the ranger
fp5-tof-view.py     GTK4 readout of the live script
fp5_tof.py          parsers and the GPIO allow-list
linux-shim/         small Arduino Wire shim for the ST API
oot/                tof-rail.ko, enables VTOF_LDO_2P8
bindings/           draft st,vl53l3cx binding (not mailed)
third_party/VL53L3CX   STM32duino library, BSD-3-Clause
```

The board draft is `qcm6490-fairphone-fp5-tof.dtsi.snippet`.

## Build

Host or phone. The ranger is C++17. pthread is not required.

```sh
make
python3 tests/test_fp5_tof.py
```

`make` writes `./fp5-tof-range`. The kernel module needs an arm64 tree
that already has the `VTOF_LDO_2P8` regulator:

```sh
make -C oot KDIR=/path/to/kernel
```

## Run

On the phone, after the module is built for the running kernel:

```sh
sudo insmod oot/tof-rail.ko
sudo gpioset -c /dev/gpiochip4 49=1 &
sudo ./fp5-tof-range /dev/i2c-9
```

`fp5-tof-live.sh` does those steps and then runs `fp5-tof-range --follow`.
`fp5-tof-view.py` is a GTK4 window over that script. It needs `sudo -n`.
Point the rear camera island at a wall. Quitting the view unloads
`tof-rail`.

The ranger does not request the NFC reset line. NFC shares this I2C bus.

## License

GPL-2.0-only for the kernel module and the userspace in this tree.
`third_party/VL53L3CX` is BSD-3-Clause. See `LICENSE`.
