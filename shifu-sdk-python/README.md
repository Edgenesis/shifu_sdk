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

### Install
```bash
# Clone and install in editable mode
git clone <your-repo-url>
cd shifu-sdk
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## Quick Start

### Environment Setup
```bash
export EDGEDEVICE_NAME="my-device"
export EDGEDEVICE_NAMESPACE="devices"  # Optional, defaults to "devices"
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
| `EDGEDEVICE_NAMESPACE` | No | "devices" | Kubernetes namespace |
| `SHIFU_API_GROUP` | No | "shifu.edgenesis.io" | Kubernetes API group for EdgeDevices |
| `SHIFU_API_VERSION` | No | "v1alpha1" | Kubernetes API version for EdgeDevices |
| `SHIFU_API_PLURAL` | No | "edgedevices" | Kubernetes API plural name for EdgeDevices |

### Kubernetes API Configuration
```bash
# Default values (standard Shifu installation)
export SHIFU_API_GROUP="shifu.edgenesis.io"
export SHIFU_API_VERSION="v1alpha1"
export SHIFU_API_PLURAL="edgedevices"

# Custom values (for custom installations)
export SHIFU_API_GROUP="custom.domain.com"
export SHIFU_API_VERSION="v2beta1"
export SHIFU_API_PLURAL="customdevices"
```

## Examples

- **`examples/basic.py`** - Single device using global functions
- **`examples/multiple_devices.py`** - Multiple devices using DeviceShifu class

## API Reference

### EdgeDevicePhase Enum
- `RUNNING`: Device is operational
- `FAILED`: Device has encountered an error  
- `PENDING`: Device is initializing
- `UNKNOWN`: Device status is unclear

### Global Functions
- `init()` - Initialize SDK and Kubernetes client
- `get_edgedevice()` - Get EdgeDevice configuration
- `update_phase(phase)` - Update device status phase
- `add_health_checker(checker)` - Register health check function
- `start()` - Start health monitoring loop (3-second intervals)
- `get_device_config()` - Get device configuration
- `get_device_address()` - Get device address
- `get_device_protocol()` - Get device protocol
- `log_device_info()` - Log device information
- `setup_device_shifu(name, checker)` - Complete setup function

### DeviceShifu Class
- `DeviceShifu(name, namespace)` - Create device instance
- All methods from global functions available as instance methods

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
kubectl get edgedevices -n devices
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
