"""Fairphone 5 ToF (VL53L3) lab helpers.

VTOF is GPIO 141 via regulator-fixed VTOF_LDO_2P8. XSHUT is TLMM 49.
NFC reset is TLMM 38 on the same I2C adapter — this module must never
request GPIO 38.

Not for lore. Do not mail st,vl53l1x while L1X range stays 0.
"""

from __future__ import annotations

import re

# TLMM lines. 38 is NFC reset — do not use.
TOF_XSHUT_GPIO = 49
TOF_VDD_GPIO = 141
NFC_RESET_GPIO = 38

I2C_BUS = 9
TOF_ADDR = 0x29
REG_MODEL_ID = 0x010F
REG_FW_STATUS = 0x00E5
REG_L1X_RANGE_MM = 0x0096

MODEL_VL53L3 = 0xEAAA
MODEL_VL53L1X = 0xEACC


def gpio_lines_for_tof() -> tuple[int, ...]:
    """GPIOs this lab path may touch (never NFC reset)."""
    return (TOF_XSHUT_GPIO, TOF_VDD_GPIO)


def asserts_nfc_reset_untouched() -> None:
    if NFC_RESET_GPIO in gpio_lines_for_tof():
        raise AssertionError("ToF helper must not request NFC reset GPIO 38")


def parse_i2ctransfer_bytes(text: str) -> list[int]:
    """Parse ``i2ctransfer`` hex stdout like ``0xea 0xaa`` into ints."""
    out: list[int] = []
    for tok in (text or "").replace(",", " ").split():
        t = tok.strip().lower()
        if t.startswith("0x"):
            out.append(int(t, 16))
        elif re.fullmatch(r"[0-9a-f]{2}", t):
            out.append(int(t, 16))
    return out


def parse_model_id(text: str) -> int | None:
    """Two-byte big-endian model ID from i2ctransfer of register 0x010F."""
    b = parse_i2ctransfer_bytes(text)
    if len(b) < 2:
        return None
    return (b[0] << 8) | b[1]


def parse_u16(text: str) -> int | None:
    b = parse_i2ctransfer_bytes(text)
    if len(b) < 2:
        return None
    return (b[0] << 8) | b[1]


def parse_u8(text: str) -> int | None:
    b = parse_i2ctransfer_bytes(text)
    if not b:
        return None
    return b[0]


def is_vl53l3_model(model_id: int | None) -> bool:
    return model_id == MODEL_VL53L3


def l1x_range_is_unusable(range_mm: int | None) -> bool:
    """True when the mainline VL53L1X range register did not produce a range."""
    return range_mm is None or int(range_mm) == 0


def parse_uld_sample(text: str) -> dict | None:
    """Parse one ``RANGE mm=… status=…`` line for the live view.

    Returns mm/status/obj/valid. ``valid`` is ST status 0 and 1..8190 mm.
    Invalid samples are still returned so a UI can show them.
    """
    m = re.search(r"RANGE mm=(-?\d+)\s+status=(\d+)(?:\s+obj=(\d+))?", text or "")
    if not m:
        return None
    mm = int(m.group(1))
    status = int(m.group(2))
    obj = int(m.group(3) or 0)
    valid = status == 0 and 0 < mm < 8191
    return {"mm": mm, "status": status, "obj": obj, "valid": valid}


def parse_uld_range_line(text: str) -> int | None:
    """Parse ``RANGE mm=<n> status=<s> ...`` from ``fp5-tof-range``.

    Accepts a valid ST range (status 0, 1..8190 mm). Rejects L1X-style
    zero dumps and the ST 'no target' sentinel 8191.
    """
    sample = parse_uld_sample(text)
    if not sample or not sample["valid"]:
        return None
    return int(sample["mm"])
