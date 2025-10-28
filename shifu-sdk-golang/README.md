# Shifu SDK — Go SDK for IoT Device Management

Minimal, production-ready Go SDK that provides both **global functions** (deprecated) and **Client-based API** for managing IoT devices in the Shifu framework.

## Features

- ✅ **Client-Based Architecture**: Modern, testable design with dependency injection
- 🔧 **Kubernetes Integration**: Automatic EdgeDevice status management
- 📊 **Health Monitoring**: Continuous device health checking and reporting
- 🎯 **Flexible Configuration**: Support for different namespaces and device types
- 🧪 **High Test Coverage**: 78.9% test coverage with comprehensive test suite
- 🚀 **Production Ready**: Used in real-world IoT deployments
- 🔄 **Backward Compatible**: Legacy global functions still supported (deprecated)

## Installation

### Prerequisites
- Go 1.21+
- Kubernetes cluster access (or local kubeconfig)
- Access to Shifu EdgeDevice CRDs

### Install
```bash
go get github.com/Edgenesis/shifu_sdk/shifu-sdk-golang
```

Or add to your `go.mod`:
```go
require (
    github.com/Edgenesis/shifu_sdk/shifu-sdk-golang latest
)
```

### Run Tests
```bash
cd shifu-sdk-golang
go test -v -cover
```

## Quick Start

### Environment Setup
```bash
export EDGEDEVICE_NAME="my-device"
export EDGEDEVICE_NAMESPACE="devices"  # Optional, defaults to "devices"
export KUBECONFIG="$HOME/.kube/config" # Optional, uses in-cluster config by default
```

### Basic Usage Examples

#### 1. EdgeDevice Management (Recommended Client API)

```go
package main

import (
    "context"
    "fmt"
    "log"

    shifusdk "github.com/Edgenesis/shifu_sdk/shifu-sdk-golang"
    "github.com/edgenesis/shifu/pkg/k8s/api/v1alpha1"
)

func main() {
    ctx := context.Background()

    // Create client with custom configuration
    client, err := shifusdk.NewClient(ctx, &shifusdk.Config{
        Namespace:  "devices",
        DeviceName: "my-temperature-sensor",
    })
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }

    // Get device information
    device, err := client.GetEdgeDevice()
    if err != nil {
        log.Fatalf("Failed to get device: %v", err)
    }
    fmt.Printf("Device: %s\n", device.Name)
    fmt.Printf("Status: %v\n", device.Status.EdgeDevicePhase)

    // Update device phase
    err = client.UpdatePhase(v1alpha1.EdgeDeviceRunning)
    if err != nil {
        log.Fatalf("Failed to update phase: %v", err)
    }
    fmt.Println("Phase updated successfully")
}
```

#### 2. Create Client from Environment Variables

```go
package main

import (
    "context"
    "log"

    shifusdk "github.com/Edgenesis/shifu_sdk/shifu-sdk-golang"
)

func main() {
    ctx := context.Background()

    // Create client using environment variables
    // Reads EDGEDEVICE_NAME, EDGEDEVICE_NAMESPACE, KUBECONFIG
    client, err := shifusdk.NewClientFromEnv(ctx)
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }

    device, err := client.GetEdgeDevice()
    if err != nil {
        log.Fatalf("Failed to get device: %v", err)
    }

    log.Printf("Device initialized: %s", device.Name)
}
```

#### 3. Health Monitoring with Custom Checker

