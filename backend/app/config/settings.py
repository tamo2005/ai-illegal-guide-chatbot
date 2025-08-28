"""
⚙️ Application Configuration
============================

Professional configuration management with environment-based settings,
validation, and best practices for security and maintainability.

Features:
- Environment variable management
- Configuration validation
- Multiple environment support
- Security-focused defaults
- Type hints and documentation

Author: AI Backend Architect
"""

import os
from functools import lru_cache
from typing import List, Optional, Union
from pydantic import BaseSettings, Field, validator
from dotenv import load_dotenv


class Settings(BaseSettings):
    """
    🔧 Application Settings
    
    Centralized configuration management with automatic environment
    variable loading and validation.
    """
    
    # ===== CORE APPLICATION SETTINGS =====
    APP_NAME: str = Field(
        default="AI Illegal Guide Chatbot",
        description="Application name"
    )
    
    API_VERSION: str = Field(
        default="v1",
        description="API version identifier"
    )
    
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
    
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # ===== SERVER CONFIGURATION =====
    HOST: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )
    
    PORT: int = Field(
        default=8000,
        description="Server port number"
    )
    
    # ===== SECURITY SETTINGS =====
    SECRET_KEY: str = Field(
        description="Secret key for encryption and security",
        min_length=32
    )
    
    ALLOWED_HOSTS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001"
        ],
        description="Allowed CORS origins"
    )
    
    # ===== API KEYS =====
    GOOGLE_API_KEY: str = Field(
        description="Google Generative AI API key",
        min_length=10
    )
    
    # ===== RATE LIMITING =====
    RATE_LIMIT_CALLS: int = Field(
        default=100,
        description="Number of API calls allowed per period",
        ge=1
    )
    
    RATE_LIMIT_PERIOD: int = Field(
        default=3600,  # 1 hour in seconds
        description="Rate limit period in seconds",
        ge=60
    )
    
    # ===== LOGGING CONFIGURATION =====
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format: json, text"
    )
    
    LOG_FILE: Optional[str] = Field(
        default=None,
        description="Log file path (optional)"
    )
    
    # ===== AI/ML SETTINGS =====
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-flash-latest",
        description="Google Gemini model to use"
    )
    
    EMBEDDING_MODEL: str = Field(
        default="models/embedding-001",
        description="Google embedding model"
    )
    
    MAX_TOKENS: int = Field(
        default=2048,
        description="Maximum tokens for AI responses",
        ge=100,
        le=8192
    )
    
    TEMPERATURE: float = Field(
        default=0.7,
        description="AI model temperature (creativity level)",
        ge=0.0,
        le=2.0
    )
    
    # ===== VECTOR DATABASE SETTINGS =====
    VECTOR_DB_TYPE: str = Field(
        default="memory",
        description="Vector database type: memory, persistent"
    )
    
    VECTOR_DB_PATH: Optional[str] = Field(
        default=None,
        description="Path for persistent vector database"
    )
    
    VECTOR_DIMENSION: int = Field(
        default=768,
        description="Vector embedding dimension",
        ge=128
    )
    
    SIMILARITY_THRESHOLD: float = Field(
        default=0.7,
        description="Minimum similarity score for retrieval",
        ge=0.0,
        le=1.0
    )
    
    TOP_K_RESULTS: int = Field(
        default=5,
        description="Number of top results to retrieve",
        ge=1,
        le=20
    )
    
    # ===== KNOWLEDGE BASE SETTINGS =====
    KNOWLEDGE_BASE_PATH: str = Field(
        default="app/data/sources",
        description="Path to knowledge base files"
    )
    
    KNOWLEDGE_BASE_FILES: List[str] = Field(
        default=["hacks.json"],
        description="Knowledge base file names"
    )
    
    AUTO_RELOAD_KB: bool = Field(
        default=True,
        description="Auto-reload knowledge base on changes"
    )
    
    # ===== CACHING SETTINGS =====
    CACHE_ENABLED: bool = Field(
        default=True,
        description="Enable response caching"
    )
    
    CACHE_TTL: int = Field(
        default=3600,  # 1 hour
        description="Cache time-to-live in seconds",
        ge=60
    )
    
    CACHE_MAX_SIZE: int = Field(
        default=1000,
        description="Maximum cache entries",
        ge=10
    )
    
    # ===== MONITORING & ANALYTICS =====
    ENABLE_METRICS: bool = Field(
        default=True,
        description="Enable performance metrics collection"
    )
    
    ENABLE_ANALYTICS: bool = Field(
        default=True,
        description="Enable usage analytics"
    )
    
    METRICS_RETENTION_DAYS: int = Field(
        default=30,
        description="Days to retain metrics data",
        ge=1
    )
    
    # ===== SAFETY & CONTENT FILTERING =====
    CONTENT_FILTER_ENABLED: bool = Field(
        default=True,
        description="Enable content filtering"
    )
    
    RISK_ASSESSMENT_ENABLED: bool = Field(
        default=True,
        description="Enable risk assessment"
    )
    
    MAX_QUERY_LENGTH: int = Field(
        default=1000,
        description="Maximum query length in characters",
        ge=10,
        le=5000
    )
    
    BLOCKED_KEYWORDS: List[str] = Field(
        default=[],
        description="Keywords to block in queries"
    )
    
    # ===== VALIDATORS =====
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment setting"""
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v.lower()
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level setting"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()
    
    @validator("LOG_FORMAT")
    def validate_log_format(cls, v):
        """Validate log format setting"""
        allowed = ["json", "text"]
        if v.lower() not in allowed:
            raise ValueError(f"Log format must be one of: {allowed}")
        return v.lower()
    
    @validator("VECTOR_DB_TYPE")
    def validate_vector_db_type(cls, v):
        """Validate vector database type"""
        allowed = ["memory", "persistent"]
        if v.lower() not in allowed:
            raise ValueError(f"Vector DB type must be one of: {allowed}")
        return v.lower()
    
    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("KNOWLEDGE_BASE_FILES", pre=True)
    def parse_kb_files(cls, v):
        """Parse knowledge base files from string or list"""
        if isinstance(v, str):
            return [file.strip() for file in v.split(",")]
        return v
    
    @validator("BLOCKED_KEYWORDS", pre=True)
    def parse_blocked_keywords(cls, v):
        """Parse blocked keywords from string or list"""
        if isinstance(v, str):
            return [keyword.strip().lower() for keyword in v.split(",")]
        return [keyword.lower() for keyword in v] if v else []
    
    # ===== POST-INIT VALIDATION =====
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._post_init_validation()
    
    def _post_init_validation(self):
        """Additional validation after initialization"""
        
        # Set debug mode for development
        if self.ENVIRONMENT == "development":
            self.DEBUG = True
        
        # Production-specific settings
        if self.ENVIRONMENT == "production":
            self.DEBUG = False
            if "localhost" in str(self.ALLOWED_HOSTS):
                raise ValueError("Localhost not allowed in production CORS origins")
        
        # Ensure knowledge base path exists
        if not os.path.exists(self.KNOWLEDGE_BASE_PATH):
            os.makedirs(self.KNOWLEDGE_BASE_PATH, exist_ok=True)
    
    # ===== UTILITY METHODS =====
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT == "production"
    
    @property
    def database_url(self) -> Optional[str]:
        """Get database URL if configured"""
        return os.getenv("DATABASE_URL")
    
    def get_knowledge_base_files(self) -> List[str]:
        """Get full paths to knowledge base files"""
        return [
            os.path.join(self.KNOWLEDGE_BASE_PATH, filename)
            for filename in self.KNOWLEDGE_BASE_FILES
        ]
    
    class Config:
        # Configuration for pydantic BaseSettings
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        allow_mutation = False  # Make settings immutable
        validate_assignment = True  # Validate on assignment


@lru_cache()
def get_settings() -> Settings:
    """
    🏭 Settings Factory
    
    Creates and caches application settings instance.
    Uses LRU cache to ensure singleton pattern.
    
    Returns:
        Settings: Configured settings instance
    """
    
    # Load environment variables from .env file
    env_files = [".env", "../.env", "../../.env"]
    for env_file in env_files:
        if os.path.exists(env_file):
            load_dotenv(env_file)
            break
    
    try:
        return Settings()
    except Exception as e:
        print(f"❌ Configuration Error: {str(e)}")
        print("💡 Please check your .env file and environment variables")
        raise


# Export for easy imports
settings = get_settings()

# Configuration summary for debugging
if __name__ == "__main__":
    print("🔧 Configuration Summary:")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Debug Mode: {settings.DEBUG}")
    print(f"   Host: {settings.HOST}:{settings.PORT}")
    print(f"   API Version: {settings.API_VERSION}")
    print(f"   Allowed Origins: {len(settings.ALLOWED_HOSTS)} configured")
    print(f"   Log Level: {settings.LOG_LEVEL}")
    print(f"   Knowledge Base: {len(settings.KNOWLEDGE_BASE_FILES)} files")
    print(f"   Rate Limit: {settings.RATE_LIMIT_CALLS} calls/{settings.RATE_LIMIT_PERIOD}s")
    print("✅ Configuration loaded successfully!")