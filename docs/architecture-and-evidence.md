# Architecture, LED map, and evidence boundaries

This page explains how the experimental bridge used our host-side findings. It distinguishes what we **wrote to USB**, what the user **saw on the wheel**, and what remains unknown between the base and rim. For a practical test, start with [reproduction.md](reproduction.md); for byte positions, see [host-protocol.md](host-protocol.md) and [worked vectors](test-vectors.md).

## Terms used in these notes

| Term | Meaning here |
| --- | --- |
| Host | The Windows PC running SimPro, SimHub or a HID test program |
| HID feature report | A fixed-length command/response exchanged between the PC and the Alpha U USB interface |
| RF | The wireless link between Alpha U and the NEO X rim; its LED payload was **not decoded** here |
| Canonical configuration | The 241-byte local representation rebuilt from the wheel's own SimPro fields, before splitting into four writes |
| Readback | The base's `0x90` response, useful for comparisons but **lossy for LED fields** |
| RPM stage | One of ten stored LED rows; the live report selects a row rather than transmitting nine new RGB values each time |
| FLAG | A hardware button-light trigger controlled by one shared live telemetry byte |
| Output Hz | Completed PC-to-base report writes per second, **not** confirmed RF deliveries or LED refreshes |

## Two different communication layers

```text
SimHub profiles / game data                  SimPro 2 reference capture
            │                                          │
            └────────── Windows application ───────────┘
                              │
                   241-byte HID feature reports
                              │ USB
                           Alpha U base
                              │ RF (payload not decoded here)
                           NEO X rim LEDs
```

“Direct USB” in the bridge means **direct USB to the Alpha U base**, while the rim remains connected to the base by RF. Plugging the rim's own USB-C port directly into the PC is a separate mode with different behavior and was only compared visually. A Windows `HidD_SetFeature`/HidSharp `SetFeature` completion measures the host-to-base call; it does not acknowledge an LED frame at the rim.

