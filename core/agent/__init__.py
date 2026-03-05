"""
Channel registry with auto-discovery.

Every channel module in this directory is imported automatically.
Channels register themselves via register_channel().
Channels whose credentials are missing are skipped (return None).

"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Callable

from core.channels.base import Channel, MessageHandler
from core.config import Config

# Type for factory functions
ChannelFactory = Callable[[Config], Channel | None]

# Registry: name → factory
_registry: dict[str, ChannelFactory] = {}


def register_channel(name: str, factory: ChannelFactory) -> None:
    """Register a channel factory. Called by each channel module."""
    _registry[name] = factory


def create_channels(config: Config) -> list[Channel]:
    """Create all registered channels. Skips missing credentials."""
    channels = []
    for name, factory in _registry.items():
        channel = factory(config)
        if channel is not None:
            channels.append(channel)
    return channels


# Auto-discovery: Import all modules in this package.
# Each module calls register_channel() on import.
def _discover_channels():
    package_path = __path__
    for _importer, module_name, _ispkg in pkgutil.iter_modules(package_path):
        if module_name != "base":  # skip base.py
            importlib.import_module(f"core.channels.{module_name}")


_discover_channels()