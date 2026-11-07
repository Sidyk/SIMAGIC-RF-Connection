# Limits, open questions, and useful next measurements

## What these tests do not show

We have **not** captured the base-to-rim RF payload, decoded ACK payload LED commands, or measured radio retries. The HID reports `91 00`–`91 04` belong to the PC-to-base USB protocol and cannot be copied onto an nRF24 radio as if they were rim packets. Kegetys' [radio analysis](https://github.com/Kegetys/simagic-arduino-poc) is the relevant prior work for that layer.

We also have no direct timestamp at the rim. A successful `HidD_SetFeature` return and a short USB call duration do not mean the rim accepted or displayed the frame. The observed 500 ms/250 ms button-color result is unresolved and should not be used to set a claimed maximum update rate.

## Suggested experiments

1. Capture PC USB writes, the base's radio-module SPI traffic, and high-frame-rate video of the LEDs on a shared clock. Mark a single color transition rather than a long animation; compare `91 04` and full-configuration paths.
2. Inspect actual base-to-rim ACK payloads for changes when stored RPM stages, a FLAG, and a single button color are changed separately. Keep the radio capture distinct from the host HID capture.
3. Repeat the latency test with a fixed SimPro/firmware version and one software owner at a time. Competing SimPro and bridge writes produced visible violet flicker in one trial.
4. Check whether the candidate input byte 28 remains stable across reconnects, other controls, firmware versions, and another wheel model before using it as connection or identity detection.
5. Compare direct USB-C LED commands to the base's USB and RF traffic to see whether independent encoder-spot control exists over the Alpha U path.

## Practical cautions for implementers

The base's configuration readback is lossy in this setup. A raw readback report cannot safely be replayed as a complete write report. Preserve current mappings, clutch settings, and RPM thresholds when changing lighting. Keep a verified recovery copy before experiments. A base power cycle or a separate SimPro session can change those fields, so a recovery routine should stop rather than blindly overwrite them.

The NEO X bridge used for these tests has been removed from the local SimHub installation. This repository is research documentation, not an installable driver or an endorsed lighting integration.
