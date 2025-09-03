"""Tests for JSON codec."""

import json
import uuid
from datetime import datetime

import pytest

from dotmac.events import Event, JsonCodec


class TestJsonCodec:
    """Test JSON codec functionality."""
    
    def test_encode_decode_roundtrip(self):
        """Test encoding and decoding round trip."""
        codec = JsonCodec.compact()
        
        event = Event(
            topic="test.topic",
            payload={"key": "value", "number": 42, "boolean": True},
            key="test-key",
            headers={"x-custom": "header"},
            tenant_id="tenant-123",
        )
        
        # Encode
        encoded = codec.encode(event)
        assert isinstance(encoded, bytes)
        
        # Decode
        decoded = codec.decode(encoded)
        
        # Verify
        assert decoded.topic == event.topic
        assert decoded.payload == event.payload
        assert decoded.key == event.key
        assert decoded.headers == event.headers
        assert decoded.tenant_id == event.tenant_id
        assert decoded.id == event.id
    
    def test_encode_produces_valid_json(self):
        """Test that encoding produces valid JSON."""
        codec = JsonCodec.compact()
        
        event = Event(
            topic="test.topic",
            payload={"message": "hello world"},
        )
        
        encoded = codec.encode(event)
        
        # Should be valid JSON
        data = json.loads(encoded.decode("utf-8"))
        assert isinstance(data, dict)
        assert data["topic"] == "test.topic"
        assert data["payload"]["message"] == "hello world"
    
    def test_stable_serialization(self):
        """Test that serialization is stable (sorted keys)."""
        codec = JsonCodec.compact()
        
        event = Event(
            topic="test.topic",
            payload={"z": 3, "a": 1, "b": 2},  # Unsorted keys
        )
        
        encoded1 = codec.encode(event)
        encoded2 = codec.encode(event)
        
        # Should be identical
        assert encoded1 == encoded2
        
        # Keys should be sorted in JSON
        json_str = encoded1.decode("utf-8")
        # Find payload section and verify order
        assert '"payload":{"a":1,"b":2,"z":3}' in json_str
    
    def test_pretty_codec_formatting(self):
        """Test pretty-printed codec formatting."""
        codec = JsonCodec.pretty()
        
        event = Event(
            topic="test.topic",
            payload={"key": "value"},
        )
        
        encoded = codec.encode(event)
        json_str = encoded.decode("utf-8")
        
        # Should have indentation
        assert "\n" in json_str
        assert "  " in json_str  # Indentation spaces
    
    def test_decode_invalid_json(self):
        """Test decoding invalid JSON."""
        codec = JsonCodec.compact()
        
        with pytest.raises(ValueError, match="Invalid JSON data"):
            codec.decode(b"invalid json")
    
    def test_decode_missing_required_fields(self):
        """Test decoding JSON missing required fields."""
        codec = JsonCodec.compact()
        
        # Missing topic
        with pytest.raises(ValueError, match="must have a 'topic' field"):
            codec.decode(b'{"payload": {"key": "value"}}')
        
        # Missing payload
        with pytest.raises(ValueError, match="must have a 'payload' field"):
            codec.decode(b'{"topic": "test"}')
    
    def test_content_type(self):
        """Test codec content type."""
        codec = JsonCodec()
        assert codec.content_type == "application/json"
    
    def test_schema_validation(self):
        """Test schema validation hook."""
        validation_calls = []
        
        def validate_schema(topic: str, payload: dict) -> None:
            validation_calls.append((topic, payload))
            if topic == "invalid.topic":
                raise ValueError("Invalid topic")
        
        codec = JsonCodec.with_schema_validation(validate_schema)
        
        # Valid event
        event = Event(topic="valid.topic", payload={"key": "value"})
        codec.encode(event)
        
        assert len(validation_calls) == 1
        assert validation_calls[0] == ("valid.topic", {"key": "value"})
        
        # Invalid event
        invalid_event = Event(topic="invalid.topic", payload={})
        with pytest.raises(ValueError, match="Invalid topic"):
            codec.encode(invalid_event)
    
    def test_datetime_serialization(self):
        """Test datetime object serialization."""
        codec = JsonCodec.compact()
        
        # Event with metadata containing datetime
        event = Event(
            topic="test.topic",
            payload={"key": "value"},
        )
        
        # Encode and decode
        encoded = codec.encode(event)
        decoded = codec.decode(encoded)
        
        # Timestamps should be preserved (as ISO format)
        assert decoded.timestamp is not None
        assert isinstance(decoded.timestamp, datetime)
    
    def test_uuid_serialization(self):
        """Test UUID serialization."""
        codec = JsonCodec.compact()
        
        event = Event(
            topic="test.topic",
            payload={"key": "value"},
        )
        
        original_id = event.id
        
        # Encode and decode
        encoded = codec.encode(event)
        decoded = codec.decode(encoded)
        
        # ID should be preserved
        assert decoded.id == original_id
        assert isinstance(decoded.id, uuid.UUID)
    
    def test_empty_optional_fields(self):
        """Test handling of empty optional fields."""
        codec = JsonCodec.compact()
        
        event = Event(
            topic="test.topic",
            payload={"key": "value"},
            # No key, headers, tenant_id
        )
        
        encoded = codec.encode(event)
        decoded = codec.decode(encoded)
        
        assert decoded.key is None
        assert decoded.tenant_id is None
        # headers should be empty dict, not None due to __post_init__
        assert decoded.headers == {}
    
    def test_unicode_handling(self):
        """Test Unicode string handling."""
        codec = JsonCodec(ensure_ascii=False)
        
        event = Event(
            topic="test.topic",
            payload={"message": "Hello 世界! 🌍"},
            headers={"description": "Test événement"},
        )
        
        encoded = codec.encode(event)
        decoded = codec.decode(encoded)
        
        assert decoded.payload["message"] == "Hello 世界! 🌍"
        assert decoded.headers["description"] == "Test événement"