"""
DRY common validation utilities to reduce Pydantic validator duplication.
Provides reusable validation functions across the platform.
"""

import re
from typing import List, Optional, Union
from pydantic import field_validator, model_validator
from pydantic_core import ValidationError


class ValidationPatterns:
    """Common regex patterns for validation"""
    
    SUBDOMAIN = re.compile(r'^[a-z0-9-]+$')
    EMAIL_DOMAIN = re.compile(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    PHONE_BASIC = re.compile(r'^\+?[\d\s\-\(\)]{10,}$')
    ALPHANUMERIC = re.compile(r'^[a-zA-Z0-9\s]+$')
    SLUG = re.compile(r'^[a-z0-9-_]+$')


class CommonValidators:
    """
    DRY validation utilities to reduce duplication across Pydantic models.
    Use these as static methods or in custom validators.
    """
    
    @staticmethod
    def validate_required_string(value: str, field_name: str, min_length: int = 2, max_length: int = 100) -> str:
        """
        Standard string validation with length requirements.
        
        Args:
            value: String to validate
            field_name: Name of field for error messages
            min_length: Minimum string length (default: 2)
            max_length: Maximum string length (default: 100)
            
        Returns:
            Stripped and validated string
            
        Raises:
            ValueError: If validation fails
        """
        if not value or not value.strip():
            raise ValueError(f'{field_name} is required')
        
        clean_value = value.strip()
        
        if len(clean_value) < min_length:
            raise ValueError(f'{field_name} must be at least {min_length} characters')
            
        if len(clean_value) > max_length:
            raise ValueError(f'{field_name} must be less than {max_length} characters')
        
        return clean_value
    
    @staticmethod
    def validate_subdomain(value: str) -> str:
        """
        Standard subdomain validation for tenant provisioning.
        
        Args:
            value: Subdomain to validate
            
        Returns:
            Clean subdomain string
            
        Raises:
            ValueError: If validation fails
        """
        if not value:
            raise ValueError('Subdomain is required')
        
        # Clean and normalize
        subdomain = value.lower().strip()
        
        # Format validation
        if not ValidationPatterns.SUBDOMAIN.match(subdomain):
            raise ValueError('Subdomain can only contain lowercase letters, numbers, and hyphens')
        
        # Length limits
        if len(subdomain) < 3:
            raise ValueError('Subdomain must be at least 3 characters')
        if len(subdomain) > 30:
            raise ValueError('Subdomain must be less than 30 characters')
        
        # Cannot start or end with hyphen
        if subdomain.startswith('-') or subdomain.endswith('-'):
            raise ValueError('Subdomain cannot start or end with a hyphen')
        
        # Reserved subdomains (common across platform)
        reserved = [
            'api', 'www', 'admin', 'app', 'mail', 'ftp', 'blog', 'shop', 
            'test', 'staging', 'dev', 'demo', 'support', 'help', 'docs',
            'status', 'billing', 'payments', 'secure', 'login', 'auth',
            'cdn', 'assets', 'static', 'media', 'uploads', 'downloads'
        ]
        
        if subdomain in reserved:
            raise ValueError(f'Subdomain "{subdomain}" is reserved')
        
        return subdomain
    
    @staticmethod
    def validate_company_name(value: str) -> str:
        """Standard company name validation"""
        return CommonValidators.validate_required_string(value, "Company name", 2, 100)
    
    @staticmethod
    def validate_user_name(value: str) -> str:
        """Standard user name validation"""  
        return CommonValidators.validate_required_string(value, "Name", 2, 80)
    
    @staticmethod
    def validate_description(value: Optional[str], max_length: int = 500) -> Optional[str]:
        """Optional description validation"""
        if not value:
            return None
        
        clean_value = value.strip()
        if len(clean_value) > max_length:
            raise ValueError(f'Description must be less than {max_length} characters')
        
        return clean_value if clean_value else None
    
    @staticmethod
    def validate_region(value: str, allowed_regions: List[str] = None) -> str:
        """Standard region validation"""
        if allowed_regions is None:
            allowed_regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
        
        if value not in allowed_regions:
            raise ValueError(f'Region must be one of: {allowed_regions}')
        
        return value
    
    @staticmethod
    def validate_phone(value: Optional[str]) -> Optional[str]:
        """Basic phone number validation"""
        if not value:
            return None
        
        clean_phone = value.strip()
        if not ValidationPatterns.PHONE_BASIC.match(clean_phone):
            raise ValueError('Invalid phone number format')
        
        return clean_phone
    
    @staticmethod
    def validate_acceptance(value: bool, field_name: str) -> bool:
        """Validate acceptance checkboxes (terms, privacy, etc.)"""
        if not value:
            raise ValueError(f'You must accept {field_name.replace("_", " ")}')
        return value
    
    @staticmethod
    def validate_slug(value: str, field_name: str = "slug") -> str:
        """Validate URL-safe slug format"""
        if not value:
            raise ValueError(f'{field_name} is required')
        
        clean_slug = value.lower().strip()
        
        if not ValidationPatterns.SLUG.match(clean_slug):
            raise ValueError(f'{field_name} can only contain lowercase letters, numbers, hyphens, and underscores')
        
        if len(clean_slug) < 2:
            raise ValueError(f'{field_name} must be at least 2 characters')
        if len(clean_slug) > 50:
            raise ValueError(f'{field_name} must be less than 50 characters')
        
        return clean_slug


# Pydantic v2 field validators for easy reuse
class ValidatorMixins:
    """Mixin class providing common Pydantic v2 validators"""
    
    @field_validator('company_name')
    @classmethod
    def validate_company_name_field(cls, v):
        return CommonValidators.validate_company_name(v)
    
    @field_validator('subdomain')
    @classmethod
    def validate_subdomain_field(cls, v):
        return CommonValidators.validate_subdomain(v)
    
    @field_validator('admin_name', 'name')
    @classmethod
    def validate_name_field(cls, v):
        return CommonValidators.validate_user_name(v)
    
    @field_validator('region')
    @classmethod
    def validate_region_field(cls, v):
        return CommonValidators.validate_region(v)
    
    @field_validator('accept_terms', 'accept_privacy')
    @classmethod
    def validate_acceptance_field(cls, v, info):
        field_name = info.field_name
        return CommonValidators.validate_acceptance(v, field_name)
    
    @field_validator('description')
    @classmethod
    def validate_description_field(cls, v):
        return CommonValidators.validate_description(v)
    
    @field_validator('phone')
    @classmethod
    def validate_phone_field(cls, v):
        return CommonValidators.validate_phone(v)


# Helper functions for custom validators
def create_company_name_validator():
    """Create a Pydantic v2 company name validator"""
    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v):
        return CommonValidators.validate_company_name(v)
    return validate_company_name


def create_subdomain_validator():
    """Create a Pydantic v2 subdomain validator"""
    @field_validator('subdomain')
    @classmethod
    def validate_subdomain(cls, v):
        return CommonValidators.validate_subdomain(v)
    return validate_subdomain


def create_region_validator(allowed_regions: List[str] = None):
    """Create a Pydantic v2 region validator"""
    @field_validator('region')
    @classmethod
    def validate_region(cls, v):
        return CommonValidators.validate_region(v, allowed_regions)
    return validate_region


# Export for easy importing
__all__ = [
    "CommonValidators",
    "ValidationPatterns", 
    "ValidatorMixins",
    "create_company_name_validator",
    "create_subdomain_validator",
    "create_region_validator"
]