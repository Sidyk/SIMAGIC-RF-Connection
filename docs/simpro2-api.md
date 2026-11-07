# SimPro 2 local API observations

This page documents the **first, SimPro-mediated** lighting tests on the NEO X 1.0.9 and Alpha U. The later direct HID method in [reproduction.md](reproduction.md) is separate. Use one software owner at a time: this API requires SimPro 2 to be running, whereas the direct HID experiment requires SimPro to be fully closed.

## Endpoint and request envelope

The installed SimPro 2 build `V2.1.8.2361-e52c6dee` exposed `http://127.0.0.1:56789/jsonrpc`. Requests were local HTTP POST with `Content-Type: application/json` and JSON-RPC 2.0 envelopes:

```json
{"id":1,"jsonrpc":"2.0","method":"query","params":{"items":["devices"]}}
{"id":1,"jsonrpc":"2.0","method":"get_config","params":{"items":["wheel"]}}
```

The result object contained `devices` or `wheel` respectively. Our setup reported wheel name `Neo X`, `device_id` 11, firmware `1.0.9`, `connect_mode` `RF`, and base `product_id` `1314`. The API response can contain stale or placeholder fields, so use it with a fresh hardware readback and validation when constructing direct HID writes. Do not assume this endpoint or response shape is stable across SimPro versions.

The wheel object fields used in our tests were:

| JSON path inside `result.wheel` | Tested shape/use |
| --- | --- |
| `brightness` | Button-light group brightness, 0–100 in observed writes |
| `rpmled_brightness` | RPM-light group brightness |
| `button_settings.mappings` | 40 input mapping entries; preserve them |
| `button_settings.color_index` | 40 palette entries; the first 30 feed the tested host configuration buffer |
| `button_settings.trigger_mode` | 40 trigger entries; preserve when changing button colors |
| `rpm_percentage_table` | Ten thresholds, highest to lowest in the API object |
| `rpm_led_settings` | Ten rows; each row had 15 `color_index`, 15 `flash` and 15 `trigger_mode` entries |
| `clutch_rate` and other clutch fields | Preserve the user's current settings |

The generic 40-button/15-RPM-slot arrays are **not** counts of physical NEO X lights. The tested wheel has eight main button lights, two encoder rings and nine physical RPM LEDs. See [channel mapping](architecture-and-evidence.md#physical-channels-and-numbering).

## Confirmed write shapes

The controlled brightness trial used a narrow `set_config` patch, then checked `get_config`, observed the wheel, and restored the original brightness:

```json
{"id":1,"jsonrpc":"2.0","method":"set_config","params":{"items":{"wheel":{"brightness":20}}}}
```

The accepted response's `result` was `"OK"` in our client. The user physically saw the button LEDs dim from 100 to 20 and return to 100.

For one button-color change, the `set_config` patch had `wheel.button_settings` containing the **complete existing** `mappings` and `trigger_mode` arrays as well as the changed `color_index` array. A patch containing only `color_index` failed. The trial saved the original full button-settings object, changed one color entry, verified it with `get_config` and a physical observation, then submitted the original object again. The JSON shape was:

```text
set_config.params.items.wheel.button_settings = {
  mappings:     [40 existing entries],
  color_index:  [40 entries, with only the intended color changed],
  trigger_mode: [40 existing entries]
}
```

This demonstrated an RF path **PC → SimPro 2 API → Alpha U → NEO X** without MagLink. It does not show that SimPro's API can carry a fast per-frame RPM animation. A later API attempt to set `led_colors` did not visibly control RF LED colors on this setup. Saved RPM rows needed a live `91 04` telemetry report for the strip to light in the successful direct test.

## When to use this path

Use the API to read/capture the wheel's own profile and, if desired, repeat slow brightness or individual-color checks while SimPro owns the base. Use the direct HID path for the documented RPM-stage/FLAG test **only after SimPro has fully exited**. Do not compare timing between the two paths without synchronized measurements; our slow API updates and faster telemetry-stage result are observations, not a calibrated performance benchmark.
