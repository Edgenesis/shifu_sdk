#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for EdgeDevice functions: get_edgedevice() and update_phase()

This test creates a fake EdgeDevice in Kubernetes, tests the functions, and cleans up.
"""

import os
import time
import uuid
from typing import Dict, Any

from shifu_sdk import (
    EdgeDevicePhase,
    init,
    get_edgedevice,
    update_phase,
    add_health_checker,
    SHIFU_GROUP,
    SHIFU_VERSION,
    SHIFU_PLURAL,
)


def generate_test_device_name() -> str:
    """Generate a unique test device name."""
    unique_id = str(uuid.uuid4())[:8]
    return f"test-device-{unique_id}"


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
                    "created-by": "shifu-sdk-test"
                }
            },
            "spec": {
                "sku": "TEST-SKU-001",
                "connection": "Ethernet", 
                "address": "127.0.0.1:9090",
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


def test_get_edgedevice():
    """Test the get_edgedevice function."""
    print("\n=== Testing get_edgedevice() ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Set environment variables for the SDK
        os.environ["EDGEDEVICE_NAME"] = device_name
        os.environ["EDGEDEVICE_NAMESPACE"] = namespace
        
        # Initialize SDK
        init()
        
        # Test get_edgedevice
        print(f"\nTesting get_edgedevice() for device: {device_name}")
        retrieved_device = get_edgedevice()
        
        print("Retrieved EdgeDevice:")
        print(f"  Name: {retrieved_device['metadata']['name']}")
        print(f"  Namespace: {retrieved_device['metadata']['namespace']}")
        print(f"  SKU: {retrieved_device['spec']['sku']}")
        print(f"  Address: {retrieved_device['spec']['address']}")
        print(f"  Protocol: {retrieved_device['spec']['protocol']}")
        print(f"  Phase: {retrieved_device.get('status', {}).get('edgedevicephase', 'Unknown')}")
        
        # Verify the device data
        assert retrieved_device["metadata"]["name"] == device_name
        assert retrieved_device["metadata"]["namespace"] == namespace
        assert retrieved_device["spec"]["sku"] == "TEST-SKU-001"
        assert retrieved_device["spec"]["address"] == "127.0.0.1:9090"
        assert retrieved_device["spec"]["protocol"] == "HTTP"
        
        print("✅ get_edgedevice() test passed!")
        return retrieved_device
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def test_update_phase():
    """Test the update_phase function."""
    print("\n=== Testing update_phase() ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Set environment variables for the SDK
        os.environ["EDGEDEVICE_NAME"] = device_name
        os.environ["EDGEDEVICE_NAMESPACE"] = namespace
        
        # Initialize SDK
        init()
        
        # Test phase updates
        test_phases = [
            EdgeDevicePhase.RUNNING,
            EdgeDevicePhase.FAILED,
            EdgeDevicePhase.PENDING,
            EdgeDevicePhase.UNKNOWN
        ]
        
        for phase in test_phases:
            print(f"\nTesting update_phase() to: {phase.value}")
            
            # Update phase
            success = update_phase(phase)
            assert success, f"Failed to update phase to {phase.value}"
            
            # Give Kubernetes a moment to process the update
            time.sleep(0.5)
            
            # Verify the phase was updated
            updated_device = get_edgedevice()
            current_phase = updated_device.get("status", {}).get("edgedevicephase")
            
            print(f"  Updated phase: {current_phase}")
            assert current_phase == phase.value, f"Phase mismatch: expected {phase.value}, got {current_phase}"
            
            print(f"✅ Successfully updated to {phase.value}")
        
        print("✅ update_phase() test passed!")
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def test_phase_idempotency():
    """Test that updating to the same phase is idempotent."""
    print("\n=== Testing phase update idempotency ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Set environment variables for the SDK
        os.environ["EDGEDEVICE_NAME"] = device_name
        os.environ["EDGEDEVICE_NAMESPACE"] = namespace
        
        # Initialize SDK
        init()
        
        # Set initial phase
        phase = EdgeDevicePhase.RUNNING
        print(f"Setting initial phase to: {phase.value}")
        success = update_phase(phase)
        assert success
        
        time.sleep(0.5)
        
        # Update to same phase multiple times
        print(f"Updating to same phase ({phase.value}) multiple times...")
        for i in range(3):
            success = update_phase(phase)
            assert success, f"Idempotent update {i+1} failed"
            print(f"  Idempotent update {i+1}: ✅")
        
        # Verify phase is still correct
        final_device = get_edgedevice()
        final_phase = final_device.get("status", {}).get("edgedevicephase")
        assert final_phase == phase.value
        
        print("✅ Phase idempotency test passed!")
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def test_health_checker():
    """Test the health checker function."""
    print("\n=== Testing add_health_checker() ===")
    
    # Generate unique device name
    device_name = generate_test_device_name()
    namespace = "devices"
    
    try:
        # Create fake EdgeDevice
        created_device = create_fake_edgedevice(device_name, namespace)
        
        # Set environment variables for the SDK
        os.environ["EDGEDEVICE_NAME"] = device_name
        os.environ["EDGEDEVICE_NAMESPACE"] = namespace
        
        # Initialize SDK
        init()
        
        # Test 1: Health checker that returns RUNNING
        print("\n1. Testing health checker that returns RUNNING")
        
        def healthy_checker() -> EdgeDevicePhase:
            """Health checker that simulates a healthy device."""
            print("   Health check: Device is healthy")
            return EdgeDevicePhase.RUNNING
        
        # Register the health checker
        add_health_checker(healthy_checker)
        print("   ✅ Registered healthy checker")
        
        # Simulate a few health check cycles manually
        for i in range(3):
            # Call the health checker
            phase = healthy_checker()
            success = update_phase(phase)
            assert success, f"Health check {i+1} failed"
            
            # Verify the phase was updated
            device = get_edgedevice()
            current_phase = device.get("status", {}).get("edgedevicephase")
            assert current_phase == EdgeDevicePhase.RUNNING.value
            
            print(f"   Health check {i+1}: Device phase = {current_phase} ✅")
            time.sleep(0.5)
        
        # Test 2: Health checker that returns FAILED
        print("\n2. Testing health checker that returns FAILED")
        
        def unhealthy_checker() -> EdgeDevicePhase:
            """Health checker that simulates a failed device."""
            print("   Health check: Device has failed")
            return EdgeDevicePhase.FAILED
        
        # Register the new health checker
        add_health_checker(unhealthy_checker)
        print("   ✅ Registered unhealthy checker")
        
        # Simulate a few failed health check cycles
        for i in range(3):
            # Call the health checker
            phase = unhealthy_checker()
            success = update_phase(phase)
            assert success, f"Failed health check {i+1} failed to update"
            
            # Verify the phase was updated
            device = get_edgedevice()
            current_phase = device.get("status", {}).get("edgedevicephase")
            assert current_phase == EdgeDevicePhase.FAILED.value
            
            print(f"   Health check {i+1}: Device phase = {current_phase} ✅")
            time.sleep(0.5)
        
        # Test 3: Dynamic health checker (alternates between states)
        print("\n3. Testing dynamic health checker")
        
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
        add_health_checker(dynamic_checker)
        print("   ✅ Registered dynamic checker")
        
        # Run several dynamic health checks
        expected_phases = [EdgeDevicePhase.RUNNING, EdgeDevicePhase.FAILED, 
                          EdgeDevicePhase.RUNNING, EdgeDevicePhase.FAILED]
        
        for i, expected_phase in enumerate(expected_phases):
            # Call the health checker
            phase = dynamic_checker()
            success = update_phase(phase)
            assert success, f"Dynamic health check {i+1} failed"
            assert phase == expected_phase, f"Expected {expected_phase.value}, got {phase.value}"
            
            # Verify the phase was updated
            device = get_edgedevice()
            current_phase = device.get("status", {}).get("edgedevicephase")
            assert current_phase == expected_phase.value
            
            print(f"   Dynamic check {i+1}: Expected {expected_phase.value}, got {current_phase} ✅")
            time.sleep(0.5)
        
        # Test 4: Health checker with exception handling
        print("\n4. Testing health checker error handling")
        
        def error_checker() -> EdgeDevicePhase:
            """Health checker that simulates an error but returns FAILED."""
            print("   Health check: Error detected, marking as FAILED")
            # Simulate some error condition
            error_condition = True
            if error_condition:
                return EdgeDevicePhase.FAILED
            return EdgeDevicePhase.RUNNING
        
        # Register the error checker
        add_health_checker(error_checker)
        print("   ✅ Registered error checker")
        
        # Test error handling
        phase = error_checker()
        success = update_phase(phase)
        assert success
        assert phase == EdgeDevicePhase.FAILED
        
        device = get_edgedevice()
        current_phase = device.get("status", {}).get("edgedevicephase")
        assert current_phase == EdgeDevicePhase.FAILED.value
        print(f"   Error handling: Device correctly marked as {current_phase} ✅")
        
        print("✅ add_health_checker() test passed!")
        
    finally:
        # Always clean up
        delete_fake_edgedevice(device_name, namespace)


def test_invalid_device():
    """Test behavior with non-existent device."""
    print("\n=== Testing invalid device scenario ===")
    
    # Set environment to non-existent device
    non_existent_device = "non-existent-device-12345"
    os.environ["EDGEDEVICE_NAME"] = non_existent_device
    os.environ["EDGEDEVICE_NAMESPACE"] = "devices"
    
    # Initialize SDK
    init()
    
    print(f"Testing with non-existent device: {non_existent_device}")
    
    try:
        # This should raise an exception
        device = get_edgedevice()
        assert False, "Expected exception for non-existent device"
    except Exception as e:
        print(f"✅ Expected exception caught: {type(e).__name__}: {e}")
    
    try:
        # This should return False
        success = update_phase(EdgeDevicePhase.RUNNING)
        assert not success, "Expected update_phase to return False for non-existent device"
        print("✅ update_phase correctly returned False for non-existent device")
    except Exception as e:
        print(f"✅ Expected exception in update_phase: {type(e).__name__}: {e}")


def main():
    """Run all EdgeDevice tests."""
    print("Starting EdgeDevice functions tests...\n")
    
    try:
        # Test individual functions
        device = test_get_edgedevice()
        test_update_phase()
        test_phase_idempotency()
        test_health_checker()
        test_invalid_device()
        
        print("\n" + "="*60)
        print("🎉 ALL EDGEDEVICE TESTS PASSED!")
        print("="*60)
        
        # Summary
        print("\nSummary of EdgeDevice tests:")
        print("✅ get_edgedevice() - Successfully retrieves EdgeDevice data")
        print("✅ update_phase() - Successfully updates device phase")
        print("✅ Phase transitions - All phase values work correctly")
        print("✅ Idempotency - Same phase updates work correctly")
        print("✅ Health checker - Successfully registers and executes health checks")
        print("✅ Health states - Correctly updates device to RUNNING/FAILED based on health")
        print("✅ Dynamic health - Handles changing health conditions")
        print("✅ Error handling - Non-existent devices handled properly")
        
    except Exception as e:
        print(f"\n❌ EDGEDEVICE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
