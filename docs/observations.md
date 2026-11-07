# Observations and evidence

## 1. Brightness and button colors through SimPro 2

SimPro 2 exposes a local JSON-RPC API at `http://127.0.0.1:56789/jsonrpc`. On the tested NEO X + Alpha U pair, `query` for `devices` reported the wheel in `RF` mode. `get_config` for `wheel` returned lighting configuration. A `set_config` update of `wheel.brightness` from 100 to 20 and back was accepted, read back, and visibly dimmed then restored the button LEDs. A temporary change of one `button_settings.color_index` also changed one physical button and was restored.

The `button_settings` object must retain its existing `mappings` and `trigger_mode` fields when submitted; sending only `color_index` failed. Readback of a whole wheel configuration can contain placeholders and is not a safe byte-for-byte restoration strategy.

## 2. PC-to-base HID reports

Read-only analysis of the installed SimPro 2 binary and local HID enumeration found a base interface at VID `0483`, PID `0522`, with 39-byte input, 64-byte output, and 241-byte maximum feature reports. The legacy sender reaches `HID.DLL!HidD_SetFeature`. The observed PC-side report families are:

| Prefix | Observed purpose | Confidence |
| --- | --- | --- |
| `91 00`–`91 03` | Four-part lighting/configuration write | Reproduced in controlled tests |
| `91 04` | Live telemetry including RPM stage and FLAG | Reproduced in controlled tests |

In the observed `91 04` logical packet, RPM uses byte 3's low seven bits and byte 4; the stage index uses byte 5's high nibble; RPM percentage uses byte 14; FLAG uses byte 16. **Byte numbers here count from the first byte of the logical report, starting at zero.** They are not radio packet offsets. Other fields exist and have not been fully documented in this repo. The currently described values should be treated as specific to the tested legacy implementation.

The ten stored RPM rows are *stages*, while the NEO X has nine physical RPM LEDs. An idle stage value of 10 is outside those ten stored rows. Changing only the stored thresholds did not illuminate the strip in our initial trial; an active telemetry report was needed.

## 3. Physical RPM and FLAG tests

For a controlled pattern, each RPM row's first nine entries was temporarily configured as 3 green / 3 yellow / 3 red. An eight-second `91 04` stream visibly lit the RPM strip over RF. With SimPro still running, the observer saw violet interleaved with the test pattern and rapid flicker. The saved SimPro profile had a violet redline FLASH row, and SimPro was also producing telemetry. We did not isolate which competing write produced every violet frame.

Repeating the test with SimPro **completely exited**, followed by restoration and readback, produced a steady 3/3/3 strip without violet. Another controlled trial sent three stored RPM stages with FLAG activation on one button; the observer saw one LED, then about six LEDs, then redline, together with a yellow flag animation. The original configuration was restored after each trial.

For hardware FLAG on one selected button, observed flag values produced green, yellow, blue, off, and white effects in a separate five-stage trial. The colors and rates are hardware behavior in this setup; they do not imply arbitrary per-button RGB or an independently programmable blink phase. We later corrected a yellow/blue mapping in our bridge after physical observation.

## 4. Performance observations

A SimHub bridge first translated its RPM profile into frequent complete configuration updates. Even when host-side diagnostics reported about 50 completed USB frames/s, flag changes sometimes appeared about 1–2 seconds late when RPM updates were active. The same observer reported flags responding promptly when the RPM configuration updates were suppressed. A revised path kept stored RPM colors in the rim and sent live RPM stage and FLAG in `91 04`; the observer reported smooth concurrent operation during replay. These are subjective visual observations, not instrumented end-to-end latency measurements.

A separate button-color trial sent alternating full yellow/blue configurations every 500 ms for eight seconds, then every 250 ms for eight seconds. The script completed the expected host writes and restored the original. The observer reported steady light in the 500 ms phase and visible changes in the 250 ms phase, but judged the effect unreliable. This counterintuitive result is **not** evidence of a simple 250 ms threshold. The actual RF frames and rim render timing were not captured.

When the rim was later connected directly to the PC with USB-C and the base switched off, the observer reported fast animations without the same apparent lag. That comparison points toward some difference in the base/RF path or its command handling, but does not identify a particular cause.

## 5. Encoder indicators and connection status

The two physical encoder rings were addressable as logical channels 9 and 10 through the base, with left/right operation physically confirmed. Small indicator/spot LEDs 11 and 12 appeared to derive their color from the ring color in the tested RF mode. Configuration writes to tested channels 11–30 and tested FLAG settings did not change those spots independently. This negative result is limited to those commands and settings.

On the base's 39-byte input report, zero-based byte 28 (including the report ID at byte 0) changed from `0x4B` with the NEO X mounted to `0x00` when the observer removed it, and back to `0x4B` after mounting. Rotating the lower encoders and holding one button did not change that byte in these brief trials. It is only a *candidate* presence signal; it is not a proven model ID or general RF-connected flag.
