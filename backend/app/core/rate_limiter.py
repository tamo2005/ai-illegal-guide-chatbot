# backend/app/core/rate_limiter.py
import time
import asyncio
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
from ..core.logging import get_logger
from ..core.exceptions import RateLimitException

logger = get_logger(__name__)

class RateLimiter:
    def __init__(self):
        """Initialize rate limiter with multiple strategies"""
        # Request tracking by IP
        self.ip_requests: Dict[str, deque] = defaultdict(deque)
        self.ip_blocked: Dict[str, datetime] = {}
        
        # Request tracking by session
        self.session_requests: Dict[str, deque] = defaultdict(deque)
        self.session_blocked: Dict[str, datetime] = {}
        
        # Global rate limiting
        self.global_requests: deque = deque()
        
        # Configuration
        self.config = {
            'ip_limit': 60,  # requests per hour per IP
            'ip_burst_limit': 10,  # requests per minute per IP
            'session_limit': 100,  # requests per hour per session
            'session_burst_limit': 15,  # requests per minute per session
            'global_limit': 10000,  # total requests per hour
            'block_duration': 3600,  # seconds to block after violation
            'cleanup_interval': 300  # cleanup old entries every 5 minutes
        }
        
        # Start cleanup task
        self._start_cleanup_task()
        logger.info("✅ RateLimiter initialized")

    async def check_rate_limit(
        self, 
        identifier: str, 
        identifier_type: str = "ip",
        session_id: Optional[str] = None
    ) -> bool:
        """Check if request should be rate limited"""
        try:
            current_time = datetime.utcnow()
            
            # Check if identifier is currently blocked
            if identifier_type == "ip" and identifier in self.ip_blocked:
                if current_time < self.ip_blocked[identifier]:
                    raise RateLimitException(
                        f"IP {identifier} is blocked until {self.ip_blocked[identifier]}",
                        retry_after=int((self.ip_blocked[identifier] - current_time).total_seconds())
                    )
                else:
                    # Block expired, remove it
                    del self.ip_blocked[identifier]
            
            # Check session blocking if applicable
            if session_id and session_id in self.session_blocked:
                if current_time < self.session_blocked[session_id]:
                    raise RateLimitException(
                        f"Session {session_id} is blocked until {self.session_blocked[session_id]}",
                        retry_after=int((self.session_blocked[session_id] - current_time).total_seconds())
                    )
                else:
                    del self.session_blocked[session_id]
            
            # Check global rate limit
            await self._check_global_limit()
            
            # Check specific limits based on identifier type
            if identifier_type == "ip":
                await self._check_ip_limit(identifier)
            elif identifier_type == "session" and session_id:
                await self._check_session_limit(session_id)
            
            # Record the request
            await self._record_request(identifier, identifier_type, session_id)
            
            return True
            
        except RateLimitException:
            logger.warning(f"🚦 Rate limit exceeded for {identifier_type}: {identifier}")
            raise
        except Exception as e:
            logger.error(f"❌ Rate limit check failed: {str(e)}")
            # Fail open - allow request if rate limiter fails
            return True

    async def _check_global_limit(self):
        """Check global rate limit"""
        current_time = time.time()
        hour_ago = current_time - 3600
        
        # Clean old entries
        while self.global_requests and self.global_requests[0] < hour_ago:
            self.global_requests.popleft()
        
        if len(self.global_requests) >= self.config['global_limit']:
            raise RateLimitException(
                "Global rate limit exceeded",
                retry_after=3600
            )

    async def _check_ip_limit(self, ip: str):
        """Check IP-specific rate limits"""
        current_time = time.time()
        
        # Get or create request queue for this IP
        ip_queue = self.ip_requests[ip]
        
        # Check burst limit (per minute)
        minute_ago = current_time - 60
        recent_requests = sum(1 for req_time in ip_queue if req_time > minute_ago)
        
        if recent_requests >= self.config['ip_burst_limit']:
            # Block IP for burst violation
            self.ip_blocked[ip] = datetime.utcnow() + timedelta(seconds=self.config['block_duration'])
            raise RateLimitException(
                f"IP burst limit exceeded: {recent_requests} requests in last minute",
                retry_after=self.config['block_duration']
            )
        
        # Check hourly limit
        hour_ago = current_time - 3600
        hourly_requests = sum(1 for req_time in ip_queue if req_time > hour_ago)
        
        if hourly_requests >= self.config['ip_limit']:
            # Block IP for hourly violation
            self.ip_blocked[ip] = datetime.utcnow() + timedelta(seconds=self.config['block_duration'])
            raise RateLimitException(
                f"IP hourly limit exceeded: {hourly_requests} requests in last hour",
                retry_after=self.config['block_duration']
            )

    async def _check_session_limit(self, session_id: str):
        """Check session-specific rate limits"""
        current_time = time.time()
        
        # Get or create request queue for this session
        session_queue = self.session_requests[session_id]
        
        # Check burst limit (per minute)
        minute_ago = current_time - 60
        recent_requests = sum(1 for req_time in session_queue if req_time > minute_ago)
        
        if recent_requests >= self.config['session_burst_limit']:
            self.session_blocked[session_id] = datetime.utcnow() + timedelta(seconds=self.config['block_duration'])
            raise RateLimitException(
                f"Session burst limit exceeded: {recent_requests} requests in last minute",
                retry_after=self.config['block_duration']
            )
        
        # Check hourly limit
        hour_ago = current_time - 3600
        hourly_requests = sum(1 for req_time in session_queue if req_time > hour_ago)
        
        if hourly_requests >= self.config['session_limit']:
            self.session_blocked[session_id] = datetime.utcnow() + timedelta(seconds=self.config['block_duration'])
            raise RateLimitException(
                f"Session hourly limit exceeded: {hourly_requests} requests in last hour",
                retry_after=self.config['block_duration']
            )

    async def _record_request(
        self, 
        identifier: str, 
        identifier_type: str, 
        session_id: Optional[str] = None
    ):
        """Record a successful request"""
        current_time = time.time()
        
        # Record global request
        self.global_requests.append(current_time)
        
        # Record by identifier type
        if identifier_type == "ip":
            self.ip_requests[identifier].append(current_time)
            
            # Limit queue size to prevent memory bloat
            if len(self.ip_requests[identifier]) > self.config['ip_limit'] * 2:
                # Remove oldest entries beyond reasonable limit
                while len(self.ip_requests[identifier]) > self.config['ip_limit']:
                    self.ip_requests[identifier].popleft()
        
        elif identifier_type == "session" and session_id:
            self.session_requests[session_id].append(current_time)
            
            if len(self.session_requests[session_id]) > self.config['session_limit'] * 2:
                while len(self.session_requests[session_id]) > self.config['session_limit']:
                    self.session_requests[session_id].popleft()

    def get_rate_limit_status(self, identifier: str, identifier_type: str = "ip") -> Dict:
        """Get current rate limit status for an identifier"""
        try:
            current_time = time.time()
            
            if identifier_type == "ip":
                queue = self.ip_requests.get(identifier, deque())
                blocked_until = self.ip_blocked.get(identifier)
            else:
                queue = self.session_requests.get(identifier, deque())
                blocked_until = self.session_blocked.get(identifier)
            
            # Count requests in different time windows
            minute_ago = current_time - 60
            hour_ago = current_time - 3600
            
            requests_last_minute = sum(1 for req_time in queue if req_time > minute_ago)
            requests_last_hour = sum(1 for req_time in queue if req_time > hour_ago)
            
            # Calculate remaining requests
            if identifier_type == "ip":
                burst_remaining = max(0, self.config['ip_burst_limit'] - requests_last_minute)
                hourly_remaining = max(0, self.config['ip_limit'] - requests_last_hour)
            else:
                burst_remaining = max(0, self.config['session_burst_limit'] - requests_last_minute)
                hourly_remaining = max(0, self.config['session_limit'] - requests_last_hour)
            
            return {
                "identifier": identifier,
                "identifier_type": identifier_type,
                "requests_last_minute": requests_last_minute,
                "requests_last_hour": requests_last_hour,
                "burst_remaining": burst_remaining,
                "hourly_remaining": hourly_remaining,
                "is_blocked": blocked_until is not None and datetime.utcnow() < blocked_until,
                "blocked_until": blocked_until.isoformat() if blocked_until else None,
                "reset_time": datetime.utcnow() + timedelta(seconds=3600)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get rate limit status: {str(e)}")
            return {"error": "Failed to get status"}

    async def reset_rate_limit(self, identifier: str, identifier_type: str = "ip"):
        """Reset rate limits for an identifier (admin function)"""
        try:
            if identifier_type == "ip":
                if identifier in self.ip_requests:
                    del self.ip_requests[identifier]
                if identifier in self.ip_blocked:
                    del self.ip_blocked[identifier]
            else:
                if identifier in self.session_requests:
                    del self.session_requests[identifier]
                if identifier in self.session_blocked:
                    del self.session_blocked[identifier]
            
            logger.info(f"🔄 Rate limit reset for {identifier_type}: {identifier}")
            
        except Exception as e:
            logger.error(f"❌ Failed to reset rate limit: {str(e)}")
            raise

    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.config['cleanup_interval'])
                    await self._cleanup_old_entries()
                except Exception as e:
                    logger.error(f"❌ Cleanup task error: {str(e)}")
        
        # Run cleanup in background
        asyncio.create_task(cleanup_loop())

    async def _cleanup_old_entries(self):
        """Clean up old entries to prevent memory bloat"""
        try:
            current_time = time.time()
            hour_ago = current_time - 3600
            
            # Clean global requests
            while self.global_requests and self.global_requests[0] < hour_ago:
                self.global_requests.popleft()
            
            # Clean IP requests
            empty_ips = []
            for ip, queue in self.ip_requests.items():
                # Remove old requests
                while queue and queue[0] < hour_ago:
                    queue.popleft()
                
                # Mark empty queues for deletion
                if not queue:
                    empty_ips.append(ip)
            
            # Remove empty IP queues
            for ip in empty_ips:
                del self.ip_requests[ip]
            
            # Clean session requests
            empty_sessions = []
            for session_id, queue in self.session_requests.items():
                while queue and queue[0] < hour_ago:
                    queue.popleft()
                
                if not queue:
                    empty_sessions.append(session_id)
            
            for session_id in empty_sessions:
                del self.session_requests[session_id]
            
            # Clean expired blocks
            current_dt = datetime.utcnow()
            expired_ip_blocks = [ip for ip, blocked_until in self.ip_blocked.items() 
                               if current_dt >= blocked_until]
            expired_session_blocks = [sid for sid, blocked_until in self.session_blocked.items() 
                                    if current_dt >= blocked_until]
            
            for ip in expired_ip_blocks:
                del self.ip_blocked[ip]
            
            for session_id in expired_session_blocks:
                del self.session_blocked[session_id]
            
            if empty_ips or empty_sessions or expired_ip_blocks or expired_session_blocks:
                logger.info(f"🧹 Cleaned up rate limiter: {len(empty_ips)} IP queues, "
                           f"{len(empty_sessions)} session queues, "
                           f"{len(expired_ip_blocks)} IP blocks, "
                           f"{len(expired_session_blocks)} session blocks")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {str(e)}")

    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        current_time = datetime.utcnow()
        
        return {
            "active_ips": len(self.ip_requests),
            "active_sessions": len(self.session_requests),
            "blocked_ips": len(self.ip_blocked),
            "blocked_sessions": len(self.session_blocked),
            "global_requests_last_hour": len(self.global_requests),
            "config": self.config,
            "next_cleanup": "Every 5 minutes",
            "last_updated": current_time.isoformat()
        }