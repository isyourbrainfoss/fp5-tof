"""ToF helper never touches NFC GPIO 38; parses live i2ctransfer hex."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fp5_tof import (
    NFC_RESET_GPIO,
    TOF_VDD_GPIO,
    TOF_XSHUT_GPIO,
    asserts_nfc_reset_untouched,
    gpio_lines_for_tof,
    is_vl53l3_model,
    l1x_range_is_unusable,
    parse_i2ctransfer_bytes,
    parse_model_id,
    parse_u8,
    parse_u16,
    parse_uld_range_line,
    parse_uld_sample,
)


class GpioPolicy(unittest.TestCase):
    def test_never_requests_gpio_38(self) -> None:
        self.assertNotIn(NFC_RESET_GPIO, gpio_lines_for_tof())
        asserts_nfc_reset_untouched()
        self.assertEqual(NFC_RESET_GPIO, 38)
        self.assertEqual(TOF_XSHUT_GPIO, 49)
        self.assertEqual(TOF_VDD_GPIO, 141)

    def test_tof_rail_c_has_no_gpio_38(self) -> None:
        src = pathlib.Path(__file__).resolve().parents[1] / "oot" / "tof-rail.c"
        text = src.read_text()
        self.assertNotIn("38", text)
        self.assertIn("VTOF_LDO_2P8", text)
        self.assertNotIn("gpiod", text)


class ParseTransfer(unittest.TestCase):
    def test_model_eaaa(self) -> None:
        self.assertEqual(parse_i2ctransfer_bytes("0xea 0xaa\n"), [0xEA, 0xAA])
        mid = parse_model_id("0xea 0xaa")
        self.assertEqual(mid, 0xEAAA)
        self.assertTrue(is_vl53l3_model(mid))
        self.assertFalse(is_vl53l3_model(0xEACC))

    def test_fw_and_zero_range(self) -> None:
        self.assertEqual(parse_u8("0x03"), 0x03)
        self.assertEqual(parse_u16("0x00 0x00"), 0)
        self.assertTrue(l1x_range_is_unusable(0))
        self.assertTrue(l1x_range_is_unusable(None))
        self.assertFalse(l1x_range_is_unusable(12))

    def test_uld_range_line_positive_mm(self) -> None:
        line = "RANGE mm=387 status=0 obj=0\n"
        mm = parse_uld_range_line(line)
        self.assertIsNotNone(mm)
        self.assertGreater(mm, 0)
        self.assertEqual(mm, 387)
        fixture = pathlib.Path(__file__).resolve().parent / "fixtures" / "tof-range-sample.txt"
        live = fixture.read_text()
        parsed = [parse_uld_range_line(ln) for ln in live.splitlines()]
        parsed = [p for p in parsed if p is not None]
        self.assertTrue(parsed)
        self.assertTrue(all(p > 0 for p in parsed))
        self.assertEqual(parsed, [12, 13, 14])
        # L1X dump is not a range
        self.assertTrue(l1x_range_is_unusable(parse_u16("0x00 0x00")))
        self.assertIsNone(parse_uld_range_line("RANGE mm=0 status=0 obj=0"))
        self.assertIsNone(parse_uld_range_line("RANGE mm=8191 status=0 obj=0"))
        self.assertIsNone(parse_uld_range_line("RANGE mm=100 status=255 obj=0"))
        self.assertIsNone(parse_uld_range_line("RANGE mm=-227 status=4 obj=0"))

    def test_uld_wall_fixture_half_metre(self) -> None:
        fixture = pathlib.Path(__file__).resolve().parent / "fixtures" / "tof-range-wall.txt"
        live = fixture.read_text()
        parsed = [parse_uld_range_line(ln) for ln in live.splitlines()]
        valid = [p for p in parsed if p is not None]
        self.assertEqual(valid, [507, 498])
        self.assertTrue(all(300 <= p <= 2000 for p in valid))
        samples = [parse_uld_sample(ln) for ln in live.splitlines()]
        samples = [s for s in samples if s]
        self.assertFalse(samples[0]["valid"])  # status=6
        self.assertTrue(samples[1]["valid"] and samples[1]["mm"] == 507)
        self.assertFalse(samples[-1]["valid"])  # negative / status=4

    def test_uld_far_fixture_two_metres(self) -> None:
        fixture = pathlib.Path(__file__).resolve().parent / "fixtures" / "tof-range-far.txt"
        valid = [
            parse_uld_range_line(ln)
            for ln in fixture.read_text().splitlines()
        ]
        valid = [p for p in valid if p is not None]
        self.assertEqual(valid, [2090, 2146, 2098, 2145])
        self.assertTrue(all(2000 <= p <= 2500 for p in valid))
        self.assertIsNone(parse_uld_range_line("RANGE mm=-60 status=7 obj=0"))

    def test_uld_sample_keeps_invalid_for_ui(self) -> None:
        s = parse_uld_sample("RANGE mm=11 status=6 obj=0")
        self.assertIsNotNone(s)
        self.assertEqual(s["mm"], 11)
        self.assertEqual(s["status"], 6)
        self.assertFalse(s["valid"])
        ok = parse_uld_sample("RANGE mm=12 status=0 obj=0")
        self.assertTrue(ok and ok["valid"] and ok["mm"] == 12)

    def test_follow_flag_in_ranger(self) -> None:
        src = pathlib.Path(__file__).resolve().parents[1] / "fp5-tof-range.cpp"
        text = src.read_text()
        self.assertIn("--follow", text)
        self.assertIn("setvbuf", text)


class MainlineDrafts(unittest.TestCase):
    """Drive the shipped snippet + binding draft; no hardcoded blob copies."""

    @staticmethod
    def _tof_root() -> pathlib.Path:
        return pathlib.Path(__file__).resolve().parents[1]

    def test_snippet_and_binding_draft(self) -> None:
        root = self._tof_root()
        snippet_path = root / "qcm6490-fairphone-fp5-tof.dtsi.snippet"
        binding_path = root / "bindings" / "st,vl53l3cx.yaml"
        snippet = snippet_path.read_text()
        binding = binding_path.read_text()
        combined = f"{snippet}\n{binding}"

        for needle in ("st,vl53l3cx", "interrupts-extended", "vreg_vtof_ldo_2p8"):
            self.assertIn(needle, combined)

        self.assertIn("st,vl53l3cx", snippet)
        self.assertIn("st,vl53l3cx", binding)
        self.assertIn("interrupts-extended", snippet)
        self.assertIn("interrupts-extended", binding)
        self.assertIn("vreg_vtof_ldo_2p8", snippet)
        self.assertIn("vdd-supply", binding)
        self.assertIn("reset-gpios", snippet)
        self.assertIn("reset-gpios", binding)
        self.assertIn("GPIO_ACTIVE_LOW", snippet)
        self.assertIn("tof_default", snippet)

        for bad in ("output-high", "gpio38", "regulator-boot-on", "st,vl53l1x"):
            self.assertNotIn(bad, snippet)
            self.assertNotIn(bad, binding)


if __name__ == "__main__":
    unittest.main()
