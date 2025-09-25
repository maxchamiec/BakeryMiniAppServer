"""
Security Headers Middleware for AioHTTP
Adds comprehensive security headers to all HTTP responses.
"""

import hashlib
import logging
from typing import Callable, Awaitable
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response

logger = logging.getLogger(__name__)

@web.middleware
async def security_headers_middleware(request: Request, handler: Callable[[Request], Awaitable[Response]]) -> Response:
    """Add security headers to all responses."""
    
    # Content Security Policy - allows Telegram WebApp functionality, Google Fonts, and Swiper CDN
    csp_policy = (
        "default-src 'self' https://telegram.org; "
        "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://telegram.org https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://telegram.org https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' data: https://telegram.org https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https: http:; "
        "connect-src 'self' https://telegram.org https://cdn.jsdelivr.net; "
        "frame-src 'self' https://*.telegram.org https://web.telegram.org https://t.me; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests"
    )
    
    # Permissions Policy - restrict sensitive APIs (removed unrecognized features)
    permissions_policy = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "gyroscope=(), "
        "accelerometer=(), "
        "autoplay=(), "
        "encrypted-media=(), "
        "picture-in-picture=()"
    )
    
    try:
        response = await handler(request)
    except Exception as e:
        # If handler fails, create a basic error response with security headers
        response = web.Response(status=500, text="Internal Server Error")
    
    # Security headers
    response.headers.update({
        # Prevent clickjacking
        #'X-Frame-Options': 'DENY',
        
        # Prevent MIME type sniffing
        'X-Content-Type-Options': 'nosniff',
        
        # Referrer policy
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        
        # Content Security Policy
        'Content-Security-Policy': csp_policy,
        
        # Permissions Policy
        'Permissions-Policy': permissions_policy,
        
        # XSS Protection (legacy but still useful)
        'X-XSS-Protection': '1; mode=block',
        
        # Prevent caching of sensitive data
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })
    
    # Add HSTS header only for HTTPS requests
    if request.scheme == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    return response

def create_content_hash(content: bytes) -> str:
    """Create a stable content hash for ETag generation."""
    return hashlib.sha256(content).hexdigest()

# No global instance needed - use the function directly