```go
package main

import (
    "context"
    "log"
    "time"

    shifusdk "github.com/Edgenesis/shifu_sdk/shifu-sdk-golang"
    "github.com/edgenesis/shifu/pkg/k8s/api/v1alpha1"
)

func myHealthChecker() v1alpha1.EdgeDevicePhase {
    // Your health checking logic here
    // Example: ping device, check sensors, etc.

    deviceResponsive := checkDeviceConnection()
    if deviceResponsive {
        return v1alpha1.EdgeDeviceRunning
    }
    return v1alpha1.EdgeDeviceFailed
}

func checkDeviceConnection() bool {
    // Implement your device-specific health check
    return true
}

func main() {
    ctx := context.Background()

    client, err := shifusdk.NewClient(ctx, &shifusdk.Config{
        Namespace:           "devices",
        DeviceName:          "my-device",
        HealthChecker:       myHealthChecker,
        HealthCheckInterval: 5 * time.Second,
    })
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }

    // Start health monitoring loop (blocks)
    log.Println("Starting health monitoring...")
    if err := client.Start(ctx); err != nil {
        log.Fatalf("Health monitoring stopped: %v", err)
    }
}
```

#### 4. ConfigMap Configuration Loading

```go
package main

import (
    "fmt"
    "log"

    shifusdk "github.com/Edgenesis/shifu_sdk/shifu-sdk-golang"
)

type MyProtocolProperties struct {
    Protocol string `yaml:"protocol"`
    Address  string `yaml:"address"`
    Timeout  int    `yaml:"timeout"`
}

func main() {
    ctx := context.Background()

    client, err := shifusdk.NewClient(ctx, &shifusdk.Config{
        ConfigPath: "/etc/edgedevice/config",
    })
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }

    // Load complete configuration
    config, err := shifusdk.GetConfigMapTyped[MyProtocolProperties](client)
    if err != nil {
        log.Fatalf("Failed to load config: %v", err)
    }

    // Access driver properties
    fmt.Printf("Driver SKU: %s\n", config.DriverProperties.DriverSku)
    fmt.Printf("Driver Image: %s\n", config.DriverProperties.DriverImage)

    // Access instructions
    for name, instruction := range config.Instructions.Instructions {
        fmt.Printf("Instruction: %s\n", name)
        fmt.Printf("  Protocol: %s\n", instruction.ProtocolPropertyList.Protocol)
        fmt.Printf("  Address: %s\n", instruction.ProtocolPropertyList.Address)
    }
}
```

### Usage Patterns

#### Single Device Management
Use `NewClient()` or `NewClientFromEnv()` for managing one device with a structured, testable approach.

#### Multiple Device Management
Create multiple `Client` instances for managing different devices with isolated configurations.

```go
func main() {
    ctx := context.Background()

    // Create multiple clients for different devices
    tempSensor, _ := shifusdk.NewClient(ctx, &shifusdk.Config{
        DeviceName: "temperature-sensor",
        HealthChecker: tempHealthChecker,
    })

    humiditySensor, _ := shifusdk.NewClient(ctx, &shifusdk.Config{
        DeviceName: "humidity-sensor",
        HealthChecker: humidityHealthChecker,
    })

    // Start monitoring in separate goroutines
    go tempSensor.Start(ctx)
    go humiditySensor.Start(ctx)

    select {} // Block forever
}
```

## Configuration

### Environment Variables
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EDGEDEVICE_NAME` | Yes* | - | Name of your EdgeDevice |
| `EDGEDEVICE_NAMESPACE` | No | "devices" | Kubernetes namespace |
| `KUBECONFIG` | No | - | Path to kubeconfig (uses in-cluster config if not set) |

*Required when using `NewClientFromEnv()` or deprecated global functions

### Client Configuration Options

```go
type Config struct {
    Namespace           string              // Kubernetes namespace
    DeviceName          string              // EdgeDevice name
    KubeconfigPath      string              // Path to kubeconfig
    ConfigPath          string              // ConfigMap mount path
    HealthCheckInterval time.Duration       // Health check interval
    HealthChecker       HealthChecker       // Health check function
}
```

### ConfigMap Configuration

The SDK automatically reads configuration from ConfigMap files mounted in your pod at `/etc/edgedevice/config/` (configurable).

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
  instructions: |
    instructions:
      read_temperature:
        protocolPropertyList:
          protocol: "http"
          address: "/api/temperature"
          timeout: 5
      read_humidity:
        protocolPropertyList:
          protocol: "http"
          address: "/api/humidity"
```

