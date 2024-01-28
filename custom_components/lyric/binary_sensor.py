"""Support for Honeywell Lyric sensor platform."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from aiolyric import Lyric
from aiolyric.objects.device import LyricDevice
from aiolyric.objects.location import LyricLocation
from aiolyric.objects.priority import LyricAccessories, LyricRoom

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import LyricAccessoryEntity
from .const import DOMAIN


@dataclass
class LyricBinarySensorAccessoryEntityDescriptionMixin:
    """Mixin for required keys."""

    value_fn: Callable[[LyricRoom, LyricAccessories], StateType | datetime]
    suitable_fn: Callable[[LyricRoom, LyricAccessories], bool]


@dataclass
class LyricBinarySensorAccessoryEntityDescription(
    BinarySensorEntityDescription, LyricBinarySensorAccessoryEntityDescriptionMixin
):
    """Class describing Honeywell Lyric room sensor entities."""

ACCESSORY_SENSORS: list[LyricBinarySensorAccessoryEntityDescription] = [
    LyricBinarySensorAccessoryEntityDescription(
        key="room_motion",
        translation_key="room_motion",
        device_class=BinarySensorDeviceClass.MOTION,
        value_fn=lambda _, accessory: accessory.detectMotion,
        suitable_fn=lambda _, accessory: accessory.type == "IndoorAirSensor",
    )
]

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Honeywell Lyric sensor platform based on a config entry."""
    coordinator: DataUpdateCoordinator[Lyric] = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    for location in coordinator.data.locations:
        for device in location.devices:
            entities.extend(__create_accessory_entities(device, location, coordinator))

    async_add_entities(entities)

def __create_accessory_entities(
    device: LyricDevice,
    location: LyricLocation,
    coordinator: DataUpdateCoordinator[Lyric],
):
    entities = []
    for room in coordinator.data.rooms_dict.get(device.macID, {}).values():
        for accessory in room.accessories:
            for accessory_sensor in ACCESSORY_SENSORS:
                if accessory_sensor.suitable_fn(room, accessory):
                    entities.append(
                        LyricAccessorySensor(
                            coordinator,
                            accessory_sensor,
                            location,
                            device,
                            room,
                            accessory,
                        )
                    )

    return entities


class LyricAccessorySensor(LyricAccessoryEntity, BinarySensorEntity):
    """Define a Honeywell Lyric sensor."""

    entity_description: LyricBinarySensorAccessoryEntityDescription

    def __init__(
        self,
        coordinator: DataUpdateCoordinator[Lyric],
        description: LyricBinarySensorAccessoryEntityDescription,
        location: LyricLocation,
        parentDevice: LyricDevice,
        room: LyricRoom,
        accessory: LyricAccessories,
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            location,
            parentDevice,
            room,
            accessory,
            f"{parentDevice.macID}_room{room.id}_acc{accessory.id}_{description.key}",
        )
        self.room = room
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self._room, self._accessory)
