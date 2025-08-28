"""
📋 Professional Data Models & Schemas
=====================================

Comprehensive data models with validation, documentation, and type safety.

Features:
- Pydantic models with validation
- Detailed field documentation
- Custom validators
- Error handling schemas
- Response models
- Request models

Author: AI Backend Architect
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator
from pydantic.types import constr, confloat, conint


class RiskLevel(str, Enum):
    """
    🚨 Risk Level Enumeration
    
    Defines the different risk levels for administrative guidance.
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentType(str, Enum):
    """
    📄 Content Type Enumeration
    
    Defines the types of content in the knowledge base.
    """
    HACK = "hack"
    GUIDE = "guide"
    WARNING = "warning"
    TIP = "tip"
    PROCEDURE = "procedure"


class QueryStatus(str, Enum):
    """
    ⚡ Query Status Enumeration
    
    Defines the possible statuses of a query.
    """
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"


# ===== ERROR MODELS =====

class ErrorDetail(BaseModel):
    """
    ❌ Error Detail Model
    
    Detailed error information for API responses.
    """
    
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    type: str = Field(..., description="Error type identifier")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    path: Optional[str] = Field(None, description="API path where error occurred")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    
    class Config:
        schema_extra = {
            "example": {
                "code": 400,
                "message": "Invalid query format",
                "type": "VALIDATION_ERROR",
                "details": {"field": "text", "issue": "Query too long"},
                "timestamp": "2024-01-15T10:30:00Z",
                "path": "/api/v1/chat",
                "request_id": "req_abc123"
            }
        }


class ErrorResponse(BaseModel):
    """
    🚨 Error Response Model
    
    Standard error response format for all API endpoints.
    """
    
    success: bool = Field(default=False, description="Always false for error responses")
    error: ErrorDetail = Field(..., description="Error details")
    data: Optional[Any] = Field(default=None, description="Always null for error responses")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": 429,
                    "message": "Rate limit exceeded",
                    "type": "RATE_LIMIT_EXCEEDED"
                },
                "data": None
            }
        }


# ===== HEALTH CHECK MODELS =====

class HealthStatus(BaseModel):
    """
    🏥 Health Status Model
    
    System health check information.
    """
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    version: str = Field(..., description="Application version")
    uptime: float = Field(..., description="System uptime in seconds")
    
    checks: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Individual component health checks"
    )
    
    metrics: Optional[Dict[str, Any]] = Field(
        None,
        description="System metrics (optional)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "version": "2.0.0",
                "uptime": 86400.0,
                "checks": {
                    "database": {"status": "healthy", "response_time": 0.05},
                    "ai_service": {"status": "healthy", "response_time": 0.12}
                }
            }
        }


# ===== ANALYTICS MODELS =====

class QueryAnalytics(BaseModel):
    """
    📊 Query Analytics Model
    
    Analytics data for query processing and system performance.
    """
    
    query_id: str = Field(..., description="Unique query identifier")
    user_id: Optional[str] = Field(None, description="User identifier (anonymized)")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    query_length: int = Field(..., description="Length of query in characters")
    response_length: int = Field(..., description="Length of response in characters")
    
    processing_time: float = Field(..., description="Total processing time in seconds")
    retrieval_time: float = Field(..., description="Document retrieval time in seconds")
    generation_time: float = Field(..., description="AI generation time in seconds")
    
    documents_retrieved: int = Field(..., description="Number of documents retrieved")
    confidence_score: float = Field(..., description="Response confidence score")
    
    location: Optional[str] = Field(None, description="User location (anonymized)")
    language: str = Field(..., description="Query language")
    
    risk_level: RiskLevel = Field(..., description="Assessed risk level")
    content_type: ContentType = Field(..., description="Primary content type in response")
    
    user_feedback: Optional[Dict[str, Any]] = Field(None, description="User feedback if available")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analytics timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "query_id": "query_abc123",
                "session_id": "sess_xyz789",
                "query_length": 45,
                "response_length": 312,
                "processing_time": 1.23,
                "retrieval_time": 0.15,
                "generation_time": 1.08,
                "documents_retrieved": 3,
                "confidence_score": 0.89,
                "language": "english",
                "risk_level": "low",
                "content_type": "hack"
            }
        }


# ===== FEEDBACK MODELS =====

