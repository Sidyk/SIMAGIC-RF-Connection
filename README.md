# Simagic NEO X + Alpha U: host-side LED and telemetry findings

Independent reverse-engineering notes from tests on a **NEO X (firmware 1.0.9)** mounted on an **Alpha U** and connected to a Windows PC. The aim is to document what the PC can send to the base to control the rim's lighting **without MagLink**. These observations do **not** decode the radio packets or prove the base's internal RF scheduling.

This work builds on [Kegetys' Simagic wireless protocol research](https://github.com/Kegetys/simagic-arduino-poc). That project documents rim-to-base packets and describes base-to-rim ACK payloads as an open area. Our contribution investigates the **PC-to-base HID side** and its visible effects on one NEO X. Kegetys' RF packet format and our HID report format are different layers; do not treat their byte offsets as interchangeable.

## Tested setup

| Component | Observed version or identifier |
| --- | --- |
| Wheel | Simagic NEO X, firmware 1.0.9 during these tests |
| Base | Simagic Alpha U, product ID 1314 in SimPro 2 |
| Base HID interface | VID `0483`, PID `0522`; max feature report length 241 bytes |
| Software used to capture a reference | SimPro 2, build `V2.1.8.2361-e52c6dee` |
| Physical output path tested | PC USB → Alpha U → RF → NEO X |

Later firmware or SimPro versions may use different layouts or behavior. We have not measured RF airtime, ACK contents, packet loss, or the time between base USB completion and the rim LED response.

## Findings at a glance

- The PC can change NEO X button brightness and individual button colors over the base's USB connection. Both changes were physically observed on the RF-connected rim, then restored.
- SimPro 2 emits legacy HID feature reports beginning `91 00` through `91 03` for a complete lighting configuration, and `91 04` for live telemetry. These are **host-side reports**, not captured RF packets.
- A `91 04` telemetry stream selected stored RPM stages on the nine physical RPM LEDs and activated a hardware FLAG on a selected button. With SimPro completely closed, the RPM strip held a steady 3 green / 3 yellow / 3 red pattern in a controlled test.
- In a later SimHub replay using stored RPM stages, the observer reported smooth simultaneous RPM and yellow FLAG animation. The host-side diagnostic showed 50 completed USB output frames per second and, at one observed moment, zero configuration updates. This is a favorable observation for telemetry-based stage selection, not a measured RF latency guarantee.
- When RPM was driven by frequent full configuration changes instead, the observer saw flag response delays up to roughly 1–2 seconds. Small USB write durations alone did not explain the visible lag. No RF trace was taken, so the delay cannot yet be assigned to the USB driver, base firmware, radio, or rim firmware.
- Encoder ring channels 9 and 10 were independently controlled over the base path and physically verified. The small encoder indicators (11 and 12 in the SimHub artwork) did not respond to our tested configuration channels or FLAG modes; their RF control remains unknown.

See [detailed observations](docs/observations.md) and [reproduction limits and open questions](docs/open-questions.md).

## Scope and attribution

These notes describe our own tests and observations. The nRF24 setup, rim-to-base packet analysis, and ACK-payload hypothesis remain credited to [Kegetys](https://github.com/Kegetys/simagic-arduino-poc). His example code selects `RF24_250KBPS`, which means **250 kilobits/s** at the radio PHY; it does not establish useful LED throughput on our particular base/rim firmware.

No Simagic firmware or Kegetys code is redistributed here. A successful PC `HidD_SetFeature` call proves only that the host submitted a report to the base. Physical observations are called out separately below.
