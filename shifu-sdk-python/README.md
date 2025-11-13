# Shifu SDK — Python SDK for IoT Device Management

Minimal, installable Python SDK that provides both **global functions** and **DeviceShifu class** for managing IoT devices in the Shifu framework.

## Features

- ✅ **Global Functions**: Simple single-device management (backward compatible)
- 🚀 **DeviceShifu Class**: Multiple device management with isolated instances
- 🔧 **Kubernetes Integration**: Automatic EdgeDevice status management
- 📊 **Health Monitoring**: Continuous device health checking and reporting
- 🎯 **Flexible Configuration**: Support for different namespaces and device types

## Installation

### Prerequisites
- Python 3.8+
- Kubernetes cluster access (or local kubeconfig)
- `kubernetes>=28.1.0` package
- **Shifu Control Plane**: Install the official [Shifu IoT Gateway](https://github.com/Edgenesis/shifu) in your cluster
  ```bash
  kubectl apply -f https://raw.githubusercontent.com/Edgenesis/shifu/main/pkg/k8s/crd/install/shifu_install.yml
  ```
- **RBAC Permissions**: When using official Shifu, RBAC is automatically configured. For custom setups, see [RBAC_SETUP.md](RBAC_SETUP.md)

### Install
```bash
# Clone and install in editable mode
pip install git+https://github.com/Edgenesis/Shifu_sdk.git#subdirectory=shifu-sdk-python
 

#run tests
git clone <your-repo-url>
cd tests
python test_imports.py
python test_edgedevice_functions.py
python test_configmap_functions.py
```

## Quick Start

### Environment Setup
```bash
export EDGEDEVICE_NAME="my-device"
export EDGEDEVICE_NAMESPACE="deviceshifu"  # Optional, defaults to "deviceshifu"
```

### Basic Usage Examples
Check test cases in /tests
#### 1. EdgeDevice Management (Global Functions)
```python
from shifu_sdk import init, get_edgedevice, update_phase, EdgeDevicePhase

# Initialize SDK
init()

# Get device information
device = get_edgedevice()
print(f"Device: {device['metadata']['name']}")
print(f"Status: {device['status']['edgedevicephase']}")

# Update device phase
success = update_phase(EdgeDevicePhase.RUNNING)
print(f"Update successful: {success}")
```

#### 2. Health Monitoring
```python
from shifu_sdk import init, add_health_checker, start, EdgeDevicePhase

def my_health_checker() -> EdgeDevicePhase:
    """Check device health and return appropriate phase."""
    # Your health checking logic here
    try:
        # Example: ping device, check sensors, etc.
        device_responsive = check_device_connection()
        if device_responsive:
            return EdgeDevicePhase.RUNNING
        else:
            return EdgeDevicePhase.FAILED
    except Exception:
        return EdgeDevicePhase.FAILED

# Setup and start monitoring
init()
add_health_checker(my_health_checker)
start()  # Runs continuous health monitoring loop
```

#### 3. ConfigMap Configuration Loading
```python
from shifu_sdk import load_config, get_instructions, get_driver_properties, get_telemetries

# Load complete configuration from mounted ConfigMap files
config = load_config()  # Reads from /etc/edgedevice/config/

# Access different sections
driver_props = config["driverProperties"]
instructions = config["instructions"]["instructions"]
telemetries = config["telemetries"]

# Or get specific sections directly
instructions_only = get_instructions()
driver_properties_only = get_driver_properties() 
telemetries_only = get_telemetries()

print(f"Driver SKU: {driver_properties_only.get('driverSku')}")
print(f"Available instructions: {list(instructions_only.keys())}")
```

#### 4. DeviceShifu Class (Object-Oriented)
```python
from shifu_sdk import DeviceShifu, EdgeDevicePhase

# Create and initialize device instance
device = DeviceShifu("my-temperature-sensor")
device.init()

# Use instance methods
device_info = device.get_edgedevice()
device.update_phase(EdgeDevicePhase.RUNNING)

# Add health checker to instance
def temp_sensor_health() -> EdgeDevicePhase:
    # Check temperature sensor specifically
    return EdgeDevicePhase.RUNNING

device.add_health_checker(temp_sensor_health)
# device.start()  # Uncomment to start monitoring loop
```

### Usage Patterns

#### Single Device Management
Use global functions for managing one device with simple setup.

#### Multiple Device Management  
Use DeviceShifu class for managing multiple devices with isolated instances.

## Configuration

### Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EDGEDEVICE_NAME` | Yes | - | Name of your EdgeDevice |
| `EDGEDEVICE_NAMESPACE` | No | "deviceshifu" | Kubernetes namespace (use "deviceshifu" for official Shifu) |
| `SHIFU_API_GROUP` | No | "shifu.edgenesis.io" | Kubernetes API group for EdgeDevices |
| `SHIFU_API_VERSION` | No | "v1alpha1" | Kubernetes API version for EdgeDevices |
| `SHIFU_API_PLURAL` | No | "edgedevices" | Kubernetes API plural name for EdgeDevices |

### ConfigMap Configuration

The SDK automatically reads configuration from ConfigMap files mounted in your pod. These files are typically mounted at `/etc/edgedevice/config/` and contain device-specific settings.

#### Expected ConfigMap Structure
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-device-configmap
  namespace: deviceshifu
data:
  driverProperties: |
    driverSku: "SENSOR-001"
    driverImage: "my-driver:v1.0"
    enabled: true
    timeout: 30
  instructions: |
    instructions:
      read_temperature:
        command: "GET /temperature"
        timeout: 5
      read_humidity:
        command: "GET /humidity"
        method: "POST"
  telemetries: |
    telemetrySettings:
      interval: 10
      enabled: true
    telemetries:
      temperature:
        properties:
          - name: "value"
            type: "float"
            unit: "celsius"
```

#### Mounted Files Structure
When the ConfigMap is mounted, these files are created:
```
/etc/edgedevice/config/
├── driverProperties    # Driver configuration
├── instructions        # Device commands/instructions
└── telemetries         # Telemetry definitions
```

### Kubernetes API Configuration
```bash
# Default values (standard Shifu installation)
export SHIFU_API_GROUP="shifu.edgenesis.io"
export SHIFU_API_VERSION="v1alpha1"
export SHIFU_API_PLURAL="edgedevices"
```

## Examples

- **`tests/test_edgedevice_functions.py`** - Single device using SDK global functions
- **`tests/test_configmap_functions.py`** - ConfigMap configuration loading

## Advanced Usage

### Complete Health Monitoring Example
```python
from shifu_sdk import DeviceShifu, EdgeDevicePhase, load_config
import requests
import time

def create_smart_health_checker(device_name: str):
    """Create a health checker that uses ConfigMap configuration."""
    
    def health_checker() -> EdgeDevicePhase:
        try:
            # Load device configuration
            config = load_config()
            driver_props = config.get("driverProperties", {})
            
            # Check if device is enabled in config
            if not driver_props.get("enabled", True):
                print(f"{device_name}: Device disabled in configuration")
                return EdgeDevicePhase.FAILED
            
            # Get device endpoint from EdgeDevice spec  
            device = DeviceShifu(device_name)
            device.init()
            device_address = device.get_device_address()
            
            # Perform actual health check
            response = requests.get(f"http://{device_address}/health", 
                                   timeout=driver_props.get("timeout", 5))
            
            if response.status_code == 200:
                print(f"{device_name}: Health check passed")
                return EdgeDevicePhase.RUNNING
            else:
                print(f"{device_name}: Health check failed with status {response.status_code}")
                return EdgeDevicePhase.FAILED
                
        except Exception as e:
            print(f"{device_name}: Health check error: {e}")
            return EdgeDevicePhase.FAILED
    
    return health_checker

# Usage
device = DeviceShifu("temperature-sensor-01")
device.init()

health_checker = create_smart_health_checker("temperature-sensor-01")
device.add_health_checker(health_checker)
device.start()  # Start continuous monitoring
```

### Multi-Device Management Example
```python
from shifu_sdk import DeviceShifu, EdgeDevicePhase, get_instructions

def create_device_manager(device_configs):
    """Manage multiple devices with individual health checkers."""
    devices = {}
    
    for device_config in device_configs:
        device_name = device_config["name"]
        device = DeviceShifu(device_name)
        device.init()
        
        # Load device-specific instructions
        instructions = get_instructions()
        
        def create_health_checker(name, check_instruction):
            def health_checker() -> EdgeDevicePhase:
                try:
                    # Use device-specific instruction for health check
                    device_addr = device.get_device_address()
                    instruction_config = instructions.get(check_instruction, {})
                    
                    if instruction_config:
                        # Perform instruction-based health check
                        print(f"{name}: Running health check with {check_instruction}")
                        return EdgeDevicePhase.RUNNING
                    else:
                        print(f"{name}: No health check instruction found")
                        return EdgeDevicePhase.UNKNOWN
                except Exception as e:
                    print(f"{name}: Health check failed: {e}")
                    return EdgeDevicePhase.FAILED
            return health_checker
        
        # Register health checker
        health_checker = create_health_checker(device_name, device_config.get("health_instruction"))
        device.add_health_checker(health_checker)
        
        devices[device_name] = device
    
    return devices

# Usage
device_configs = [
    {"name": "temperature-sensor", "health_instruction": "read_temperature"},
    {"name": "humidity-sensor", "health_instruction": "read_humidity"},
    {"name": "pressure-sensor", "health_instruction": "read_pressure"}
]

devices = create_device_manager(device_configs)

# Start monitoring all devices
for device_name, device in devices.items():
    print(f"Starting monitoring for {device_name}")
    # In real usage, you'd start each in a separate thread
    # device.start()
```

### Configuration-Driven Device Setup
```python
from shifu_sdk import load_config, get_driver_properties, DeviceShifu, EdgeDevicePhase

def setup_device_from_config():
    """Setup device using ConfigMap configuration."""
    
    # Load configuration
    config = load_config()
    driver_props = get_driver_properties()
    
    # Get device name from config
    device_sku = driver_props.get("driverSku", "unknown-device")
    
    # Create device instance
    device = DeviceShifu(f"device-{device_sku.lower()}")
    
    # Configure based on driver properties
    timeout = driver_props.get("timeout", 30)
    enabled = driver_props.get("enabled", True)
    
    print(f"Setting up device: {device_sku}")
    print(f"Timeout: {timeout}s, Enabled: {enabled}")
    
    if not enabled:
        print("Device is disabled in configuration")
        return None
    
    def config_based_health_checker() -> EdgeDevicePhase:
        """Health checker that uses configuration values."""
        try:
            # Use timeout from configuration
            device.init()
            device_info = device.get_edgedevice()
            
            # Check if device is properly configured
            if device_info.get("spec", {}).get("protocol"):
                return EdgeDevicePhase.RUNNING
            else:
                return EdgeDevicePhase.PENDING
                
        except Exception:
            return EdgeDevicePhase.FAILED
    
    # Setup with configuration-based health checker
    success = device.setup_device_shifu(config_based_health_checker)
    if success:
        print(f"Device {device_sku} setup completed successfully")
        return device
    else:
        print(f"Device {device_sku} setup failed")
        return None

# Usage
device = setup_device_from_config()
if device:
    print("Device ready for monitoring")
    # device.start()  # Uncomment to start monitoring
```

## API Reference

### EdgeDevicePhase Enum
- `RUNNING`: Device is operational
- `FAILED`: Device has encountered an error  
- `PENDING`: Device is initializing
- `UNKNOWN`: Device status is unclear

### EdgeDevice Management Functions
- `init()` - Initialize SDK and Kubernetes client
- `get_edgedevice()` - Get EdgeDevice configuration from Kubernetes API (requires RBAC permissions)
- `update_phase(phase)` - Update device status phase (requires RBAC permissions)
- `add_health_checker(checker)` - Register health check function
- `start()` - Start health monitoring loop (3-second intervals)
- `get_device_config()` - Get device configuration from EdgeDevice spec
- `get_device_address()` - Get device address from EdgeDevice spec
- `get_device_protocol()` - Get device protocol from EdgeDevice spec
- `log_device_info()` - Log device information to console
- `setup_device_shifu(name, checker)` - Complete setup function

### ConfigMap Configuration Functions
- `load_config(config_dir="/etc/edgedevice/config")` - Load complete configuration from mounted ConfigMap files
- `get_instructions(config_dir="/etc/edgedevice/config")` - Get only instructions from ConfigMap
- `get_driver_properties(config_dir="/etc/edgedevice/config")` - Get only driver properties from ConfigMap
- `get_telemetries(config_dir="/etc/edgedevice/config")` - Get only telemetries from ConfigMap

### DeviceShifu Class
- `DeviceShifu(device_name, namespace="deviceshifu")` - Create device instance
- All EdgeDevice management methods available as instance methods
- `device.setup_device_shifu(checker)` - Instance-specific setup

## Troubleshooting

### Common Issues

#### Import Error
```bash
ModuleNotFoundError: No module named 'shifu_sdk'
```
**Solution:**
```bash
source venv/bin/activate
pip install -e .
```

#### Environment Variable Missing
```bash
ValueError: EDGEDEVICE_NAME environment variable is required
```
**Solution:**
```bash
export EDGEDEVICE_NAME="your-device-name"
```

#### Kubernetes Connection Failed
```bash
Failed to load Kubernetes config
```
**Solution:** Ensure kubectl works and cluster is accessible

#### Device Not Found
```bash
Failed to get EdgeDevice
```
**Solution:**
```bash
kubectl get edgedevices -n deviceshifu
```

### Debug Mode
Enable debug logging in your application code.

## Support

For issues and questions:
1. Check the examples directory
2. Review the troubleshooting section
3. Check source code in `src/shifu_sdk/core.py`

---

**Happy coding with Shifu SDK! 🚀**