class UserFeedback(BaseModel):
    """
    💭 User Feedback Model
    
    User feedback on AI responses for continuous improvement.
    """
    
    query_id: str = Field(..., description="Query identifier being rated")
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    rating: conint(ge=1, le=5) = Field(..., description="Rating from 1 (poor) to 5 (excellent)")
    
    helpfulness: conint(ge=1, le=5) = Field(..., description="How helpful was the response")
    accuracy: conint(ge=1, le=5) = Field(..., description="How accurate was the response")
    clarity: conint(ge=1, le=5) = Field(..., description="How clear was the response")
    
    categories: List[str] = Field(
        default_factory=list,
        description="Categories of feedback (helpful, accurate, unclear, etc.)"
    )
    
    comment: Optional[constr(max_length=1000)] = Field(
        None,
        description="Optional text feedback"
    )
    
    would_recommend: Optional[bool] = Field(
        None,
        description="Would user recommend this guidance to others"
    )
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Feedback timestamp")
    
    @validator("categories")
    def validate_categories(cls, v):
        """Validate feedback categories"""
        allowed_categories = [
            "helpful", "accurate", "clear", "comprehensive", "timely",
            "unclear", "inaccurate", "incomplete", "risky", "outdated"
        ]
        
        for category in v:
            if category.lower() not in allowed_categories:
                raise ValueError(f"Invalid category: {category}")
        
        return [cat.lower() for cat in v]
    
    class Config:
        schema_extra = {
            "example": {
                "query_id": "query_abc123",
                "rating": 4,
                "helpfulness": 4,
                "accuracy": 5,
                "clarity": 4,
                "categories": ["helpful", "accurate", "clear"],
                "comment": "Very helpful guidance, saved me a lot of time!",
                "would_recommend": True
            }
        }


# ===== CONFIGURATION MODELS =====

class SystemConfig(BaseModel):
    """
    ⚙️ System Configuration Model
    
    System configuration and feature flags.
    """
    
    features: Dict[str, bool] = Field(
        default_factory=dict,
        description="Feature flags for the application"
    )
    
    limits: Dict[str, int] = Field(
        default_factory=dict,
        description="System limits and quotas"
    )
    
    ai_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="AI model configuration"
    )
    
    security_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Security configuration"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "features": {
                    "content_filtering": True,
                    "risk_assessment": True,
                    "analytics": True
                },
                "limits": {
                    "max_query_length": 2000,
                    "rate_limit_per_hour": 100,
                    "max_session_duration": 3600
                },
                "ai_config": {
                    "model": "gemini-1.5-flash-latest",
                    "temperature": 0.7,
                    "max_tokens": 2048
                }
            }
        }


# ===== UTILITY MODELS =====

class PaginationParams(BaseModel):
    """
    📄 Pagination Parameters
    
    Standard pagination parameters for list endpoints.
    """
    
    page: conint(ge=1) = Field(default=1, description="Page number (1-based)")
    size: conint(ge=1, le=100) = Field(default=20, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Literal["asc", "desc"] = Field(default="desc", description="Sort order")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.size
    
    class Config:
        schema_extra = {
            "example": {
                "page": 1,
                "size": 20,
                "sort_by": "timestamp",
                "sort_order": "desc"
            }
        }


class PaginatedResponse(BaseModel):
    """
    📋 Paginated Response Model
    
    Generic paginated response wrapper.
    """
    
    items: List[Any] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")
    
    @root_validator
    def calculate_pagination_fields(cls, values):
        """Calculate pagination fields"""
        total = values.get('total', 0)
        size = values.get('size', 20)
        page = values.get('page', 1)
        
        pages = (total + size - 1) // size  # Ceiling division
        has_next = page < pages
        has_prev = page > 1
        
        values.update({
            'pages': pages,
            'has_next': has_next,
            'has_prev': has_prev
        })
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "items": ["... list of items ..."],
                "total": 150,
                "page": 1,
                "size": 20,
                "pages": 8,
                "has_next": True,
                "has_prev": False
            }
        }


#]== REQUEST MODELS =====

class ChatQuery(BaseModel):
    """
    💬 Chat Query Request Model
    
    Represents a user query to the AI assistant.
    """
    
    text: constr(min_length=1, max_length=2000, strip_whitespace=True) = Field(
        ...,
        description="The user's question or query text",
        example="How do I get a PAN card quickly without long queues?"
    )
    
    location: Optional[constr(min_length=2, max_length=100)] = Field(
        None,
        description="User's location for context-aware responses",
        example="Mumbai, Maharashtra"
    )
    
    session_id: Optional[str] = Field(
        None,
        description="Unique session identifier for conversation tracking",
        example="sess_12345_abcde"
    )
    
    user_id: Optional[str] = Field(
        None,
        description="User identifier (if authenticated)",
        example="user_98765"
    )
    
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context information",
        example={"previous_queries": 2, "user_type": "individual"}
    )
    
    language: Optional[str] = Field(
        default="english",
        description="Preferred response language",
        example="hindi"
    )
    
    include_sources: bool = Field(
        default=True,
        description="Whether to include source references in response"
    )
    
    max_response_length: Optional[conint(ge=100, le=5000)] = Field(
        default=None,
        description="Maximum desired response length in characters"
    )
    
    @validator("text")
    def validate_text(cls, v):
        """Validate query text for content and format"""
        if not v or not v.strip():
            raise ValueError("Query text cannot be empty")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\b(hack|crack|break|illegal|fraud)\b.*\b(system|database|security)\b',
            r'\b(steal|theft|robbery|scam)\b',
        ]
        
        text_lower = v.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, text_lower):
                raise ValueError("Query contains potentially harmful content")
        
        return v.strip()
    
    @validator("location")
    def validate_location(cls, v):
        """Validate location format"""
        if v:
            # Basic validation for location format
            if len(v.split(',')) > 3:
                raise ValueError("Location format should be: City, State or City, State, Country")
        return v
    
    @validator("language")
    def validate_language(cls, v):
        """Validate language code"""
        if v:
            allowed_languages = [
                "english", "hindi", "bengali", "tamil", "telugu", 
                "marathi", "gujarati", "kannada", "malayalam", "punjabi"
            ]
            if v.lower() not in allowed_languages:
                raise ValueError(f"Language must be one of: {', '.join(allowed_languages)}")
        return v.lower() if v else "english"
    
    class Config:
        schema_extra = {
            "example": {
                "text": "How can I expedite my passport application process?",
                "location": "Bangalore, Karnataka",
                "session_id": "sess_abc123",
                "language": "english",
                "include_sources": True
            }
        }


