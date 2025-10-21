#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shifu SDK - Base functions 

This module provides the already-working base functions:
- init(), get_edgedevice(), update_phase(), add_health_checker(), start()
- helpers: get_device_config(), get_device_address(), get_device_protocol(), log_device_info(), setup_device_shifu()

Now also provides DeviceShifu class for multiple device management.
"""

import os
import time
import logging
from typing import Optional, Callable, Dict, Any
from enum import Enum
from kubernetes import client, config
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# EdgeDevice field constants
METADATA_KEY = "metadata"
SPEC_KEY = "spec"
STATUS_KEY = "status"
EDGEDEVICE_PHASE_KEY = "edgedevicephase"
ADDRESS_KEY = "address"
PROTOCOL_KEY = "protocol"

# ConfigMap field constants
INSTRUCTIONS_KEY = "instructions"
DRIVER_PROPERTIES_KEY = "driverProperties"
TELEMETRIES_KEY = "telemetries"
TELEMETRY_SETTINGS_KEY = "telemetrySettings"
K3S_CONFIGMAP_DIR = "/etc/edgedevice/config"


class EdgeDevicePhase(Enum):
    RUNNING = "Running"
    FAILED = "Failed"
    PENDING = "Pending"
    UNKNOWN = "Unknown"
# =============================================================================
# EdgeDevice K8S API: Global functions (maintains existing API)
# =============================================================================

# Global variables
k8s_client: Optional[client.CustomObjectsApi] = None
health_checker: Optional[Callable[[], EdgeDevicePhase]] = None
edgedevice_namespace: str = ""
edgedevice_name: str = ""
SHIFU_API_GROUP = os.getenv("SHIFU_API_GROUP", "shifu.edgenesis.io")
SHIFU_API_VERSION = os.getenv("SHIFU_API_VERSION", "v1alpha1")
SHIFU_API_PLURAL = os.getenv("SHIFU_API_PLURAL", "edgedevices")
def init():
    """Initialize SDK (env + Kubernetes client). [Backward compatibility]"""
    global k8s_client, edgedevice_namespace, edgedevice_name
    edgedevice_namespace = os.getenv("EDGEDEVICE_NAMESPACE", "devices")
    edgedevice_name = os.getenv("EDGEDEVICE_NAME")
    SHIFU_API_GROUP = os.getenv("SHIFU_API_GROUP", "shifu.edgenesis.io")
    SHIFU_API_VERSION = os.getenv("SHIFU_API_VERSION", "v1alpha1")
    SHIFU_API_PLURAL = os.getenv("SHIFU_API_PLURAL", "edgedevices")
    if not edgedevice_name:
        raise ValueError("EDGEDEVICE_NAME environment variable is required")

    logger.info("Initializing Shifu SDK for EdgeDevice: %s in namespace: %s",
                edgedevice_name, edgedevice_namespace)

    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    except Exception:
        try:
            config.load_kube_config()
            logger.info("Loaded local Kubernetes config")
        except Exception as e:
            logger.error("Failed to load Kubernetes config: %s", e)
            raise

    k8s_client = client.CustomObjectsApi()
    logger.info("Kubernetes client initialized successfully")

def get_edgedevice() -> Dict[str, Any]:
    """Get EdgeDevice (raw dict)."""
    if not k8s_client:
        init()
    try:
        logger.debug("Getting EdgeDevice: %s from namespace: %s", edgedevice_name, edgedevice_namespace)
        edge_device = k8s_client.get_namespaced_custom_object(
            group=SHIFU_API_GROUP,
            version=SHIFU_API_VERSION,
            namespace=edgedevice_namespace,
            plural=SHIFU_API_PLURAL,
            name=edgedevice_name,
        )
        logger.debug("Successfully retrieved EdgeDevice")
        return edge_device
    except Exception as e:
        logger.error("Failed to get EdgeDevice %s: %s", edgedevice_name, e)
        raise

def update_phase(phase: EdgeDevicePhase) -> bool:
    """Patch status.edgedevicephase to target Phase. Returns True on success; False on failure. """
    if not k8s_client:
        init()
    try:
        edge_device = get_edgedevice()
        current_phase = edge_device.get(STATUS_KEY, {}).get(EDGEDEVICE_PHASE_KEY)
        if current_phase == phase.value:
            logger.debug("EdgeDevice phase unchanged: %s", phase.value)
            return True

        logger.info("Updating EdgeDevice phase: %s -> %s", current_phase, phase.value)
        status_patch = {STATUS_KEY: {EDGEDEVICE_PHASE_KEY: phase.value}}

        # Try to use status subresource first (proper way for CRDs with status subresource)
        try:
            k8s_client.patch_namespaced_custom_object_status(
                group=SHIFU_API_GROUP,
                version=SHIFU_API_VERSION,
                namespace=edgedevice_namespace,
                plural=SHIFU_API_PLURAL,
                name=edgedevice_name,
                body=status_patch,
            )
            logger.info("Successfully updated EdgeDevice phase to: %s (via status subresource)", phase.value)
        except AttributeError:
            # Fallback for older kubernetes client versions
            k8s_client.patch_namespaced_custom_object(
                group=SHIFU_API_GROUP,
                version=SHIFU_API_VERSION,
                namespace=edgedevice_namespace,
                plural=SHIFU_API_PLURAL,
                name=edgedevice_name,
                body=status_patch,
            )
            logger.info("Successfully updated EdgeDevice phase to: %s (via regular patch)", phase.value)
        return True
    except Exception as e:
        logger.error("Failed to update EdgeDevice phase to %s: %s", phase.value, e)
        return False

def add_health_checker(checker: Callable[[], EdgeDevicePhase]):
    """Register health checker that RETURNS a Phase."""
    global health_checker
    if not callable(checker):
        raise ValueError("Health checker must be callable")
    health_checker = checker
    logger.info("Health checker registered successfully")

def start(interval: float = 3.0):
    """Start foreground health loop with configurable interval.
    
    Args:
        interval: Health check interval in seconds (default: 3.0)
    """
    if not health_checker:
        logger.warning("No health checker provided, exiting")
        return

    logger.info("Starting health monitoring loop (%s-second interval)", interval)
    health_check_count = 0
    last_status_log = 0.0

    while True:
        try:
            phase = health_checker()
            health_check_count += 1
            success = update_phase(phase)

            now = time.time()
            if (count_triggered := health_check_count % 20 == 0) or now - last_status_log > 60:
                logger.info("Health Check #%s: Device status = %s", health_check_count, phase.value)
                last_status_log = now
                # Reset counter only when count-based logging triggers
                if count_triggered:
                    health_check_count = 0  

            if not success:
                logger.warning("Failed to update EdgeDevice phase, continuing...")

        except Exception as e:
            logger.error("Health check failed: %s", e)
            try:
                update_phase(EdgeDevicePhase.FAILED)
            except Exception as update_error:
                logger.error("Failed to set phase to FAILED: %s", update_error)
        time.sleep(interval)

def get_device_config() -> Dict[str, Any]:
    """Return EdgeDevice.spec or {}. [Backward compatibility]"""
    try:
        edge_device = get_edgedevice()
        return edge_device.get(SPEC_KEY, {})
    except Exception as e:
        logger.error("Failed to get device config: %s", e)
        return {}

def get_device_address() -> str:
    """Return spec.address or ''. [Backward compatibility]"""
    return get_device_config().get(ADDRESS_KEY, "")

def get_device_protocol() -> str:
    """Return spec.protocol or ''. [Backward compatibility]"""
    return get_device_config().get(PROTOCOL_KEY, "")

def log_device_info():
    """Log metadata, address/protocol, and current phase. """
    try:
        edge_device = get_edgedevice()
        meta = edge_device.get(METADATA_KEY, {}) or {}
        logger.info("EdgeDevice Name: %s", meta.get("name", "unknown"))
        logger.info("EdgeDevice Namespace: %s", meta.get("namespace", "unknown"))
        logger.info("Device Address: %s", get_device_address())
        logger.info("Device Protocol: %s", get_device_protocol())
        current_phase = edge_device.get(STATUS_KEY, {}).get(EDGEDEVICE_PHASE_KEY, "unknown")
        logger.info("Current Phase: %s", current_phase)
    except Exception as e:
        logger.error("Failed to log device info: %s", e)

def setup_device_shifu(device_name: str, health_check_func: Callable[[], EdgeDevicePhase]):
    """Set EDGEDEVICE_NAME if unset, init, log info, and register health checker."""
    try:
        if not os.getenv("EDGEDEVICE_NAME"):
            os.environ["EDGEDEVICE_NAME"] = device_name
        init()
        log_device_info()
        add_health_checker(health_check_func)
        logger.info("DeviceShifu setup completed for %s", device_name)
        return True
    except Exception as e:
        logger.error("Failed to setup DeviceShifu for %s: %s", device_name, e)
        return False


# =============================================================================
# Config file loaders (mounted ConfigMap files) and normalization
# =============================================================================

def _read_first_existing_file(base_dir: str, basename: str) -> Optional[str]:
    """Return path to the first existing file among basename, basename.yaml, basename.yml in base_dir."""
    candidates = [
        os.path.join(base_dir, basename),
        os.path.join(base_dir, f"{basename}.yaml"),
        os.path.join(base_dir, f"{basename}.yml"),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def _safe_load_yaml_file(file_path: str) -> Dict[str, Any]:
    """Safely load YAML file into a dict. Returns {} on any error or empty content."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)  # type: ignore[no-untyped-call]
            if data is None:
                return {}
            if isinstance(data, dict):
                return data
            logger.warning("YAML root in %s is not a mapping. Normalizing to {}.", file_path)
            return {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error("Failed to read YAML file %s: %s", file_path, e)
        return {}


def load_config(config_dir: str = K3S_CONFIGMAP_DIR) -> Dict[str, Any]:
    """
    Load config from mounted ConfigMap files (reads from filesystem, not Kubernetes API).
    
    When a ConfigMap is mounted into a pod via volumeMounts, the YAML data becomes 
    files in the filesystem. This function reads those mounted files directly.
    
    Args:
        config_dir: Directory where ConfigMap files are mounted (default: "/etc/edgedevice/config")
    
    Returns:
        Normalized dict with keys:
        {
          "driverProperties": {...},
          "instructions": { "instructions": {...} },
          "telemetries": {
            "telemetrySettings": {...},
            "telemetries": {...}
          }
        }
    """
    driver_properties_path = _read_first_existing_file(config_dir, "driverProperties")
    instructions_path = _read_first_existing_file(config_dir, "instructions")
    telemetries_path = _read_first_existing_file(config_dir, "telemetries")

    raw_driver_properties = _safe_load_yaml_file(driver_properties_path) if driver_properties_path else {}
    raw_instructions = _safe_load_yaml_file(instructions_path) if instructions_path else {}
    raw_telemetries = _safe_load_yaml_file(telemetries_path) if telemetries_path else {}

    normalized: Dict[str, Any] = {
        DRIVER_PROPERTIES_KEY: raw_driver_properties or {},
        INSTRUCTIONS_KEY: {
            INSTRUCTIONS_KEY: (raw_instructions.get(INSTRUCTIONS_KEY, {}) if isinstance(raw_instructions, dict) else {})
        },
        TELEMETRIES_KEY: {
            TELEMETRY_SETTINGS_KEY: (
                raw_telemetries.get(TELEMETRY_SETTINGS_KEY, {}) if isinstance(raw_telemetries, dict) else {}
            ),
            TELEMETRIES_KEY: (
                raw_telemetries.get(TELEMETRIES_KEY, {}) if isinstance(raw_telemetries, dict) else {}
            ),
        },
    }

    return normalized




def get_instructions(config_dir: str = K3S_CONFIGMAP_DIR) -> Dict[str, Any]:
    """
    Get only the instructions from mounted ConfigMap files.
    Uses the main load_config function internally for consistency.
    
    Args:
        config_dir: Directory where ConfigMap files are mounted (default: "/etc/edgedevice/config")
    
    Returns:
        Dictionary containing the instructions data, or empty dict if not found/error
    """
    config = load_config(config_dir)
    return config.get(INSTRUCTIONS_KEY, {}).get(INSTRUCTIONS_KEY, {})


def get_driver_properties(config_dir: str = K3S_CONFIGMAP_DIR) -> Dict[str, Any]:
    """
    Get only the driver properties from mounted ConfigMap files.
    Uses the main load_config function internally for consistency.
    
    Args:
        config_dir: Directory where ConfigMap files are mounted (default: "/etc/edgedevice/config")
    
    Returns:
        Dictionary containing the driver properties data, or empty dict if not found/error
    """
    config = load_config(config_dir)
    return config.get(DRIVER_PROPERTIES_KEY, {})


def get_telemetries(config_dir: str = K3S_CONFIGMAP_DIR) -> Dict[str, Any]:
    """
    Get only the telemetries from mounted ConfigMap files.
    Uses the main load_config function internally for consistency.
    
    Args:
        config_dir: Directory where ConfigMap files are mounted (default: "/etc/edgedevice/config")
    
    Returns:
        Dictionary containing the telemetries data, or empty dict if not found/error
    """
    config = load_config(config_dir)
    return config.get(TELEMETRIES_KEY, {})

