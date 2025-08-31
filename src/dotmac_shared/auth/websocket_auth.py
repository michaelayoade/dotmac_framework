"""
WebSocket authentication utilities.
"""

from typing import Optional, Dict, Any
from fastapi import WebSocket, status
from urllib.parse import parse_qs

from dotmac_shared.utils.logging import get_logger

logger = get_logger(__name__)


async def get_websocket_user_context(websocket: WebSocket) -> Optional[Dict[str, Any]]:
    """
    Extract user context from WebSocket connection.
    
    This is a simplified implementation. In production, you would:
    1. Extract JWT token from query params or headers
    2. Validate the token
    3. Return user_id and tenant_id
    """
    try:
        # Extract query parameters
        query_params = parse_qs(websocket.url.query)
        
        # Look for token in query params
        token = None
        if 'token' in query_params:
            token = query_params['token'][0]
        
        # Extract user_id and tenant_id (simplified - would validate JWT in production)
        user_id = query_params.get('user_id', [None])[0]
        tenant_id = query_params.get('tenant_id', [None])[0]
        
        if not user_id or not tenant_id:
            logger.warning("WebSocket connection missing user_id or tenant_id")
            return None
        
        # In production, validate JWT token here
        # For now, just return the provided IDs
        return {
            'user_id': user_id,
            'tenant_id': tenant_id,
            'token': token
        }
        
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {str(e)}")
        return None


def extract_websocket_token(websocket: WebSocket) -> Optional[str]:
    """Extract authentication token from WebSocket headers or query params."""
    try:
        # Try to get from query parameters first
        query_params = parse_qs(websocket.url.query)
        if 'token' in query_params:
            return query_params['token'][0]
        
        # Try to get from headers (if available)
        headers = dict(websocket.headers)
        auth_header = headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to extract WebSocket token: {str(e)}")
        return None


async def authenticate_websocket_connection(websocket: WebSocket, 
                                          required_permissions: Optional[list] = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate WebSocket connection and return user context.
    
    Args:
        websocket: WebSocket connection
        required_permissions: Optional list of required permissions
        
    Returns:
        User context dict if authenticated, None otherwise
    """
    context = await get_websocket_user_context(websocket)
    
    if not context:
        return None
    
    # In production, you would:
    # 1. Validate JWT token
    # 2. Check user permissions
    # 3. Verify tenant access
    # 4. Check if user is active/enabled
    
    # For now, just return the context
    return context