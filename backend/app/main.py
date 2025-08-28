"""
🚀 JUGAAD AI - Professional Backend
===================================

Main FastAPI application with advanced features:
- Professional error handling
- Comprehensive logging
- Health checks
- Rate limiting
- Request validation
- CORS configuration
- API documentation

Author: AI Backend Architect
Version: 2.0.0 Professional Edition
"""

import os
import sys
import asyncio
import uvicorn
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import our custom modules
try:
    from .api.v1.chat import router as chat_router
    from .core.config import settings
    from .core.logging import get_logger, setup_logging
    from .core.exceptions import (
        BaseAPIException, RateLimitException, SafetyException,
        ServiceUnavailableException
    )
    from .core.middleware import RateLimitMiddleware, RequestLoggingMiddleware
    from .services.rag_service import rag_service
except ImportError:
    # Fallback imports for development
    from app.api.v1.chat import router as chat_router
    from app.core.config import settings
    from app.core.logging import get_logger, setup_logging
    from app.core.exceptions import (
        BaseAPIException, RateLimitException, SafetyException,
        ServiceUnavailableException
    )
    from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware
    from app.services.rag_service import rag_service

# Setup logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    🔄 Application Lifespan Manager
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("🚀 Starting JUGAAD AI Backend...")
    logger.info(f"🔧 Environment: {getattr(settings, 'ENVIRONMENT', 'development')}")
    logger.info(f"🌐 API Version: {getattr(settings, 'API_VERSION', 'v1')}")
    
    try:
        # Initialize services
        logger.info("🔧 Initializing services...")
        
        # Initialize RAG service if available
        try:
            await rag_service.initialize()
            logger.info("✅ RAG Service initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ RAG Service initialization failed: {str(e)}")
        
        # Perform health checks
        health_status = await perform_startup_checks()
        if not health_status["healthy"]:
            logger.warning("⚠️ Some startup health checks failed, continuing anyway...")
        
        logger.info("🎉 JUGAAD AI Backend startup completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Failed to initialize backend: {str(e)}")
        # Don't exit in production, just log the error
        if getattr(settings, 'ENVIRONMENT', 'development') == 'production':
            logger.warning("🚨 Running in degraded mode due to initialization errors")
        else:
            raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down JUGAAD AI Backend...")
    try:
        await rag_service.cleanup()
    except Exception as e:
        logger.warning(f"⚠️ Error during RAG service cleanup: {str(e)}")
    
    logger.info("👋 JUGAAD AI Backend shutdown completed")


async def perform_startup_checks() -> Dict[str, Any]:
    """
    🏥 Startup Health Checks
    Verifies all critical components are working properly.
    """
    checks = {
        "healthy": True,
        "checks": {
            "api_key": False,
            "rag_service": False,
            "knowledge_base": False
        }
    }
    
    try:
        # Check API key
        api_key = getattr(settings, 'GOOGLE_API_KEY', None) or getattr(settings, 'OPENAI_API_KEY', None)
        if api_key and len(api_key) > 10:
            checks["checks"]["api_key"] = True
            logger.info("✅ API Key validated")
        else:
            logger.error("❌ Invalid or missing API Key")
            checks["healthy"] = False
        
        # Check RAG service
        try:
            if rag_service.is_healthy():
                checks["checks"]["rag_service"] = True
                logger.info("✅ RAG Service is healthy")
        except Exception as e:
            logger.error(f"❌ RAG Service health check failed: {str(e)}")
            checks["healthy"] = False
        
        # Check knowledge base
        try:
            kb_status = await rag_service.check_knowledge_base()
            if kb_status.get("loaded", False):
                checks["checks"]["knowledge_base"] = True
                logger.info(f"✅ Knowledge base loaded: {kb_status.get('count', 0)} entries")
        except Exception as e:
            logger.error(f"❌ Knowledge base check failed: {str(e)}")
            checks["healthy"] = False
            
    except Exception as e:
        logger.error(f"💥 Health check failed: {str(e)}")
        checks["healthy"] = False
    
    return checks


