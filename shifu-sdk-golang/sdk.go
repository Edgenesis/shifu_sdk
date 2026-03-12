package shifusdk

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/edgenesis/shifu/pkg/k8s/api/v1alpha1"
	"github.com/edgenesis/shifu/pkg/logger"
	"gopkg.in/yaml.v3"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/runtime/serializer"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/kubectl/pkg/scheme"
)

const (
	DefaultConfigPath          = "/etc/edgedevice/config"
	DefaultNamespace           = "devices"
	DefaultHealthCheckInterval = 30 * time.Second
)

// EdgeDeviceClient interface for Kubernetes API interactions
type EdgeDeviceClient interface {
	Get() *rest.Request
	Put() *rest.Request
}

// HealthChecker is a function that returns the current health phase
type HealthChecker func() v1alpha1.EdgeDevicePhase

// ConfigLoader interface for loading configuration
type ConfigLoader interface {
	LoadInstructions(path string) (*DeviceShifuInstructions[any], error)
}

// Client represents the Shifu SDK client with all dependencies
type Client struct {
	restClient          EdgeDeviceClient
	healthChecker       HealthChecker
	edgedeviceNamespace string
	edgedeviceName      string
	configPath          string
	healthCheckInterval time.Duration
	configLoader        ConfigLoader
	ctx                 context.Context
}

// Config holds configuration for creating a new Client
type Config struct {
	Namespace           string
	DeviceName          string
	KubeconfigPath      string
	ConfigPath          string
	HealthCheckInterval time.Duration
	HealthChecker       HealthChecker
}

// DeviceShifuInstruction represents a single instruction configuration
type DeviceShifuInstruction[T any] struct {
	ProtocolPropertyList T `yaml:"protocolPropertyList,omitempty"`
}

// DeviceShifuInstructions represents the instructions configuration
type DeviceShifuInstructions[T any] struct {
	Instructions map[string]*DeviceShifuInstruction[T] `yaml:"instructions"`
}

// DeviceShifuDriverProperties represents driver configuration
type DeviceShifuDriverProperties struct {
	DriverSku   string `yaml:"driverSku,omitempty"`
	DriverImage string `yaml:"driverImage,omitempty"`
}

// DeviceShifuConfig represents the complete configuration from configmap
type DeviceShifuConfig[T any] struct {
	DriverProperties DeviceShifuDriverProperties `yaml:"driverProperties,omitempty"`
	Instructions     DeviceShifuInstructions[T]  `yaml:"instructions,omitempty"`
}

// defaultConfigLoader implements ConfigLoader
type defaultConfigLoader struct{}

func (d *defaultConfigLoader) LoadInstructions(path string) (*DeviceShifuInstructions[any], error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read instructions file: %w", err)
	}

	var instructions DeviceShifuInstructions[any]
	if err := yaml.Unmarshal(data, &instructions); err != nil {
		return nil, fmt.Errorf("failed to unmarshal instructions: %w", err)
	}

	log.Printf("Loaded %d instructions from configmap file", len(instructions.Instructions))
	return &instructions, nil
}

// NewClient creates a new Shifu SDK client with the given configuration
func NewClient(ctx context.Context, cfg *Config) (*Client, error) {
	if ctx == nil {
		ctx = context.Background()
	}

	if cfg == nil {
		cfg = &Config{}
	}

	// Set defaults
	if cfg.Namespace == "" {
		cfg.Namespace = getEnv("EDGEDEVICE_NAMESPACE", DefaultNamespace)
	}
	if cfg.DeviceName == "" {
		cfg.DeviceName = os.Getenv("EDGEDEVICE_NAME")
	}
	if cfg.ConfigPath == "" {
		cfg.ConfigPath = DefaultConfigPath
	}
	if cfg.HealthCheckInterval == 0 {
		cfg.HealthCheckInterval = DefaultHealthCheckInterval
	}
	if cfg.KubeconfigPath == "" {
		cfg.KubeconfigPath = os.Getenv("KUBECONFIG")
	}

	// Create REST config
	restConfig, err := getRestConfig(cfg.KubeconfigPath)
	if err != nil {
		return nil, fmt.Errorf("failed to get rest config: %w", err)
	}

	// Create REST client
	restClient, err := newEdgeDeviceRestClient(restConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create edge device rest client: %w", err)
	}

	client := &Client{
		restClient:          restClient,
		healthChecker:       cfg.HealthChecker,
		edgedeviceNamespace: cfg.Namespace,
		edgedeviceName:      cfg.DeviceName,
		configPath:          cfg.ConfigPath,
		healthCheckInterval: cfg.HealthCheckInterval,
		configLoader:        &defaultConfigLoader{},
		ctx:                 ctx,
	}

	logger.Infof("Edge device rest client initialized successfully")
	return client, nil
}

