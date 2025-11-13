#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple DeviceShifu Example - Tests Shifu SDK in Kubernetes

This example:
1. Initializes the SDK
2. Gets EdgeDevice information
3. Runs health checks
4. Updates device status
"""

import time
import logging
from shifu_sdk import (
    init,
    get_edgedevice,
    update_phase,
    add_health_checker,
    start,
    EdgeDevicePhase,
    load_config,
    get_device_address,
    get_device_protocol,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def simple_health_checker() -> EdgeDevicePhase:
    """
    Simple health checker that always returns RUNNING.
    
    In a real deviceShifu, this would:
    - Check if the device is responsive
    - Validate sensor readings
    - Test connectivity
    """
    logger.info("Performing health check...")
    
    try:
        # Get device address
        address = get_device_address()
        protocol = get_device_protocol()
        
        logger.info(f"Device address: {address}")
        logger.info(f"Device protocol: {protocol}")
        
        # In a real implementation, you would:
        # - Make HTTP/MQTT/etc request to the device
        # - Check if response is valid
        # - Return RUNNING if healthy, FAILED if not
        
        # For this example, always return RUNNING
        logger.info("Health check passed - device is healthy")
        return EdgeDevicePhase.RUNNING
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return EdgeDevicePhase.FAILED


def main():
    """Main entry point for the deviceShifu."""
    logger.info("=" * 60)
    logger.info("Starting DeviceShifu Example")
    logger.info("=" * 60)
    
    try:
        # Step 1: Initialize SDK
        logger.info("Step 1: Initializing Shifu SDK...")
        init()
        logger.info("✅ SDK initialized successfully")
        
        # Step 2: Get EdgeDevice information
        logger.info("\nStep 2: Getting EdgeDevice information...")
        edge_device = get_edgedevice()
        
        logger.info("EdgeDevice Information:")
        logger.info(f"  Name: {edge_device['metadata']['name']}")
        logger.info(f"  Namespace: {edge_device['metadata']['namespace']}")
        logger.info(f"  Address: {edge_device['spec'].get('address', 'N/A')}")
        logger.info(f"  Protocol: {edge_device['spec'].get('protocol', 'N/A')}")
        logger.info(f"  SKU: {edge_device['spec'].get('sku', 'N/A')}")
        logger.info(f"  Current Phase: {edge_device.get('status', {}).get('edgedevicephase', 'Unknown')}")
        logger.info("✅ EdgeDevice retrieved successfully")
        
        # Step 3: Load configuration from ConfigMap
        logger.info("\nStep 3: Loading configuration from ConfigMap...")
        try:
            config = load_config()
            driver_props = config.get('driverProperties', {})
            logger.info("Configuration loaded:")
            logger.info(f"  Driver SKU: {driver_props.get('driverSku', 'N/A')}")
            logger.info(f"  Driver Image: {driver_props.get('driverImage', 'N/A')}")
            logger.info("✅ Configuration loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load configuration: {e}")
            logger.info("ℹ️  This is normal if no ConfigMap is mounted")
        
        # Step 4: Test manual phase update
        logger.info("\nStep 4: Testing manual phase update...")
        success = update_phase(EdgeDevicePhase.RUNNING)
        if success:
            logger.info("✅ Phase updated to RUNNING")
        else:
            logger.error("❌ Failed to update phase")
        
        # Verify the update
        time.sleep(1)
        updated_device = get_edgedevice()
        current_phase = updated_device.get('status', {}).get('edgedevicephase')
        logger.info(f"  Verified phase: {current_phase}")
        
        # Step 5: Register health checker
        logger.info("\nStep 5: Registering health checker...")
        add_health_checker(simple_health_checker)
        logger.info("✅ Health checker registered")
        
        # Step 6: Start health monitoring loop
        logger.info("\nStep 6: Starting health monitoring loop...")
        logger.info("Health checks will run every 30 seconds")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        start(interval=30.0)
        
    except KeyboardInterrupt:
        logger.info("\n\nReceived interrupt signal - shutting down gracefully")
        logger.info("✅ DeviceShifu stopped")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
        # Set phase to FAILED before exiting
        try:
            update_phase(EdgeDevicePhase.FAILED)
        except:
            pass
        
        raise


if __name__ == "__main__":
    main()