# Create FastAPI application
app = FastAPI(
    title="JUGAAD AI - Administrative Assistant API",
    description="""
    🤖 **JUGAAD AI** - Your Intelligent Administrative Assistant
    
    A sophisticated AI-powered chatbot designed to help navigate administrative challenges,
    bureaucratic processes, and everyday problems in India with creative, practical solutions.
    
    ## Features
    - 💬 **Intelligent Chat**: Advanced conversational AI with context awareness
    - 🔍 **Knowledge Base**: RAG-powered responses with relevant information
    - 🛡️ **Safety First**: Comprehensive safety filtering and risk assessment  
    - 📊 **Analytics**: Usage tracking and performance monitoring
    - ⚡ **Real-time**: WebSocket support for streaming responses
    - 🔒 **Secure**: Rate limiting, input validation, and security middleware
    
    ## Getting Started
    1. Send a POST request to `/api/v1/chat` with your question
    2. Get intelligent, contextual responses with safety assessments
    3. Use `/api/v1/chat/stream` for real-time streaming responses
    
    Built with ❤️ for solving real-world problems through technology.
    """,
    version="2.0.0",
    docs_url="/docs" if getattr(settings, 'DEBUG', True) else None,
    redoc_url="/redoc" if getattr(settings, 'DEBUG', True) else None,
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add middleware stack (order matters!)

# Request logging middleware (first to catch all requests)
try:
    app.add_middleware(RequestLoggingMiddleware)
except Exception:
    logger.warning("⚠️ Request logging middleware not available")

# Rate limiting middleware
try:
    app.add_middleware(
        RateLimitMiddleware,
        calls=getattr(settings, 'RATE_LIMIT_CALLS', 100),
        period=getattr(settings, 'RATE_LIMIT_PERIOD', 60)
    )
except Exception:
    logger.warning("⚠️ Rate limiting middleware not available")

# Security Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if getattr(settings, 'DEBUG', True) else ["localhost", "127.0.0.1", "0.0.0.0"]
)

# Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS Middleware - Fixed configuration
allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000"]
if hasattr(settings, 'ALLOWED_ORIGINS'):
    allowed_origins = settings.ALLOWED_ORIGINS if not getattr(settings, 'DEBUG', True) else allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-Request-ID", "X-Response-Time"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    
    # Add request ID for tracking
    request.state.request_id = f"req_{int(start_time * 1000)}"
    
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request.state.request_id
    
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with professional error responses"""
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "HTTP_EXCEPTION",
                "timestamp": time.time(),
                "path": request.url.path
            },
            "data": None
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed information"""
    logger.error(
        f"Validation error: {exc.errors()}",
        extra={"path": request.url.path, "method": request.method}
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": 422,
                "message": "Validation failed",
                "type": "VALIDATION_ERROR",
                "details": exc.errors(),
                "timestamp": time.time(),
                "path": request.url.path
            },
            "data": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions gracefully"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal server error occurred",
                "type": "INTERNAL_ERROR",
                "timestamp": time.time(),
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", "unknown")
            },
            "data": None
        }
    )


# Root endpoint
@app.get("/", tags=["🏠 Root"])
async def root():
    """
    🏠 Root Endpoint
    Welcome message and basic API information.
    """
    return {
        "success": True,
        "message": "🤖 JUGAAD AI - Administrative Assistant API",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": time.time(),
        "documentation": "/docs",
        "health_check": "/health"
    }


