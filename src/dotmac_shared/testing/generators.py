"""
Data Generation Utilities for Test Factories

Provides realistic and consistent test data generation with support for:
- Fake data generation using provider patterns
- Sequence generation for unique values
- ISP-specific data patterns (IP addresses, MAC addresses, etc.)
- Multi-tenant aware data generation
- Localized data support
"""

import random
import secrets
import string
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
from uuid import UUID, uuid4

from dotmac_shared.utils.datetime_utils import utc_now

# Try to import faker if available, fallback to basic generation
try:
    from faker import Faker
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False


class DataType(Enum):
    """Supported data types for generation."""
    STRING = "string"
    EMAIL = "email"
    PHONE = "phone"
    NAME = "name"
    ADDRESS = "address"
    COMPANY = "company"
    URL = "url"
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    UUID = "uuid"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"


@dataclass
class GenerationConfig:
    """Configuration for data generation."""
    locale: str = "en_US"
    seed: Optional[int] = None
    unique: bool = False
    sequence_start: int = 1
    custom_providers: Dict[str, Callable] = field(default_factory=dict)


class DataProvider(ABC):
    """Abstract base class for data providers."""
    
    @abstractmethod
    def generate(self, data_type: DataType, **kwargs) -> Any:
        """Generate data of specified type."""
        pass
        
    @abstractmethod
    def supports(self, data_type: DataType) -> bool:
        """Check if provider supports data type."""
        pass


class FakeDataProvider(DataProvider):
    """Faker-based data provider for realistic test data."""
    
    def __init__(self, config: GenerationConfig):
        """Initialize with generation config."""
        self.config = config
        
        if HAS_FAKER:
            self.faker = Faker(config.locale)
            if config.seed:
                self.faker.seed_instance(config.seed)
        else:
            self.faker = None
            
        self._unique_values: Dict[str, Set] = {}
        
    def supports(self, data_type: DataType) -> bool:
        """Check if data type is supported."""
        if not HAS_FAKER:
            return data_type in {DataType.STRING, DataType.UUID, DataType.INTEGER, DataType.BOOLEAN}
        return True
        
    def generate(self, data_type: DataType, **kwargs) -> Any:
        """Generate fake data of specified type."""
        if not self.supports(data_type):
            raise ValueError(f"Data type {data_type} not supported")
            
        # Check for custom provider
        if data_type.value in self.config.custom_providers:
            return self.config.custom_providers[data_type.value](**kwargs)
            
        # Use faker if available
        if HAS_FAKER and self.faker:
            return self._generate_with_faker(data_type, **kwargs)
        else:
            return self._generate_basic(data_type, **kwargs)
            
    def _generate_with_faker(self, data_type: DataType, **kwargs) -> Any:
        """Generate using Faker library."""
        generators = {
            DataType.STRING: lambda: self.faker.text(max_nb_chars=kwargs.get('max_length', 100)),
            DataType.EMAIL: lambda: self.faker.email(),
            DataType.PHONE: lambda: self.faker.phone_number(),
            DataType.NAME: lambda: self.faker.name(),
            DataType.ADDRESS: lambda: self.faker.address(),
            DataType.COMPANY: lambda: self.faker.company(),
            DataType.URL: lambda: self.faker.url(),
            DataType.IP_ADDRESS: lambda: self.faker.ipv4(),
            DataType.MAC_ADDRESS: lambda: self.faker.mac_address(),
            DataType.UUID: lambda: str(self.faker.uuid4()),
            DataType.INTEGER: lambda: self.faker.random_int(
                min=kwargs.get('min', 1), 
                max=kwargs.get('max', 1000)
            ),
            DataType.DECIMAL: lambda: Decimal(str(self.faker.pydecimal(
                left_digits=kwargs.get('left_digits', 5),
                right_digits=kwargs.get('right_digits', 2),
                positive=kwargs.get('positive', True)
            ))),
            DataType.BOOLEAN: lambda: self.faker.boolean(),
            DataType.DATE: lambda: self.faker.date_between(
                start_date=kwargs.get('start_date', '-1y'),
                end_date=kwargs.get('end_date', 'today')
            ),
            DataType.DATETIME: lambda: self.faker.date_time_between(
                start_date=kwargs.get('start_date', '-1y'),
                end_date=kwargs.get('end_date', 'now')
            ),
            DataType.JSON: lambda: {
                "key1": self.faker.word(),
                "key2": self.faker.random_int(),
                "key3": self.faker.boolean()
            }
        }
        
        generator = generators.get(data_type)
        if not generator:
            raise ValueError(f"No generator for {data_type}")
            
        value = generator()
        
        # Handle uniqueness
        if self.config.unique:
            value = self._ensure_unique(data_type.value, value, lambda: generator())
            
        return value
        
    def _generate_basic(self, data_type: DataType, **kwargs) -> Any:
        """Generate using basic Python without Faker.""" 
        generators = {
            DataType.STRING: lambda: ''.join(
                random.choices(
                    string.ascii_letters + string.digits, 
                    k=kwargs.get('length', 10)
                )
            ),
            DataType.UUID: lambda: str(uuid4()),
            DataType.INTEGER: lambda: random.randint(
                kwargs.get('min', 1), 
                kwargs.get('max', 1000)
            ),
            DataType.BOOLEAN: lambda: random.choice([True, False]),
            DataType.EMAIL: lambda: f"user{random.randint(1000, 9999)}@example.com",
            DataType.DATETIME: lambda: utc_now() - timedelta(
                days=random.randint(0, 365)
            )
        }
        
        generator = generators.get(data_type)
        if not generator:
            raise ValueError(f"No basic generator for {data_type}")
            
        return generator()
        
    def _ensure_unique(self, key: str, value: Any, regenerator: Callable) -> Any:
        """Ensure generated value is unique."""
        if key not in self._unique_values:
            self._unique_values[key] = set()
            
        unique_set = self._unique_values[key]
        
        # Try to regenerate if not unique (max 100 attempts)
        attempts = 0
        while value in unique_set and attempts < 100:
            value = regenerator()
            attempts += 1
            
        if attempts >= 100:
            # Add a random suffix to ensure uniqueness
            value = f"{value}_{secrets.token_hex(4)}"
            
        unique_set.add(value)
        return value


