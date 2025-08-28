# backend/app/services/safety_service.py
import re
import asyncio
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from ..models.schemas import RiskAssessment
from ..core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class SafetyResult:
    is_safe: bool
    confidence: float
    reason: Optional[str] = None
    flagged_content: Optional[List[str]] = None
    severity: str = "low"  # low, medium, high, critical

class SafetyService:
    def __init__(self):
        """Initialize safety service with comprehensive filters"""
        self.is_initialized = True
        self._load_safety_patterns()
        self._load_risk_indicators()
        logger.info("✅ SafetyService initialized")

    def _load_safety_patterns(self):
        """Load safety patterns and keywords"""
        # Illegal activity patterns
        self.illegal_patterns = [
            r'\b(?:bribe|bribery|under[_\s]?the[_\s]?table|black[_\s]?money)\b',
            r'\b(?:fake|forged?|counterfeit|fraudulent)\s+(?:document|certificate|id|passport|license)\b',
            r'\b(?:hack|hacking|break[_\s]?into|unauthorized[_\s]?access)\b',
            r'\b(?:illegal|unlawful|criminal|against[_\s]?the[_\s]?law)\s+(?:way|method|means|approach)\b',
            r'\b(?:smuggl|trafficking|contraband)\b',
        ]
        
        # Harmful content patterns
        self.harmful_patterns = [
            r'\b(?:violence|violent|harm|hurt|damage)\s+(?:person|people|individual|someone)\b',
            r'\b(?:threat|threaten|intimidat)\b',
            r'\b(?:discriminat|racist|sexist|hate[_\s]?speech)\b',
            r'\b(?:suicide|self[_\s]?harm|end[_\s]?life)\b',
        ]
        
        # High-risk keywords
        self.high_risk_keywords = [
            'bypass security', 'circumvent system', 'avoid detection', 'hide from authorities',
            'illegal money', 'tax evasion', 'money laundering', 'corruption',
            'fake identity', 'stolen documents', 'identity theft',
            'drug trafficking', 'weapon smuggling', 'human trafficking'
        ]
        
        # Medium-risk keywords (requires context analysis)
        self.medium_risk_keywords = [
            'backdoor', 'workaround', 'shortcut', 'quick fix',
            'under the radar', 'off the books', 'cash only',
            'no questions asked', 'discretion', 'confidential arrangement'
        ]
        
        # Sensitive topics (not necessarily unsafe, but require careful handling)
        self.sensitive_topics = [
            'government official', 'police', 'court', 'legal proceeding',
            'immigration', 'visa', 'citizenship', 'refugee',
            'medical emergency', 'mental health', 'addiction',
            'domestic violence', 'child abuse', 'harassment'
        ]

    def _load_risk_indicators(self):
        """Load risk assessment indicators"""
        self.risk_indicators = {
            'legal_risk': [
                'court case', 'legal action', 'lawsuit', 'prosecution',
                'criminal charges', 'penalty', 'fine', 'imprisonment'
            ],
            'financial_risk': [
                'money loss', 'financial penalty', 'cost', 'expensive',
                'scam', 'fraud', 'financial loss', 'debt'
            ],
            'personal_safety_risk': [
                'dangerous', 'unsafe', 'risk', 'harm', 'injury',
                'physical danger', 'threat', 'violence'
            ],
            'reputation_risk': [
                'reputation damage', 'public shame', 'embarrassment',
                'social consequences', 'professional impact'
            ],
            'system_risk': [
                'system failure', 'data loss', 'security breach',
                'technical problems', 'malfunction', 'error'
            ]
        }

    def is_healthy(self) -> bool:
        """Check if safety service is operational"""
        return self.is_initialized

    async def check_safety(self, content: str) -> SafetyResult:
        """Comprehensive safety check for user input"""
        try:
            content_lower = content.lower()
            flagged_items = []
            max_severity = "low"
            reasons = []

            # Check for illegal activity patterns
            for pattern in self.illegal_patterns:
                matches = re.finditer(pattern, content_lower, re.IGNORECASE)
                for match in matches:
                    flagged_items.append(match.group())
                    reasons.append(f"Potential illegal activity reference: {match.group()}")
                    max_severity = "critical"

            # Check for harmful content
            for pattern in self.harmful_patterns:
                matches = re.finditer(pattern, content_lower, re.IGNORECASE)
                for match in matches:
                    flagged_items.append(match.group())
                    reasons.append(f"Harmful content detected: {match.group()}")
                    if max_severity not in ["critical"]:
                        max_severity = "high"

            # Check high-risk keywords
            for keyword in self.high_risk_keywords:
                if keyword.lower() in content_lower:
                    flagged_items.append(keyword)
                    reasons.append(f"High-risk keyword: {keyword}")
                    if max_severity not in ["critical", "high"]:
                        max_severity = "high"

            # Check medium-risk keywords with context
            medium_risk_count = 0
            for keyword in self.medium_risk_keywords:
                if keyword.lower() in content_lower:
                    medium_risk_count += 1
                    flagged_items.append(keyword)
                    
            if medium_risk_count >= 2:
                reasons.append(f"Multiple medium-risk indicators detected")
                if max_severity == "low":
                    max_severity = "medium"

            # Content length and complexity analysis
            word_count = len(content.split())
            if word_count > 500:
                # Very long queries might be trying to overwhelm safety filters
                reasons.append("Unusually long query detected")
                if max_severity == "low":
                    max_severity = "medium"

            # Calculate confidence score
            confidence = self._calculate_safety_confidence(
                content, flagged_items, len(reasons)
            )

            # Determine if content is safe
            is_safe = max_severity == "low" and len(flagged_items) == 0
            
            # Special handling for sensitive topics
            sensitive_detected = []
            for topic in self.sensitive_topics:
                if topic.lower() in content_lower:
                    sensitive_detected.append(topic)
            
            if sensitive_detected and is_safe:
                reasons.append(f"Sensitive topic detected: {', '.join(sensitive_detected[:2])}")
                # Still safe but requires careful handling

            result = SafetyResult(
                is_safe=is_safe,
                confidence=confidence,
                reason="; ".join(reasons) if reasons else None,
                flagged_content=list(set(flagged_items)) if flagged_items else None,
                severity=max_severity
            )

            if not is_safe:
                logger.warning(f"🚨 Safety violation detected: {result.reason}")
            
            return result

        except Exception as e:
            logger.error(f"❌ Safety check failed: {str(e)}")
            # Fail safe: if safety check fails, assume unsafe
            return SafetyResult(
                is_safe=False,
                confidence=0.0,
                reason=f"Safety check system error: {str(e)}",
                severity="high"
            )

    async def assess_response_risk(
        self, 
        user_query: str, 
        response: str
    ) -> RiskAssessment:
        """Assess risk levels for the AI response"""
        try:
            risks = {
                'legal_risk': 0.0,
                'safety_risk': 0.0,
                'misinformation_risk': 0.0,
                'ethical_risk': 0.0
            }
            
            risk_details = []
            combined_text = f"{user_query} {response}".lower()

            # Assess legal risk
            legal_score = self._assess_legal_risk(combined_text)
            risks['legal_risk'] = legal_score
            if legal_score > 0.5:
                risk_details.append(f"Legal risk detected (score: {legal_score:.2f})")

            # Assess safety risk
            safety_score = self._assess_safety_risk(combined_text)
            risks['safety_risk'] = safety_score
            if safety_score > 0.5:
                risk_details.append(f"Safety risk detected (score: {safety_score:.2f})")

            # Assess misinformation risk
            misinfo_score = self._assess_misinformation_risk(response)
            risks['misinformation_risk'] = misinfo_score
            if misinfo_score > 0.5:
                risk_details.append(f"Potential misinformation (score: {misinfo_score:.2f})")

            # Assess ethical risk
            ethical_score = self._assess_ethical_risk(combined_text)
            risks['ethical_risk'] = ethical_score
            if ethical_score > 0.5:
                risk_details.append(f"Ethical concerns (score: {ethical_score:.2f})")

            # Calculate overall risk
            max_risk = max(risks.values())
            avg_risk = sum(risks.values()) / len(risks)
            overall_risk = (max_risk * 0.7) + (avg_risk * 0.3)  # Weighted average

            # Determine risk level
            if overall_risk < 0.3:
                risk_level = "low"
                recommendation = "Response appears safe to provide"
            elif overall_risk < 0.6:
                risk_level = "medium" 
                recommendation = "Proceed with caution and appropriate disclaimers"
            elif overall_risk < 0.8:
                risk_level = "high"
                recommendation = "Significant risk - add strong warnings and disclaimers"
            else:
                risk_level = "critical"
                recommendation = "Critical risk - consider refusing to provide response"

            return RiskAssessment(
                overall_risk=risk_level,
                risk_score=round(overall_risk, 2),
                categories=risks,
                recommendation=recommendation,
                details=risk_details,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"❌ Risk assessment failed: {str(e)}")
            return RiskAssessment(
                overall_risk="high",
                risk_score=0.8,
                categories={'unknown_risk': 0.8},
                recommendation="Risk assessment failed - proceed with extreme caution",
                details=[f"Assessment error: {str(e)}"]
            )

    def _calculate_safety_confidence(
        self, 
        content: str, 
        flagged_items: List[str], 
        violation_count: int
    ) -> float:
        """Calculate confidence score for safety assessment"""
        base_confidence = 0.9
        
        # Reduce confidence based on flagged items
        confidence = base_confidence - (len(flagged_items) * 0.1)
        
        # Reduce confidence based on violation count
        confidence -= (violation_count * 0.05)
        
        # Content complexity factor
        word_count = len(content.split())
        if word_count > 200:
            confidence -= 0.05  # Longer content is harder to assess
        
        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))

    def _assess_legal_risk(self, text: str) -> float:
        """Assess legal risk in the content"""
        risk_score = 0.0
        
        for indicator in self.risk_indicators['legal_risk']:
            if indicator in text:
                risk_score += 0.15
        
        # Check for specific legal warning patterns
        legal_warning_patterns = [
            r'\b(?:illegal|unlawful|against.*law|prohibited|banned|forbidden)\b',
            r'\b(?:fine|penalty|punishment|jail|prison|arrest|prosecution)\b',
            r'\b(?:court|judge|lawyer|legal.*action|lawsuit)\b'
        ]
        
        for pattern in legal_warning_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                risk_score += 0.1
        
        return min(1.0, risk_score)

    def _assess_safety_risk(self, text: str) -> float:
        """Assess physical safety risk"""
        risk_score = 0.0
        
        for indicator in self.risk_indicators['personal_safety_risk']:
            if indicator in text:
                risk_score += 0.2
        
        # Physical harm patterns
        harm_patterns = [
            r'\b(?:dangerous|hazardous|risky|unsafe|harmful|toxic)\b',
            r'\b(?:injury|hurt|damage|harm|wound|accident)\b',
            r'\b(?:caution|warning|danger|alert|beware)\b'
        ]
        
        for pattern in harm_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                risk_score += 0.1
        
        return min(1.0, risk_score)

    def _assess_misinformation_risk(self, response: str) -> float:
        """Assess risk of providing misinformation"""
        risk_score = 0.0
        
        # Check for absolute statements without disclaimers
        absolute_patterns = [
            r'\b(?:always|never|definitely|certainly|guaranteed|100%|absolutely)\b',
            r'\b(?:all|every|none|no one)\s+(?:people|person|cases|situations)\b'
        ]
        
        disclaimer_patterns = [
            r'\b(?:may|might|could|possibly|likely|probably|generally|usually)\b',
            r'\b(?:consult|verify|check|confirm|official|authorized)\b',
            r'\b(?:disclaimer|warning|note|important|caution)\b'
        ]
        
        absolute_count = sum(1 for pattern in absolute_patterns 
                           if re.search(pattern, response, re.IGNORECASE))
        disclaimer_count = sum(1 for pattern in disclaimer_patterns 
                             if re.search(pattern, response, re.IGNORECASE))
        
        if absolute_count > 0 and disclaimer_count == 0:
            risk_score += 0.3
        elif absolute_count > disclaimer_count:
            risk_score += 0.2
        
        # Check response length vs specificity
        word_count = len(response.split())
        specific_terms = ['step', 'first', 'then', 'next', 'contact', 'office', 'form']
        specific_count = sum(1 for term in specific_terms if term in response.lower())
        
        if word_count > 100 and specific_count < 3:
            risk_score += 0.1  # Long response with few specifics might be generic/inaccurate
        
        return min(1.0, risk_score)

    def _assess_ethical_risk(self, text: str) -> float:
        """Assess ethical concerns in the content"""
        risk_score = 0.0
        
        # Check for discrimination indicators
        discrimination_patterns = [
            r'\b(?:discriminat|bias|prejudice|stereotype)\b',
            r'\b(?:race|gender|religion|caste|class|age).*(?:based|specific)\b',
            r'\b(?:only.*(?:men|women|rich|poor|young|old))\b'
        ]
        
        for pattern in discrimination_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                risk_score += 0.2
        
        # Check for unfair advantage patterns
        unfair_patterns = [
            r'\b(?:unfair.*advantage|gaming.*system|exploit.*loophole)\b',
            r'\b(?:cheat|trick|manipulat|deceive).*(?:system|official|authority)\b',
            r'\b(?:insider.*information|special.*connection|backdoor.*access)\b'
        ]
        
        for pattern in unfair_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                risk_score += 0.25
        
        # Check for privacy violations
        privacy_patterns = [
            r'\b(?:personal.*information|private.*data|confidential.*details)\b',
            r'\b(?:without.*permission|unauthorized.*access|breach.*privacy)\b'
        ]
        
        for pattern in privacy_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                risk_score += 0.15
        
        return min(1.0, risk_score)

    async def filter_response(self, response: str) -> str:
        """Filter and modify response if needed for safety"""
        try:
            # Check if response needs safety modifications
            safety_check = await self.check_safety(response)
            
            if not safety_check.is_safe:
                logger.warning(f"🚨 Filtering unsafe response: {safety_check.reason}")
                
                if safety_check.severity == "critical":
                    return self._get_refusal_response()
                elif safety_check.severity == "high":
                    return self._add_strong_warning(response)
                elif safety_check.severity == "medium":
                    return self._add_caution_notice(response)
            
            # Add standard disclaimers for sensitive topics
            if self._contains_sensitive_topic(response):
                response = self._add_standard_disclaimer(response)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Response filtering failed: {str(e)}")
            return self._add_error_notice(response)

    def _contains_sensitive_topic(self, text: str) -> bool:
        """Check if text contains sensitive topics"""
        text_lower = text.lower()
        return any(topic.lower() in text_lower for topic in self.sensitive_topics)

    def _get_refusal_response(self) -> str:
        """Generate a polite refusal response for critical safety violations"""
        return """I understand you're looking for help, but I can't provide assistance with this particular request as it may involve unsafe or illegal activities.

Instead, I'd be happy to help you with:
- Legal and ethical approaches to your situation
- Information about official procedures and proper channels
- Guidance on contacting relevant authorities or organizations
- Alternative solutions that follow proper protocols

Please feel free to rephrase your question, and I'll do my best to help you in a safe and appropriate way."""

    def _add_strong_warning(self, response: str) -> str:
        """Add strong safety warning to response"""
        warning = """
⚠️ **IMPORTANT SAFETY WARNING** ⚠️
The information below may involve significant risks. Please exercise extreme caution and:
- Verify all information with official sources
- Consult with qualified professionals
- Ensure all actions comply with applicable laws
- Consider potential consequences carefully

"""
        return warning + response + """

🚨 **Remember**: This information is for educational purposes only. You are responsible for ensuring your actions are legal, safe, and appropriate for your situation."""

    def _add_caution_notice(self, response: str) -> str:
        """Add moderate caution notice to response"""
        return response + """

⚠️ **Please Note**: Always verify information with official sources and ensure compliance with applicable laws and regulations. When in doubt, consult with qualified professionals."""

    def _add_standard_disclaimer(self, response: str) -> str:
        """Add standard disclaimer for sensitive topics"""
        return response + """

📋 **Disclaimer**: This information is provided for general guidance only. For specific situations, especially those involving legal, medical, or safety concerns, please consult with appropriate professionals or authorities."""

    def _add_error_notice(self, response: str) -> str:
        """Add error notice when filtering fails"""
        return response + """

⚠️ **System Note**: There was an issue with content verification. Please use this information with extra caution and verify all details independently."""

    async def log_safety_event(
        self, 
        event_type: str, 
        content: str, 
        severity: str, 
        user_id: Optional[str] = None
    ):
        """Log safety-related events for monitoring and analysis"""
        try:
            safety_event = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,  # "violation", "warning", "filter", etc.
                "severity": severity,
                "content_hash": hash(content),  # Don't log actual content for privacy
                "content_length": len(content),
                "user_id": user_id,
                "flagged_patterns": []
            }
            
            # Log to appropriate monitoring system
            # In production, this would go to a security monitoring system
            logger.warning(f"🔒 Safety event logged: {event_type} - {severity}")
            
            # Could implement rate limiting based on safety events here
            
        except Exception as e:
            logger.error(f"❌ Failed to log safety event: {str(e)}")

    def get_safety_stats(self) -> Dict[str, Any]:
        """Get safety service statistics"""
        return {
            "patterns_loaded": {
                "illegal_patterns": len(self.illegal_patterns),
                "harmful_patterns": len(self.harmful_patterns),
                "high_risk_keywords": len(self.high_risk_keywords),
                "medium_risk_keywords": len(self.medium_risk_keywords),
                "sensitive_topics": len(self.sensitive_topics)
            },
            "risk_indicators": {
                category: len(indicators) 
                for category, indicators in self.risk_indicators.items()
            },
            "service_status": "operational" if self.is_initialized else "error",
            "last_updated": datetime.utcnow().isoformat()
        }