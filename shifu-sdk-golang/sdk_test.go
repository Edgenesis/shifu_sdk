package shifusdk

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/edgenesis/shifu/pkg/k8s/api/v1alpha1"
	"gopkg.in/yaml.v3"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/runtime/serializer"
	"k8s.io/client-go/rest"
	"k8s.io/kubectl/pkg/scheme"
)

// Mock implementations for testing

type mockEdgeDeviceClient struct {
	getFunc func() *rest.Request
	putFunc func() *rest.Request
}

func (m *mockEdgeDeviceClient) Get() *rest.Request {
	if m.getFunc != nil {
		return m.getFunc()
	}
	return nil
}

func (m *mockEdgeDeviceClient) Put() *rest.Request {
	if m.putFunc != nil {
		return m.putFunc()
	}
	return nil
}

type mockConfigLoader struct {
	loadFunc func(path string) (*DeviceShifuInstructions[any], error)
}

func (m *mockConfigLoader) LoadInstructions(path string) (*DeviceShifuInstructions[any], error) {
	if m.loadFunc != nil {
		return m.loadFunc(path)
	}
	return &DeviceShifuInstructions[any]{
		Instructions: make(map[string]*DeviceShifuInstruction[any]),
	}, nil
}

// TestProtocolPropertyList is a sample property list for testing
type TestProtocolPropertyList struct {
	Protocol string `yaml:"protocol,omitempty"`
	Address  string `yaml:"address,omitempty"`
}

// Helper functions

func setupMockServer(t *testing.T, handler http.HandlerFunc) (*httptest.Server, *rest.RESTClient) {
	server := httptest.NewServer(handler)

	err := v1alpha1.AddToScheme(scheme.Scheme)
	if err != nil {
		t.Fatalf("Failed to add to scheme: %v", err)
	}

	config := &rest.Config{
		Host: server.URL,
		ContentConfig: rest.ContentConfig{
			GroupVersion:         &schema.GroupVersion{Group: v1alpha1.GroupVersion.Group, Version: v1alpha1.GroupVersion.Version},
			NegotiatedSerializer: serializer.NewCodecFactory(scheme.Scheme),
		},
		APIPath: "/apis",
	}

	restClient, err := rest.UnversionedRESTClientFor(config)
	if err != nil {
		server.Close()
		t.Fatalf("Failed to create REST client: %v", err)
	}

	return server, restClient
}

func createTestClient(t *testing.T, restClient EdgeDeviceClient) *Client {
	return &Client{
		restClient:          restClient,
		edgedeviceNamespace: "test-namespace",
		edgedeviceName:      "test-device",
		configPath:          "/tmp/test-config",
		healthCheckInterval: 100 * time.Millisecond,
		configLoader:        &defaultConfigLoader{},
	}
}

// Tests for utility functions

func TestGetEnv(t *testing.T) {
	tests := []struct {
		name         string
		key          string
		defaultValue string
		envValue     string
		setEnv       bool
		expected     string
	}{
		{
			name:         "environment variable set",
			key:          "TEST_VAR",
			defaultValue: "default",
			envValue:     "custom",
			setEnv:       true,
			expected:     "custom",
		},
		{
			name:         "environment variable not set",
			key:          "TEST_VAR_UNSET",
			defaultValue: "default",
			setEnv:       false,
			expected:     "default",
		},
		{
			name:         "environment variable set to empty string",
			key:          "TEST_VAR_EMPTY",
			defaultValue: "default",
			envValue:     "",
			setEnv:       true,
			expected:     "default",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.setEnv {
				os.Setenv(tt.key, tt.envValue)
				defer os.Unsetenv(tt.key)
			}

			result := getEnv(tt.key, tt.defaultValue)
			if result != tt.expected {
				t.Errorf("getEnv() = %v, want %v", result, tt.expected)
			}
		})
	}
}

