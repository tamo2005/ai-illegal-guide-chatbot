"""
📝 Professional Logging System
===============================

Advanced logging configuration with structured logging, performance tracking,
and production-ready features.

Features:
- JSON and text formatted logging
- Request ID tracking
- Performance metrics
- Error tracking
- File and console output
- Log rotation

Author: AI Backend Architect
"""

import os
import sys
import json
import time
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from functools import wraps

import structlog
from pythonjsonlogger import jsonlogger

# Context variables for request tracking
request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class ColoredFormatter(logging.Formatter):
    """
    🎨 Colored Console Formatter
    
    Provides colorized output for console logging in development.
    """
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }
    
    def format(self, record):
        # Add color to level name
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        
        return super().format(record)


class StructuredFormatter(jsonlogger.JsonFormatter):
    """
    📋 Structured JSON Formatter
    
    Provides structured JSON logging for production environments.
    """
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]):
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add request context
        log_record['request_id'] = request_id.get()
        log_record['user_id'] = user_id.get()
        
        # Add service info
        log_record['service'] = 'ai-illegal-guide-chatbot'
        log_record['version'] = '2.0.0'
        
        # Add process info
        log_record['process_id'] = os.getpid()
        log_record['thread_name'] = record.thread


class RequestContextFilter(logging.Filter):
    """
    🔍 Request Context Filter
    
    Adds request context to all log records.
    """
    
    def filter(self, record):
        record.request_id = request_id.get() or 'no-request'
        record.user_id = user_id.get() or 'anonymous'
        return True


class PerformanceLogger:
    """
    ⚡ Performance Logger
    
    Tracks and logs performance metrics for functions and requests.
    """
    
    def __init__(self, logger_name: str = "performance"):
        self.logger = logging.getLogger(logger_name)
    
    def log_execution_time(self, func_name: str, execution_time: float, **kwargs):
        """Log function execution time"""
        self.logger.info(
            f"⏱️ Function executed: {func_name}",
            extra={
                "execution_time": execution_time,
                "function_name": func_name,
                "performance_metric": True,
                **kwargs
            }
        )
    
    def log_request_metrics(self, method: str, path: str, status_code: int, 
                          response_time: float, **kwargs):
        """Log request performance metrics"""
        self.logger.info(
            f"🌐 Request completed: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "status_code": status_code,
                "response_time": response_time,
                "request_metric": True,
                **kwargs
            }
        )


def timing_decorator(logger_name: str = None):
    """
    ⏰ Timing Decorator
    
    Decorator to automatically log function execution times.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger = logging.getLogger(logger_name or f"{func.__module__}.{func.__name__}")
                logger.debug(
                    f"✅ {func.__name__} completed successfully",
                    extra={
                        "execution_time": execution_time,
                        "function": func.__name__,
                        "module": func.__module__,
                        "success": True
                    }
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger = logging.getLogger(logger_name or f"{func.__module__}.{func.__name__}")
                logger.error(
                    f"❌ {func.__name__} failed",
                    extra={
                        "execution_time": execution_time,
                        "function": func.__name__,
                        "module": func.__module__,
                        "success": False,
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    exc_info=True
                )
                
                raise
        
        return wrapper
    return decorator


def setup_logging(level: str = "INFO", format_type: str = "json", log_file: Optional[str] = None):
    """
    🔧 Setup Logging Configuration
    
    Configures the application logging with appropriate handlers and formatters.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type (json, text)
        log_file: Optional log file path
    """
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear any existing handlers
    root_logger.handlers = []
    
    # Add request context filter
    context_filter = RequestContextFilter()
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.addFilter(context_filter)
    
    if format_type == "json":
        # JSON formatter for production
        json_formatter = StructuredFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s'
        )
        console_handler.setFormatter(json_formatter)
    else:
        # Colored text formatter for development
        text_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-20s | %(request_id)-12s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(text_formatter)
    
    root_logger.addHandler(console_handler)
    
    # Setup file handler if specified
    if log_file:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Use rotating file handler for log rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.addFilter(context_filter)
        
        # Always use JSON format for file logging
        json_formatter = StructuredFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s'
        )
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    configure_third_party_loggers()
    
    # Log startup message
    logger = logging.getLogger("logging")
    logger.info(
        "📝 Logging system initialized",
        extra={
            "log_level": level,
            "format_type": format_type,
            "file_logging": log_file is not None,
            "log_file": log_file
        }
    )


def configure_third_party_loggers():
    """
    🔧 Configure Third-Party Loggers
    
    Configures logging levels for third-party libraries to reduce noise.
    """
    
    # Reduce verbosity of third-party loggers
    third_party_loggers = {
        "urllib3.connectionpool": "WARNING",
        "google.auth": "WARNING",
        "google.auth.transport": "WARNING",
        "httpx": "WARNING",
        "httpcore": "WARNING",
        "qdrant_client": "WARNING",
        "transformers": "WARNING",
        "sentence_transformers": "WARNING"
    }
    
    for logger_name, level in third_party_loggers.items():
        logging.getLogger(logger_name).setLevel(getattr(logging, level))


def get_logger(name: str) -> logging.Logger:
    """
    🏷️ Get Logger Instance
    
    Returns a configured logger instance for the given name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


def set_request_context(req_id: str, user: Optional[str] = None):
    """
    🔍 Set Request Context
    
    Sets the request context for logging.
    
    Args:
        req_id: Request ID
        user: User ID (optional)
    """
    request_id.set(req_id)
    if user:
        user_id.set(user)


def clear_request_context():
    """
    🧹 Clear Request Context
    
    Clears the current request context.
    """
    request_id.set(None)
    user_id.set(None)


class LoggerMixin:
    """
    📊 Logger Mixin
    
    Mixin class to add logging capabilities to other classes.
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    def log_info(self, message: str, **kwargs):
        """Log info message with extra context"""
        self.logger.info(message, extra=kwargs)
    
    def log_error(self, message: str, error: Exception = None, **kwargs):
        """Log error message with exception info"""
        self.logger.error(
            message, 
            extra=kwargs, 
            exc_info=error is not None
        )
    
    def log_warning(self, message: str, **kwargs):
        """Log warning message with extra context"""
        self.logger.warning(message, extra=kwargs)
    
    def log_debug(self, message: str, **kwargs):
        """Log debug message with extra context"""
        self.logger.debug(message, extra=kwargs)


# Create performance logger instance
perf_logger = PerformanceLogger()

# Export commonly used items
__all__ = [
    'setup_logging',
    'get_logger',
    'set_request_context',
    'clear_request_context',
    'timing_decorator',
    'LoggerMixin',
    'PerformanceLogger',
    'perf_logger'
]