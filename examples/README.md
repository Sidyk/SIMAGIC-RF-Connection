# Reference examples

These files reproduce the **tested host-side** report construction and controlled Alpha U HID trial. They are independent examples, not the abandoned SimHub plugin.

| File | Purpose | Hardware access |
| --- | --- | --- |
| `host_codec.py` | Rebuilds canonical settings from a private SimPro 2 wheel object and matching `0x90` readback; creates four original parts, four yellow-FLAG test parts and four telemetry samples | None |
| `test_host_codec.py` | Synthetic regression tests for report packing, stage selection and preflight checks | None |
| `Build-HidReproducer.ps1` | Compiles the C# runner against the user's installed SimHub `HidSharp.dll` | None |
| `HidReproducer.cs` | `list` enumerates HID metadata; `capture` saves a readback; `test ... --send` performs the 12-second LED trial with recovery; `recover` retries pending restoration | `capture` sends a read request; `test` and `recover` send LED reports |

Start with [the full reproduction procedure](../docs/reproduction.md). Never use another person's wheel profile or copy a `0x90` readback directly into configuration writes. Generated `.exe`, `HidSharp.dll` and private wheel files are excluded from this repository; no vendor binaries are redistributed.
