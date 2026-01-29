"""IP whitelist middleware for FastAPI."""

import os
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..utils.logger import get_logger

logger = get_logger()


class IPFilterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to filter requests by IP address.
    
    Configure via IP_WHITELIST environment variable:
    - Empty or not set: allow all IPs
    - Comma-separated list: only allow listed IPs
    
    Example: IP_WHITELIST=192.168.1.100,10.0.0.1
    """
    
    def __init__(self, app):
        super().__init__(app)
        whitelist = os.getenv("IP_WHITELIST", "")
        self.allowed_ips = set(ip.strip() for ip in whitelist.split(",") if ip.strip())
        
        if self.allowed_ips:
            logger.info(f"IP whitelist enabled: {len(self.allowed_ips)} IPs allowed")
        else:
            logger.info("IP whitelist disabled: all IPs allowed")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # If whitelist is empty, allow all
        if not self.allowed_ips:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else None
        
        # Check X-Forwarded-For header for reverse proxy support
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain (original client)
            client_ip = forwarded.split(",")[0].strip()
        
        # Also check X-Real-IP header (nginx)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip.strip()
        
        # Check if IP is allowed
        if client_ip not in self.allowed_ips:
            logger.warning(f"Access denied for IP: {client_ip}")
            raise HTTPException(status_code=403, detail="Access denied")
        
        return await call_next(request)
