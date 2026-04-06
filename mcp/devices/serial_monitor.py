import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional

from serial import Serial

from mcp.plugins import plugins

# Module-level state
logger: Optional[logging.Logger] = None
monitor_thread: Optional[threading.Thread] = None
serial_connection: Optional[Serial] = None
obs: Any = None

# Hardware protocol constants
CMD_START = b'\xFE'
CMD_END = b'\xFF'

HEARTBEAT_STATUS_DELTA = timedelta(seconds=15)
HEARTBEAT_FAILURE_DELTA = timedelta(seconds=120)

callables: List[Callable] = []

class Host:
    """Represents a hardware transceiver at a specific address."""
    address: int = 17
    is_active: bool = False
    last_status_request: datetime = datetime.min
    last_status: datetime = datetime.min

    def __init__(self, serial_inst: Serial):
        self._serial = serial_inst

    def admit_access(self, door_num: int) -> None:
        """Sends an access granted command to the device."""
        checksum = ord('A') ^ door_num
        payload = bytes([ord(CMD_START), ord('A'), door_num, checksum, ord(CMD_END)])
        self._serial.write(payload)

hosts: List[Host] = []

def init(config: Any, obs_main: Any) -> None:
    """Initialize the serial polling engine."""
    global monitor_thread, logger, serial_connection, obs
    logger = logging.getLogger(__name__)
    obs = obs_main

    port = config.get('serial', 'port')
    baud = config.getint('serial', 'baud')
    timeout = config.getint('serial', 'timeout', fallback=1)

    logger.info(f"Connecting to hardware via serial ({port} @ {baud} baud)")
    serial_connection = Serial(port, baud, timeout=timeout)

    hosts.append(Host(serial_connection))
    _load_serial_plugins(config, obs_main)

    monitor_thread = threading.Thread(target=watch_serial, daemon=True)
    monitor_thread.start()

def _load_serial_plugins(config: Any, obs_main: Any) -> None:
    """Discovers and configures device plugins."""
    logger.info("Scanning for device interaction plugins...")
    plugin_path = os.path.join(os.path.dirname(__file__), '..', '..', 'plugins', 'devices')
    dev_plugins = plugins.get_plugins(plugin_path, 'mcp.plugins.devices')
    
    for plugin in dev_plugins:
        if hasattr(plugin, 'configure'):
            plugin.configure(config, obs_main)
        for name, value in plugin.__dict__.items():
            if hasattr(value, 'command') and callable(value):
                callables.append(value)

def watch_serial() -> None:
    """Main background loop monitoring the serial bus."""
    logger.info("Serial monitor loop active.")
    if not serial_connection: return

    while True:
        for host in hosts:
            try:
                time.sleep(0.1)
                now = datetime.now()
                
                if (now - host.last_status > HEARTBEAT_STATUS_DELTA):
                    if (now - host.last_status_request > HEARTBEAT_STATUS_DELTA):
                        host.last_status_request = now
                        serial_connection.write(CMD_START + b'SS' + CMD_END)

                line = serial_connection.readline()
                if line:
                    _process_hardware_line(host, line)

                if (now - host.last_status > HEARTBEAT_FAILURE_DELTA):
                    if host.is_active:
                        logger.error(f"Hardware at address {host.address} unreachable.")
                        obs.trigger('device_down', host)
                    host.is_active = False
                    host.last_status = now - HEARTBEAT_STATUS_DELTA + timedelta(seconds=60)
            except Exception:
                logger.error("Hardware communication error", exc_info=True)
                time.sleep(5)

def _process_hardware_line(host: Host, data: bytes) -> None:
    """Parses and routes raw bytes from hardware to plugin callbacks."""
    try:
        start_idx = data.find(CMD_START)
        end_idx = data.find(CMD_END)
        if start_idx == -1 or end_idx == -1: return

        command_body = data[start_idx + 1:end_idx].decode('utf-8', errors='ignore').strip()
        args = command_body.split(',')
        if not args: return
            
        cmd_type = args[0]
        for callback in callables:
            if getattr(callback, 'command', None) == cmd_type:
                callback(host, command_body, args)
    except Exception as e:
        logger.error(f"Data processing failure: {e}")
