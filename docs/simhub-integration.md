# Recreating the experimental SimHub bridge architecture

This is an implementation description of the bridge we tested with **SimHub 9.11.9**. It is not an installable plugin and does not claim a stable SimHub extension API. The byte encoder is in [host_codec.py](../examples/host_codec.py); the hardware sequence is in [reproduction.md](reproduction.md). The local abandoned bridge source was **not** copied into this documentation repository.

## Device attachment

The plugin implemented SimHub `IPlugin`, `IDataPlugin` and `IWPFSettingsV2`, plus an `IDeviceExtensionFilter`. It matched the existing *Simagic Neo X* `DeviceTypeID` `8A985050-74B7-48AD-BDB9-EB00436F5CED`. The extension added a **NEO X Bridge 2.0** settings tab to that device; it did **not** register a new physical device. It retained the installed SimHub profiles and substituted an `ILedDeviceManager` wrapper for the device's `LedModuleSettings.DeviceDriver`, keeping the original manager for direct wheel USB fallback.

The installed SimHub build exposed the settings/driver through internal members, so the bridge used reflection. This is a version-specific integration point that can break after SimHub updates. A developer should first verify the current SimHub device descriptor and public extension options instead of assuming that this ID or reflection path still works.

The original manager and wrapper both participated in the tile's `IsConnected()` decision. In RF mode, the bridge's “connected” state was driven by enumeration of the saved **Alpha U USB HID path**; it did not prove that the rim remained mounted or receiving RF. The candidate input-report byte 28 is documented separately and was never promoted to a production identity detector.

## Input profiles and runtime pipeline

| SimHub input | Bridge behavior in the tested native-stage mode |
| --- | --- |
| Devices → Simagic Neo X → **Buttons lighting** | Rendered eight main button colors plus two encoder rings; colors mapped to the fixed hardware palette |
| Devices → Simagic Neo X → **Telemetry LEDs** | Its arbitrary per-frame LED profile was **not** the RF RPM source in native-stage mode; it could still serve the rim's direct USB-C mode |
| Bridge RPM editor | Stored ten threshold rows, nine visible colors per row and FLASH values; sent as configuration only when edited or on activation |
| `GameData.NewData.Rpms` | Current game RPM; clamped to 0–32767 for the host report |
| `GameData.NewData.MaxRpm` | Primary maximum RPM; `CarSettings_MaxRPM` fallback when nonpositive |
| `GameData.GameRunning` | Invalid or stopped game selected idle row 10 |
| User FLAG rules | Evaluated a SimHub property name with `PluginManager.GetPropertyValue(name)` against a configured value; first valid match won |

The bridge computed `percent = 100 * Rpms / MaxRpm`, validated 0–100, then selected the **first** saved threshold no greater than the percentage from an array ordered highest to lowest. It put RPM, selected row, percentage and the active FLAG value into one `91 04` report. RPM did **not** require four configuration parts per frame. If the game stopped, data was invalid or RPM fell below every threshold, it selected row 10 (idle/off).

A FLAG rule selected each button for Blink, steady On, or its ordinary profile. For Blink, the button entry used the chosen palette index with trigger mode `5`, and byte 16 of the live report carried the shared hardware FLAG code. For steady On, the selected button used that palette index with static trigger `0`. There was one global active FLAG code, so separate independently phased flag animations were not established. The corrected mapping was FLAG green `1`, blue `2`, yellow `3`, white `5`; code `4` produced off in the controlled trial. Missing SimHub properties failed the rule closed. A rule transition could require a four-part button configuration update before the new FLAG had visible effect.

## Output worker and timing

The worker accepted the newest rendered button frame, dropped stale frames and ran at a selectable **2–60 Hz host target**. At each tick it compared the desired canonical configuration with the last sent one. If unchanged, it sent only `91 04`; if changed, it sent four `91 00`–`91 03` parts followed by `91 04`. This distinction matters because frequent full RPM configuration updates coincided with delayed FLAG reactions in our first bridge mode. The revised saved-stage mode kept RPM updates in telemetry and was reported smooth in replay.

The panel counted **SimHub input frames**, completed **USB output frames** (including keepalive), changed **configuration updates**, and host write durations/frame age. These counters excluded game detection delay, base processing, RF delivery and rim rendering. A 50 Hz output display therefore cannot establish 50 Hz LED response. The 500 ms/250 ms visual alternation trial remained inconclusive.

## Ownership, setup and shutdown

1. While SimPro 2 is running, capture its `wheel` object and validate NEO X/Alpha U identity. Keep this as a private reference.
2. Fully exit SimPro. On the saved Alpha U HID path, read `0x90` twice, compare mappings, thresholds and clutch, reconstruct canonical settings, and create a durable recovery journal before the first write.
3. Start the worker only after validation. Send the stored RPM stage configuration and selected FLAG/button state as needed; keep runtime RPM and FLAG in `91 04`.
4. On normal pause/shutdown, send idle, restore original canonical parts, send idle again, verify raw writable readback and clear the journal only on success.
5. After an interrupted run, recover **before** any new profile output. Disarm on SimPro conflict, readback mismatch or USB error. A base power cycle or newer SimPro profile can make the old reference stale; do not overwrite changed mappings or thresholds automatically.

The source was removed from the installed SimHub environment at the user's request. This page and the offline encoder document the design; they do not substitute for the original plugin binary, SimHub vendor assemblies or fresh compatibility testing.