#### Mounted Files Structure
```
/etc/edgedevice/config/
├── driverProperties    # Driver configuration
└── instructions        # Device commands/instructions
```

## Examples

### Complete Health Monitoring Example

```go
package main

import (
    "context"
    "fmt"
    "log"
    "net/http"
    "time"

    shifusdk "github.com/Edgenesis/shifu_sdk/shifu-sdk-golang"
    "github.com/edgenesis/shifu/pkg/k8s/api/v1alpha1"
)

type DeviceHealthChecker struct {
    client     *shifusdk.Client
    deviceURL  string
    timeout    time.Duration
}

func (d *DeviceHealthChecker) Check() v1alpha1.EdgeDevicePhase {
    // Load configuration for timeout
    config, err := d.client.GetConfigMap()
    if err != nil {
        log.Printf("Failed to load config: %v", err)
        return v1alpha1.EdgeDeviceFailed
    }

    // Perform HTTP health check
    httpClient := &http.Client{
        Timeout: d.timeout,
    }

    resp, err := httpClient.Get(d.deviceURL + "/health")
    if err != nil {
        log.Printf("Health check failed: %v", err)
        return v1alpha1.EdgeDeviceFailed
    }
    defer resp.Body.Close()

    if resp.StatusCode == http.StatusOK {
        log.Println("Health check passed")
        return v1alpha1.EdgeDeviceRunning
    }

    log.Printf("Health check failed with status: %d", resp.StatusCode)
    return v1alpha1.EdgeDeviceFailed
}

func main() {
    ctx := context.Background()

    // Create health checker
    checker := &DeviceHealthChecker{
        deviceURL: "http://device-endpoint",
        timeout:   5 * time.Second,
    }

    // Create client with health checker
    client, err := shifusdk.NewClient(ctx, &shifusdk.Config{
        DeviceName: "smart-sensor-01",
        HealthChecker: checker.Check,
        HealthCheckInterval: 10 * time.Second,
    })
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }

    checker.client = client

    // Start monitoring
    log.Println("Starting health monitoring...")
    if err := client.Start(ctx); err != nil {
        log.Fatalf("Monitoring stopped: %v", err)
    }
}
```

### Multi-Device Management Example

```go
package main

import (
    "context"
    "fmt"
    "log"
    "sync"

    shifusdk "github.com/Edgenesis/shifu_sdk/shifu-sdk-golang"
    "github.com/edgenesis/shifu/pkg/k8s/api/v1alpha1"
)

type DeviceConfig struct {
    Name          string
    HealthChecker shifusdk.HealthChecker
}

func createDeviceManager(ctx context.Context, configs []DeviceConfig) ([]*shifusdk.Client, error) {
    clients := make([]*shifusdk.Client, 0, len(configs))

    for _, cfg := range configs {
        client, err := shifusdk.NewClient(ctx, &shifusdk.Config{
            DeviceName:    cfg.Name,
            HealthChecker: cfg.HealthChecker,
        })
        if err != nil {
            return nil, fmt.Errorf("failed to create client for %s: %w", cfg.Name, err)
        }
        clients = append(clients, client)
    }

    return clients, nil
}

func tempSensorHealth() v1alpha1.EdgeDevicePhase {
    // Temperature sensor specific health check
    return v1alpha1.EdgeDeviceRunning
}

func humiditySensorHealth() v1alpha1.EdgeDevicePhase {
    // Humidity sensor specific health check
    return v1alpha1.EdgeDeviceRunning
}

func main() {
    ctx := context.Background()

    deviceConfigs := []DeviceConfig{
        {Name: "temperature-sensor", HealthChecker: tempSensorHealth},
        {Name: "humidity-sensor", HealthChecker: humiditySensorHealth},
    }

    clients, err := createDeviceManager(ctx, deviceConfigs)
    if err != nil {
        log.Fatalf("Failed to create device manager: %v", err)
    }

    // Start monitoring all devices in parallel
    var wg sync.WaitGroup
    for _, client := range clients {
        wg.Add(1)
        go func(c *shifusdk.Client) {
            defer wg.Done()
            if err := c.Start(ctx); err != nil {
                log.Printf("Client stopped: %v", err)
            }
        }(client)
    }

    log.Println("All devices monitoring started")
    wg.Wait()
}
```

