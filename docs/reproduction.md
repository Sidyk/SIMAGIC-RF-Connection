# Reproducing the host-side LED observations

This is a procedure for reproducing the **PC USB → Alpha U → RF → NEO X** observations on the same tested setup. It is not a ready-to-run SimHub plugin, an RF packet implementation, or a verified recipe for other firmware. The report layout and limitations are in [host-protocol.md](host-protocol.md).

## Tested prerequisites

- Windows PC, Alpha U connected by USB, NEO X mounted by RF, wheel firmware **1.0.9**.
- SimPro 2 build **V2.1.8.2361-e52c6dee** for capturing the wheel's own settings; the experimental SimHub integration was tested with **SimHub 9.11.9**.
- One HID interface matching VID `0483`, PID `0522`, with a 241-byte maximum feature report. Select the exact device path found on the test PC; a VID/PID match alone does not identify the rim or prove an RF connection.
- A HID library that can send and receive Windows feature reports (our local experiment used HidSharp). Keep SimPro fully closed, including its tray/background process, before any direct HID output. SimHub or another LED controller must also stop writing to this interface.

## 1. Capture a canonical reference while SimPro 2 owns the wheel

SimPro 2 exposed a local JSON-RPC endpoint at `http://127.0.0.1:56789/jsonrpc` in our test. Requests were HTTP POST with `Content-Type: application/json`. The following **read-only** request shapes were observed:

```json
{"id":1,"jsonrpc":"2.0","method":"query","params":{"items":["devices"]}}
{"id":1,"jsonrpc":"2.0","method":"get_config","params":{"items":["wheel"]}}
```

Check `devices.wheel.name == "Neo X"`, `devices.wheel.connect_mode == "RF"`, `devices.wheel.firmware_version == "1.0.9"`, and `devices.base.product_id == "1314"`. Save the returned `wheel` configuration privately, including all 40 input mappings, all 40 button colors and trigger modes, ten RPM thresholds, ten 15-slot RPM rows, both brightness values and clutch fields. **Do not publish a personal settings dump as a universal device profile.** These settings are the basis for reconstructing the writable configuration and restoring this particular wheel.

## 2. Read and validate the base before writing

Exit SimPro 2 completely. Open only the saved Alpha U HID path. Send a 241-byte feature report with bytes `80 05 BB BB` at positions 0–3 and zeros elsewhere. In our observed routine, wait about 200 ms, then request feature report ID `0x90` into a 241-byte buffer. Read it twice and require both responses to agree on the writable fields. The firmware indicator at readback byte 235 was `9` for the tested 1.0.9 wheel.

Before the first write, compare readback bytes 1–40 with the captured mappings, bytes 41–50 with the **reversed** captured RPM thresholds, and byte 233 with captured clutch rate. Reject changed settings. Keep both the raw readback and the canonical configuration described below in a durable recovery journal. Do not start if an earlier journal is still pending.

The `0x90` response is **lossy for LED settings**. It cannot simply be changed from report ID `0x90` to `0x91` and replayed. Our tests found repeated/sampled LED values in its read view.

## 3. Reconstruct the writable configuration

Build a 241-byte canonical buffer from the **captured SimPro fields**, using the current validated readback only for fields that must remain intact. Its leading byte is `0x90` for the local validation representation; the four transmitted parts use report ID `0x91`. All positions below are zero-based:

| Canonical positions | Value source |
| --- | --- |
| 1–40 | Captured input mappings |
| 41–50 | Ten captured RPM thresholds, reversed |
| 51–80 | First 30 button entries: `(color_index << 4) | trigger_mode` |
| 81–230 | RPM entry at `81 + led*10 + row` for 15 LED slots × 10 rows: `(color_index << 4) | (flash << 3) | trigger_mode` |
| 231 | Captured button brightness |
| 232–233 | Preserve current clutch mode/other bit and clutch rate |
| 234 | Captured RPM brightness |
| 235–240 | Zero on transmission; never copy readback firmware byte 235 |

