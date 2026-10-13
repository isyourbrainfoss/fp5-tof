# Fairphone 5 — VL53L3 time of flight

> **Note**
> This is very experimental. Assume nothing here is written, or necessarily read through or fully understood, by a human unless stated, and that includes this text. Use it at your own risk, but you're encouraged to reuse any parts you find useful. The human work here is mainly ideas, testing in reality, and persistence with a vision.

Userspace ranger for the rear time-of-flight sensor on Fairphone 5
(Qualcomm SM7325 / sc7280). The part is a VL53L3CX. It is not the
STK33562 light and proximity sensor, which is a separate device and is
not what this tree talks to.

Status: **experimental**. Not upstream. Not an official Fairphone or
distribution package. There is no IIO driver here. The binding and the
board snippet are local drafts and have not been mailed.

Ranging that returned millimetres was on kernel `7.2.0-nfc-test+`: a
close target (`mm=11..14` on 2026-08-24), about half a metre
(`mm=498..507`), and about 2.1 m (`mm=2090..2146`) on 2026-08-25. Those
captures are `tests/fixtures/`. An earlier run used the hybrid boot
image `boot-voice2-imx800-cma128-tof.img`, which spliced a node into
the DTB. Luca's 7.2.y DTS still has only the comment `VL53L3 ToF @ 29`.
That is not a working node. The edge kernel package 7.2.9-r0 was not
installed on the phone these ranges were taken on, so 7.2.9 behaviour
is unknown.

## Hardware

Wiring from the Android `dtbo` overlay, checked against a live
`i2ctransfer` on this phone.

| signal | where |
| --- | --- |
| Supply | `VTOF_LDO_2P8`, regulator `vreg_vtof_ldo_2p8`, GPIO 141, 2.8 V. Android name `camera_tof`. |
| Bus | I2C bus 9 (`a84000`), address `0x29`. NFC (`9-0008`) is on the same bus. |
| IRQ | TLMM GPIO 48, edge. Android `intr-gpio`. |
| XSHUT | TLMM GPIO 49. Android `xsdn-gpio`. Active-low reset, held high to run. |

`IDENTIFICATION__MODEL_ID` (`0x010f`) reads `0xEAAA`. A VL53L1X reads
`0xEACC`. Firmware status `0x00E5` reads `0x03`. The L1X range register
`0x0096` stays `0x0000`.

```sh
i2ctransfer -y 9 w2@0x29 0x01 0x0f r2
```

That transfer returned `0xea 0xaa` with the rail on and XSHUT high.

The rail module exists because `VTOF_LDO_2P8` has no sysfs `enable`.
GPIO 141 is hogged by a `regulator-fixed`, so userspace cannot turn the
regulator on through sysfs. `oot/tof-rail.ko` calls
`regulator_enable("VTOF_LDO_2P8")`. Removing the module drops the rail.
The board DTS already had `vreg_vtof_ldo_2p8` and left it unused.

This ranger does not request GPIO 48. With no driver bound, debugfs
showed gpio 48 as an input, high, pull-up. XSHUT is held from
userspace: `gpioset` on `gpiochip4` line 49 = 1. Do not touch NFC reset
GPIO 38. NFC stayed powered across the ranging check that avoided that
line.

Mainline `drivers/iio/proximity/vl53l1x-i2c.c` probes this part and
does not range it. The driver accepts a foreign model id and continues.
The L1X config blob does not range an L3, so teaching that driver the
id `0xEAAA` is not sufficient. `series/` on this branch is that draft rebased onto Linux 7.3-rc7
(commit 24a19b953). The binding keeps Siratul Islam's address
siratul.islam@linux.dev. `st,vl53l3cx` stays on the existing
`st,vl53l0x.yaml` binding. The driver checks model id `0xEAAA` and
does not range yet. It has not been mailed. The v7.2.0-sc7280 copy
remains on `mainline-draft`.
`bindings/st,vl53l3cx.yaml` and
`qcm6490-fairphone-fp5-tof.dtsi.snippet` are the earlier separate
drafts.

## Reproduce

Host or phone. The ranger is C++17. pthread is not required.

```sh
make
python3 tests/test_fp5_tof.py
```

`make` writes `./fp5-tof-range`. The kernel module needs an arm64 tree
that already contains the `VTOF_LDO_2P8` regulator, built for the
running kernel:

```sh
make -C oot KDIR=/path/to/kernel
```

On the phone:

```sh
sudo insmod oot/tof-rail.ko
sudo gpioset -c /dev/gpiochip4 49=1 &
sudo ./fp5-tof-range /dev/i2c-9
```

`fp5-tof-live.sh` enables the rail, holds XSHUT, and runs
`fp5-tof-range --follow`.

## Demo

`fp5-tof-view.py` is a GTK4 window over `fp5-tof-live.sh`. It needs
`sudo -n`. Quitting the window unloads `tof-rail`.

## Layout

```
fp5-tof-range.cpp   ST ULD ranger (millimetres on stdout)
fp5-tof-live.sh     enable the rail, hold XSHUT, run the ranger
fp5-tof-view.py     GTK4 readout of the live script
fp5_tof.py          parsers and the GPIO allow-list
linux-shim/         small Arduino Wire shim for the ST API
oot/                tof-rail.ko, enables VTOF_LDO_2P8
bindings/           earlier separate st,vl53l3cx binding (not mailed)
series/             mainline draft against v7.2.0-sc7280 (not mailed)
third_party/VL53L3CX   STM32duino library, BSD-3-Clause
```

## License

GPL-2.0-only for the kernel module and the userspace in this tree.
`third_party/VL53L3CX` is BSD-3-Clause. See `LICENSE`.
