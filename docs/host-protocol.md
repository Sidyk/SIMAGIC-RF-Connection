# Host-side protocol notes (Alpha U + NEO X 1.0.9)

These offsets describe **Windows HID feature reports between the PC and the Alpha U base**. They are derived from read-only analysis of the installed SimPro 2 build `V2.1.8.2361-e52c6dee`, recorded HID responses, and controlled physical LED tests. They are **not** nRF24 packet offsets or decoded ACK payloads. Do not apply them to other hardware or firmware without a fresh capture.

## Interface and report families

The tested base interface was VID `0483`, PID `0522`; the maximum feature report length was 241 bytes. SimPro 2 uses `HID.DLL!HidD_SetFeature` for the following observed report families:

| Report bytes | Observed role |
| --- | --- |
| `91 00` to `91 03` | Four configuration parts, each with up to 60 data bytes from one canonical configuration buffer |
| `91 04` | Live game telemetry: RPM, stored-stage selection, FLAG and other fields |
| `80 05 BB BB` | Request used before reading the wheel's configuration view |
| `90 ...` | 241-byte feature response after the read request; **lossy view, not a write template** |

For each of the four configuration parts, byte 0 of the HID report is `0x91`, byte 1 is the part number `0`–`3`, and bytes 2–61 carry up to 60 bytes from the canonical configuration. The remaining bytes of the 241-byte feature report are padding. The write buffer positions below include its leading `0x91` byte and are **zero-based**. The four-part sender uses source positions `1 + part*60` through `60 + part*60`; positions beyond 234 are written as zero. In particular, the readback's firmware byte 235 must not be copied into a write.

## Canonical configuration buffer

| Position(s) | Observed meaning |
| --- | --- |
| 1–40 | Input mappings (40 slots) |
| 41–50 | Ten RPM percentage thresholds, in reverse order relative to the SimPro API array |
| 51–80 | Thirty button/lighting slots: `(palette_color << 4) | trigger_mode` |
| 81–230 | 150 RPM values, addressed by `81 + led*10 + row`; ten rows for each of 15 protocol LED slots. Value: `(palette_color << 4) | (flash << 3) | trigger_mode` |
| 231 | Button brightness |
| 232 | Clutch mode plus another bit (not fully decoded) |
| 233 | Clutch rate |
| 234 | RPM brightness |
| 235–240 | Zero in the observed native write buffer; byte 235 in a `0x90` *read* response represented firmware 1.0.9 as `9` |

The container has 15 RPM slots per row and 30 button slots, but the tested NEO X has **nine physical RPM LEDs**. Container size is not a count of addressable physical lights. In the bridge's eight primary button channels, the observed protocol index order was `4, 5, 6, 7, 0, 1, 2, 3` for logical buttons 1–8. Physical left/right placement was checked by the observer; other channels need separate verification.

## Telemetry report `91 04`

The observed logical telemetry report starts with `0x91, 0x04`. Within that report, RPM is carried in byte 3's low seven bits plus byte 4, the stored RPM stage in byte 5's high nibble, RPM percentage in byte 14, and a FLAG value in byte 16. An idle stage value of 10 was observed; the saved lighting table has rows 0–9. The packet also contains other game data, including gear, that is not fully specified here. Zeroing unknown fields is **not** a general safe recipe for all devices or games.

Our controlled test selected stored RPM rows and one FLAG-triggered button through this path. The observer saw the pattern physically via Alpha U RF. That supports the behavior of the *whole PC-to-base-to-rim path* for this configuration; it does not reveal the RF translation performed inside the base.

## Readback and restoration limitation

SimPro 2 requests a configuration read with feature bytes `80 05 BB BB`, waits about 200 ms in the observed routine, then reads feature report ID `0x90` (241 bytes). In a controlled read, two raw responses matched each other, but 153 of 233 candidate fields differed from the SimPro API's canonical fields, mostly LED fields. A later direct-copy write from this raw readback failed the expected readback comparison. The raw response is therefore **not an invertible copy of the write configuration**.

The read view appeared to repeat sampled values across groups of five button slots and across halves of each ten-row RPM group. This is an observation on the tested firmware, not a general rule. A recovery did reconstruct a canonical write from saved SimPro fields while preserving input mappings, thresholds and clutch settings, then verified the original 241-byte readback. That successful reconstruction does not make arbitrary readback-to-write conversion safe. We also observed both palette codes `0` and `9` being used to represent off in different contexts.

## What remains unknown at the RF layer

We have no direct capture of the Alpha U radio-module SPI lines or the base-to-rim ACK payloads. We cannot yet say whether `91 04` is forwarded, compressed, translated into an ACK payload, or acted on through another internal schedule. Kegetys' [Simagic wireless research](https://github.com/Kegetys/simagic-arduino-poc) documents a separate rim/base radio layer and leaves the LED reply format open. The host HID offsets here are intended to help correlate a future USB trace with a simultaneous radio trace.
