"""Offline reference encoder for the tested Alpha U / NEO X 1.0.9 host HID path.

No HID or SimPro access occurs here. Never treat its output as a universal wheel
profile: supply your own private SimPro 2 wheel configuration and current 0x90
readback, and follow docs/reproduction.md before any hardware writes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPORT_LENGTH = 241
BUTTON_TARGETS = (4, 5, 6, 7, 0, 1, 2, 3)
PALETTE = {
    0: "off", 1: "red", 2: "orange", 3: "yellow", 4: "green",
    5: "blue", 6: "cyan", 7: "violet", 8: "white", 9: "off (SimPro UI)",
}
FLAG = {0: "inactive", 1: "green", 2: "blue", 3: "yellow", 4: "off", 5: "white"}


def _int_list(value: object, count: int, low: int, high: int, label: str) -> list[int]:
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f"{label}: expected {count} entries")
    if any(type(item) is not int or not low <= item <= high for item in value):
        raise ValueError(f"{label}: entries must be integers in {low}..{high}")
    return value


def validate_readback(raw: bytes) -> None:
    if len(raw) != REPORT_LENGTH or raw[0] != 0x90:
        raise ValueError("expected a complete 241-byte 0x90 readback")
    if raw[235] != 9:
        raise ValueError("tested firmware 1.0.9 expected at readback byte 235")


def writable_equal(a: bytes, b: bytes) -> bool:
    validate_readback(a)
    validate_readback(b)
    return a[1:235] == b[1:235]


def observable_fields_match(canonical: bytes, raw: bytes) -> bool:
    """Partial LED projection seen in the tested readback; NOT full LED proof."""
    validate_readback(canonical)
    validate_readback(raw)
    if canonical[1:51] != raw[1:51] or canonical[231:234] != raw[231:234]:
        return False
    for group in range(2):
        if raw[51 + 5 * group:56 + 5 * group] != bytes([canonical[51 + 5 * group]]) * 5:
            return False
    for led in range(9):
        for group in range(2):
            start = 81 + led * 10 + group * 5
            if raw[start:start + 5] != bytes([canonical[start]]) * 5:
                return False
    return True


def from_reference(raw: bytes, wheel: dict) -> bytes:
    """Reconstruct native write fields from a private SimPro wheel object."""
    validate_readback(raw)
    if not isinstance(wheel, dict):
        raise ValueError("wheel must be the get_config result's wheel object")
    buttons = wheel["button_settings"]
    mappings = _int_list(buttons["mappings"], 40, 0, 255, "mappings")
    # SimPro's generic array has 40 slots, but the native write uses only the
    # first 30. Unused trigger slots can contain values above 15 in real data.
    button_colors = _int_list(buttons["color_index"], 40, 0, 255, "button colors")
    button_triggers = _int_list(buttons["trigger_mode"], 40, 0, 255, "button triggers")
    if any(c > 9 for c in button_colors[:30]) or any(t > 15 for t in button_triggers[:30]):
        raise ValueError("first 30 button colors/triggers outside tested encoding")
    thresholds = _int_list(wheel["rpm_percentage_table"], 10, 0, 100, "RPM thresholds")
    if thresholds != sorted(thresholds, reverse=True):
        raise ValueError("RPM thresholds must be highest to lowest in the SimPro object")
    rows = wheel["rpm_led_settings"]
    if not isinstance(rows, list) or len(rows) != 10:
        raise ValueError("expected ten RPM rows")
    brightness = wheel["brightness"]
    rpm_brightness = wheel["rpmled_brightness"]
    clutch_rate = wheel["clutch_rate"]
    if any(type(v) is not int or not 0 <= v <= 100 for v in (brightness, rpm_brightness)):
        raise ValueError("brightness must be an integer in 0..100")
    if type(clutch_rate) is not int or not 0 <= clutch_rate <= 255:
        raise ValueError("clutch_rate must be one byte")
    if list(raw[1:41]) != mappings:
        raise ValueError("input mapping changed since reference capture")
    if list(raw[41:51]) != thresholds[::-1]:
        raise ValueError("RPM thresholds changed since reference capture")
    if raw[233] != clutch_rate:
        raise ValueError("clutch rate changed since reference capture")

    result = bytearray(raw)
    for i in range(30):
        result[51 + i] = (button_colors[i] << 4) | button_triggers[i]

    rpm_colors: list[list[int]] = []
    for row_index, row in enumerate(rows):
        colors = _int_list(row["color_index"], 15, 0, 9, f"RPM row {row_index} colors")
        flashes = _int_list(row["flash"], 15, 0, 1, f"RPM row {row_index} flash")
        triggers = _int_list(row["trigger_mode"], 15, 0, 7, f"RPM row {row_index} triggers")
        rpm_colors.append(colors)
        for led in range(15):
            color = 0 if colors[led] == 9 else colors[led]
            result[81 + led * 10 + row_index] = (color << 4) | (flashes[led] << 3) | triggers[led]

    # This observed off convention reproduced the verified original readback.
    off_nine = any(
        rpm_colors[row][led] == 9 and raw[81 + led * 10 + row] >> 4 == 9
        for led in range(9) for row in (0, 5)
    )
    if off_nine:
        for row in range(10):
            for led in range(15):
                if rpm_colors[row][led] == 9:
                    offset = 81 + led * 10 + row
                    result[offset] = (result[offset] & 0x0F) | 0x90

    result[231] = brightness
    # Bytes 232 and 233 remain from the validated raw readback.
    result[234] = rpm_brightness
    canonical = bytes(result)
    if not observable_fields_match(canonical, raw):
        raise ValueError("reconstructed reference does not match observable readback fields")
    return canonical


def configuration_reports(canonical: bytes) -> tuple[bytes, bytes, bytes, bytes]:
    validate_readback(canonical)
    parts = []
    for part in range(4):
        report = bytearray(REPORT_LENGTH)
        report[0:2] = bytes((0x91, part))
        for i in range(60):
            source = 1 + part * 60 + i
            if source <= 234:
                report[2 + i] = canonical[source]
        parts.append(bytes(report))
    return tuple(parts)


def with_yellow_flag_button(canonical: bytes, logical_button: int = 1) -> bytes:
    validate_readback(canonical)
    if not 1 <= logical_button <= 8:
        raise ValueError("logical button must be 1..8")
    changed = bytearray(canonical)
    changed[51 + BUTTON_TARGETS[logical_button - 1]] = 0x35
    return bytes(changed)


def telemetry(row: int, rpm: int, percent: int, flag: int) -> bytes:
    if any(type(v) is not int for v in (row, rpm, percent, flag)):
        raise ValueError("telemetry values must be integers")
    if not (0 <= row <= 10 and 0 <= rpm <= 32767 and 0 <= percent <= 100 and flag in FLAG):
        raise ValueError("telemetry value outside tested range")
    report = bytearray(REPORT_LENGTH)
    report[0:2] = b"\x91\x04"
    report[3] = rpm >> 8
    report[4] = rpm & 0xFF
    report[5] = row << 4
    report[6] = 0x10
    report[14] = percent
    report[16] = flag
    return bytes(report)


def select_row(percent: float, thresholds: list[int], running: bool = True) -> int:
    _int_list(thresholds, 10, 0, 100, "RPM thresholds")
    if thresholds != sorted(thresholds, reverse=True):
        raise ValueError("RPM thresholds must be highest to lowest")
    if not running or not 0 <= percent <= 100:
        return 10
    for row, threshold in enumerate(thresholds):
        if percent >= threshold:
            return row
    return 10


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate offline host HID reports; never writes to hardware")
    parser.add_argument("--wheel", type=Path, required=True, help="private get_config wheel object JSON")
    parser.add_argument("--readback", type=Path, required=True, help="private 241-byte 0x90 readback")
    parser.add_argument("--out", type=Path, required=True, help="private output directory")
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        parser.error("output directory must be empty")
    wheel = json.loads(args.wheel.read_text(encoding="utf-8-sig"))
    raw = args.readback.read_bytes()
    baseline = from_reference(raw, wheel)
    flag_config = with_yellow_flag_button(baseline)
    args.out.mkdir(parents=True, exist_ok=True)
    for label, config in (("original", baseline), ("yellow-flag-button-1", flag_config)):
        for part, packet in enumerate(configuration_reports(config)):
            (args.out / f"{label}-config-{part}.bin").write_bytes(packet)
    for label, values in (
        ("idle", (10, 0, 0, 0)),
        ("stage-9", (9, 6000, 76, 0)),
        ("stage-4-yellow-flag", (4, 7000, 88, 3)),
        ("stage-0-yellow-flag", (0, 8000, 99, 3)),
    ):
        (args.out / f"telemetry-{label}.bin").write_bytes(telemetry(*values))
    print("Generated 12 private 241-byte reports. NO HID data was sent.")
    print("Read docs/reproduction.md before attempting a hardware write.")


if __name__ == "__main__":
    main()