func TestGetRestConfig_WithKubeconfig(t *testing.T) {
	tmpDir := t.TempDir()
	kubeconfigPath := filepath.Join(tmpDir, "kubeconfig")

	kubeconfigContent := `apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://localhost:6443
  name: test-cluster
contexts:
- context:
    cluster: test-cluster
    user: test-user
  name: test-context
current-context: test-context
users:
- name: test-user
  user:
    token: test-token
`

	err := os.WriteFile(kubeconfigPath, []byte(kubeconfigContent), 0644)
	if err != nil {
		t.Fatalf("Failed to create kubeconfig: %v", err)
	}

	config, err := getRestConfig(kubeconfigPath)
	if err != nil {
		t.Fatalf("getRestConfig() error = %v", err)
	}
	if config == nil {
		t.Fatal("getRestConfig() returned nil config")
	}
	if config.Host != "https://localhost:6443" {
		t.Errorf("Host = %v, want %v", config.Host, "https://localhost:6443")
	}
}

func TestGetRestConfig_InvalidKubeconfig(t *testing.T) {
	config, err := getRestConfig("/nonexistent/kubeconfig")
	if err == nil {
		t.Error("getRestConfig() expected error for invalid path, got nil")
	}
	if config != nil {
		t.Error("getRestConfig() expected nil config on error")
	}
}

func TestLoadInstructionsFromFile(t *testing.T) {
	tests := []struct {
		name        string
		fileContent string
		wantErr     bool
		wantCount   int
	}{
		{
			name: "valid instructions file",
			fileContent: `instructions:
  read_value:
    protocolPropertyList:
      protocol: "http"
      address: "/api/v1/value"
  write_value:
    protocolPropertyList:
      protocol: "http"
      address: "/api/v1/write"
`,
			wantErr:   false,
			wantCount: 2,
		},
		{
			name:        "invalid YAML",
			fileContent: `invalid: yaml: content: [[[`,
			wantErr:     true,
			wantCount:   0,
		},
		{
			name:        "empty file",
			fileContent: ``,
			wantErr:     false,
			wantCount:   0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tmpDir := t.TempDir()
			tmpFile := filepath.Join(tmpDir, "instructions")
			err := os.WriteFile(tmpFile, []byte(tt.fileContent), 0644)
			if err != nil {
				t.Fatalf("Failed to create temp file: %v", err)
			}

			result, err := loadInstructionsFromFile[TestProtocolPropertyList](tmpFile)

			if (err != nil) != tt.wantErr {
				t.Errorf("loadInstructionsFromFile() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if !tt.wantErr && result != nil {
				if len(result.Instructions) != tt.wantCount {
					t.Errorf("loadInstructionsFromFile() instruction count = %v, want %v", len(result.Instructions), tt.wantCount)
				}
			}
		})
	}
}

func TestLoadInstructionsFromFile_FileNotFound(t *testing.T) {
	result, err := loadInstructionsFromFile[TestProtocolPropertyList]("/nonexistent/path/instructions")

	if err == nil {
		t.Error("loadInstructionsFromFile() expected error for nonexistent file, got nil")
	}

	if result != nil {
		t.Error("loadInstructionsFromFile() expected nil result for nonexistent file")
	}
}

// Tests for Client methods

func TestNewClient(t *testing.T) {
	tmpDir := t.TempDir()
	kubeconfigPath := filepath.Join(tmpDir, "kubeconfig")

	kubeconfigContent := `apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://localhost:6443
  name: test-cluster
contexts:
- context:
    cluster: test-cluster
    user: test-user
  name: test-context
current-context: test-context
users:
- name: test-user
  user:
    token: test-token
`

	os.WriteFile(kubeconfigPath, []byte(kubeconfigContent), 0644)

	tests := []struct {
		name      string
		config    *Config
		wantError bool
	}{
		{
			name: "with valid config",
			config: &Config{
				Namespace:      "test-ns",
				DeviceName:     "test-device",
				KubeconfigPath: kubeconfigPath,
				ConfigPath:     "/tmp/config",
			},
			wantError: false,
		},
		{
			name:      "with nil config",
			config:    nil,
			wantError: true, // Will fail without valid kubeconfig
		},
		{
			name: "with partial config",
			config: &Config{
				KubeconfigPath: kubeconfigPath,
			},
			wantError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()
			client, err := NewClient(ctx, tt.config)

			if tt.wantError {
				if err == nil {
					t.Error("NewClient() expected error, got nil")
				}
			} else {
				if err != nil {
					t.Errorf("NewClient() unexpected error = %v", err)
				}
				if client == nil {
					t.Error("NewClient() returned nil client")
				}
			}
		})
	}
}

