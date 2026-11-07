# SimHub bridge experiments and project record

This page records the main outcomes of the NEO X + Alpha U research project, including the experimental SimHub bridge. It is an **observational record**, not a downloadable plugin or a claim of production readiness. Tests used the hardware and software versions listed in the [README](../README.md); firmware compatibility was not established beyond that setup.

## How the bridge evolved

1. **SimPro 2 API prototype.** We confirmed RF-connected button brightness and individual palette colors by changing SimPro's wheel configuration and observing the physical NEO X. This proved a PC → SimPro 2 → Alpha U → RF → wheel lighting path without MagLink. API configuration changes were slow and could compete with SimPro's own output.
2. **Direct base HID.** We identified the Alpha U feature-report interface, reproduced the four-part configuration write and the live `91 04` telemetry report, and moved runtime output to direct USB writes to the base. SimPro 2 remained useful for capturing a canonical reference; it had to be fully closed while the bridge drove the LEDs.
3. **Native SimHub device integration.** The experimental plugin attached to SimHub's existing *Simagic Neo X* device, taking its Buttons lighting and, in the first mode, Telemetry LEDs profile output. It was a separate plugin/menu, not a new physical HID device. The displayed Connected state initially followed base USB presence; that alone was not proof that the RF rim was mounted.
4. **Saved-stage RPM plus hardware FLAG.** Frequent complete RPM configuration writes interfered with button flag responsiveness. The successful mode kept ten RPM lighting rows and their thresholds in the wheel/base configuration, then sent RPM stage, RPM value and FLAG state in the small live telemetry report. This is the same broad *configure stages, then select by telemetry* model observed in SimPro 2. It **does not** render arbitrary per-frame SimHub RPM LED animations over this RF route.
5. **Local rollback.** The user chose to stop the bridge project. Its DLL was removed from the local SimHub installation. The source, offline tests and research records remain local; this public repository contains only documentation.

## FLAG and buttons

The tested hardware FLAG mechanism required selected button channels to have a FLAG trigger mode in their lighting configuration. The live `91 04` report then carried a FLAG state. One selected button blinked rapidly in a controlled test while other buttons kept their colors. Several flags/colors were physically observed. The FLAG state is shared, so independently timed, opposite-phase blinking on multiple groups was **not** established.

The bridge later offered SimHub property-based FLAG rules with selectable buttons, a Blink choice and additional user-created rules. Rule transitions could configure selected buttons for hardware FLAG or leave unselected channels on their usual profiles. These UI/rule options were experimental; the one-button hardware behavior was physically confirmed, but every combination of rules, game properties, colors and button selections was not.

Ordinary SimHub button lighting also worked through the base path. Eight main button channels and two encoder ring channels (logical 9 and 10) were physically confirmed in parts of the investigation. The small encoder indicator/spot LEDs were not independently controlled over this RF path by the tested commands. Both FLAG and button colors used the wheel's limited hardware palette rather than arbitrary RGB.

## RPM and timing

The physical strip has **nine LEDs**. The saved configuration has **ten RPM stages**, each stored in a larger 15-slot protocol row. Stage thresholds and colors were captured from SimPro 2, then editable in the experimental bridge. A stage could specify nine colors and a FLASH setting. The bridge selected the stage using normalized game RPM and maximum RPM; without valid game telemetry it sent an idle/off stage. RPM, stage and FLAG shared one `91 04` telemetry report. RPM changes in this mode did not require resending the four configuration parts unless the stored stages themselves changed.

A controlled physical test showed one RPM LED, then about six, then redline while a yellow FLAG animation ran on a button. In a later SimHub replay the observer reported that both worked smoothly together. The bridge exposed selectable host output rates from 2 to 60 Hz. A displayed **50/50 Hz** meant completed PC-to-base writes, not 50 confirmed RF deliveries per second. When full RPM configuration updates were active, the observer saw occasional flag delays of roughly 1–2 seconds despite short host USB writes; suppressing that configuration traffic improved flag response. This is why the saved-stage telemetry route was preferred in this setup.

The 500 ms versus 250 ms button-color test remained inconclusive. A 500 ms change interval appeared steady while 250 ms produced visible changes but was judged unreliable. It does not establish a reliable maximum RF animation rate. The observer separately reported that animations were fast when NEO X was connected directly to the PC with USB-C and the base was off.

## Connection, conflicts and recovery

SimPro 2 and the bridge could send competing lighting/telemetry. During one test, the original violet redline FLASH profile visibly alternated with a 3 green / 3 yellow / 3 red test pattern. After SimPro 2 fully exited, the same test pattern held steady. A base power cycle and a SimPro 3 session later changed the observed configuration relative to an older saved reference; automatic restoration correctly stopped rather than overwrite changed input mappings or RPM thresholds.

The base's `0x90` configuration readback was lossy for LED fields. Initial attempts to replay it as a complete write failed. A canonical write reconstructed from saved SimPro fields, while preserving mappings, clutch and thresholds, did reproduce a verified original readback in one recovery. This is a narrow result, not a generic restore algorithm for other firmware. The local bridge kept a recovery journal and disarmed on conflicts or readback mismatch. After the bridge was removed from SimHub, a pending recovery file was retained because the base was switched off; removal of the DLL did not itself restore the wheel's hardware state.

An input-report byte (offset 28) changed `0x4B → 0x00 → 0x4B` when the observer removed and remounted the NEO X. This is a candidate connection indicator only. Its meaning, stability across firmware and ability to distinguish wheel models remain unproven.

## Status of the evidence

The strongest results are **physical observations on one setup**: RF button brightness/color control; steady nine-LED RPM pattern with SimPro closed; saved RPM stages with a yellow hardware FLAG; independent encoder ring colors; and fast direct-USB animation. Host report layouts were corroborated by SimPro 2 analysis and controlled writes. We have no simultaneous USB/radio/video trace and no decoded base-to-rim ACK payload. For byte-level details, see [host protocol notes](host-protocol.md); for unresolved experiments, see [open questions](open-questions.md).