[Kegetys' independent wireless research](https://github.com/Kegetys/simagic-arduino-poc) describes nRF24 communication and ACK payloads for other Simagic hardware, and explicitly leaves base-to-rim LED data undecoded. His example configures `RF24_250KBPS` (250 **kilobits** per second at the radio PHY), enables ACK payloads and dynamic payloads, but does not establish the usable LED rate or ACK contents on our NEO X/Alpha U firmware. His source later calls `setRetries(0, 0)` after an earlier retry setting, so it is not evidence of this base's actual retry policy. Our `91 xx` bytes are from the PC-side HID layer and must **not** be interpreted as an RF packet format.

## Which lighting path worked

| Path tested | What was sent | Physical outcome | Practical conclusion |
| --- | --- | --- | --- |
| SimPro 2 local API | Updated wheel brightness and one button color | Button brightness and color changed, then restored | Valid RF path, but slow and competing with SimPro output |
| Direct HID full configuration | Four `91 00`–`91 03` parts for button or stored RPM settings | Button color and steady 3/3/3 RPM pattern observed | Use for *infrequent configuration changes* |
| Direct HID telemetry | Repeated `91 04` with RPM, selected stored stage and FLAG | Saved RPM stages and yellow FLAG animation worked together | Preferred live path for RPM/FLAG on this setup |
| Frequent full RPM configuration | Rewrote large configuration as SimHub RPM changed | FLAG changes sometimes appeared roughly 1–2 seconds late | Avoid a full configuration write for every RPM frame |
| Rim USB-C connected directly to PC | Direct wheel USB mode, base off | User reported fast animation | Different route; not proof of any particular RF bottleneck |

The revised SimHub replay using saved RPM stages and hardware FLAG was described by the observer as smooth. The bridge panel displayed 50 completed PC-to-base output calls per second at one point, with zero configuration changes in that one-second window. This supports the design choice; **no end-to-end latency or RF delivery rate was measured**. The odd 500 ms versus 250 ms color-alternation test did not establish a reliable update-frequency limit.

## Physical channels and numbering

The SimHub artwork and protocol array use different orders. The table is for the first eight *button light* positions, not button input mappings:

| SimHub light | Physical position in the tested drawing | Protocol button index | Canonical byte |
| ---: | --- | ---: | ---: |
| 1 | upper left | 4 | 55 |
| 2 | outer left, upper | 5 | 56 |
| 3 | left lower, inner | 6 | 57 |
| 4 | left lower, outer | 7 | 58 |
| 5 | right lower, outer | 0 | 51 |
| 6 | right lower, inner | 1 | 52 |
| 7 | outer right, upper | 2 | 53 |
| 8 | upper right | 3 | 54 |
| 9 | left encoder ring | 8 | 59 |
| 10 | right encoder ring | 9 | 60 |

The first eight order follows the bridge mapping and physically checked upper-left button. The user separately confirmed that channels 9 and 10 reached the correct left/right encoder rings in the installed bridge. Treat positions 11 and 12 in SimHub artwork as **small encoder spot indicators**: our tested RF configuration and FLAG commands did not control them independently. The user reported this automatic ring-to-spot mapping:

| Ring color | Observed spot color |
| --- | --- |
| Orange | Cyan |
| Blue | Red |
| Red | Blue |
| Yellow | Violet |
| Green | Red |
| Cyan | Orange |
| Violet | Yellow |
| White | Off |
| Off | Red |

This is one user's physical observation on the tested firmware, not a decoded spot-control protocol. SimHub could expose separate 11/12 colors when the rim was connected directly to the PC by USB-C; our RF route did not reproduce that independent control.

There are **nine physical RPM LEDs**. The canonical configuration reserves 15 RPM entries per saved row and has **ten rows**. The runtime report selects row 0–9; row 10 was the observed idle/off value. Rows are ordered from the highest RPM threshold to the lowest. Row FLASH is encoded in each stored entry and was visible at the original violet redline profile, but we did not isolate the exact firmware timing of the flash effect.

## How the SimHub bridge operated

The experimental plugin extended the installed SimHub *Simagic Neo X* device rather than registering a new wheel. It used the device's **Buttons lighting** profile for eight buttons and two encoder rings. It configured ten RPM stage rows in a separate bridge editor; in native-stage mode, the ordinary SimHub Telemetry LEDs profile did not drive RF RPM output. These editor and device integration details depended on SimHub 9.11.9 internals and are not a stable public API contract.

At runtime, SimHub provided current RPM, maximum RPM and a game-running state. The bridge computed `percent = 100 * rpm / maxRpm`, chose the first descending saved threshold no greater than that percentage, and sent the selected row, RPM and percent in `91 04`; invalid/absent telemetry selected row 10. It evaluated user-specified SimHub properties for FLAG rules, with the **first matching valid rule** taking precedence. A rule selected button masks for blinking or steady light. Blinking buttons received trigger mode `5`, and the shared FLAG value went in telemetry byte 16. Steady selected buttons used the corresponding palette color with static trigger. Only one shared FLAG code was sent at a time; independently phased left/right flashes were not proven.

The bridge had a latest-frame worker with a selectable **2–60 Hz host output target**. It coalesced stale SimHub frames and skipped unchanged configuration writes while continuing telemetry keepalives. A displayed output rate counted completed host calls, including keepalive; “configuration updates” counted actual changed full configurations. Its host diagnostics could not locate delay inside the base, radio or rim. Keeping RPM on stored stages reduced full-configuration traffic that had interfered with FLAG response in the earlier mode.

## Device ownership and recovery

SimPro and the bridge could both address the base. In a controlled test with SimPro running, the original violet RPM redline profile flickered between our 3/3/3 pattern. The same pattern stayed steady when SimPro exited fully. A reproducible setup therefore has **one software owner** during direct HID output.

The bridge detected the matching **base USB interface**, not a proven RF wheel identity. A 39-byte base input report changed byte 28 from `0x4B` mounted to `0x00` removed and back, but that byte is only a candidate presence marker. It was not validated across other wheels, controls or firmware.

Before writes, the bridge compared the current readback with a reference, saved raw and reconstructed canonical originals in a recovery journal, and stopped on mismatched input mappings, thresholds or clutch fields. It restored the original canonical configuration and verified the resulting raw readback before clearing the journal. A base power cycle or SimPro 3 session later changed saved state relative to an older reference; automatic restoration correctly stopped rather than overwrite changed controls. See [the detailed procedure](reproduction.md) for the tested restoration sequence.

## Evidence levels and unresolved work

| Claim | Evidence level |
| --- | --- |
| Button brightness/color and encoder rings can change through Alpha U RF | User's physical observations plus controlled host writes |
| Nine-LED steady RPM pattern and saved stages with yellow FLAG work | User's physical observations with SimPro closed, plus host report logs |
| `91 00`–`91 04` fields and canonical write layout | SimPro 2 binary analysis, local code/tests, readbacks and selected hardware trials |
| Byte 28 identifies a live RF NEO X | **Unproven** candidate from one remove/remount sequence |
| Alpha U forwards HID bytes as an RF ACK payload | **Unproven**; no radio/SPI capture |
| 250 kb/s is available for our LED data, or 50 Hz reaches the rim | **Unproven**; radio PHY setting in Kegetys' separate example and host USB counters only |
| Spot indicators 11/12 have independent RF color commands | **Unproven** after the tested commands failed |

A definitive RF analysis would require synchronized host USB, base radio-module SPI/air capture and high-frame-rate video of the LEDs. Keep each trace labeled by layer and timestamp. Our notes are complete for the **observed host-side method** on the tested hardware, while the actual base-to-rim transport remains an open investigation.
