"""Input sanitization utilities."""

import re
import html
from typing import Any, Dict, List, Union
from urllib.parse import quote

from dotmac_isp.core.exceptions import SecurityViolationError


class InputSanitizer:
    """Input sanitizer for preventing injection attacks."""
    
    def __init__(self):
        """  Init   operation."""
        # SQL injection patterns
        self.sql_patterns = [
            r"(\bor\b\s+\d+\s*=\s*\d+)",  # OR 1=1
            r"(\bunion\b\s+\bselect\b)",   # UNION SELECT
            r"(\bdrop\b\s+\btable\b)",     # DROP TABLE
            r"(\bdelete\b\s+\bfrom\b)",    # DELETE FROM
            r"(\binsert\b\s+\binto\b)",    # INSERT INTO
            r"(\bupdate\b\s+\w+\s+\bset\b)",  # UPDATE SET
            r"(\bexec\b\s*\()",            # EXEC()
            r"(\bsp_\w+)",                 # Stored procedures
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<\s*script\b[^<]*(?:(?!<\s*\/\s*script\s*>)<[^<]*)*<\s*\/\s*script\s*>",
            r"javascript\s*:",
            r"on\w+\s*=",
            r"<\s*iframe\b",
            r"<\s*object\b",
            r"<\s*embed\b",
            r"<\s*link\b",
            r"<\s*meta\b",
        ]
    
    def sanitize_string(self, value: str, allow_html: bool = False) -> str:
        """Sanitize string input."""
        if not isinstance(value, str):
            return str(value)
        
        # Check for SQL injection
        if self._contains_sql_injection(value):
            raise SecurityViolationError("Potential SQL injection detected")
        
        # Check for XSS
        if self._contains_xss(value):
            raise SecurityViolationError("Potential XSS attack detected")
        
        # HTML escape if not allowing HTML
        if not allow_html:
            value = html.escape(value)
        
        return value.strip()
    
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values."""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = self.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = self.sanitize_list(value)
            else:
                sanitized[key] = value
        return sanitized
    
    def sanitize_list(self, data: List[Any]) -> List[Any]:
        """Sanitize list values."""
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(self.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(self.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(self.sanitize_list(item))
            else:
                sanitized.append(item)
        return sanitized
    
    def _contains_sql_injection(self, value: str) -> bool:
        """Check for SQL injection patterns."""
        value_lower = value.lower()
        for pattern in self.sql_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        return False
    
    def _contains_xss(self, value: str) -> bool:
        """Check for XSS patterns."""
        value_lower = value.lower()
        for pattern in self.xss_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        return False
    
    def url_encode(self, value: str) -> str:
        """URL encode string."""
        return quote(value)
    
    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format."""
        # Remove common separators
        clean_phone = re.sub(r'[^\d+]', '', phone)
        # Check if it's a reasonable phone number
        return len(clean_phone) >= 10 and len(clean_phone) <= 15