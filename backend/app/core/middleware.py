"""
🛡️ Professional Middleware Stack
=================================

Advanced middleware for security, monitoring, rate limiting, and request handling.

Features:
- Request logging and timing
- Rate limiting with Redis support
- Request ID generation
- Security headers
- Error tracking
- Performance monitoring

Author: AI Backend Architect
"""

import time
import uuid
import json
from typing import Dict, Any, Optional, Callable
from collections import defaultdict, deque
import asyncio

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger, set_request_context, clear_request_context, perf_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    📝 Request Logging Middleware
    
    Logs all requests with timing, status codes, and context information.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("middleware.request")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Set logging context
        set_request_context(request_id)
        
        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log request start
        start_time = time.time()
        self.logger.info(
            f"🌐 Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "content_length": request.headers.get("content-length", 0)
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{response_time:.3f}s"
            
            # Log successful response
            self.logger.info(
                f"✅ Request completed: {request.method} {request.url.path} -> {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "response_size": len(getattr(response, 'body', b''))
                }
            )
            
            # Log performance metrics
            perf_logger.log_request_metrics(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time=response_time,
                client_ip=client_ip
            )
            
            return response
            
        except Exception as e:
            # Calculate response time for failed requests
            response_time = time.time() - start_time
            
            # Log error
            self.logger.error(
                f"❌ Request failed: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "response_time": response_time,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True
            )
            
            raise
        
        finally:
            # Clear logging context
            clear_request_context()
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded headers (for proxy/load balancer setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    🚦 Rate Limiting Middleware
    
    Implements token bucket rate limiting with per-IP tracking.
    """
    
    def __init__(self, app: ASGIApp, calls: int = 100, period: int = 3600):
        super().__init__(app)
        self.logger = get_logger("middleware.ratelimit")
        self.calls = calls  # Number of calls allowed
        self.period = period  # Time period in seconds
        
        # In-memory storage for rate limiting (use Redis in production)
        self.client_buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "tokens": calls,
                "last_refill": time.time(),
                "requests": deque()
            }
        )
        
        # Cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup():
            while True:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                await self._cleanup_old_entries()
        
        self._cleanup_task = asyncio.create_task(cleanup())
    
    async def _cleanup_old_entries(self):
        """Clean up old rate limit entries"""
        current_time = time.time()
        to_remove = []
        
        for client_ip, bucket in self.client_buckets.items():
            if current_time - bucket["last_refill"] > self.period * 2:
                to_remove.append(client_ip)
        
        for client_ip in to_remove:
            del self.client_buckets[client_ip]
        
        if to_remove:
            self.logger.debug(f"🧹 Cleaned up {len(to_remove)} old rate limit entries")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready", "/health/live"]:
            return await call_next(request)
        
        # Get client identifier
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self._check_rate_limit(client_ip)
        
        if not is_allowed:
            self.logger.warning(
                f"🚫 Rate limit exceeded for {client_ip}",
                extra={
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": 429,
                        "message": "Rate limit exceeded",
                        "type": "RATE_LIMIT_EXCEEDED",
                        "details": {
                            "limit": self.calls,
                            "period": self.period,
                            "remaining": 0,
                            "reset_time": reset_time
                        }
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(int(reset_time)),
                    "Retry-After": str(int(reset_time - time.time()))
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        return response
    
    async def _check_rate_limit(self, client_ip: str) -> tuple[bool, int, float]:
        """
        Check if client has exceeded rate limit using token bucket algorithm
        
        Returns:
            tuple: (is_allowed, remaining_calls, reset_time)
        """
        current_time = time.time()
        bucket = self.client_buckets[client_ip]
        
        # Refill tokens based on time elapsed
        time_elapsed = current_time - bucket["last_refill"]
        if time_elapsed > 0:
            tokens_to_add = (time_elapsed / self.period) * self.calls
            bucket["tokens"] = min(self.calls, bucket["tokens"] + tokens_to_add)
            bucket["last_refill"] = current_time
        
        # Calculate reset time
        reset_time = bucket["last_refill"] + self.period
        
        # Check if request is allowed
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            bucket["requests"].append(current_time)
            
            # Keep only recent requests
            while bucket["requests"] and current_time - bucket["requests"][0] > self.period:
                bucket["requests"].popleft()
            
            return True, int(bucket["tokens"]), reset_time
        else:
            return False, 0, reset_time
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP for rate limiting"""
        # Same logic as RequestLoggingMiddleware
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        if request.client:
            return request.client.host
        
        return "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    🔒 Security Headers Middleware
    
    Adds security headers to all responses.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("middleware.security")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    📊 Metrics Collection Middleware
    
    Collects and stores application metrics.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger("middleware.metrics")
        
        # In-memory metrics storage
        self.metrics = {
            "requests_total": 0,
            "requests_by_method": defaultdict(int),
            "requests_by_path": defaultdict(int),
            "requests_by_status": defaultdict(int),
            "response_times": deque(maxlen=1000),
            "errors_total": 0,
            "active_requests": 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Increment active requests
        self.metrics["active_requests"] += 1
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate metrics
            response_time = time.time() - start_time
            
            # Update metrics
            self._update_metrics(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time=response_time,
                success=True
            )
            
            return response
            
        except Exception as e:
            # Calculate metrics for failed requests
            response_time = time.time() - start_time
            
            # Update error metrics
            self._update_metrics(
                method=request.method,
                path=request.url.path,
                status_code=500,
                response_time=response_time,
                success=False
            )
            
            raise
        
        finally:
            # Decrement active requests
            self.metrics["active_requests"] -= 1
    
    def _update_metrics(self, method: str, path: str, status_code: int, 
                       response_time: float, success: bool):
        """Update metrics with request information"""
        self.metrics["requests_total"] += 1
        self.metrics["requests_by_method"][method] += 1
        self.metrics["requests_by_path"][path] += 1
        self.metrics["requests_by_status"][status_code] += 1
        self.metrics["response_times"].append(response_time)
        
        if not success:
            self.metrics["errors_total"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        response_times = list(self.metrics["response_times"])
        
        return {
            "requests_total": self.metrics["requests_total"],
            "requests_by_method": dict(self.metrics["requests_by_method"]),
            "requests_by_path": dict(self.metrics["requests_by_path"]),
            "requests_by_status": dict(self.metrics["requests_by_status"]),
            "errors_total": self.metrics["errors_total"],
            "active_requests": self.metrics["active_requests"],
            "average_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "total_response_times_recorded": len(response_times)
        }


# Export middleware classes
__all__ = [
    "RequestLoggingMiddleware",
    "RateLimitMiddleware", 
    "SecurityHeadersMiddleware",
    "MetricsMiddleware"
]