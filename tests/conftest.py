"""Pytest global test fixtures and environment mocks for Home Assistant integration."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

# 1. Mock homeassistant package hierarchy
if "homeassistant" not in sys.modules:
    ha_mock = MagicMock()
    sys.modules["homeassistant"] = ha_mock
    sys.modules["homeassistant.core"] = ha_mock
    sys.modules["homeassistant.const"] = ha_mock
    sys.modules["homeassistant.helpers"] = ha_mock
    sys.modules["homeassistant.helpers.storage"] = ha_mock
    sys.modules["homeassistant.data_entry_flow"] = ha_mock

    class MockConfigEntryAuthFailed(Exception):
        pass

    exceptions_mock = MagicMock()
    exceptions_mock.ConfigEntryAuthFailed = MockConfigEntryAuthFailed
    sys.modules["homeassistant.exceptions"] = exceptions_mock
    ha_mock.exceptions = exceptions_mock

    class MockConfigFlow:
        def __init_subclass__(cls, **kwargs):
            pass

        def __init__(self):
            self.hass = MagicMock()
            self.context = {}

        async def async_set_unique_id(self, unique_id):
            self._unique_id = unique_id

        def _abort_if_unique_id_configured(self):
            pass

        def async_show_form(self, step_id, data_schema=None, errors=None):
            return {"type": "form", "step_id": step_id, "errors": errors or {}}

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_abort(self, reason):
            return {"type": "abort", "reason": reason}

    class MockStore:
        def __init__(self, hass, version, key):
            self.hass = hass
            self.version = version
            self.key = key
            self.async_load = MagicMock()
            self.async_save = MagicMock()

    storage_mock = MagicMock()
    storage_mock.Store = MockStore
    sys.modules["homeassistant.helpers.storage"] = storage_mock

    class MockUpdateFailed(Exception):
        pass

    class MockDataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, name, update_interval=None, **kwargs):
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.data = None

        async def _async_update_data(self):
            raise NotImplementedError

        async def async_config_entry_first_refresh(self):
            self.data = await self._async_update_data()

    class MockCoordinatorEntity:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, coordinator):
            self.coordinator = coordinator

    update_coordinator_mock = MagicMock()
    update_coordinator_mock.DataUpdateCoordinator = MockDataUpdateCoordinator
    update_coordinator_mock.CoordinatorEntity = MockCoordinatorEntity
    update_coordinator_mock.UpdateFailed = MockUpdateFailed
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator_mock

    class MockSensorEntity:
        def __init__(self):
            pass

    class MockSensorEntityDescription:
        def __init__(
            self,
            key,
            name=None,
            native_unit_of_measurement=None,
            device_class=None,
            state_class=None,
            icon=None,
        ):
            self.key = key
            self.name = name
            self.native_unit_of_measurement = native_unit_of_measurement
            self.device_class = device_class
            self.state_class = state_class
            self.icon = icon

    components_mock = MagicMock()
    sensor_mock = MagicMock()
    sensor_mock.SensorEntity = MockSensorEntity
    sensor_mock.SensorEntityDescription = MockSensorEntityDescription
    components_mock.sensor = sensor_mock
    sys.modules["homeassistant.components"] = components_mock
    sys.modules["homeassistant.components.sensor"] = sensor_mock
    ha_mock.components = components_mock

    entity_platform_mock = MagicMock()
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform_mock

    helpers_mock = MagicMock()
    helpers_mock.storage = storage_mock
    helpers_mock.update_coordinator = update_coordinator_mock
    helpers_mock.entity_platform = entity_platform_mock
    sys.modules["homeassistant.helpers"] = helpers_mock
    ha_mock.helpers = helpers_mock

    config_entries_mock = MagicMock()
    config_entries_mock.ConfigFlow = MockConfigFlow
    sys.modules["homeassistant.config_entries"] = config_entries_mock
    ha_mock.config_entries = config_entries_mock

# 2. Mock voluptuous
if "voluptuous" not in sys.modules:
    vol_mock = MagicMock()
    vol_mock.Schema = lambda schema: lambda data=None: data
    vol_mock.Required = lambda key, default=None: key
    vol_mock.Optional = lambda key, default=None: key
    vol_mock.In = lambda choices: lambda val: val
    sys.modules["voluptuous"] = vol_mock

# 3. Mock garminconnect
if "garminconnect" not in sys.modules:
    gc_mock = MagicMock()

    class MockGarminConnectAuthenticationError(Exception):
        pass

    class MockGarminConnectConnectionError(Exception):
        pass

    class MockGarminConnectMfaRequired(Exception):
        pass

    gc_mock.GarminConnectAuthenticationError = MockGarminConnectAuthenticationError
    gc_mock.GarminConnectConnectionError = MockGarminConnectConnectionError
    gc_mock.GarminConnectMfaRequired = MockGarminConnectMfaRequired
    sys.modules["garminconnect"] = gc_mock
