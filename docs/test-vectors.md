# Worked host-report examples

Every byte position on this page is **zero-based** and refers to the 241-byte Windows HID feature report or canonical host buffer. These are PC ↔ Alpha U values, **not RF or ACK payloads**. Unlisted positions in the minimal telemetry samples are zero. Configuration fields not shown here depend on the reader's own captured wheel profile and must not be replaced with zeros.

## Four configuration parts

The canonical local buffer has 241 bytes and begins with `0x90` only because it was based on a `0x90` readback. That first byte is **never copied** to a configuration part. The four sent reports are:

| Part | Sent bytes 0–1 | Canonical source positions copied to sent positions 2–61 |
| --- | --- | --- |
| 0 | `91 00` | 1–60 |
| 1 | `91 01` | 61–120 |
| 2 | `91 02` | 121–180 |
| 3 | `91 03` | 181–234, followed by six zeros |

All four reports are 241 bytes; positions after 61 are zero. The last six source positions 235–240 are also transmitted as zero. Readback position 235 can contain the observed firmware indicator `9`; it is **not** a writable configuration field.

For the tested yellow FLAG on logical button 1, the physical button maps to protocol button index 4. Its canonical offset is `51 + 4 = 55`; the test value is `0x35`, meaning palette index `3` (yellow) and trigger mode `5` (FLAG). It appears at **sent part 0, byte 56**, because the part adds one prefix byte before source position 1.

As an **illustration**, if RPM row 0 uses nine fixed colors `green, green, green, yellow, yellow, yellow, red, red, red`, with flash and trigger bits clear, its first nine LED values are:

| Physical RPM LED | Canonical offset `81 + led*10 + row` | Example byte |
| --- | --- | --- |
| 1 | 81 | `0x40` |
| 2 | 91 | `0x40` |
| 3 | 101 | `0x40` |
| 4 | 111 | `0x30` |
| 5 | 121 | `0x30` |
| 6 | 131 | `0x30` |
| 7 | 141 | `0x10` |
| 8 | 151 | `0x10` |
| 9 | 161 | `0x10` |

This example is **not** a complete valid configuration report. The remaining mappings, clutch fields, thresholds, colors and brightness must come from the wheel's own validated profile. In the physical 3/3/3 trial, the pattern was temporarily applied to all ten saved rows, then the original canonical configuration was restored.

## Minimal `91 04` telemetry samples

The controlled stage test sent each of these reports repeatedly at roughly 50 ms intervals for about four seconds. For each row, all **unlisted** bytes are zero; byte 6 is `0x10` in this minimal test. The table shows the nonzero and structural positions through byte 16:

| Phase | Row | RPM | Percent | FLAG | Bytes 0–6 | Byte 14 | Byte 16 |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Idle | 10 | 0 | 0 | 0 | `91 04 00 00 00 A0 10` | `00` | `00` |
| First stage | 9 | 6000 | 76 | 0 | `91 04 00 17 70 90 10` | `4C` | `00` |
| Middle stage | 4 | 7000 | 88 | 3 | `91 04 00 1B 58 40 10` | `58` | `03` |
| Redline stage | 0 | 8000 | 99 | 3 | `91 04 00 1F 40 00 10` | `63` | `03` |

The physical observer saw one RPM LED, then about six, then redline with a yellow FLAG animation. This result depended on that wheel's captured stage colors. The logical stage byte in these samples is **selected directly**; the separate percentage field does not by itself prove that the base chooses a stage from the thresholds. The bridge chose the row on the PC side from its stored descending thresholds.

## Flag values and button palette

The corrected physical FLAG observations were `1` green, `2` blue, `3` yellow, `4` off and `5` white. An earlier bridge UI confused blue and yellow; the corrected mapping is the one used here. `0` means inactive. FLAG value is a **single shared byte** in the telemetry report. Buttons configured with trigger mode 5 can respond; buttons left in static mode retain their ordinary palette color.

Palette index and FLAG value are distinct concepts. The palette is `0` off, `1` red, `2` orange, `3` yellow, `4` green, `5` blue, `6` cyan, `7` violet, `8` white; `9` also appeared as off in SimPro fields. The visual RGB values in the SimPro 2 UI were approximations for rendering the fixed palette, not arbitrary per-channel RGB values delivered over this route.

## Offline check

Run `python -m unittest discover -s examples -p 'test_*.py'` from the repository root. The tests verify the part boundaries, the button/FLAG byte, the telemetry vector and refusal of changed mappings or unsupported firmware. They use synthetic data and never access the wheel. The [encoder](../examples/host_codec.py) can generate complete reports from a **private** SimPro wheel object plus a matching private `0x90` readback; it performs no HID writes.

During preparation of this public example, we also compared the encoder's **entire 241-byte canonical output** with a private, previously verified recovery fixture from our 2026-11-03 experiment; it matched byte for byte. That private profile and raw device readback are not published because they include the user's wheel-specific settings. This offline match supports the packing algorithm, while only the original physical trials support claims about LEDs on the rim.