class ISPDataProvider(DataProvider):
    """Provider for ISP-specific data patterns."""
    
    def __init__(self, config: GenerationConfig):
        """Initialize ISP data provider."""
        self.config = config
        
    def supports(self, data_type: DataType) -> bool:
        """Check supported ISP data types."""
        return data_type in {
            DataType.IP_ADDRESS, 
            DataType.MAC_ADDRESS,
            DataType.STRING  # For ISP-specific strings
        }
        
    def generate(self, data_type: DataType, **kwargs) -> Any:
        """Generate ISP-specific data."""
        if data_type == DataType.IP_ADDRESS:
            return self._generate_ip_address(**kwargs)
        elif data_type == DataType.MAC_ADDRESS:
            return self._generate_mac_address(**kwargs)
        elif data_type == DataType.STRING:
            pattern = kwargs.get('pattern')
            if pattern == 'service_id':
                return self._generate_service_id()
            elif pattern == 'customer_number':
                return self._generate_customer_number()
        
        raise ValueError(f"Unsupported ISP data type: {data_type}")
        
    def _generate_ip_address(self, **kwargs) -> str:
        """Generate realistic IP addresses."""
        ip_type = kwargs.get('type', 'private')
        
        if ip_type == 'private':
            # Generate private IP ranges
            ranges = [
                (10, random.randint(0, 255), random.randint(0, 255), random.randint(1, 254)),
                (172, random.randint(16, 31), random.randint(0, 255), random.randint(1, 254)),
                (192, 168, random.randint(0, 255), random.randint(1, 254))
            ]
            return '.'.join(map(str, random.choice(ranges)))
        elif ip_type == 'public':
            # Avoid private and reserved ranges
            while True:
                octets = [random.randint(1, 223) for _ in range(4)]
                ip = '.'.join(map(str, octets))
                if not self._is_reserved_ip(ip):
                    return ip
        else:
            # Random IP
            return '.'.join(str(random.randint(1, 254)) for _ in range(4))
            
    def _generate_mac_address(self, **kwargs) -> str:
        """Generate MAC addresses."""
        vendor = kwargs.get('vendor')
        
        if vendor:
            # Use known vendor prefixes
            vendor_prefixes = {
                'cisco': '00:1B:D4',
                'mikrotik': '4C:5E:0C', 
                'ubiquiti': '44:D9:E7'
            }
            prefix = vendor_prefixes.get(vendor.lower(), '00:00:00')
            suffix = ':'.join([f"{random.randint(0, 255):02X}" for _ in range(3)])
            return f"{prefix}:{suffix}"
        else:
            # Random MAC
            return ':'.join([f"{random.randint(0, 255):02X}" for _ in range(6)])
            
    def _generate_service_id(self) -> str:
        """Generate service ID in ISP format."""
        return f"SRV-{random.randint(100000, 999999)}"
        
    def _generate_customer_number(self) -> str:
        """Generate customer number in ISP format."""
        return f"CUST-{random.randint(10000, 99999)}"
        
    def _is_reserved_ip(self, ip: str) -> bool:
        """Check if IP is in reserved range."""
        octets = list(map(int, ip.split('.')))
        first = octets[0]
        
        # Check common reserved ranges
        if first in [10, 127, 169, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239]:
            return True
        if first == 172 and 16 <= octets[1] <= 31:
            return True
        if first == 192 and octets[1] == 168:
            return True
            
        return False


