from shifu_sdk import (
    EdgeDevicePhase,
    init, add_health_checker, start,
    log_device_info,
    load_config,
)

# Required env:
#   EDGEDEVICE_NAME
# Optional:
#   EDGEDEVICE_NAMESPACE (defaults to 'devices')

init()
log_device_info()

# Load configuration from mounted ConfigMap files
config = load_config()
print("Loaded config:", config)

def checker() -> EdgeDevicePhase:
    # Replace with real logic
    # You can use the loaded config here
    return EdgeDevicePhase.RUNNING

add_health_checker(checker)
start()
