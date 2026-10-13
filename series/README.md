# VL53L3CX series on Linux 7.2.10

Not mailed. Do not send this series. Do not flash a kernel that
contains the Fairphone 5 node while ranging still goes through
i2c-dev. An I2C client at 0x29 reserves that address.

## Base

Linux 7.2.10, commit 7b20d05fd ("Linux 7.2.10"). `git am --3way` of
the v7.2.0-sc7280 series applied with no conflicts. This tree is
kernel.org stable. It has `qcm6490-fairphone-fp5.dts` and the
upstream Raydium RM692E5 panel driver. It does not have the
sc7280-mainline q6voice, IMX800, or FT8722 pieces.

pmaports does not carry an sc7280 7.2.10 package. On origin/main
(2026-10-13) `linux-postmarketos-qcom-sc7280` is 7.2.9-r1.
`linux-postmarketos-stable` is generic 7.2.10.
`linux-postmarketos-mainline` is generic 7.3-rc7.

## Rebase

No conflict. Diffstat matches the v7.2.0-sc7280 series: 6 files,
332 insertions, 3 deletions.

## Checks

`scripts/checkpatch.pl --strict` on each of the three patches:
0 errors, 0 warnings, 0 checks.

`make O=... ARCH=arm64 LLVM=1 dt_binding_check DT_SCHEMA_FILES=Documentation/devicetree/bindings/iio/proximity/st,vl53l0x.yaml`
exited 0. The binding example built.

`make O=... ARCH=arm64 LLVM=1 CHECK_DTBS=1 qcom/qcm6490-fairphone-fp5.dtb`
exited 0. The built DTB has `proximity@29` compatible `st,vl53l3cx`,
interrupt TLMM 48 type 2 (edge falling), reset GPIO 49 active low.
No schema warning mentioned that node.

## Commits

```
511c4feb3 dt-bindings: iio: proximity: document the ST VL53L3CX
625181e81 iio: proximity: add an ST VL53L3CX driver
b138d9b0a arm64: dts: qcom: qcm6490-fairphone-fp5: add the VL53L3CX
```

Local kernel branch `fp5-vl53l3cx-draft` in the 7.2.10 clone. Not pushed
to a kernel remote.
