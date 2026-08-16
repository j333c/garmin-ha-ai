"""Pytest global test fixtures and environment mocks for Home Assistant integration."""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

# 1. Mock homeassistant package hierarchy
if "homeassistant" not in sys.modules:
    ha_mock = MagicMock()
    def mock_callback(func):
        return func
    ha_mock.callback = mock_callback
    ha_mock.core.callback = mock_callback
    sys.modules["homeassistant"] = ha_mock
    sys.modules["homeassistant.core"] = ha_mock
    core_mock = MagicMock()
    core_mock.callback = mock_callback
    sys.modules["homeassistant.core"] = core_mock


    sys.modules["homeassistant.const"] = ha_mock
    sys.modules["homeassistant.helpers"] = ha_mock
    sys.modules["homeassistant.helpers.storage"] = ha_mock
    sys.modules["homeassistant.data_entry_flow"] = ha_mock


    class MockHomeAssistantError(Exception):
        pass

    class MockConfigEntryAuthFailed(MockHomeAssistantError):
        pass

    class MockServiceNotFound(MockHomeAssistantError):
        pass

    exceptions_mock = MagicMock()
    exceptions_mock.HomeAssistantError = MockHomeAssistantError
    exceptions_mock.ConfigEntryAuthFailed = MockConfigEntryAuthFailed
    exceptions_mock.ServiceNotFound = MockServiceNotFound
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
            self.async_load = AsyncMock(return_value={})
            self.async_save = AsyncMock(return_value=None)

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
            self._listeners = []

        def async_update_listeners(self):
            for listener in list(self._listeners):
                listener()

        def async_add_listener(self, update_callback, context=None):
            self._listeners.append(update_callback)
            return lambda: self._listeners.remove(update_callback)

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

    class MockDeviceInfo(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.__dict__.update(kwargs)

    entity_mock = MagicMock()
    entity_mock.DeviceInfo = MockDeviceInfo
    sys.modules["homeassistant.helpers.entity"] = entity_mock

    from datetime import datetime, timezone
    dt_util_mock = MagicMock()
    dt_util_mock.now.return_value = datetime.now(timezone.utc)
    sys.modules["homeassistant.util"] = MagicMock()
    sys.modules["homeassistant.util.dt"] = dt_util_mock


    entity_platform_mock = MagicMock()
    sys.modules["homeassistant.helpers.entity_platform"] = entity_platform_mock

    config_validation_mock = MagicMock()
    sys.modules["homeassistant.helpers.config_validation"] = config_validation_mock

    helpers_mock = MagicMock()
    helpers_mock.storage = storage_mock
    helpers_mock.update_coordinator = update_coordinator_mock
    helpers_mock.entity_platform = entity_platform_mock
    helpers_mock.entity = entity_mock
    helpers_mock.config_validation = config_validation_mock
    sys.modules["homeassistant.helpers"] = helpers_mock
    ha_mock.helpers = helpers_mock



    class MockOptionsFlow:
        def __init__(self, config_entry=None):
            self.config_entry = config_entry
            self.hass = None

        def async_show_form(self, step_id, data_schema=None, errors=None):
            return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}

        def async_create_entry(self, title="", data=None):
            return {"type": "create_entry", "title": title, "data": data or {}}

    config_entries_mock = MagicMock()
    config_entries_mock.ConfigFlow = MockConfigFlow
    config_entries_mock.OptionsFlow = MockOptionsFlow
    sys.modules["homeassistant.config_entries"] = config_entries_mock
    ha_mock.config_entries = config_entries_mock


# 2. Mock voluptuous
if "voluptuous" not in sys.modules:
    vol_mock = MagicMock()

    class MockInvalid(Exception):
        pass

    def mock_schema(schema_dict):
        def validator(data):
            if not isinstance(data, dict):
                return data
            for key, val_func in schema_dict.items():
                k_name = key.schema if hasattr(key, "schema") else str(key)
                if k_name in data:
                    val = data[k_name]
                    if callable(val_func):
                        val_func(val)
            return data
        return validator

    class MockRange:
        def __init__(self, min=None, max=None):
            self.min = min
            self.max = max
        def __call__(self, val):
            if self.min is not None and val < self.min:
                raise MockInvalid(f"{val} < {self.min}")
            if self.max is not None and val > self.max:
                raise MockInvalid(f"{val} > {self.max}")
            return val

    class MockAll:
        def __init__(self, *validators):
            self.validators = validators
        def __call__(self, val):
            for v in self.validators:
                if callable(v):
                    val = v(val)
            return val

    vol_mock.Invalid = MockInvalid
    vol_mock.Schema = mock_schema
    vol_mock.Range = MockRange
    vol_mock.All = MockAll
    vol_mock.Coerce = lambda type_: type_
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

    class MockGarminConnectTooManyRequestsError(MockGarminConnectConnectionError):
        pass

    class MockGarminConnectNotFoundError(MockGarminConnectConnectionError):
        pass

    gc_mock.GarminConnectAuthenticationError = MockGarminConnectAuthenticationError
    gc_mock.GarminConnectConnectionError = MockGarminConnectConnectionError
    gc_mock.GarminConnectTooManyRequestsError = MockGarminConnectTooManyRequestsError
    gc_mock.GarminConnectNotFoundError = MockGarminConnectNotFoundError
    gc_mock.Garmin = MagicMock
    sys.modules["garminconnect"] = gc_mock

# 4. Mock httpx
if "httpx" not in sys.modules:
    httpx_mock = MagicMock()

    class MockTimeoutException(Exception):
        pass

    class MockHTTPStatusError(Exception):
        def __init__(self, *args, **kwargs):
            self.response = kwargs.get("response") or MagicMock()
            self.request = kwargs.get("request") or MagicMock()
            super().__init__(*args)

    class MockRequestError(Exception):
        pass

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"choices": [{"message": {"content": "OK"}}]}
            return resp

    httpx_mock.TimeoutException = MockTimeoutException
    httpx_mock.HTTPStatusError = MockHTTPStatusError
    httpx_mock.RequestError = MockRequestError
    httpx_mock.AsyncClient = MockAsyncClient
    sys.modules["httpx"] = httpx_mock


# 5. Mock google.genai
if "google" not in sys.modules or "google.genai" not in sys.modules:
    google_mock = MagicMock()
    genai_mock = MagicMock()
    errors_mock = MagicMock()

    class MockAPIError(Exception):
        def __init__(self, code=429, message="Quota", details=None):
            self.code = code
            self.message = message
            self.details = details
            super().__init__(message)

    errors_mock.APIError = MockAPIError
    genai_mock.errors = errors_mock

    types_mock = MagicMock()
    class MockGenerateContentConfig:
        def __init__(self, system_instruction=None, **kwargs):
            self.system_instruction = system_instruction

    types_mock.GenerateContentConfig = MockGenerateContentConfig
    genai_mock.types = types_mock

    google_mock.genai = genai_mock
    sys.modules["google"] = google_mock
    sys.modules["google.genai"] = genai_mock
    sys.modules["google.genai.types"] = types_mock
    sys.modules["google.genai.errors"] = errors_mock


# 6. Mock pytest_homeassistant_custom_component
if "pytest_homeassistant_custom_component" not in sys.modules:
    pahcc_mock = MagicMock()
    pahcc_common = MagicMock()

    class MockConfigEntry:
        def __init__(self, domain="garmin_ha_ai", title="Garmin Test", data=None, options=None, entry_id="test_entry_id"):
            self.domain = domain
            self.title = title
            self.entry_id = entry_id
            self.data = data or {}
            self.options = options or {}

        def add_to_hass(self, hass):
            if not hasattr(hass, "config_entries"):
                hass.config_entries = MagicMock()

    pahcc_common.MockConfigEntry = MockConfigEntry
    pahcc_mock.common = pahcc_common
    sys.modules["pytest_homeassistant_custom_component"] = pahcc_mock
    sys.modules["pytest_homeassistant_custom_component.common"] = pahcc_common


import asyncio
import pytest


@pytest.fixture
def hass() -> MagicMock:
    """Provide a mock HomeAssistant instance fixture for tests."""
    hass_inst = MagicMock()
    hass_inst.data = {}

    service_handlers: dict[tuple[str, str], Any] = {}

    def has_service(domain: str, service: str) -> bool:
        return (domain, service) in service_handlers

    def async_register(domain: str, service: str, service_func: Any, schema: Any = None, *args: Any, **kwargs: Any) -> None:
        service_handlers[(domain, service)] = service_func


    async def async_call(
        domain: str, service: str, service_data: dict | None = None, blocking: bool = False, return_response: bool = False
    ) -> Any:
        key = (domain, service)
        if key not in service_handlers:
            from homeassistant.exceptions import ServiceNotFound
            raise ServiceNotFound(domain, service)
        func = service_handlers[key]
        call_obj = MagicMock()
        call_obj.data = service_data or {}
        res = func(call_obj)
        if asyncio.iscoroutine(res):
            res = await res
        return res

    services_mock = MagicMock()
    services_mock.has_service = has_service
    services_mock.async_register = async_register
    services_mock.async_call = AsyncMock(side_effect=async_call)

    hass_inst.services = services_mock

    async def async_add_executor_job(target: Any, *args: Any) -> Any:
        res = target(*args)
        if asyncio.iscoroutine(res):
            return await res
        return res

    hass_inst.async_add_executor_job = AsyncMock(side_effect=async_add_executor_job)

    def _create_task(coro):
        if inspect.iscoroutine(coro):
            coro.close()
        return MagicMock()

    hass_inst.async_create_task = MagicMock(side_effect=_create_task)
    return hass_inst



import inspect


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    """Run async test functions in an asyncio event loop."""
    if inspect.iscoroutinefunction(pyfuncitem.obj):
        testargs = {arg: pyfuncitem.funcargs[arg] for arg in pyfuncitem._fixtureinfo.argnames}
        asyncio.run(pyfuncitem.obj(**testargs))
        return True
    return None

