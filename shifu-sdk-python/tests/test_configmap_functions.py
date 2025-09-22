#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for config loading functions: get_instructions, get_driver_properties, get_telemetries

This test creates mock ConfigMap files and tests the three get functions.
"""

import os
import tempfile
import shutil
from pathlib import Path

from shifu_sdk import (
    load_config,
    get_instructions,
    get_driver_properties,
    get_telemetries,
)


def create_test_config_files(test_dir: str):
    """Create test ConfigMap files in the test directory."""
    
    # Create driverProperties file
    driver_properties_content = '''driverSku: "TAS-WS-R0020"
driverImage: "test-image:v1.0"
enabled: true
timeout: 30'''
    
    with open(os.path.join(test_dir, "driverProperties"), "w") as f:
        f.write(driver_properties_content)
    
    # Create instructions file
    instructions_content = '''instructions:
  th:
    command: "GET /temperature"
    timeout: 5
  Temperature:
    command: "GET /temp"
    method: "POST"
  Humidity:
    command: "GET /humidity"
    params:
      unit: "percent"'''
    
    with open(os.path.join(test_dir, "instructions"), "w") as f:
        f.write(instructions_content)
    
    # Create telemetries file
    telemetries_content = '''telemetries:
  temperature:
    properties:
      - name: "value"
        type: "float"
        unit: "celsius"
  humidity:
    properties:
      - name: "value"
        type: "float"
        unit: "percent"
telemetrySettings:
  interval: 10
  enabled: true'''
    
    with open(os.path.join(test_dir, "telemetries"), "w") as f:
        f.write(telemetries_content)


def test_load_config():
    """Test the main load_config function."""
    print("=== Testing load_config() ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary test directory: {temp_dir}")
        
        # Create test files
        create_test_config_files(temp_dir)
        
        # Test load_config
        config = load_config(temp_dir)
        
        print("Loaded config structure:")
        print(f"  driverProperties keys: {list(config.get('driverProperties', {}).keys())}")
        print(f"  instructions keys: {list(config.get('instructions', {}).get('instructions', {}).keys())}")
        print(f"  telemetries keys: {list(config.get('telemetries', {}).keys())}")
        
        # Verify structure
        assert "driverProperties" in config
        assert "instructions" in config
        assert "telemetries" in config
        assert "instructions" in config["instructions"]
        
        print("✅ load_config() test passed!")
        return config


def test_get_driver_properties():
    """Test the get_driver_properties function."""
    print("\n=== Testing get_driver_properties() ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary test directory: {temp_dir}")
        
        # Create test files
        create_test_config_files(temp_dir)
        
        # Test get_driver_properties
        driver_props = get_driver_properties(temp_dir)
        
        print("Driver Properties:")
        for key, value in driver_props.items():
            print(f"  {key}: {value}")
        
        # Verify content
        assert driver_props.get("driverSku") == "TAS-WS-R0020"
        assert driver_props.get("enabled") is True
        assert driver_props.get("timeout") == 30
        
        print("✅ get_driver_properties() test passed!")
        return driver_props


def test_get_instructions():
    """Test the get_instructions function."""
    print("\n=== Testing get_instructions() ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary test directory: {temp_dir}")
        
        # Create test files
        create_test_config_files(temp_dir)
        
        # Test get_instructions
        instructions = get_instructions(temp_dir)
        
        print("Instructions:")
        for key, value in instructions.items():
            print(f"  {key}: {value}")
        
        # Verify content
        assert "th" in instructions
        assert "Temperature" in instructions
        assert "Humidity" in instructions
        assert instructions["th"]["command"] == "GET /temperature"
        assert instructions["Humidity"]["params"]["unit"] == "percent"
        
        print("✅ get_instructions() test passed!")
        return instructions


def test_get_telemetries():
    """Test the get_telemetries function."""
    print("\n=== Testing get_telemetries() ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary test directory: {temp_dir}")
        
        # Create test files
        create_test_config_files(temp_dir)
        
        # Test get_telemetries
        telemetries = get_telemetries(temp_dir)
        
        print("Telemetries:")
        for key, value in telemetries.items():
            print(f"  {key}: {value}")
        
        # Verify content
        assert "telemetries" in telemetries
        assert "telemetrySettings" in telemetries
        assert telemetries["telemetrySettings"]["interval"] == 10
        assert telemetries["telemetrySettings"]["enabled"] is True
        assert "temperature" in telemetries["telemetries"]
        assert "humidity" in telemetries["telemetries"]
        
        print("✅ get_telemetries() test passed!")
        return telemetries


def test_missing_files():
    """Test behavior when config files are missing."""
    print("\n=== Testing missing files scenario ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using empty test directory: {temp_dir}")
        
        # Test with empty directory (no files)
        config = load_config(temp_dir)
        driver_props = get_driver_properties(temp_dir)
        instructions = get_instructions(temp_dir)
        telemetries = get_telemetries(temp_dir)
        
        print("Results with missing files:")
        print(f"  config: {config}")
        print(f"  driver_props: {driver_props}")
        print(f"  instructions: {instructions}")
        print(f"  telemetries: {telemetries}")
        
        # Verify empty results (but with consistent structure)
        assert config["driverProperties"] == {}
        assert config["instructions"]["instructions"] == {}
        assert config["telemetries"] == {"telemetrySettings": {}, "telemetries": {}}
        assert driver_props == {}
        assert instructions == {}
        assert telemetries == {"telemetrySettings": {}, "telemetries": {}}
        
        print("✅ Missing files test passed!")


def main():
    """Run all tests."""
    print("Starting ConfigMap functions tests...\n")
    
    try:
        # Run individual tests
        config = test_load_config()
        driver_props = test_get_driver_properties()
        instructions = test_get_instructions()
        telemetries = test_get_telemetries()
        
        # Test edge case
        test_missing_files()
        
        print("\n" + "="*50)
        print("🎉 ALL TESTS PASSED!")
        print("="*50)
        
        # Summary
        print("\nSummary of test results:")
        print(f"✅ load_config() - Found {len(config)} main sections")
        print(f"✅ get_driver_properties() - Found {len(driver_props)} properties")
        print(f"✅ get_instructions() - Found {len(instructions)} instructions")
        print(f"✅ get_telemetries() - Found {len(telemetries)} telemetry sections")
        print("✅ Missing files handling works correctly")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    main()
