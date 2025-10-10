"""
Configuration module for loading and managing naming values and patterns.
"""

from .naming_values_loader import NamingValuesLoader
from .naming_patterns_loader import NamingPatternsLoader, NamingPattern, PatternError
from .configuration_manager import ConfigurationManager, GeneratedName
from .scope_filter import ScopeFilter, FilterMode, ScopeConfig

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
