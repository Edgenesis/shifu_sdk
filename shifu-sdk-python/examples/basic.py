from shifu_sdk import (
    EdgeDevicePhase,
    init, add_health_checker, start,
    log_device_info,
)

# Required env:
#   EDGEDEVICE_NAME
# Optional:
#   EDGEDEVICE_NAMESPACE (defaults to 'devices')

init()
log_device_info()

def checker() -> EdgeDevicePhase:
    # Replace with real logic
    return EdgeDevicePhase.RUNNING

add_health_checker(checker)
start()