# ===== RESPONSE MODELS =====

class SourceDocument(BaseModel):
    """
    📄 Source Document Model
    
    Represents a source document used in generating the response.
    """
    
    id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title")
    content_type: ContentType = Field(..., description="Type of content")
    summary: str = Field(..., description="Brief summary of the document")
    confidence_score: confloat(ge=0.0, le=1.0) = Field(..., description="Relevance confidence score")
    risk_level: RiskLevel = Field(..., description="Risk level of the guidance")
    location_specific: bool = Field(default=False, description="Whether advice is location-specific")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    url: Optional[str] = Field(None, description="Source URL if available")
    tags: List[str] = Field(default_factory=list, description="Content tags")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "doc_passport_001",
                "title": "Fast Track Passport Application",
                "content_type": "hack",
                "summary": "Methods to expedite passport processing through proper channels",
                "confidence_score": 0.92,
                "risk_level": "low",
                "location_specific": True,
                "tags": ["passport", "travel", "documents", "fast-track"]
            }
        }


class RiskAssessment(BaseModel):
    """
    🚨 Risk Assessment Model
    
    Represents the risk analysis of the provided guidance.
    """
    
    overall_risk: RiskLevel = Field(..., description="Overall risk level")
    
    legal_risk: RiskLevel = Field(..., description="Legal compliance risk level")
    
    financial_risk: RiskLevel = Field(..., description="Financial risk level")
    
    safety_risk: RiskLevel = Field(..., description="Personal safety risk level")
    
    success_probability: confloat(ge=0.0, le=1.0) = Field(
        ..., 
        description="Estimated probability of success"
    )
    
    warnings: List[str] = Field(
        default_factory=list,
        description="Specific warnings and cautions"
    )
    
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Prerequisites before following the guidance"
    )
    
    alternatives: List[str] = Field(
        default_factory=list,
        description="Alternative approaches to consider"
    )
    
    disclaimer: str = Field(
        default="This guidance is for informational purposes only. Always verify with official sources.",
        description="Legal disclaimer"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "overall_risk": "low",
                "legal_risk": "low",
                "financial_risk": "low",
                "safety_risk": "low",
                "success_probability": 0.85,
                "warnings": ["Ensure all documents are genuine"],
                "prerequisites": ["Valid identity proof", "Address proof"],
                "alternatives": ["Standard processing", "Online application"]
            }
        }


class ChatResponse(BaseModel):
    """
    💬 Chat Response Model
    
    Comprehensive response model for AI assistant replies.
    """
    
    success: bool = Field(default=True, description="Whether the request was successful")
    
    query: str = Field(..., description="Original user query")
    
    response: str = Field(..., description="AI assistant response")
    
    confidence_score: confloat(ge=0.0, le=1.0) = Field(
        ..., 
        description="Overall confidence in the response"
    )
    
    risk_assessment: RiskAssessment = Field(..., description="Risk analysis of the guidance")
    
    context_sources: List[SourceDocument] = Field(
        ..., 
        description="Source documents used to generate the response"
    )
    
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions"
    )
    
    related_topics: List[str] = Field(
        default_factory=list,
        description="Related topics that might interest the user"
    )
    
    processing_time: float = Field(..., description="Response processing time in seconds")
    
    session_id: Optional[str] = Field(None, description="Session identifier")
    
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the response"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "query": "How to get PAN card quickly?",
                "response": "Here are several legitimate ways to expedite your PAN card application...",
                "confidence_score": 0.89,
                "processing_time": 1.23,
                "follow_up_questions": [
                    "What documents do I need for PAN card application?",
                    "How much does expedited processing cost?"
                ],
                "related_topics": ["Aadhaar card", "Income tax filing", "Bank account opening"]
            }
        }


# ===# ===

# Export all models
__all__ = [
    # Enums
    "RiskLevel", "ContentType", "QueryStatus",
    
    # Request models
    "ChatQuery",
    
    # Response models
    "SourceDocument", "RiskAssessment", "ChatResponse",
    
    # Error models
    "ErrorDetail", "ErrorResponse",
    
    # Health models
    "HealthStatus",
    
    # Analytics models
    "QueryAnalytics", "UserFeedback",
    
    # Configuration models
    "SystemConfig",
    
    # Utility models
    "PaginationParams", "PaginatedResponse"
]