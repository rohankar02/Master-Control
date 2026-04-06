import importlib.util
import logging
import os
import sys
from typing import Any, List

def get_plugins(plugin_dir: str, module_prefix: str) -> List[Any]:
    """Dynamically loads Python plugins from a directory.
    
    Args:
        plugin_dir: Directory containing .py files.
        module_prefix: Prefix for the generated module name.
        
    Returns:
        List of successfully loaded module objects.
    """
    plugins = []
    logger = logging.getLogger(__name__)

    if not os.path.exists(plugin_dir):
        logger.warning(f"Plugin directory not found: {plugin_dir}")
        return plugins

    # Filter for python files excluding __init__.py
    plugin_files = [f for f in os.listdir(plugin_dir) if f.endswith('.py') and f != '__init__.py']

    for plugin_file in plugin_files:
        plugin_name = plugin_file[:-3]
        plugin_path = os.path.join(plugin_dir, plugin_file)
        full_module_name = f"{module_prefix.strip('.')}.{plugin_name}"
        
        logger.info(f"Attempting to load plugin: {plugin_name} from {plugin_path}")
        
        try:
            # Modern importlib logic
            spec = importlib.util.spec_from_file_location(full_module_name, plugin_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[full_module_name] = module
                spec.loader.exec_module(module)
                
                # Optional setup call
                if hasattr(module, 'setup'):
                    module.setup()
                
                plugins.append(module)
                logger.debug(f"Successfully loaded and initialized: {plugin_name}")
            else:
                logger.error(f"Could not create spec for plugin: {plugin_path}")
                
        except Exception as e:
            logger.error(f"Failure during plugin load/setup ({plugin_file}): {str(e)}", exc_info=True)

    return plugins