# Add health check endpoint
@app.get("/health", tags=["🏥 Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "success": True,
        "status": "healthy",
        "timestamp": time.time(),
        "version": "2.0.0"
    }


# Include routers
app.include_router(
    chat_router,
    prefix="/api/v1",
    tags=["🤖 Chat & AI"]
)


if __name__ == "__main__":
    logger.info("🚀 Starting development server...")
    uvicorn.run(
        "app.main:app",
        host=getattr(settings, 'HOST', '0.0.0.0'),
        port=getattr(settings, 'PORT', 8000),
        reload=getattr(settings, 'DEBUG', True),
        log_level=getattr(settings, 'LOG_LEVEL', 'info').lower(),
        access_log=True
    )
import time
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Import our custom modules
from app.api.v1 import chat, health
from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.services.rag_service import rag_service

# Initialize settings and logger
settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    🔄 Application Lifespan Manager
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("🚀 Starting AI Illegal Guide Chatbot Backend...")
    logger.info(f"🔧 Environment: {settings.ENVIRONMENT}")
    logger.info(f"🌐 API Version: {settings.API_VERSION}")
    
    try:
        # Initialize RAG service
        await rag_service.initialize()
        logger.info("✅ RAG Service initialized successfully")
        
        # Perform health checks
        health_status = await perform_startup_checks()
        if not health_status["healthy"]:
            logger.error("❌ Startup health checks failed")
            sys.exit(1)
        
        logger.info("🎉 Backend startup completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Failed to initialize backend: {str(e)}")
        sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI Illegal Guide Chatbot Backend...")
    await rag_service.cleanup()
    logger.info("👋 Backend shutdown completed")


async def perform_startup_checks() -> Dict[str, Any]:
    """
    🏥 Startup Health Checks
    Verifies all critical components are working properly.
    """
    checks = {
        "healthy": True,
        "checks": {
            "api_key": False,
            "rag_service": False,
            "knowledge_base": False
        }
    }
    
    try:
        # Check API key
        if settings.GOOGLE_API_KEY and len(settings.GOOGLE_API_KEY) > 10:
            checks["checks"]["api_key"] = True
            logger.info("✅ Google API Key validated")
        else:
            logger.error("❌ Invalid or missing Google API Key")
            checks["healthy"] = False
        
        # Check RAG service
        if rag_service.is_healthy():
            checks["checks"]["rag_service"] = True
            logger.info("✅ RAG Service is healthy")
        else:
            logger.error("❌ RAG Service health check failed")
            checks["healthy"] = False
        
        # Check knowledge base
        kb_status = await rag_service.check_knowledge_base()
        if kb_status["loaded"]:
            checks["checks"]["knowledge_base"] = True
            logger.info(f"✅ Knowledge base loaded: {kb_status['count']} entries")
        else:
            logger.error("❌ Knowledge base not loaded")
            checks["healthy"] = False
            
    except Exception as e:
        logger.error(f"💥 Health check failed: {str(e)}")
        checks["healthy"] = False
    
    return checks


def create_application() -> FastAPI:
    """
    🏗️ Application Factory
    Creates and configures the FastAPI application with all middleware and routes.
    """
    
    # Initialize logging first
    setup_logging(
        level=settings.LOG_LEVEL,
        format_type=settings.LOG_FORMAT
    )
    
    # Create FastAPI application
    app = FastAPI(
        title="🤖 AI Illegal Guide Chatbot API",
        description="""
        ## 🚀 Professional AI-Powered Administrative Assistant
        
        Navigate India's complex administrative landscape with AI-powered guidance.
        
        ### Features:
        - 🧠 **RAG-Enhanced Responses**: Intelligent document retrieval and generation
        - 🛡️ **Safety-First Approach**: Built-in risk assessment and ethical guidelines
        - 🌍 **Location-Aware**: Context-sensitive responses based on your location
        - ⚡ **Real-Time Processing**: Fast, efficient query processing
        - 🔒 **Secure & Private**: Enterprise-grade security and privacy protection
        
        ### Usage:
        1. Send your administrative query to `/api/v1/chat`
        2. Receive intelligent, contextual responses
        3. Get risk assessments and safety recommendations
        4. Access relevant source documents and references
        
        ---
        *Built with ❤️ using FastAPI, Google AI, and modern Python practices*
        """,
        version=settings.API_VERSION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
        debug=settings.DEBUG
    )
    
    # Add middleware stack (order matters!)
    add_middleware(app)
    
    # Add exception handlers
    add_exception_handlers(app)
    
    # Include routers
    add_routers(app)
    
    return app


def add_middleware(app: FastAPI) -> None:
    """
    🛡️ Middleware Configuration
    Sets up all middleware for security, logging, and performance.
    """
    
    # Request logging middleware (first to catch all requests)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        calls=settings.RATE_LIMIT_CALLS,
        period=settings.RATE_LIMIT_PERIOD
    )
    
    # GZip compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # CORS middleware (should be last)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time"]
    )


def add_exception_handlers(app: FastAPI) -> None:
    """
    🚨 Exception Handlers
    Professional error handling for all types of exceptions.
    """
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with professional error responses"""
        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "HTTP_EXCEPTION",
                    "timestamp": time.time(),
                    "path": request.url.path
                },
                "data": None
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with detailed information"""
        logger.error(
            f"Validation error: {exc.errors()}",
            extra={"path": request.url.path, "method": request.method}
        )
        
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": 422,
                    "message": "Validation failed",
                    "type": "VALIDATION_ERROR",
                    "details": exc.errors(),
                    "timestamp": time.time(),
                    "path": request.url.path
                },
                "data": None
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions gracefully"""
        logger.error(
            f"Unhandled exception: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": "Internal server error occurred",
                    "type": "INTERNAL_ERROR",
                    "timestamp": time.time(),
                    "path": request.url.path,
                    "request_id": getattr(request.state, "request_id", "unknown")
                },
                "data": None
            }
        )


def add_routers(app: FastAPI) -> None:
    """
    🛣️ Router Configuration
    Adds all API routes to the application.
    """
    
    # Health check routes (no prefix for easy monitoring)
    app.include_router(
        health.router,
        tags=["🏥 Health & Status"]
    )
    
    # Main chat API routes
    app.include_router(
        chat.router,
        prefix=f"/api/{settings.API_VERSION}",
        tags=["🤖 Chat & AI"]
    )
    
    # Root endpoint
    @app.get("/", tags=["🏠 Root"])
    async def root():
        """
        🏠 Root Endpoint
        Welcome message and basic API information.
        """
        return {
            "success": True,
            "message": "🤖 AI Illegal Guide Chatbot API",
            "version": settings.API_VERSION,
            "status": "operational",
            "timestamp": time.time(),
            "documentation": "/docs",
            "health_check": "/health"
        }


# Create the application instance
app = create_application()

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting development server...")
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )