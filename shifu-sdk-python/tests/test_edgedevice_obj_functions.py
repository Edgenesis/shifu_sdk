#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for DeviceShifu class methods: get_edgedevice(), update_phase(), add_health_checker()

This test creates a fake EdgeDevice in Kubernetes, tests the DeviceShifu class methods, and cleans up.
Uses the object-oriented approach with DeviceShifu class instead of global functions.
"""

import os
import time
import uuid
from typing import Dict, Any

from shifu_sdk import (
    EdgeDevicePhase,
    DeviceShifu,
    SHIFU_GROUP,
    SHIFU_VERSION,
    SHIFU_PLURAL,
)


def generate_test_device_name() -> str:
    """Generate a unique test device name."""
    unique_id = str(uuid.uuid4())[:8]
    return f"test-device-obj-{unique_id}"


def create_fake_edgedevice(device_name: str, namespace: str = "devices") -> Dict[str, Any]:
    """Create a fake EdgeDevice in Kubernetes for testing."""
    print(f"Creating fake EdgeDevice: {device_name} in namespace: {namespace}")
    
    # Import kubernetes client directly for creation
    from kubernetes import client
    
    try:
        # Load kubernetes config
        from kubernetes import config
        try:
            config.load_incluster_config()
            print("Loaded in-cluster Kubernetes config")
        except Exception:
            try:
                config.load_kube_config()
                print("Loaded local Kubernetes config")
            except Exception as e:
                print(f"Failed to load Kubernetes config: {e}")
                raise
        
        # Create CustomObjectsApi client
        k8s_client = client.CustomObjectsApi()
        
        # Define the EdgeDevice manifest
        edge_device_manifest = {
            "apiVersion": f"{SHIFU_GROUP}/{SHIFU_VERSION}",
            "kind": "EdgeDevice",
            "metadata": {
                "name": device_name,
                "namespace": namespace,
                "labels": {
                    "test": "true",
                    "created-by": "shifu-sdk-obj-test"
                }
            },
            "spec": {
                "sku": "TEST-OBJ-SKU-001",
                "connection": "Ethernet", 
                "address": "127.0.0.1:8080",
                "protocol": "HTTP"
            },
            "status": {
                "edgedevicephase": "Pending"
            }
        }
        
        # Create the EdgeDevice
        created_device = k8s_client.create_namespaced_custom_object(
            group=SHIFU_GROUP,
            version=SHIFU_VERSION,
            namespace=namespace,
            plural=SHIFU_PLURAL,
            body=edge_device_manifest
        )
        
        print(f"✅ Created EdgeDevice: {device_name}")
        print(f"   - SKU: {created_device['spec']['sku']}")
        print(f"   - Address: {created_device['spec']['address']}")
        print(f"   - Protocol: {created_device['spec']['protocol']}")
        print(f"   - Initial Phase: {created_device.get('status', {}).get('edgedevicephase', 'Unknown')}")
        
        return created_device
        
    except Exception as e:
        print(f"❌ Failed to create EdgeDevice {device_name}: {e}")
        raise


def delete_fake_edgedevice(device_name: str, namespace: str = "devices"):
    """Delete the fake EdgeDevice from Kubernetes."""
    print(f"Deleting EdgeDevice: {device_name} from namespace: {namespace}")
    
    # Import kubernetes client directly for deletion
    from kubernetes import client, config
    
    try:
        # Load kubernetes config
        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()
        
        # Create CustomObjectsApi client
        k8s_client = client.CustomObjectsApi()
        
        # Delete the EdgeDevice
        k8s_client.delete_namespaced_custom_object(
            group=SHIFU_GROUP,
            version=SHIFU_VERSION,
            namespace=namespace,
            plural=SHIFU_PLURAL,
            name=device_name
        )
        
        print(f"✅ Deleted EdgeDevice: {device_name}")
        
    except Exception as e:
        print(f"❌ Failed to delete EdgeDevice {device_name}: {e}")
        # Don't raise - cleanup should be best effort


def test_deviceshifu_get_edgedevice():
    """Test the DeviceShifu.get_edgedevice() method."""
    print("\n=== Testing DeviceShifu.get_edgedevice() ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Create DeviceShifu instance
        device_shifu = DeviceShifu(device_name)
        device_shifu.init()
        
        # Test get_edgedevice method
        print(f"\nTesting DeviceShifu.get_edgedevice() for device: {device_name}")
        retrieved_device = device_shifu.get_edgedevice()
        
        print("Retrieved EdgeDevice via DeviceShifu:")
        print(f"  Name: {retrieved_device['metadata']['name']}")
        print(f"  Namespace: {retrieved_device['metadata']['namespace']}")
        print(f"  SKU: {retrieved_device['spec']['sku']}")
        print(f"  Address: {retrieved_device['spec']['address']}")
        print(f"  Protocol: {retrieved_device['spec']['protocol']}")
        print(f"  Phase: {retrieved_device.get('status', {}).get('edgedevicephase', 'Unknown')}")
        
        # Verify the device data
        assert retrieved_device["metadata"]["name"] == device_name
        assert retrieved_device["metadata"]["namespace"] == namespace
        assert retrieved_device["spec"]["sku"] == "TEST-OBJ-SKU-001"
        assert retrieved_device["spec"]["address"] == "127.0.0.1:8080"
        assert retrieved_device["spec"]["protocol"] == "HTTP"
        
        print("✅ DeviceShifu.get_edgedevice() test passed!")
        return retrieved_device
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def test_deviceshifu_update_phase():
    """Test the DeviceShifu.update_phase() method."""
    print("\n=== Testing DeviceShifu.update_phase() ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Create DeviceShifu instance
        device_shifu = DeviceShifu(device_name)
        device_shifu.init()
        
        # Test phase updates
        test_phases = [
            EdgeDevicePhase.RUNNING,
            EdgeDevicePhase.FAILED,
            EdgeDevicePhase.PENDING,
            EdgeDevicePhase.UNKNOWN
        ]
        
        for phase in test_phases:
            print(f"\nTesting DeviceShifu.update_phase() to: {phase.value}")
            
            # Update phase using DeviceShifu method
            success = device_shifu.update_phase(phase)
            assert success, f"Failed to update phase to {phase.value}"
            
            # Give Kubernetes a moment to process the update
            time.sleep(0.5)
            
            # Verify the phase was updated using DeviceShifu method
            updated_device = device_shifu.get_edgedevice()
            current_phase = updated_device.get("status", {}).get("edgedevicephase")
            
            print(f"  Updated phase: {current_phase}")
            assert current_phase == phase.value, f"Phase mismatch: expected {phase.value}, got {current_phase}"
            
            print(f"✅ Successfully updated to {phase.value}")
        
        print("✅ DeviceShifu.update_phase() test passed!")
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def test_deviceshifu_phase_idempotency():
    """Test that DeviceShifu phase updates are idempotent."""
    print("\n=== Testing DeviceShifu phase update idempotency ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Create DeviceShifu instance
        device_shifu = DeviceShifu(device_name)
        device_shifu.init()
        
        # Set initial phase
        phase = EdgeDevicePhase.RUNNING
        print(f"Setting initial phase to: {phase.value}")
        success = device_shifu.update_phase(phase)
        assert success
        
        time.sleep(0.5)
        
        # Update to same phase multiple times
        print(f"Updating to same phase ({phase.value}) multiple times...")
        for i in range(3):
            success = device_shifu.update_phase(phase)
            assert success, f"Idempotent update {i+1} failed"
            print(f"  Idempotent update {i+1}: ✅")
        
        # Verify phase is still correct
        final_device = device_shifu.get_edgedevice()
        final_phase = final_device.get("status", {}).get("edgedevicephase")
        assert final_phase == phase.value
        
        print("✅ DeviceShifu phase idempotency test passed!")
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def test_deviceshifu_health_checker():
    """Test the DeviceShifu.add_health_checker() method."""
    print("\n=== Testing DeviceShifu.add_health_checker() ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Create DeviceShifu instance
        device_shifu = DeviceShifu(device_name)
        device_shifu.init()
        
        # Test 1: Health checker that returns RUNNING
        print("\n1. Testing DeviceShifu health checker that returns RUNNING")
        
        def healthy_checker() -> EdgeDevicePhase:
            """Health checker that simulates a healthy device."""
            print("   Health check: Device is healthy")
            return EdgeDevicePhase.RUNNING
        
        # Register the health checker using DeviceShifu method
        device_shifu.add_health_checker(healthy_checker)
        print("   ✅ Registered healthy checker via DeviceShifu")
        
        # Simulate a few health check cycles manually
        for i in range(3):
            # Call the health checker
            phase = healthy_checker()
            success = device_shifu.update_phase(phase)
            assert success, f"Health check {i+1} failed"
            
            # Verify the phase was updated
            device = device_shifu.get_edgedevice()
            current_phase = device.get("status", {}).get("edgedevicephase")
            assert current_phase == EdgeDevicePhase.RUNNING.value
            
            print(f"   Health check {i+1}: Device phase = {current_phase} ✅")
            time.sleep(0.5)
        
        # Test 2: Health checker that returns FAILED
        print("\n2. Testing DeviceShifu health checker that returns FAILED")
        
        def unhealthy_checker() -> EdgeDevicePhase:
            """Health checker that simulates a failed device."""
            print("   Health check: Device has failed")
            return EdgeDevicePhase.FAILED
        
        # Register the new health checker
        device_shifu.add_health_checker(unhealthy_checker)
        print("   ✅ Registered unhealthy checker via DeviceShifu")
        
        # Simulate a few failed health check cycles
        for i in range(3):
            # Call the health checker
            phase = unhealthy_checker()
            success = device_shifu.update_phase(phase)
            assert success, f"Failed health check {i+1} failed to update"
            
            # Verify the phase was updated
            device = device_shifu.get_edgedevice()
            current_phase = device.get("status", {}).get("edgedevicephase")
            assert current_phase == EdgeDevicePhase.FAILED.value
            
            print(f"   Health check {i+1}: Device phase = {current_phase} ✅")
            time.sleep(0.5)
        
        # Test 3: Dynamic health checker (alternates between states)
        print("\n3. Testing DeviceShifu dynamic health checker")
        
        health_check_count = 0
        
        def dynamic_checker() -> EdgeDevicePhase:
            """Health checker that alternates between healthy and unhealthy."""
            nonlocal health_check_count
            health_check_count += 1
            
            if health_check_count % 2 == 1:
                print(f"   Health check {health_check_count}: Device is healthy")
                return EdgeDevicePhase.RUNNING
            else:
                print(f"   Health check {health_check_count}: Device has issues") 
                return EdgeDevicePhase.FAILED
        
        # Register the dynamic health checker
        device_shifu.add_health_checker(dynamic_checker)
        print("   ✅ Registered dynamic checker via DeviceShifu")
        
        # Run several dynamic health checks
        expected_phases = [EdgeDevicePhase.RUNNING, EdgeDevicePhase.FAILED, 
                          EdgeDevicePhase.RUNNING, EdgeDevicePhase.FAILED]
        
        for i, expected_phase in enumerate(expected_phases):
            # Call the health checker
            phase = dynamic_checker()
            success = device_shifu.update_phase(phase)
            assert success, f"Dynamic health check {i+1} failed"
            assert phase == expected_phase, f"Expected {expected_phase.value}, got {phase.value}"
            
            # Verify the phase was updated
            device = device_shifu.get_edgedevice()
            current_phase = device.get("status", {}).get("edgedevicephase")
            assert current_phase == expected_phase.value
            
            print(f"   Dynamic check {i+1}: Expected {expected_phase.value}, got {current_phase} ✅")
            time.sleep(0.5)
        
        # Test 4: Health checker with error handling
        print("\n4. Testing DeviceShifu health checker error handling")
        
        def error_checker() -> EdgeDevicePhase:
            """Health checker that simulates an error but returns FAILED."""
            print("   Health check: Error detected, marking as FAILED")
            # Simulate some error condition
            error_condition = True
            if error_condition:
                return EdgeDevicePhase.FAILED
            return EdgeDevicePhase.RUNNING
        
        # Register the error checker
        device_shifu.add_health_checker(error_checker)
        print("   ✅ Registered error checker via DeviceShifu")
        
        # Test error handling
        phase = error_checker()
        success = device_shifu.update_phase(phase)
        assert success
        assert phase == EdgeDevicePhase.FAILED
        
        device = device_shifu.get_edgedevice()
        current_phase = device.get("status", {}).get("edgedevicephase")
        assert current_phase == EdgeDevicePhase.FAILED.value
        print(f"   Error handling: Device correctly marked as {current_phase} ✅")
        
        print("✅ DeviceShifu.add_health_checker() test passed!")
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def test_deviceshifu_helper_methods():
    """Test DeviceShifu helper methods: get_device_config, get_device_address, etc."""
    print("\n=== Testing DeviceShifu helper methods ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Create DeviceShifu instance
        device_shifu = DeviceShifu(device_name)
        device_shifu.init()
        
        # Test helper methods
        print("\nTesting DeviceShifu helper methods:")
        
        # Test get_device_config
        config = device_shifu.get_device_config()
        print(f"  get_device_config(): {config}")
        assert isinstance(config, dict)
        assert config.get("sku") == "TEST-OBJ-SKU-001"
        assert config.get("address") == "127.0.0.1:8080"
        assert config.get("protocol") == "HTTP"
        
        # Test get_device_address
        address = device_shifu.get_device_address()
        print(f"  get_device_address(): {address}")
        assert address == "127.0.0.1:8080"
        
        # Test get_device_protocol
        protocol = device_shifu.get_device_protocol()
        print(f"  get_device_protocol(): {protocol}")
        assert protocol == "HTTP"
        
        # Test log_device_info
        print("\n  Testing log_device_info():")
        device_shifu.log_device_info()
        
        print("✅ DeviceShifu helper methods test passed!")
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def test_deviceshifu_setup():
    """Test DeviceShifu.setup_device_shifu() method."""
    print("\n=== Testing DeviceShifu.setup_device_shifu() ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Create DeviceShifu instance
        device_shifu = DeviceShifu(device_name)
        
        # Define a simple health check function
        def setup_health_checker() -> EdgeDevicePhase:
            """Simple health checker for setup test."""
            print("   Setup health check: Device is running")
            return EdgeDevicePhase.RUNNING
        
        # Test setup_device_shifu method
        print(f"\nTesting DeviceShifu.setup_device_shifu() for device: {device_name}")
        success = device_shifu.setup_device_shifu(setup_health_checker)
        assert success, "setup_device_shifu failed"
        
        # Verify the setup worked by running a health check cycle
        phase = setup_health_checker()
        update_success = device_shifu.update_phase(phase)
        assert update_success
        
        # Verify the device state
        device = device_shifu.get_edgedevice()
        current_phase = device.get("status", {}).get("edgedevicephase")
        assert current_phase == EdgeDevicePhase.RUNNING.value
        
        print(f"  Setup completed, device phase: {current_phase} ✅")
        print("✅ DeviceShifu.setup_device_shifu() test passed!")
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def main():
    """Run all DeviceShifu class tests."""
    print("Starting DeviceShifu class functions tests...\n")
    
    try:
        # Test DeviceShifu class methods
        device = test_deviceshifu_get_edgedevice()
        test_deviceshifu_update_phase()
        test_deviceshifu_phase_idempotency()
        test_deviceshifu_health_checker()
        test_deviceshifu_helper_methods()
        test_deviceshifu_setup()
        
        print("\n" + "="*60)
        print("🎉 ALL DEVICESHIFU CLASS TESTS PASSED!")
        print("="*60)
        
        # Summary
        print("\nSummary of DeviceShifu class tests:")
        print("✅ DeviceShifu.get_edgedevice() - Successfully retrieves EdgeDevice data")
        print("✅ DeviceShifu.update_phase() - Successfully updates device phase")
        print("✅ DeviceShifu phase transitions - All phase values work correctly")
        print("✅ DeviceShifu idempotency - Same phase updates work correctly")
        print("✅ DeviceShifu health checker - Successfully registers and executes health checks")
        print("✅ DeviceShifu health states - Correctly updates device to RUNNING/FAILED")
        print("✅ DeviceShifu dynamic health - Handles changing health conditions")
        print("✅ DeviceShifu helper methods - get_device_config, address, protocol work")
        print("✅ DeviceShifu setup method - Complete initialization and setup works")
        
    except Exception as e:
        print(f"\n❌ DEVICESHIFU CLASS TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