### Configuration-Driven Device Setup

```go
package main

import (
    "context"
    "fmt"
    "log"

    shifusdk "github.com/Edgenesis/shifu_sdk/shifu-sdk-golang"
    "github.com/edgenesis/shifu/pkg/k8s/api/v1alpha1"
)

type DriverProperties struct {
    DriverSku   string `yaml:"driverSku"`
    DriverImage string `yaml:"driverImage"`
    Enabled     bool   `yaml:"enabled"`
    Timeout     int    `yaml:"timeout"`
}

func setupDeviceFromConfig(ctx context.Context) (*shifusdk.Client, error) {
    // Create client first to load config
    client, err := shifusdk.NewClient(ctx, &shifusdk.Config{
        ConfigPath: "/etc/edgedevice/config",
    })
    if err != nil {
        return nil, fmt.Errorf("failed to create client: %w", err)
    }

    // Load configuration
    config, err := shifusdk.GetConfigMapTyped[DriverProperties](client)
    if err != nil {
        return nil, fmt.Errorf("failed to load config: %w", err)
    }

    props := config.DriverProperties
    log.Printf("Setting up device: %s", props.DriverSku)
    log.Printf("Timeout: %ds, Enabled: %v", props.Timeout, props.Enabled)

    if !props.Enabled {
        return nil, fmt.Errorf("device is disabled in configuration")
    }

    // Create health checker based on config
    healthChecker := func() v1alpha1.EdgeDevicePhase {
        device, err := client.GetEdgeDevice()
        if err != nil {
            return v1alpha1.EdgeDeviceFailed
        }

        if device.Spec.Protocol != nil {
            return v1alpha1.EdgeDeviceRunning
        }
        return v1alpha1.EdgeDevicePending
    }

    client.SetHealthChecker(healthChecker)

    log.Printf("Device %s setup completed successfully", props.DriverSku)
    return client, nil
}

func main() {
    ctx := context.Background()

    client, err := setupDeviceFromConfig(ctx)
    if err != nil {
        log.Fatalf("Failed to setup device: %v", err)
    }

    log.Println("Device ready for monitoring")
    if err := client.Start(ctx); err != nil {
        log.Fatalf("Monitoring failed: %v", err)
    }
}
```

## API Reference

### EdgeDevicePhase Constants
```go
const (
    EdgeDeviceRunning = "Running"  // Device is operational
    EdgeDeviceFailed  = "Failed"   // Device has encountered an error
    EdgeDevicePending = "Pending"  // Device is initializing
    EdgeDeviceUnknown = "Unknown"  // Device status is unclear
)
```

### Client Creation Functions
- `NewClient(ctx context.Context, cfg *Config) (*Client, error)` - Create a new client with custom configuration
- `NewClientFromEnv(ctx context.Context) (*Client, error)` - Create a client using environment variables

### Client Methods
- `Start(ctx context.Context) error` - Start health monitoring loop
- `GetEdgeDevice() (*v1alpha1.EdgeDevice, error)` - Get EdgeDevice resource from Kubernetes
- `UpdatePhase(phase v1alpha1.EdgeDevicePhase) error` - Update device status phase
- `SetHealthChecker(hc HealthChecker)` - Set/update health checker function
- `GetConfigMap() (*DeviceShifuConfig[any], error)` - Load configuration from ConfigMap

### Configuration Functions
- `GetConfigMapTyped[T any](c *Client) (*DeviceShifuConfig[T], error)` - Load typed configuration from ConfigMap

