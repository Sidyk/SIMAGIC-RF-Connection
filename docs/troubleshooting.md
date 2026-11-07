# Troubleshooting the tested setup

This page is for reproducing the NEO X 1.0.9 + Alpha U host-side experiment. It does not diagnose other Simagic hardware. Begin with the [reproduction preflight](reproduction.md) and stop sending reports if the profile or device identity differs.

| Symptom | What our tests suggest | What to check |
| --- | --- | --- |
| Base HID interface is present, but the wheel does not react | Enumeration proves only the **base USB interface** is present | Verify NEO X is powered/mounted and visible as RF in SimPro 2 before capture; do not treat the bridge's Connected tile as RF confirmation |
| SimPro and a HID sender are both open | They can send competing LED/telemetry updates | Exit SimPro fully, including the tray process, before direct HID output; in one test violet redline frames disappeared only after full exit |
| RPM colors were written, but strip remains off | Ten saved rows are **configuration**, not live activation | Send a valid `91 04` stage/RPM report; row 10 is the observed idle/off selection |
| FLAG does not animate a selected button | FLAG byte alone is insufficient | Configure that button with trigger mode `5`, then send the matching byte 16 FLAG code; other buttons can stay static |
| Yellow rule appears blue, or blue appears yellow | Early bridge mapping was corrected after a physical trial | Use FLAG `3` for yellow and `2` for blue; palette indexes are a separate numbering scheme |
| FLAG response lags when RPM runs | Frequent four-part RPM configuration traffic interfered in our tests | Use saved RPM stages and change only the selected row in `91 04` during runtime; do not infer the exact RF cause without a radio trace |
| Configuration readback differs from SimPro colors | The `0x90` read view is lossy for LEDs | Rebuild writable fields from the captured SimPro wheel object; never replay a raw `0x90` read as a write |
| Preflight rejects changed mappings, thresholds or clutch | Reference may be stale after a power cycle or another SimPro session | Stop output and capture a fresh reference only after understanding the current wheel state; retain any pending recovery journal |
| USB sender reports successful writes, but the LEDs lag or do nothing | Host success does not confirm rim render | Check SimPro ownership and physical wheel state first; a synchronized USB/radio/video trace is needed to locate remaining delay |
| Ring colors work but small spots 11/12 do not | Our tested RF commands did not independently address those spots | Their color appeared to follow the encoder ring automatically; independent RF control remains unknown |
| The wheel animates faster on its own USB-C cable | Direct rim USB is a different route | Do not infer a fixed RF frequency limit from this comparison or copy direct-wheel USB commands onto Alpha U HID |

## Recovery order after an interrupted write

1. Stop the test sender and ensure SimPro is fully closed.
2. Confirm the **same** Alpha U HID path and the tested wheel firmware. If the base is off, preserve the recovery data until it is available.
3. Read `0x90` again and compare current mappings, thresholds and clutch fields with the journal. A mismatch means the old baseline must **not** be applied automatically.
4. If those fields match, send idle `91 04`, the four **original canonical** configuration parts in order, wait for settling, then send idle telemetry again.
5. Read `0x90` and compare writable readback bytes 1–234 with the saved original raw readback. Keep the journal on failure. Independently inspect the physical LEDs because the readback samples LED fields.

This is the recovery sequence that succeeded on one setup. It is not proof that an arbitrary profile can be reconstructed from `0x90` alone. See [reproduction.md](reproduction.md) for the exact fields and [architecture-and-evidence.md](architecture-and-evidence.md) for the evidence limits.