The observed palette indexes were `0` off, `1` red, `2` orange, `3` yellow, `4` green, `5` blue, `6` cyan, `7` violet and `8` white. Some SimPro fields used `9` for off while one physical baseline used `0`; preserve the convention verified on the particular wheel. The eight main SimHub button positions map to protocol button indexes `4,5,6,7,0,1,2,3`. The two independently confirmed encoder rings are logical channels 9 and 10. There are nine physical RPM LEDs, despite 15 storage slots per row.

Split canonical source positions `1 + 60*part` through `60 + 60*part` into four 241-byte feature reports. Each starts `91 00`, `91 01`, `91 02` or `91 03`; source bytes occupy transmitted positions 2–61, and unused positions are zero. Send the parts in order. A successful host write is **not** proof of RF receipt or a visible LED change.

## 4. Select saved RPM stages and a hardware FLAG

Configure the ten stored RPM rows before runtime, using the normal write procedure above. In the controlled test, the wheel's own saved rows 9, 4 and 0 were selected in sequence. For a FLAG on the first logical button, protocol button index 4 (canonical byte 55) was set to `0x35`: yellow palette `3` with FLAG trigger mode `5`.

For each runtime update, send a **241-byte** `91 04` feature report. Our tested minimal logical fields were:

| Byte | Value |
| --- | --- |
| 0–1 | `91 04` |
| 3–4 | RPM, high byte then low byte (tested range 0–32767) |
| 5 high nibble | Selected row `0`–`9`; `10` was the observed idle/off row |
| 6 | `0x10` in our minimal test report |
| 14 | RPM percentage, 0–100 |
| 16 | FLAG: `0` inactive; observed codes `1` green, `2` blue, `3` yellow, `4` off, `5` white |

Other telemetry fields were left at zero **only for this controlled LED test**. This is not a complete game telemetry specification. The test sent the following three states at roughly 50 ms intervals for four seconds each: `(row 9, 6000 RPM, 76%, FLAG 0)`, `(row 4, 7000 RPM, 88%, FLAG 3)`, `(row 0, 8000 RPM, 99%, FLAG 3)`. The observer saw one RPM LED, then about six, then redline, while the yellow FLAG animated on the selected button. Those exact pictures depend on the captured row colors. For live SimHub use, choose the first saved threshold at or below the normalized RPM percentage, with thresholds ordered highest to lowest; use idle row 10 when game telemetry is invalid or below all thresholds.

The hardware FLAG mechanism has one shared FLAG value in this report. Selecting a button requires a compatible FLAG trigger in its saved configuration. Independent per-button blink phase or arbitrary SimHub RPM LED frames were not demonstrated by this path.

## 5. Restore and verify

Send idle telemetry (row 10, RPM 0, percent 0, FLAG 0), then the four original **canonical** configuration parts, wait for the base to settle (our implementation waited one second), and send idle telemetry again. Re-read configuration using `80 05 BB BB` / `0x90`. In the successful recovery test, writable readback positions 1–234 matched the original raw readback. Only then remove the recovery journal. If the current mapping, thresholds or clutch fields changed, or readback differs after restoration, retain the journal and stop; do not overwrite a changed profile blindly.

The readback is sampled/lossy for LED fields, so this verification does not establish every individual LED's color. Observe the physical wheel and compare its original profile as a separate check. A stopped or unplugged base can defer recovery.

## What this repository does not yet provide

There is no published, buildable bridge source or installer, no sanitized reference fixture or automated hardware test, and no decoded base-to-rim RF/ACK payload. The procedure above is sufficient to **implement and test the same host-side approach on the specified setup**, but it is not a turnkey reproduction of our SimHub UI or a guarantee that the wheel will react identically on other firmware. The original experimental plugin was removed from the local SimHub installation; the local source project was left untouched.
