import logging

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Add Kia e-Niro sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        [
            KiaSocSensor(coordinator, entry.entry_id),
            KiaBatteryVoltageSensor(coordinator, entry.entry_id),
            KiaAuxBatteryVoltageSensor(coordinator, entry.entry_id),
            KiaBatteryPowerSensor(coordinator, entry.entry_id),
            KiaOdometerSensor(coordinator, entry.entry_id),
            KiaTirePressureSensor(coordinator, entry.entry_id, "front_left", "Front Left"),
            KiaTirePressureSensor(coordinator, entry.entry_id, "front_right", "Front Right"),
            KiaTirePressureSensor(coordinator, entry.entry_id, "rear_right", "Rear Right"),
            KiaTirePressureSensor(coordinator, entry.entry_id, "rear_left", "Rear Left"),
        ],
        True,
    )

class BaseKiaSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": "Kia e-Niro",
            "manufacturer": "Kia",
            "model": "e-Niro ELM327 WiFi",
        }


class KiaSocSensor(BaseKiaSensor):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_name = "Displayed State of Charge"
        self._attr_unique_id = f"{entry_id}_soc_display_pct"
        self._attr_icon = "mdi:battery"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_device_class = "battery"
        self._attr_state_class = "measurement"

    @property
    def native_value(self):
        return self.coordinator.data.get("soc_display_pct")


class KiaBatteryVoltageSensor(BaseKiaSensor):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_name = "Battery Voltage"
        self._attr_unique_id = f"{entry_id}_battery_voltage"
        self._attr_icon = "mdi:car-battery"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = "voltage"
        self._attr_state_class = "measurement"

    @property
    def native_value(self):
        return self.coordinator.data.get("battery_voltage")


class KiaAuxBatteryVoltageSensor(BaseKiaSensor):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_name = "Auxiliary Battery Voltage"
        self._attr_unique_id = f"{entry_id}_aux_battery_voltage"
        self._attr_icon = "mdi:car-battery"
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_device_class = "voltage"
        self._attr_state_class = "measurement"

    @property
    def native_value(self):
        return self.coordinator.data.get("aux_battery_voltage")


class KiaBatteryPowerSensor(BaseKiaSensor):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_name = "Battery Power"
        self._attr_unique_id = f"{entry_id}_battery_power_kw"
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
        self._attr_device_class = "power"
        self._attr_state_class = "measurement"

    @property
    def native_value(self):
        return self.coordinator.data.get("battery_power_kw")


class KiaOdometerSensor(BaseKiaSensor):
    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator, entry_id)
        self._attr_name = "Odometer"
        self._attr_unique_id = f"{entry_id}_odometer"
        self._attr_icon = "mdi:counter"
        self._attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
        self._attr_device_class = "distance"
        self._attr_state_class = "total_increasing"

    @property
    def native_value(self):
        return self.coordinator.data.get("odometer_km")


class KiaTirePressureSensor(BaseKiaSensor):
    def __init__(self, coordinator, entry_id, wheel, wheel_name):
        super().__init__(coordinator, entry_id)
        self._attr_name = f"{wheel_name} Tire Pressure"
        self._attr_unique_id = f"{entry_id}_{wheel}_tire_pressure"
        self._attr_icon = "mdi:car-tire-alert"
        self._attr_native_unit_of_measurement = UnitOfPressure.BAR
        self._attr_device_class = "pressure"
        self._attr_state_class = "measurement"
        self._sensor_key = f"{wheel}_pressure_bar"

    @property
    def native_value(self):
        return self.coordinator.data.get(self._sensor_key)