func TestClient_GetEdgeDevice(t *testing.T) {
	phase := v1alpha1.EdgeDeviceRunning
	mockEdgeDevice := &v1alpha1.EdgeDevice{
		Status: v1alpha1.EdgeDeviceStatus{
			EdgeDevicePhase: &phase,
		},
	}
	mockEdgeDevice.Name = "test-device"

	handler := func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "GET" {
			t.Errorf("Expected GET request, got %s", r.Method)
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(mockEdgeDevice)
	}

	server, restClient := setupMockServer(t, handler)
	defer server.Close()

	client := createTestClient(t, restClient)

	result, err := client.GetEdgeDevice()
	if err != nil {
		t.Fatalf("GetEdgeDevice() error = %v", err)
	}
	if result == nil {
		t.Fatal("GetEdgeDevice() returned nil")
	}
	if result.Name != "test-device" {
		t.Errorf("EdgeDevice name = %v, want %v", result.Name, "test-device")
	}
}

func TestClient_GetEdgeDevice_Error(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		w.Write([]byte(`{"kind":"Status","status":"Failure"}`))
	}

	server, restClient := setupMockServer(t, handler)
	defer server.Close()

	client := createTestClient(t, restClient)

	result, err := client.GetEdgeDevice()
	if err == nil {
		t.Error("GetEdgeDevice() expected error, got nil")
	}
	if result != nil {
		t.Error("GetEdgeDevice() expected nil result on error")
	}
}

func TestClient_GetEdgeDevice_NilClient(t *testing.T) {
	client := createTestClient(t, nil)

	result, err := client.GetEdgeDevice()
	if err == nil {
		t.Error("GetEdgeDevice() expected error with nil client, got nil")
	}
	if result != nil {
		t.Error("GetEdgeDevice() expected nil result with nil client")
	}
}

func TestClient_UpdatePhase(t *testing.T) {
	currentPhase := v1alpha1.EdgeDevicePending
	newPhase := v1alpha1.EdgeDeviceRunning

	mockEdgeDevice := &v1alpha1.EdgeDevice{
		Status: v1alpha1.EdgeDeviceStatus{
			EdgeDevicePhase: &currentPhase,
		},
	}
	mockEdgeDevice.Name = "test-device"

	getCount := 0
	putCount := 0

	handler := func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.Method {
		case "GET":
			getCount++
			json.NewEncoder(w).Encode(mockEdgeDevice)
		case "PUT":
			putCount++
			mockEdgeDevice.Status.EdgeDevicePhase = &newPhase
			json.NewEncoder(w).Encode(mockEdgeDevice)
		}
	}

	server, restClient := setupMockServer(t, handler)
	defer server.Close()

	client := createTestClient(t, restClient)

	err := client.UpdatePhase(newPhase)
	if err != nil {
		t.Fatalf("UpdatePhase() error = %v", err)
	}

	if getCount != 1 {
		t.Errorf("Expected 1 GET request, got %d", getCount)
	}
	if putCount != 1 {
		t.Errorf("Expected 1 PUT request, got %d", putCount)
	}
}

func TestClient_UpdatePhase_SamePhase(t *testing.T) {
	currentPhase := v1alpha1.EdgeDeviceRunning

	mockEdgeDevice := &v1alpha1.EdgeDevice{
		Status: v1alpha1.EdgeDeviceStatus{
			EdgeDevicePhase: &currentPhase,
		},
	}
	mockEdgeDevice.Name = "test-device"

	putCount := 0

	handler := func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.Method {
		case "GET":
			json.NewEncoder(w).Encode(mockEdgeDevice)
		case "PUT":
			putCount++
			json.NewEncoder(w).Encode(mockEdgeDevice)
		}
	}

	server, restClient := setupMockServer(t, handler)
	defer server.Close()

	client := createTestClient(t, restClient)

	err := client.UpdatePhase(currentPhase)
	if err != nil {
		t.Fatalf("UpdatePhase() error = %v", err)
	}

	if putCount != 0 {
		t.Errorf("Expected 0 PUT requests, got %d", putCount)
	}
}

func TestClient_UpdatePhase_NilPhase(t *testing.T) {
	mockEdgeDevice := &v1alpha1.EdgeDevice{
		Status: v1alpha1.EdgeDeviceStatus{
			EdgeDevicePhase: nil,
		},
	}
	mockEdgeDevice.Name = "test-device"

	putCalled := false

	handler := func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.Method {
		case "GET":
			json.NewEncoder(w).Encode(mockEdgeDevice)
		case "PUT":
			putCalled = true
			json.NewEncoder(w).Encode(mockEdgeDevice)
		}
	}

	server, restClient := setupMockServer(t, handler)
	defer server.Close()

	client := createTestClient(t, restClient)

	err := client.UpdatePhase(v1alpha1.EdgeDeviceRunning)
	if err != nil {
		t.Fatalf("UpdatePhase() error = %v", err)
	}

	if !putCalled {
		t.Error("Expected PUT to be called when current phase is nil")
	}
}

func TestClient_UpdatePhase_NilClient(t *testing.T) {
	client := createTestClient(t, nil)

	err := client.UpdatePhase(v1alpha1.EdgeDeviceRunning)
	if err == nil {
		t.Error("UpdatePhase() expected error with nil client, got nil")
	}
}

func TestClient_Start(t *testing.T) {
	currentPhase := v1alpha1.EdgeDevicePending
	mockEdgeDevice := &v1alpha1.EdgeDevice{
		Status: v1alpha1.EdgeDeviceStatus{
			EdgeDevicePhase: &currentPhase,
		},
	}
	mockEdgeDevice.Name = "test-device"

	handler := func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(mockEdgeDevice)
	}

	server, restClient := setupMockServer(t, handler)
	defer server.Close()

	client := createTestClient(t, restClient)
	client.healthChecker = func() v1alpha1.EdgeDevicePhase {
		return v1alpha1.EdgeDeviceRunning
	}

	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	err := client.Start(ctx)
	if err != context.DeadlineExceeded {
		t.Logf("Start() returned err = %v (expected deadline exceeded)", err)
	}
}

func TestClient_Start_NoHealthChecker(t *testing.T) {
	server, restClient := setupMockServer(t, func(w http.ResponseWriter, r *http.Request) {})
	defer server.Close()

	client := createTestClient(t, restClient)
	client.healthChecker = nil

	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	err := client.Start(ctx)
	if err != context.DeadlineExceeded {
		t.Logf("Start() with no health checker returned err = %v", err)
	}
}

func TestClient_Start_NilClient(t *testing.T) {
	client := createTestClient(t, nil)

	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()

	err := client.Start(ctx)
	if err == nil {
		t.Error("Start() expected error with nil client, got nil")
	}
}

func TestClient_Start_ContextCancellation(t *testing.T) {
	currentPhase := v1alpha1.EdgeDeviceRunning
	mockEdgeDevice := &v1alpha1.EdgeDevice{
		Status: v1alpha1.EdgeDeviceStatus{
			EdgeDevicePhase: &currentPhase,
		},
	}
	mockEdgeDevice.Name = "test-device"

	handler := func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(mockEdgeDevice)
	}

	server, restClient := setupMockServer(t, handler)
	defer server.Close()

	client := createTestClient(t, restClient)
	client.healthChecker = func() v1alpha1.EdgeDevicePhase {
		return v1alpha1.EdgeDeviceRunning
	}

	ctx, cancel := context.WithCancel(context.Background())

	done := make(chan error)
	go func() {
		done <- client.Start(ctx)
	}()

	time.Sleep(10 * time.Millisecond)
	cancel()

	select {
	case err := <-done:
		if err != context.Canceled {
			t.Errorf("Start() error = %v, want context.Canceled", err)
		}
	case <-time.After(200 * time.Millisecond):
		t.Error("Start() did not return after context cancellation")
	}
}

func TestClient_GetConfigMap(t *testing.T) {
	client := &Client{
		configPath:   "/tmp/test-config",
		configLoader: &defaultConfigLoader{},
	}

	result, err := client.GetConfigMap()
	if err != nil {
		t.Fatalf("GetConfigMap() error = %v", err)
	}
	if result == nil {
		t.Error("GetConfigMap() returned nil")
	}
}

func TestClient_GetConfigMap_WithMock(t *testing.T) {
	mockLoader := &mockConfigLoader{
		loadFunc: func(path string) (*DeviceShifuInstructions[any], error) {
			return &DeviceShifuInstructions[any]{
				Instructions: map[string]*DeviceShifuInstruction[any]{
					"test": {},
				},
			}, nil
		},
	}

	client := &Client{
		configPath:   "/tmp/test",
		configLoader: mockLoader,
	}

	result, err := client.GetConfigMap()
	if err != nil {
		t.Fatalf("GetConfigMap() error = %v", err)
	}
	if result == nil {
		t.Fatal("GetConfigMap() returned nil")
	}
	if len(result.Instructions.Instructions) != 1 {
		t.Errorf("Expected 1 instruction, got %d", len(result.Instructions.Instructions))
	}
}

func TestClient_SetHealthChecker(t *testing.T) {
	client := &Client{}

	testPhase := v1alpha1.EdgeDevicePending
	testFunc := func() v1alpha1.EdgeDevicePhase {
		return testPhase
	}

	client.SetHealthChecker(testFunc)

	if client.healthChecker == nil {
		t.Error("SetHealthChecker() did not set healthChecker")
		return
	}

	result := client.healthChecker()
	if result != testPhase {
		t.Errorf("healthChecker() = %v, want %v", result, testPhase)
	}
}

func TestGetConfigMapTyped(t *testing.T) {
	tmpDir := t.TempDir()
	instructionsPath := filepath.Join(tmpDir, "instructions")

	instructionsContent := `instructions:
  test_cmd:
    protocolPropertyList:
      protocol: "http"
      address: "/test"
`

	err := os.WriteFile(instructionsPath, []byte(instructionsContent), 0644)
	if err != nil {
		t.Fatalf("Failed to create instructions file: %v", err)
	}

	client := &Client{
		configPath:   tmpDir,
		configLoader: &defaultConfigLoader{},
	}

	result, err := GetConfigMapTyped[TestProtocolPropertyList](client)
	if err != nil {
		t.Fatalf("GetConfigMapTyped() error = %v", err)
	}
	if result == nil {
		t.Error("GetConfigMapTyped() returned nil")
	}
}

// Tests for deprecated functions

func TestDeprecated_GetEdgedevice(t *testing.T) {
	if globalClient == nil {
		t.Skip("Global client not initialized")
	}

	// Just test that it doesn't panic
	_, _ = GetEdgedevice()
}

func TestDeprecated_UpdatePhase(t *testing.T) {
	if globalClient == nil {
		t.Skip("Global client not initialized")
	}

	// Just test that it doesn't panic
	_ = UpdatePhase(v1alpha1.EdgeDevicePending)
}

func TestDeprecated_Start(t *testing.T) {
	if globalClient == nil {
		t.Skip("Global client not initialized")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Millisecond)
	defer cancel()

	// Just test that it doesn't panic
	Start(ctx)
}

func TestDeprecated_GetConfigMap(t *testing.T) {
	result, err := GetConfigMap[TestProtocolPropertyList]()
	if err != nil {
		t.Fatalf("GetConfigMap() error = %v", err)
	}
	if result == nil {
		t.Error("GetConfigMap() returned nil")
	}
}

func TestDeprecated_AddHealthChecker(t *testing.T) {
	testFunc := func() v1alpha1.EdgeDevicePhase {
		return v1alpha1.EdgeDevicePending
	}

	// Just test that it doesn't panic
	AddHealthChecker(testFunc)
}

// Tests for struct types