class SequenceGenerator:
    """Generates sequential values for unique identifiers."""
    
    def __init__(self, start: int = 1):
        """Initialize sequence generator."""
        self.sequences: Dict[str, int] = {}
        self.start = start
        
    def next(self, name: str) -> int:
        """Get next value in sequence."""
        if name not in self.sequences:
            self.sequences[name] = self.start
        else:
            self.sequences[name] += 1
        return self.sequences[name]
        
    def reset(self, name: str) -> None:
        """Reset sequence to start value."""
        self.sequences[name] = self.start
        
    def reset_all(self) -> None:
        """Reset all sequences."""
        self.sequences.clear()


class DataGenerator:
    """
    Main data generator orchestrating multiple providers.
    
    Provides a unified interface for generating test data using
    multiple providers and generation strategies.
    """
    
    def __init__(self, config: Optional[GenerationConfig] = None):
        """Initialize data generator with providers."""
        self.config = config or GenerationConfig()
        self.providers: List[DataProvider] = [
            FakeDataProvider(self.config),
            ISPDataProvider(self.config)
        ]
        self.sequence_generator = SequenceGenerator(self.config.sequence_start)
        
    def generate(self, data_type: DataType, **kwargs) -> Any:
        """Generate data using first supporting provider."""
        for provider in self.providers:
            if provider.supports(data_type):
                return provider.generate(data_type, **kwargs)
                
        raise ValueError(f"No provider supports data type: {data_type}")
        
    def generate_dict(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dictionary from schema definition."""
        result = {}
        
        for key, spec in schema.items():
            if isinstance(spec, dict):
                data_type = DataType(spec['type'])
                kwargs = spec.get('kwargs', {})
                result[key] = self.generate(data_type, **kwargs)
            elif isinstance(spec, DataType):
                result[key] = self.generate(spec)
            else:
                result[key] = spec  # Use literal value
                
        return result
        
    def add_provider(self, provider: DataProvider) -> None:
        """Add custom data provider."""
        self.providers.insert(0, provider)  # Insert at beginning for priority
        
    def next_sequence(self, name: str) -> int:
        """Get next sequence value."""
        return self.sequence_generator.next(name)


# Global instances for convenience
_global_config = GenerationConfig()
_global_generator = DataGenerator(_global_config)


def generate_fake_data(data_type: DataType, **kwargs) -> Any:
    """Generate fake data using global generator."""
    return _global_generator.generate(data_type, **kwargs)


def generate_sequence(name: str) -> int:
    """Generate next sequence value using global generator."""
    return _global_generator.next_sequence(name)