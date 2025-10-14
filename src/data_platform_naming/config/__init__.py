"""
Configuration module for loading and managing naming values and patterns.
"""

from .configuration_manager import ConfigurationManager, GeneratedName
from .naming_patterns_loader import NamingPattern, NamingPatternsLoader, PatternError
from .naming_values_loader import NamingValuesLoader
from .scope_filter import FilterMode, ScopeConfig, ScopeFilter

__all__ = [
    "NamingValuesLoader",
    "NamingPatternsLoader",
    "NamingPattern",
    "PatternError",
    "ConfigurationManager",
    "GeneratedName",
    "ScopeFilter",
    "FilterMode",
    "ScopeConfig"
]
