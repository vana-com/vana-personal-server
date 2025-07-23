"""
Rate limiting utilities using Upstash Redis.

Provides rate limiting functionality for API endpoints with support for
IP-based and signature-based rate limiting.
"""

import logging
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from fastapi import Request, HTTPException
from upstash_ratelimit import Ratelimit, FixedWindow, SlidingWindow
from upstash_redis import Redis

from settings import get_settings
from domain.exceptions import VanaAPIError

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests: int
    window: str  # e.g., "1m", "1h", "1d"


class RateLimitError(VanaAPIError):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        message = "Rate limit exceeded"
        if retry_after:
            message += f". Try again in {retry_after} seconds"
        super().__init__(message, "RATE_LIMIT_ERROR", 429)
        self.retry_after = retry_after


class RateLimiter:
    """Rate limiter using Upstash Redis."""

    def __init__(self):
        self.settings = get_settings()
        self.enabled = self._is_enabled()
        self.limiters = {}

        logger.debug(f"Rate limiting enabled: {self.enabled}")
        logger.debug(f"Upstash URL configured: {bool(self.settings.upstash_redis_rest_url)}")
        logger.debug(f"Upstash token configured: {bool(self.settings.upstash_redis_rest_token)}")

        if self.enabled:
            try:
                # Initialize Upstash Redis client
                self.redis_client = Redis(
                    url=self.settings.upstash_redis_rest_url,
                    token=self.settings.upstash_redis_rest_token
                )

                # Create rate limiters for different endpoints
                self.limiters = {
                    "default": Ratelimit(
                        redis=self.redis_client,
                        limiter=FixedWindow(max_requests=self.settings.rate_limit_default_rpm, window=60),
                    ),
                    "operations": Ratelimit(
                        redis=self.redis_client,
                        limiter=FixedWindow(max_requests=self.settings.rate_limit_operations_per_hour, window=3600),
                    ),
                    "identity": Ratelimit(
                        redis=self.redis_client,
                        limiter=FixedWindow(max_requests=self.settings.rate_limit_identity_rpm, window=60),
                    )
                }

                logger.info("Rate limiting initialized successfully")
                logger.debug(f"Rate limiters created: {list(self.limiters.keys())}")
                logger.debug(f"Default RPM: {self.settings.rate_limit_default_rpm}")
                logger.debug(f"Operations per hour: {self.settings.rate_limit_operations_per_hour}")
                logger.debug(f"Identity RPM: {self.settings.rate_limit_identity_rpm}")

            except Exception as e:
                logger.error(f"Failed to initialize rate limiting: {str(e)}")
                logger.exception("Full traceback:")
                self.enabled = False
                self.limiters = {}

    def _is_enabled(self) -> bool:
        """Check if rate limiting is enabled and properly configured."""
        return (
                self.settings.rate_limit_enabled
                and self.settings.upstash_redis_rest_url is not None
                and self.settings.upstash_redis_rest_token is not None
        )

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        # Check for X-Forwarded-For header (common in proxied environments)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Check for X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted."""
        return ip in self.settings.rate_limit_whitelist_ips

    def check_rate_limit(
            self,
            request: Request,
            limiter_name: str = "default",
            identifier: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check rate limit for a request.

        Args:
            request: The FastAPI request object
            limiter_name: Name of the limiter to use
            identifier: Optional custom identifier (e.g., signature)

        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        logger.debug(f"Checking rate limit for limiter: {limiter_name}")

        if not self.enabled:
            logger.debug("Rate limiting is disabled")
            return True, None

        # Get client IP
        client_ip = self._get_client_ip(request)
        logger.debug(f"Client IP: {client_ip}")

        # Check whitelist
        if self._is_whitelisted(client_ip):
            logger.debug(f"IP {client_ip} is whitelisted, skipping rate limit")
            return True, None

        # Build identifier
        identifiers = []

        if self.settings.rate_limit_use_ip:
            identifiers.append(f"ip:{client_ip}")

        if self.settings.rate_limit_use_signature and identifier:
            identifiers.append(f"sig:{identifier}")

        logger.debug(f"Identifiers: {identifiers}")

        if not identifiers:
            # No identifiers configured, allow request
            logger.debug("No identifiers configured, allowing request")
            return True, None

        # Check rate limit for each identifier
        limiter = self.limiters.get(limiter_name, self.limiters["default"])
        logger.debug(f"Using limiter: {limiter_name}")

        for ident in identifiers:
            try:
                logger.debug(f"Checking rate limit for identifier: {ident}")
                result = limiter.limit(ident)
                logger.debug(f"Rate limit result for {ident}: allowed={result.allowed}, limit={result.limit}, remaining={result.remaining}")

                if not result.allowed:
                    # Rate limit exceeded
                    rate_limit_info = {
                        "limit": result.limit,
                        "remaining": result.remaining,
                        "reset": result.reset,
                        "retry_after": int(max(0, result.reset - int(time.time()))) if result.reset else 60
                    }

                    logger.warning(
                        f"Rate limit exceeded for {ident} on {limiter_name}: "
                        f"limit={result.limit}, remaining={result.remaining}"
                    )

                    return False, rate_limit_info

            except Exception as e:
                logger.error(f"Error checking rate limit for {ident}: {str(e)}")
                logger.exception("Full traceback:")
                # On error, allow the request but log the issue
                continue

        logger.debug("Rate limit check passed")
        return True, None


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def check_rate_limit_sync(
        request: Request,
        limiter_name: str = "default",
        identifier: Optional[str] = None
) -> None:
    """
    Check rate limit for a request and raise exception if exceeded (synchronous version).

    Args:
        request: The FastAPI request object
        limiter_name: Name of the limiter to use
        identifier: Optional custom identifier

    Raises:
        HTTPException: If rate limit is exceeded
    """
    logger.debug(f"check_rate_limit_sync called with limiter: {limiter_name}, identifier: {identifier}")

    try:
        rate_limiter = get_rate_limiter()
        allowed, rate_limit_info = rate_limiter.check_rate_limit(
            request, limiter_name, identifier
        )

        if not allowed:
            retry_after = rate_limit_info.get("retry_after") if rate_limit_info else None

            # Include rate limit headers in the response
            headers = {}
            if rate_limit_info:
                headers["X-RateLimit-Limit"] = str(rate_limit_info.get("limit", ""))
                headers["X-RateLimit-Remaining"] = str(rate_limit_info.get("remaining", 0))
                headers["X-RateLimit-Reset"] = str(rate_limit_info.get("reset", ""))
                if retry_after:
                    headers["Retry-After"] = str(retry_after)

            raise HTTPException(
                status_code=429,
                detail={
                    "detail": f"Rate limit exceeded. Try again in {retry_after} seconds" if retry_after else "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_ERROR"
                },
                headers=headers
            )
    except HTTPException:
        # Re-raise HTTPException as is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in check_rate_limit_sync: {str(e)}")
        logger.exception("Full traceback:")
        # Don't fail the request on rate limit errors
        pass