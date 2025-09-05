"""JSON codec for event serialization/deserialization."""

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from ..message import Event

__all__ = ["JsonCodec"]


class JsonCodec:
    """
    JSON codec for encoding/decoding events.

    Provides stable JSON serialization with proper handling of datetime
    and UUID objects. Supports schema validation hooks for payload validation.
    """

    def __init__(
        self,
        *,
        ensure_ascii: bool = False,
        indent: Optional[int] = None,
        separators: Optional[tuple[str, str]] = (",", ":"),
        sort_keys: bool = True,
        schema_validator: Optional[Callable[[str, dict[str, Any]], None]] = None,
    ):
        """
        Initialize JSON codec.

        Args:
            ensure_ascii: If True, escape non-ASCII characters
            indent: JSON indentation (None for compact output)
            separators: JSON separators (item, key-value)
            sort_keys: If True, sort dictionary keys for stable output
            schema_validator: Optional function to validate event payload schema
        """
        self.ensure_ascii = ensure_ascii
        self.indent = indent
        self.separators = separators
        self.sort_keys = sort_keys
        self.schema_validator = schema_validator

    @property
    def content_type(self) -> str:
        """Content type identifier for JSON codec."""
        return "application/json"

    def encode(self, event: Event) -> bytes:
        """
        Encode an event to JSON bytes.

        Args:
            event: Event to encode

        Returns:
            JSON-encoded event as bytes
        """
        # Validate payload schema if validator is configured
        if self.schema_validator:
            self.schema_validator(event.topic, event.payload)

        # Convert event to dictionary
        event_dict = event.to_dict()

        # Serialize to JSON with custom encoder for datetime/UUID
        json_str = json.dumps(
            event_dict,
            default=self._json_encoder,
            ensure_ascii=self.ensure_ascii,
            indent=self.indent,
            separators=self.separators,
            sort_keys=self.sort_keys,
        )

        return json_str.encode("utf-8")

    def decode(self, data: bytes) -> Event:
        """
        Decode JSON bytes to an event.

        Args:
            data: JSON bytes to decode

        Returns:
            Decoded Event object

        Raises:
            ValueError: If data is not valid JSON or event structure
        """
        try:
            # Decode bytes to string and parse JSON
            json_str = data.decode("utf-8")
            event_dict = json.loads(json_str)

            # Validate required fields
            if not isinstance(event_dict, dict):
                raise ValueError("Event data must be a JSON object")

            if "topic" not in event_dict:
                raise ValueError("Event must have a 'topic' field")

            if "payload" not in event_dict:
                raise ValueError("Event must have a 'payload' field")

            # Create event from dictionary
            return Event.from_dict(event_dict)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON data: {e}") from e
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid event structure: {e}") from e

    def _json_encoder(self, obj: Any) -> Any:
        """Custom JSON encoder for datetime and UUID objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        else:
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    # Factory methods for common configurations

    @classmethod
    def compact(cls, **kwargs: Any) -> "JsonCodec":
        """Create a compact JSON codec (no indentation, minimal spacing)."""
        return cls(ensure_ascii=False, indent=None, separators=(",", ":"), sort_keys=True, **kwargs)

    @classmethod
    def pretty(cls, **kwargs: Any) -> "JsonCodec":
        """Create a pretty-printed JSON codec (with indentation)."""
        return cls(ensure_ascii=False, indent=2, separators=(",", ": "), sort_keys=True, **kwargs)

    @classmethod
    def with_schema_validation(
        cls, schema_validator: Callable[[str, dict[str, Any]], None], **kwargs: Any
    ) -> "JsonCodec":
        """
        Create a JSON codec with schema validation.

        Args:
            schema_validator: Function that validates (topic, payload) and raises
                           an exception if invalid
            **kwargs: Additional codec options
        """
        return cls(schema_validator=schema_validator, **kwargs)
