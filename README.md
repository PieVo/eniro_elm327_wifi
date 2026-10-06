# Kia e-Niro ELM327 WiFi

Home Assistant integration for local Kia e-Niro readings over a WiFi-connected ELM327 adapter.

## Origin

This repository's original integration targeted the Nissan Ariya. The current version adapts it for the Kia e-Niro using Kia-specific PID and read-method references, including [OBD-PIDs-for-HKMC-EVs](https://github.com/JejuSoul/OBD-PIDs-for-HKMC-EVs). The original ELM327 WiFi adapter reference is [dconlon/icar_obd_wifi](https://github.com/dconlon/icar_obd_wifi).

## Sensors

- Displayed State of Charge, read using PID `22 01 05` at byte offset `af` (`31`), scaled by `1/2` as specified in the supplied Kona/Niro BMS CSV. This is distinct from BMS SOC (`22 01 01`, byte `e`).
- High-voltage battery voltage, from the same BMS response.
- Auxiliary 12 V battery voltage, read using PID `21 02` from ECU `7E2` (response `7EA`), with the CSV formula `((signed(U) * 256) + T) / 1000`.
- Battery power in kW, calculated as signed battery current multiplied by battery voltage and divided by 1000. Positive and negative values retain the BMS current direction for tracing charge/discharge power.
- Odometer, read from the instrument cluster using PID `22 B0 02` on transmit header `7C6` (response header `7CE`). Bytes `g:h:i` are decoded as an unsigned 24-bit kilometer value.

The BMS request uses transmit header `7E4` and response header `7EC`.

## Setup

Add the integration in Home Assistant and enter the ELM327 WiFi adapter's IP address and TCP port (usually `35000`). The coordinator polls at the configured interval (default 10 minutes), which can be set to 1-60 minutes in the integration options. Diagnostic requests retry once after one second if the ELM returns `CAN ERROR` or `NO DATA`. No cloud service is used.
