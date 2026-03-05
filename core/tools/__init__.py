"""Tool registry with auto-discovery.

Every tool module in this directory is imported automatically.
Tools register themselves via register_tools().
Tools that return None from their factory are skipped."""

import importlib
import pkgutil
from typing import Callable

from core.config import Config
from core.tools.base import Tool


# Type for factory functions
ToolFactory = Callable[[Config], Tool | None]

# Registry: name → factory
_registry: dict[str, ToolFactory] = {}


def register_tools(name: str, factory: ToolFactory) -> None:
    """Register a tools factory. Called by each tool module."""
    _registry[name] = factory


def create_tools(config: Config) -> list[Tool]:
    """Create all registered tools """
    working_dir = config.data_dir / "working_dir"
    working_dir.mkdir(parents=True, exist_ok=True)

    tools = []
    for name, factory in _registry.items():
        tool = factory(config)
        if tool is not None:
            tools.append(tool)
    return tools


# Auto-discovery: Import all modules in this package.
# Each module calls register_tool() on import.
def _discover_tools():
    package_path = __path__
    for _importer, module_name, _ispkg in pkgutil.iter_modules(package_path):
        if module_name != "base":  # skip base.py
            importlib.import_module(f"core.tools.{module_name}")


_discover_tools()