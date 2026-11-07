"""Synthetic, offline tests. No wheel profile or HID device is required."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from host_codec import (
    configuration_reports,
    from_reference,
    select_row,
    telemetry,
    with_yellow_flag_button,
    writable_equal,
)


class HostCodecTests(unittest.TestCase):
    def setUp(self):
        self.thresholds = [98, 93, 91, 90, 88, 86, 84, 81, 78, 74]
        self.wheel = {
            "button_settings": {
                "mappings": list(range(40)),
                "color_index": [0] * 40,
                "trigger_mode": [0] * 34 + [193, 244, 138, 2, 0, 0],
            },
            "rpm_percentage_table": self.thresholds,
            "rpm_led_settings": [
                {"color_index": [0] * 15, "flash": [0] * 15, "trigger_mode": [0] * 15}
                for _ in range(10)
            ],
            "brightness": 50,
            "rpmled_brightness": 60,
            "clutch_rate": 25,
        }
        raw = bytearray(241)
        raw[0] = 0x90
        raw[1:41] = bytes(range(40))
        raw[41:51] = bytes(self.thresholds[::-1])
        raw[231] = 50
        raw[232] = 0x12
        raw[233] = 25
        raw[234] = 1  # Readback can differ from the canonical API brightness.
        raw[235] = 9
        self.raw = bytes(raw)

    def test_four_parts_and_flag_button(self):
        original = from_reference(self.raw, self.wheel)
        self.assertEqual(original[234], 60)
        self.assertEqual(original[232], 0x12)
        changed = with_yellow_flag_button(original)
        self.assertEqual(changed[55], 0x35)
        parts = configuration_reports(changed)
        self.assertEqual(len(parts), 4)
        self.assertTrue(all(len(part) == 241 for part in parts))
        self.assertEqual([part[:2] for part in parts], [b"\x91\x00", b"\x91\x01", b"\x91\x02", b"\x91\x03"])
        self.assertEqual(parts[0][56], 0x35)  # Source byte 55 becomes report byte 56.
        self.assertEqual(parts[3][2 + (234 - 181)], 60)
        self.assertEqual(parts[3][2 + (235 - 181)], 0)

    def test_telemetry_vector_and_stage_order(self):
        frame = telemetry(4, 7000, 88, 3)
        self.assertEqual(len(frame), 241)
        self.assertEqual(frame[:7], bytes([0x91, 4, 0, 0x1B, 0x58, 0x40, 0x10]))
        self.assertEqual(frame[14], 88)
        self.assertEqual(frame[16], 3)
        self.assertEqual(select_row(99, self.thresholds), 0)
        self.assertEqual(select_row(88, self.thresholds), 4)
        self.assertEqual(select_row(70, self.thresholds), 10)
        self.assertEqual(select_row(99, self.thresholds, running=False), 10)

    def test_refuses_changed_controls(self):
        raw = bytearray(self.raw)
        raw[15] ^= 1
        with self.assertRaisesRegex(ValueError, "mapping changed"):
            from_reference(bytes(raw), self.wheel)
        self.assertFalse(writable_equal(self.raw, bytes(raw)))

    def test_refuses_unsupported_firmware(self):
        raw = bytearray(self.raw)
        raw[235] = 10
        with self.assertRaisesRegex(ValueError, "firmware"):
            from_reference(bytes(raw), self.wheel)

    def test_cli_generates_private_frames_without_hid(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            wheel = root / "wheel.json"
            readback = root / "readback.bin"
            output = root / "frames"
            wheel.write_text(json.dumps(self.wheel), encoding="utf-8")
            readback.write_bytes(self.raw)
            script = Path(__file__).with_name("host_codec.py")
            completed = subprocess.run(
                [sys.executable, str(script), "--wheel", str(wheel), "--readback", str(readback), "--out", str(output)],
                capture_output=True, text=True, check=True,
            )
            self.assertIn("NO HID data was sent", completed.stdout)
            self.assertEqual(len(list(output.glob("*.bin"))), 12)
            self.assertEqual((output / "telemetry-stage-4-yellow-flag.bin").read_bytes(), telemetry(4, 7000, 88, 3))


if __name__ == "__main__":
    unittest.main()
