import logging
from typing import List, Tuple, Any, Dict, Type

# Assuming DeviceStep and DeviceConfig are defined elsewhere in device_operations.py
class DeviceStep:
    def __init__(self, method: str, kwargs: Dict[str, Any]):
        self.method = method
        self.kwargs = kwargs

class DeviceConfig:
    def __init__(self, name: str, ip: str, username: str, password: str, manager_class: Type, steps: List[DeviceStep]):
        self.name = name
        self.ip = ip
        self.username = username
        self.password = password
        self.manager_class = manager_class
        self.steps = steps

def apply_configurations(device_configs: List[DeviceConfig]) -> None:
    """
    Apply configurations to network devices with detailed logging and rollback capability.
    
    Args:
        device_configs (List[DeviceConfig]): List of device configurations to apply.
    
    Raises:
        Exception: If an error occurs during configuration, after attempting rollback.
    """
    # Set up logging with timestamp, level, and message format
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Log the start of the entire configuration process
    logger.info("Starting network device configuration")

    # Track all successfully applied steps across devices for global rollback
    applied_steps: List[Tuple[DeviceConfig, DeviceStep]] = []

    try:
        # Process each device configuration
        for device_config in device_configs:
            logger.info(f"Configuring device: {device_config.name} ({device_config.ip})")
            device_steps = []  # Track steps applied to this device for device-specific rollback
            try:
                # Connect to the device using its manager class
                with device_config.manager_class(
                    ip=device_config.ip,
                    username=device_config.username,
                    password=device_config.password
                ) as manager:
                    # Apply each configuration step
                    for step in device_config.steps:
                        logger.info(f"Applying step: {step.method} with kwargs: {step.kwargs}")
                        getattr(manager, step.method)(**step.kwargs)
                        logger.info(f"Successfully applied step: {step.method}")
                        device_steps.append(step)
                # Record all steps applied to this device in the global list
                applied_steps.extend((device_config, step) for step in device_steps)
                logger.info(f"Completed configuration for device: {device_config.name} ({device_config.ip})")
            except Exception as error:
                # Log the error and initiate rollback for this device
                logger.error(f"Error applying configuration on {device_config.name} ({device_config.ip}): {str(error)}")
                logger.info(f"Starting rollback for device: {device_config.name} ({device_config.ip})")
                for step in reversed(device_steps):
                    try:
                        with device_config.manager_class(
                            ip=device_config.ip,
                            username=device_config.username,
                            password=device_config.password
                        ) as rollback_manager:
                            logger.info(f"Rolling back step: {step.method} with kwargs: {step.kwargs}")
                            getattr(rollback_manager, step.method)(**step.kwargs, undo=True)
                            logger.info(f"Successfully rolled back step: {step.method}")
                    except Exception as rollback_error:
                        logger.error(f"Error rolling back step {step.method} on {device_config.name} ({device_config.ip}): {str(rollback_error)}")
                # Raise the original exception to trigger global rollback
                raise
        # Log successful completion if all devices are configured
        logger.info("All devices configured successfully")
    except Exception as error:
        # Log the global failure and initiate full rollback
        logger.info("Starting global rollback")
        for device_config, step in reversed(applied_steps):
            try:
                with device_config.manager_class(
                    ip=device_config.ip,
                    username=device_config.username,
                    password=device_config.password
                ) as manager:
                    logger.info(f"Rolling back step: {step.method} on {device_config.name} ({device_config.ip} with kwargs: {step.kwargs}")
                    getattr(manager, step.method)(**step.kwargs, undo=True)
                    logger.info(f"Successfully rolled back step: {step.method} on {device_config.name} ({device_config.ip})")
            except Exception as rollback_error:
                logger.error(f"Error rolling back step {step.method} on {device_config.name} ({device_config.ip}) with kwargs {step.kwargs}: {str(rollback_error)}")
        # Re-raise the original exception after attempting global rollback
        raise

def undo_configurations(device_configs: List[DeviceConfig]) -> None:
    """
    Undo configurations applied to network devices.
    
    This function reverses the configurations by processing devices in reverse order and,
    for each device, undoing its steps in reverse order. Each step's method is called with
    its original kwargs and undo=True. If an error occurs during an undo attempt, it is
    logged, and the process continues to ensure all possible steps are undone, aiming to
    restore the original state of the devices as much as possible.
    
    Args:
        device_configs (List[DeviceConfig]): List of device configurations to undo.
    """
    # Set up logging with timestamp, level, and message format
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Log the start of the undo process
    logger.info("Starting undo of network device configurations")
    
    # Process devices in reverse order
    for device_config in reversed(device_configs):
        logger.info(f"Undoing configurations for device: {device_config.name} ({device_config.ip})")
        
        # Process steps in reverse order for the current device
        for step in reversed(device_config.steps):
            try:
                # Establish a new connection for each step to ensure reliability
                with device_config.manager_class(
                    ip=device_config.ip,
                    username=device_config.username,
                    password=device_config.password
                ) as manager:
                    logger.info(f"Undoing step: {step.method} with kwargs: {step.kwargs}")
                    getattr(manager, step.method)(**step.kwargs, undo=True)
                    logger.info(f"Successfully undid step: {step.method}")
            except Exception as error:
                logger.error(f"Error undoing step {step.method} on {device_config.name} ({device_config.ip}): {str(error)}")
        
        # Log completion of undo for this device
        logger.info(f"Completed undoing configurations for device: {device_config.name} ({device_config.ip})")
    
    # Log completion of the entire undo process
    logger.info("Completed undo of all network device configurations")