// NewClientFromEnv creates a new client using environment variables
func NewClientFromEnv(ctx context.Context) (*Client, error) {
	return NewClient(ctx, &Config{})
}

// Start begins the health check loop
func (c *Client) Start(ctx context.Context) error {
	if ctx == nil {
		ctx = context.Background()
	}

	if c.restClient == nil {
		return fmt.Errorf("edge device rest client is not initialized")
	}

	if c.healthChecker == nil {
		log.Println("no health checker configured, blocking indefinitely")
		<-ctx.Done()
		return ctx.Err()
	}

	ticker := time.NewTicker(c.healthCheckInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			phase := c.healthChecker()
			if err := c.updatePhase(ctx, phase); err != nil {
				logger.Errorf("failed to update edge device phase: %v", err)
			}
		case <-ctx.Done():
			return ctx.Err()
		}
	}
}

// GetEdgeDevice retrieves the EdgeDevice resource
func (c *Client) GetEdgeDevice() (*v1alpha1.EdgeDevice, error) {
	return c.getEdgeDevice(c.ctx)
}

func (c *Client) getEdgeDevice(ctx context.Context) (*v1alpha1.EdgeDevice, error) {
	if ctx == nil {
		ctx = context.Background()
	}

	if c.restClient == nil {
		return nil, fmt.Errorf("rest client is not initialized")
	}

	ed := &v1alpha1.EdgeDevice{}
	err := c.restClient.Get().
		Namespace(c.edgedeviceNamespace).
		Resource("edgedevices").
		Name(c.edgedeviceName).
		Do(ctx).
		Into(ed)
	if err != nil {
		logger.Errorf("Error GET EdgeDevice resource: %v", err)
		return nil, err
	}
	return ed, nil
}

// UpdatePhase updates the EdgeDevice phase
func (c *Client) UpdatePhase(phase v1alpha1.EdgeDevicePhase) error {
	return c.updatePhase(c.ctx, phase)
}

func (c *Client) updatePhase(ctx context.Context, phase v1alpha1.EdgeDevicePhase) error {
	if c.restClient == nil {
		return fmt.Errorf("rest client is not initialized")
	}

	if ctx == nil {
		ctx = context.Background()
	}

	ed, err := c.getEdgeDevice(ctx)
	if err != nil {
		return err
	}

	// Skip update if phase hasn't changed
	if ed.Status.EdgeDevicePhase != nil && *ed.Status.EdgeDevicePhase == phase {
		logger.Debugf("EdgeDevice phase is already set to %s, no update needed", phase)
		return nil
	}

	logger.Debugf("Updating EdgeDevice phase from %v to %s", ed.Status.EdgeDevicePhase, phase)

	ed.Status.EdgeDevicePhase = &phase
	err = c.restClient.Put().
		Namespace(c.edgedeviceNamespace).
		Resource("edgedevices").
		Name(c.edgedeviceName).
		Body(ed).
		Do(ctx).
		Error()
	if err != nil {
		logger.Errorf("Error PUT EdgeDevice resource: %v", err)
		return err
	}
	return nil
}