func TestDeviceShifuConfigUnmarshal(t *testing.T) {
	yamlContent := `driverProperties:
  driverSku: "test-driver-v1"
  driverImage: "test/driver:latest"
instructions:
  instructions:
    read_data:
      protocolPropertyList:
        protocol: "http"
        address: "/api/data"
`

	var config DeviceShifuConfig[TestProtocolPropertyList]
	err := yaml.Unmarshal([]byte(yamlContent), &config)
	if err != nil {
		t.Fatalf("Failed to unmarshal config: %v", err)
	}

	if config.DriverProperties.DriverSku != "test-driver-v1" {
		t.Errorf("DriverSku = %v, want %v", config.DriverProperties.DriverSku, "test-driver-v1")
	}
}

func TestNewEdgeDeviceRestClient(t *testing.T) {
	config := &rest.Config{
		Host: "https://localhost:6443",
		ContentConfig: rest.ContentConfig{
			NegotiatedSerializer: serializer.NewCodecFactory(scheme.Scheme),
		},
	}

	client, err := newEdgeDeviceRestClient(config)
	if err != nil {
		t.Fatalf("newEdgeDeviceRestClient() error = %v", err)
	}
	if client == nil {
		t.Error("newEdgeDeviceRestClient() returned nil client")
	}
}

func TestDefaultConfigLoader(t *testing.T) {
	tmpDir := t.TempDir()
	instructionsPath := filepath.Join(tmpDir, "instructions")

	instructionsContent := `instructions:
  cmd1:
    protocolPropertyList:
      protocol: "http"
      address: "/api"
`

	err := os.WriteFile(instructionsPath, []byte(instructionsContent), 0644)
	if err != nil {
		t.Fatalf("Failed to create file: %v", err)
	}

	loader := &defaultConfigLoader{}
	result, err := loader.LoadInstructions(instructionsPath)
	if err != nil {
		t.Fatalf("LoadInstructions() error = %v", err)
	}
	if result == nil {
		t.Fatal("LoadInstructions() returned nil")
	}
	if len(result.Instructions) != 1 {
		t.Errorf("Expected 1 instruction, got %d", len(result.Instructions))
	}
}

func TestDefaultConfigLoader_Error(t *testing.T) {
	loader := &defaultConfigLoader{}
	result, err := loader.LoadInstructions("/nonexistent/file")
	if err == nil {
		t.Error("LoadInstructions() expected error, got nil")
	}
	if result != nil {
		t.Error("LoadInstructions() expected nil result on error")
	}
}

// Benchmark tests

func BenchmarkGetEnv(b *testing.B) {
	os.Setenv("BENCH_TEST", "value")
	defer os.Unsetenv("BENCH_TEST")

	for i := 0; i < b.N; i++ {
		getEnv("BENCH_TEST", "default")
	}
}

func BenchmarkLoadInstructionsFromFile(b *testing.B) {
	tmpDir := b.TempDir()
	tmpFile := filepath.Join(tmpDir, "instructions")
	content := `instructions:
  test:
    protocolPropertyList:
      protocol: "http"
      address: "/api"
`
	os.WriteFile(tmpFile, []byte(content), 0644)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		loadInstructionsFromFile[TestProtocolPropertyList](tmpFile)
	}
}

func BenchmarkClient_UpdatePhase(b *testing.B) {
	currentPhase := v1alpha1.EdgeDeviceRunning
	mockEdgeDevice := &v1alpha1.EdgeDevice{
		Status: v1alpha1.EdgeDeviceStatus{
			EdgeDevicePhase: &currentPhase,
		},
	}
	mockEdgeDevice.Name = "test-device"

	handler := func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(mockEdgeDevice)
	}

	server := httptest.NewServer(http.HandlerFunc(handler))
	defer server.Close()

	v1alpha1.AddToScheme(scheme.Scheme)

	config := &rest.Config{
		Host: server.URL,
		ContentConfig: rest.ContentConfig{
			GroupVersion:         &schema.GroupVersion{Group: v1alpha1.GroupVersion.Group, Version: v1alpha1.GroupVersion.Version},
			NegotiatedSerializer: serializer.NewCodecFactory(scheme.Scheme),
		},
		APIPath: "/apis",
	}

	restClient, _ := rest.UnversionedRESTClientFor(config)

	client := &Client{
		restClient:          restClient,
		edgedeviceNamespace: "test-namespace",
		edgedeviceName:      "test-device",
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		client.UpdatePhase(v1alpha1.EdgeDeviceRunning)
	}
}
