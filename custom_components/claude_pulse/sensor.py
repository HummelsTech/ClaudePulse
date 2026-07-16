"""Sensor platform for Claude Pulse."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FABLE_QUOTA, DEFAULT_FABLE_QUOTA, DOMAIN
from .coordinator import ClaudePulseCoordinator


@dataclass(frozen=True)
class ClaudePulseSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with the coordinator data key."""

    data_key: str = ""


SENSOR_DESCRIPTIONS: tuple[ClaudePulseSensorDescription, ...] = (
    ClaudePulseSensorDescription(
        key="session_pct",
        data_key="session_pct",
        translation_key="session_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chart-arc",
    ),
    ClaudePulseSensorDescription(
        key="weekly_pct",
        data_key="weekly_pct",
        translation_key="weekly_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chart-bar",
    ),
    ClaudePulseSensorDescription(
        key="session_countdown",
        data_key="session_reset_countdown",
        translation_key="session_reset_countdown",
        icon="mdi:timer-outline",
    ),
    ClaudePulseSensorDescription(
        key="session_reset_time",
        data_key="session_reset_time",
        translation_key="session_reset_time",
        icon="mdi:clock-outline",
    ),
    ClaudePulseSensorDescription(
        key="weekly_reset",
        data_key="weekly_reset",
        translation_key="weekly_reset",
        icon="mdi:calendar-clock",
    ),
    ClaudePulseSensorDescription(
        key="weekly_reset_weekday",
        data_key="weekly_reset_weekday",
        translation_key="weekly_reset_weekday",
        icon="mdi:calendar-week",
    ),
    ClaudePulseSensorDescription(
        key="weekly_reset_time",
        data_key="weekly_reset_time",
        translation_key="weekly_reset_time",
        icon="mdi:clock-check-outline",
    ),
    ClaudePulseSensorDescription(
        key="session_used",
        data_key="session_used",
        translation_key="session_used",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
    ),
    ClaudePulseSensorDescription(
        key="session_limit",
        data_key="session_limit",
        translation_key="session_limit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge-full",
    ),
    ClaudePulseSensorDescription(
        key="plan",
        data_key="plan",
        translation_key="plan",
        icon="mdi:card-account-details-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ClaudePulseSensorDescription(
        key="fable_pct",
        data_key="fable_pct",
        translation_key="fable_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:book-open-variant",
    ),
    ClaudePulseSensorDescription(
        key="fable_reset",
        data_key="fable_reset",
        translation_key="fable_reset",
        icon="mdi:calendar-clock",
    ),
)

# Sensor data keys gated behind the optional Fable quota toggle.
FABLE_DATA_KEYS = frozenset({"fable_pct", "fable_reset"})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Claude Pulse sensors from a config entry."""
    coordinator: ClaudePulseCoordinator = hass.data[DOMAIN][entry.entry_id]
    fable_enabled = entry.data.get(CONF_FABLE_QUOTA, DEFAULT_FABLE_QUOTA)
    async_add_entities(
        ClaudePulseSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
        if description.data_key not in FABLE_DATA_KEYS or fable_enabled
    )


class ClaudePulseSensor(CoordinatorEntity[ClaudePulseCoordinator], SensorEntity):
    """A single Claude Pulse sensor backed by the shared coordinator."""

    entity_description: ClaudePulseSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ClaudePulseCoordinator,
        entry: ConfigEntry,
        description: ClaudePulseSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Claude Pulse",
            manufacturer="nolmedo.dev",
            model="Claude.ai Usage Monitor",
            entry_type="service",
            configuration_url="https://claude.ai/settings/usage",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value from the latest coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.data_key)
