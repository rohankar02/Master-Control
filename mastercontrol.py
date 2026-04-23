import configparser
import errno
import logging
import logging.config
import os
import signal
import sys
import time
from typing import NoReturn

from observable import Observable

from mcp.db import db
from mcp.devices import serial_monitor
from mcp.mq import mq

def setup_logging() -> None:
    """Ensures log directories exist and configures the logger."""
    log_dir = 'logs'
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print(f"Failed to create logs directory: {e}")
            sys.exit(1)
            
    if os.path.exists("config/logging.ini"):
        logging.config.fileConfig("config/logging.ini")
    else:
        logging.basicConfig(level=logging.INFO)

def signal_handler(sig: int, frame: Any) -> NoReturn:
    """
    This function handles when you press Ctrl+C to stop the program.
    It prints a message and closes the program safely.
    """
    print("\n^C received - shutting down Master Control...")
    sys.exit(0)

def main() -> None:
    """
    This is where the program starts running.
    """
    print("--- Master Control System v2.0 Starting ---")
    
    # 1. We load our configuration file to get settings
    config = configparser.ConfigParser()
    config_path = "config/mastercontrol.ini"
    
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}")
        print("Please copy config/template.ini to config/mastercontrol.ini and update values.")
        sys.exit(1)
        
    config.read(config_path)
    
    # 2. Setup our logger so we can track what happens
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Master Control System...")

    # 3. Tell the computer what to do when we stop the program
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Core Components Setup
    obs = Observable()
    
    try:
        db.init(config)
        serial_monitor.init(config, obs)
        mq.init(config, obs)
    except Exception as e:
        logger.critical(f"Failed to initialize core components: {str(e)}", exc_info=True)
        sys.exit(1)

    logger.info("System fully initialized. Entering main monitoring loop.")
    
    # Main application loop
    try:
        while True:
            time.sleep(100)
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        sys.exit(1)

if __name__ == "__main__":
    from typing import Any # Local import for signal handler frame
    main()

