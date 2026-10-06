import asyncio
import datetime
import logging
import re
import socket

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
TPMS_PSI_TO_BAR = 0.0689476


async def send(sock, cmd):
    sock.send((cmd + "\r").encode())
    await asyncio.sleep(1.0)
    try:
        response = sock.recv(4096).decode(errors="ignore")
        clean_response = response.replace(">", "").strip()
        _LOGGER.debug("ELM CMD: %s -> RESP: %s", cmd, clean_response)
        return clean_response
    except OSError:
        return None


def check_host(ip, port, timeout=1):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def response_payload(response, expected_header):
    """Extract a diagnostic payload from ELM-formatted CAN response frames."""
    if not response:
        return []

    expected = [int(expected_header[index:index + 2], 16) for index in range(0, len(expected_header), 2)]
    response_addresses = {"7EC", "7EA", "7A8", "7CE"}
    payload = []
    expected_length = None

    for line in response.splitlines() or [response]:
        if "NO DATA" in line.upper():
            continue
        chunks = re.findall(r"[0-9A-F]+", line.upper())
        if chunks and chunks[0] in response_addresses:
            chunks = chunks[1:]
        elif len(chunks) == 1:
            for address in response_addresses:
                if chunks[0].startswith(address):
                    chunks[0] = chunks[0][len(address):]
                    break
        frame_hex = "".join(chunks)
        if len(frame_hex) % 2:
            continue
        frame = [int(frame_hex[index:index + 2], 16) for index in range(0, len(frame_hex), 2)]
        if not frame:
            continue

        if frame[:len(expected)] == expected:
            return frame[len(expected):]

        frame_type = frame[0] >> 4
        if frame_type == 0:
            frame_length = frame[0] & 0x0F
            payload = frame[1:1 + frame_length]
            break
        if frame_type == 1 and len(frame) >= 2:
            expected_length = ((frame[0] & 0x0F) << 8) | frame[1]
            payload = frame[2:]
        elif frame_type == 2 and payload:
            payload.extend(frame[1:])

        if expected_length is not None and len(payload) >= expected_length:
            payload = payload[:expected_length]
            break

    if payload[:len(expected)] == expected:
        return payload[len(expected):]
    return payload


class SocCoordinator(DataUpdateCoordinator):
    def __init__(self, config, hass):
        super().__init__(
            hass,
            _LOGGER,
            name="kia_eniro_elm327_wifi",
            update_interval=datetime.timedelta(minutes=2),
        )
        self.config = config

    async def async_force_refresh(self):
        await self.async_request_refresh()

    async def _async_update_data(self):
        data = dict(self.data or {
            "soc_display_pct": None,
            "battery_voltage": None,
            "aux_battery_voltage": None,
            "battery_power_kw": None,
            "odometer_km": None,
            "front_left_pressure_bar": None,
            "front_right_pressure_bar": None,
            "rear_right_pressure_bar": None,
            "rear_left_pressure_bar": None,
        })

        if not check_host(self.config["elm_ip"], self.config["elm_port"]):
            return data

        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self.config["elm_ip"], self.config["elm_port"]))

            for cmd in ("ATZ", "ATE0", "ATL0", "ATS0", "ATH1", "ATCAF1", "ATSP6"):
                await send(sock, cmd)

            await send(sock, "ATSH7E4")
            await send(sock, "ATCRA7EC")
            bms_response = await send(sock, "220101")
            bms_data = response_payload(bms_response, "620101")
            if len(bms_data) > 13:
                voltage = ((bms_data[12] << 8) | bms_data[13]) / 10.0
                current_high = bms_data[10]
                if current_high >= 0x80:
                    current_high -= 0x100
                current = ((current_high << 8) | bms_data[11]) / 10.0
                if 100 <= voltage <= 500:
                    data["battery_voltage"] = voltage
                    if -230 <= current <= 230:
                        data["battery_power_kw"] = round(current * voltage / 1000.0, 3)

            await send(sock, "ATSH7E2")
            await send(sock, "ATCRA7EA")
            aux_battery_response = await send(sock, "2102")
            aux_battery_data = response_payload(aux_battery_response, "6102")
            if len(aux_battery_data) > 20:
                current_high = aux_battery_data[20]
                if current_high >= 0x80:
                    current_high -= 0x100
                aux_voltage = ((current_high << 8) | aux_battery_data[19]) / 1000.0
                if 8 <= aux_voltage <= 16:
                    data["aux_battery_voltage"] = round(aux_voltage, 3)

            await send(sock, "ATSH7E4")
            await send(sock, "ATCRA7EC")
            display_soc_response = await send(sock, "220105")
            display_soc_data = response_payload(display_soc_response, "620105")
            if len(display_soc_data) > 31:
                display_soc = display_soc_data[31] / 2.0
                if 0 <= display_soc <= 100:
                    data["soc_display_pct"] = display_soc

            await send(sock, "ATSH7A0")
            await send(sock, "ATCRA7A8")
            tpms_response = await send(sock, "22C00B")
            tpms_data = response_payload(tpms_response, "62C00B")
            wheel_offsets = {
                "front_left_pressure_bar": 4,
                "front_right_pressure_bar": 8,
                "rear_right_pressure_bar": 12,
                "rear_left_pressure_bar": 16,
            }
            if len(tpms_data) >= 18:
                for sensor_key, offset in wheel_offsets.items():
                    pressure_psi = tpms_data[offset] / 5.0
                    data[sensor_key] = round(pressure_psi * TPMS_PSI_TO_BAR, 2)

            await send(sock, "ATSH7C6")
            await send(sock, "ATCRA7CE")
            odometer_response = await send(sock, "22B002")
            odometer_data = response_payload(odometer_response, "62B002")
            if len(odometer_data) > 8:
                data["odometer_km"] = int.from_bytes(odometer_data[6:9], "big")

        except (OSError, ValueError) as error:
            _LOGGER.warning("Kia E-Niro OBD read failed: %s", error)
        finally:
            if sock:
                sock.close()

        return data
