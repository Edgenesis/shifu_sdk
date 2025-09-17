def test_imports():
    from shifu_sdk import (
        EdgeDevicePhase, init, get_edgedevice, update_phase,
        add_health_checker, start, get_device_config, get_device_address,
        get_device_protocol, log_device_info, setup_device_shifu
    )
    assert EdgeDevicePhase.RUNNING.value == "Running"