// GetConfigMap loads configuration from the configmap
func (c *Client) GetConfigMap() (*DeviceShifuConfig[any], error) {
	instructions, err := c.loadInstructionsFromFile(c.configPath + "/instructions")
	if err != nil {
		log.Printf("Warning: Failed to load instructions from configmap file: %v", err)
		// Return empty instructions instead of failing
		instructions = &DeviceShifuInstructions[any]{
			Instructions: make(map[string]*DeviceShifuInstruction[any]),
		}
	}

	driverProperties, err := loadDriverPropertiesFromFile(c.configPath + "/driverProperties")
	if err != nil {
		log.Printf("Warning: Failed to load driver properties from configmap file: %v", err)
		driverProperties = &DeviceShifuDriverProperties{}
	}

	return &DeviceShifuConfig[any]{
		DriverProperties: *driverProperties,
		Instructions:     *instructions,
	}, nil
}

// GetConfigMapTyped loads configuration with a specific type parameter
func GetConfigMapTyped[T any](c *Client) (*DeviceShifuConfig[T], error) {
	instructions, err := loadInstructionsFromFile[T](c.configPath + "/instructions")
	if err != nil {
		log.Printf("Warning: Failed to load instructions from configmap file: %v", err)
		instructions = &DeviceShifuInstructions[T]{
			Instructions: make(map[string]*DeviceShifuInstruction[T]),
		}
	}

	driverProperties, err := loadDriverPropertiesFromFile(c.configPath + "/driverProperties")
	if err != nil {
		log.Printf("Warning: Failed to load driver properties from configmap file: %v", err)
		driverProperties = &DeviceShifuDriverProperties{}
	}

	return &DeviceShifuConfig[T]{
		DriverProperties: *driverProperties,
		Instructions:     *instructions,
	}, nil
}

// SetHealthChecker sets the health checker function
func (c *Client) SetHealthChecker(hc HealthChecker) {
	c.healthChecker = hc
}

// loadInstructionsFromFile loads instructions from a file
func (c *Client) loadInstructionsFromFile(filePath string) (*DeviceShifuInstructions[any], error) {
	return c.configLoader.LoadInstructions(filePath)
}

// loadInstructionsFromFile loads typed instructions from a file (generic function)
func loadInstructionsFromFile[T any](filePath string) (*DeviceShifuInstructions[T], error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read instructions file: %w", err)
	}

	var instructions DeviceShifuInstructions[T]
	if err := yaml.Unmarshal(data, &instructions); err != nil {
		return nil, fmt.Errorf("failed to unmarshal instructions: %w", err)
	}

	log.Printf("Loaded %d instructions from configmap file", len(instructions.Instructions))
	return &instructions, nil
}

// loadDriverPropertiesFromFile loads driver properties from a file
func loadDriverPropertiesFromFile(filePath string) (*DeviceShifuDriverProperties, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read driverProperties file: %w", err)
	}

	var driverProperties DeviceShifuDriverProperties
	if err := yaml.Unmarshal(data, &driverProperties); err != nil {
		return nil, fmt.Errorf("failed to unmarshal driver properties: %w", err)
	}

	log.Printf("Loaded driver properties from configmap file")
	return &driverProperties, nil
}

// newEdgeDeviceRestClient creates a REST client for EdgeDevice resources
func newEdgeDeviceRestClient(config *rest.Config) (*rest.RESTClient, error) {
	if err := v1alpha1.AddToScheme(scheme.Scheme); err != nil {
		logger.Errorf("cannot add to scheme: %v", err)
		return nil, err
	}

	crdConfig := *config
	crdConfig.ContentConfig.GroupVersion = &schema.GroupVersion{
		Group:   v1alpha1.GroupVersion.Group,
		Version: v1alpha1.GroupVersion.Version,
	}
	crdConfig.APIPath = "/apis"
	crdConfig.NegotiatedSerializer = serializer.NewCodecFactory(scheme.Scheme)
	crdConfig.UserAgent = rest.DefaultKubernetesUserAgent()

	restClient, err := rest.UnversionedRESTClientFor(&crdConfig)
	if err != nil {
		return nil, err
	}

	return restClient, nil
}

// getRestConfig returns a Kubernetes REST config
func getRestConfig(kubeConfigPath string) (*rest.Config, error) {
	if kubeConfigPath != "" {
		return clientcmd.BuildConfigFromFlags("", kubeConfigPath)
	}
	return rest.InClusterConfig()
}

// getEnv gets an environment variable with a default value
func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}
