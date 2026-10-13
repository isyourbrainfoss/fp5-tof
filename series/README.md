# VL53L3CX series on Linux 7.3-rc7

Not mailed. Do not send this series. Do not flash a kernel that
contains the Fairphone 5 node while ranging still goes through
i2c-dev. An I2C client at 0x29 reserves that address.

## Base

Linux 7.3-rc7, commit 24a19b953 ("Linux 7.3-rc7"). This is the
mainline base for a later submission. pmaports carries the same
tag as `linux-postmarketos-mainline` (generic). That package, and
this tree, do not have the sc7280-mainline q6voice, IMX800, or
FT8722 pieces. The Fairphone 5 DTS uses the upstream Raydium
RM692E5 panel compatible.

## Rebase

`git am --3way` failed on patch 1. The clone is depth 1, so git
could not build a fake ancestor for `st,vl53l0x.yaml`, and the
context does not match: Siratul Islam's address in that file is
`siratul.islam@linux.dev` (it was `email@sirat.me` on the 7.2.0
draft). `git am --abort` left the tree clean. The binding change
was applied by hand and keeps the current address. The driver
patch and the DTS patch then applied with no further conflict
(`git apply --check` on the DTS was clean before commit).

Diffstat is 6 files, 333 insertions, 3 deletions. The Kconfig and
driver text match the 7.2.10 series. The extra inserted line is in
the binding allOf, because v7.3-rc7 required vdd with
`const: st,vl53l1x` and this series uses an enum of `st,vl53l1x`
and `st,vl53l3cx`.

## Checks

`scripts/checkpatch.pl --strict` on each of the three patches:
0 errors, 0 warnings, 0 checks.

`make O=... ARCH=arm64 LLVM=1 dt_binding_check DT_SCHEMA_FILES=Documentation/devicetree/bindings/iio/proximity/st,vl53l0x.yaml`
exited 0. The binding example built.

`make O=... ARCH=arm64 LLVM=1 CHECK_DTBS=1 qcom/qcm6490-fairphone-fp5.dtb`
exited 0. The built DTB has `proximity@29` compatible `st,vl53l3cx`.
No schema warning mentioned that node.

## Commits

```
3c6cd9868 dt-bindings: iio: proximity: document the ST VL53L3CX
bad3b004b iio: proximity: add an ST VL53L3CX driver
2fe34ed7d arm64: dts: qcom: qcm6490-fairphone-fp5: add the VL53L3CX
```

Local kernel branch `fp5-vl53l3cx-draft` in the 7.3-rc7 clone. Not pushed
to a kernel remote.