### Configuration Types
```go
type Config struct {
    Namespace           string
    DeviceName          string
    KubeconfigPath      string
    ConfigPath          string
    HealthCheckInterval time.Duration
    HealthChecker       HealthChecker
}

type DeviceShifuConfig[T any] struct {
    DriverProperties DeviceShifuDriverProperties
    Instructions     DeviceShifuInstructions[T]
}

type DeviceShifuDriverProperties struct {
    DriverSku   string
    DriverImage string
}

type HealthChecker func() v1alpha1.EdgeDevicePhase
```

### Deprecated Global Functions
These functions are maintained for backward compatibility but are deprecated:
- `Start(ctx context.Context)` - **Deprecated**: Use `Client.Start()` instead
- `GetEdgedevice() (*v1alpha1.EdgeDevice, error)` - **Deprecated**: Use `Client.GetEdgeDevice()` instead
- `UpdatePhase(phase v1alpha1.EdgeDevicePhase) error` - **Deprecated**: Use `Client.UpdatePhase()` instead
- `GetConfigMap[T any]() (*DeviceShifuConfig[T], error)` - **Deprecated**: Use `GetConfigMapTyped[T](client)` instead
- `AddHealthChecker(fn func() v1alpha1.EdgeDevicePhase)` - **Deprecated**: Use `Client.SetHealthChecker()` instead

## Troubleshooting

### Common Issues

#### Import Error
```bash
package github.com/edgenesis/shifu/shifu-sdk-golang: no Go files in ...
```
**Solution:**
```bash
go mod tidy
go mod download
```

#### Environment Variable Missing
```bash
Error: EDGEDEVICE_NAME environment variable is required
```
**Solution:**
```bash
export EDGEDEVICE_NAME="your-device-name"
```

#### Kubernetes Connection Failed
```bash
Error: failed to get rest config: unable to load in-cluster configuration
```
**Solution:**
- Running in cluster: Ensure proper RBAC permissions
- Running locally: Set `KUBECONFIG` environment variable
```bash
export KUBECONFIG="$HOME/.kube/config"
```

#### Device Not Found
```bash
Error: EdgeDevice "my-device" not found
```
**Solution:**
```bash
kubectl get edgedevices -n devices
kubectl describe edgedevice my-device -n devices
```

### Debug Mode
Enable verbose logging from the logger package:
```go
import "github.com/edgenesis/shifu/pkg/logger"

func main() {
    // Enable debug logging
    logger.SetLevel(logger.DebugLevel)

    // Your code here
}
```

## Testing

The SDK includes comprehensive tests with 78.9% coverage.

### Run Tests
```bash
# Run all tests
go test -v

# Run with coverage
go test -cover

# Generate coverage report
go test -coverprofile=coverage.out
go tool cover -html=coverage.out
```

### Writing Tests
The SDK provides interfaces and dependency injection for easy mocking:

```go
type mockClient struct{}

func (m *mockClient) Get() *rest.Request {
    // Mock implementation
}

func (m *mockClient) Put() *rest.Request {
    // Mock implementation
}

func TestMyFunction(t *testing.T) {
    client := &Client{
        restClient: &mockClient{},
    }
    // Test your code
}
```

## Migration Guide

### Migrating from Global Functions to Client API

**Before (Deprecated):**
```go
shifusdk.AddHealthChecker(myHealthChecker)
shifusdk.Start(ctx)
```

**After (Recommended):**
```go
client, _ := shifusdk.NewClient(ctx, &shifusdk.Config{
    HealthChecker: myHealthChecker,
})
client.Start(ctx)
```

### Benefits of Migration
- ✅ Better testability with dependency injection
- ✅ Multiple device management
- ✅ No global state
- ✅ Explicit error handling
- ✅ Better IDE support and type safety

## Support

For issues and questions:
1. Check the [examples](#examples) section
2. Review the [troubleshooting](#troubleshooting) section
3. Check the source code documentation
4. Open an issue on GitHub

## License

This SDK is part of the Shifu project. See the main Shifu repository for license information.

---

**Happy coding with Shifu Go SDK! 🚀**
