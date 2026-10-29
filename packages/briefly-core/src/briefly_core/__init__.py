"""Core library for Briefly."""

from .config import LoadedConfig, load_config, normalize_config, parse_config_text, resolve_config_path
from .flags import (
    BRIEF_LENGTHS,
    BriefLength,
    LengthArg,
    parse_extract_format,
    parse_length_arg,
    parse_max_extract_characters,
    parse_max_output_tokens,
    parse_stream_mode,
)

__all__ = [
    "LoadedConfig",
    "BRIEF_LENGTHS",
    "BriefLength",
    "LengthArg",
    "load_config",
    "normalize_config",
    "parse_config_text",
    "parse_extract_format",
    "parse_length_arg",
    "parse_max_extract_characters",
    "parse_max_output_tokens",
    "parse_stream_mode",
    "resolve_config_path",
]
