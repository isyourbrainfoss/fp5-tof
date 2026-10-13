# VL53L3CX mainline draft

Not mailed. Do not send this series. Do not flash a kernel that
contains the Fairphone 5 node while ranging still goes through
i2c-dev. An I2C client at 0x29 reserves that address.

## Base

sc7280-mainline tag v7.2.0-sc7280, commit f875148cc9fc
("fixup! drivers: gpu: drm: panel: Initial FT8722 support").
Apply with `git am` from that commit. The patches were produced from
a clean worktree of that commit. The local kernel branch is
`fp5-vl53l3cx-draft` and is not pushed.

The clean `&i2c9` in that tree is the NFC comment and the old VL53L3
comment. A tree that already has an NFC child on `&i2c9` will not
apply patch 3 cleanly.

## Decision

The part is a VL53L3CX, model id 0xEAAA, not a VL53L1X (0xEACC).
Mainline `vl53l1x-i2c.c` loads the 91-byte VL53L1X configuration and
does not fail probe on a foreign id. That configuration does not range
this silicon. The ST VL53LX API in userspace does.

The series does not extend the VL53L1X driver and does not paste the
ULD. It adds:

1. `st,vl53l3cx` on the existing `st,vl53l0x.yaml` binding, with
   `vdd-supply` required, matching how `st,vl53l1x` was added.
   `bindings/st,vl53l3cx.yaml` in this repo is the earlier separate
   draft. The series does not add that file upstream.
2. `vl53l3cx-i2c`: enable vdd, release XSHUT, accept only model id
   0xEAAA. `read_raw` returns `-EOPNOTSUPP`.
3. The Fairphone 5 node. The 2.8 V rail is already `regulator-fixed`
   on TLMM GPIO 141. IRQ is GPIO 48, XSHUT is GPIO 49. No
   `regulator-boot-on`. No `output-high` on the enable pin.

Ranging stays in userspace (`fp5-tof-range`) until the VL53L3CX
sequence is ported into that IIO `read_raw`.

## Checks

`scripts/checkpatch.pl --strict` on the three patches: 0 errors,
0 warnings, 0 checks. `spdxcheck.py` could not import `ply`, so that
helper printed a traceback and did not parse the SPDX line. checkpatch
still reported the driver patch ready for submission.

`make ARCH=arm64 LLVM=1 dt_binding_check DT_SCHEMA_FILES=Documentation/devicetree/bindings/iio/proximity/st,vl53l0x.yaml`
passed. The binding example built.

`make ARCH=arm64 LLVM=1 CHECK_DTBS=1 qcom/qcm6490-fairphone-fp5.dtb`
against the full processed schema (about 27 MB, 5671 schema ids)
printed two pre-existing warnings: the lpass tx-macro compatible, and
`sony,imx858` matching no schema. Nothing about `proximity@29` or
`st,vl53l3cx`. make exited 0. Schema warnings do not fail the build.

`ARCH=arm64 LLVM=1` compiled `drivers/iio/proximity/vl53l3cx-i2c.o`
and built `qcm6490-fairphone-fp5.dtb` (152718 bytes). The `.ko` was
not linked: that output directory has no `vmlinux.o`, so modpost
reported undefined core symbols. Not flashed.

## Commits

```
3734217b8 dt-bindings: iio: proximity: document the ST VL53L3CX
b1fdb97e3 iio: proximity: add an ST VL53L3CX driver
ec4f97b3c arm64: dts: qcom: qcm6490-fairphone-fp5: add the VL53L3CX
```

## Files

```
0000-cover-letter.patch
0001-dt-bindings-iio-proximity-document-the-ST-VL53L3CX.patch
0002-iio-proximity-add-an-ST-VL53L3CX-driver.patch
0003-arm64-dts-qcom-qcm6490-fairphone-fp5-add-the-VL53L3C.patch
```
