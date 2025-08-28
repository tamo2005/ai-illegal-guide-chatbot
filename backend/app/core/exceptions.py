# backend/app/core/exceptions.py
from typing import Optional, Dict, Any

class BaseAPIException(Exception):
    """Base exception class for API errors"""
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

class ChatException(BaseAPIException):
    """Exception raised during chat processing"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="CHAT_PROCESSING_ERROR",
            details=details
        )

class SafetyException(BaseAPIException):
    """Exception raised for safety violations"""
    def __init__(self, message: str, severity: str = "medium"):
        super().__init__(
            message=message,
            status_code=400,
            error_code="SAFETY_VIOLATION",
            details={"severity": severity}
        )

class RateLimitException(BaseAPIException):
    """Exception raised when rate limits are exceeded"""
    def __init__(self, message: str, retry_after: int = 3600):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )

class ValidationException(BaseAPIException):
    """Exception raised for input validation errors"""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )

class ServiceUnavailableException(BaseAPIException):
    """Exception raised when a required service is unavailable"""
    def __init__(self, service_name: str, message: Optional[str] = None):
        message = message or f"Service {service_name} is currently unavailable"
        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details={"service": service_name}
        )

class AuthenticationException(BaseAPIException):
    """Exception raised for authentication failures"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR"
        )

class AuthorizationException(BaseAPIException):
    """Exception raised for authorization failures"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR"
        )

class ResourceNotFoundException(BaseAPIException):
    """Exception raised when a requested resource is not found"""
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} with ID {resource_id} not found"
        super().__init__(
            message=message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )

class ConfigurationException(BaseAPIException):
    """Exception raised for configuration errors"""
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="CONFIGURATION_ERROR",
            details={"config_key": config_key} if config_key else {}
        )

class DatabaseException(BaseAPIException):
    """Exception raised for database-related errors"""
    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details={"operation": operation} if operation else {}
        )

class ExternalAPIException(BaseAPIException):
    """Exception raised for external API failures"""
    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        super().__init__(
            message=f"External API error from {service}: {message}",
            status_code=502,
            error_code="EXTERNAL_API_ERROR",
            details={"service": service, "upstream_status": status_code}
        )