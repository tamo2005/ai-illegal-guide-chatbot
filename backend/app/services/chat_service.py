# backend/app/services/chat_service.py
import asyncio
import json
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import google.generativeai as genai
from langchain.text_splitter import RecursiveCharacterTextSplitter
from ..core.logging import get_logger
from ..core.config import settings
from ..models.schemas import ChatMessage, RiskAssessment

logger = get_logger(__name__)

class ChatService:
    def __init__(self):
        """Initialize the chat service with Gemini AI"""
        try:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            
            # Configure the model with advanced settings
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            }
            
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
            ]
            
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-pro-latest",
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
                length_function=len,
            )
            
            logger.info("✅ ChatService initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize ChatService: {str(e)}")
            raise

    async def health_check(self) -> bool:
        """Check if the chat service is healthy"""
        try:
            # Simple test generation
            test_response = self.model.generate_content("Say 'OK' if you're working")
            return "OK" in test_response.text if test_response.text else False
        except Exception as e:
            logger.error(f"Chat service health check failed: {str(e)}")
            return False

    def _create_enhanced_prompt(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None,
        session_history: Optional[List[ChatMessage]] = None,
        location: Optional[str] = None,
        language: str = "en"
    ) -> str:
        """Create an enhanced prompt with context and conversation history"""
        
        prompt_parts = []
        
        # System instruction
        system_instruction = f"""
You are JUGAAD AI, an advanced AI assistant specialized in helping people navigate administrative challenges, bureaucratic processes, and everyday problems in India with creative, practical solutions.

Your core principles:
- Provide ethical, legal, and practical advice
- Emphasize safety and proper procedures
- Offer alternative approaches when standard methods fail
- Include relevant warnings and disclaimers
- Be empathetic and understanding of user frustrations
- Provide step-by-step guidance when possible

Language: Respond in {language}
{"Location context: " + location if location else ""}

Current date: {datetime.now().strftime("%Y-%m-%d")}
"""
        prompt_parts.append(system_instruction)
        
        # Add relevant context if available
        if context and context.get("documents"):
            prompt_parts.append("\n=== RELEVANT KNOWLEDGE BASE ===")
            for i, doc in enumerate(context["documents"][:3]):  # Top 3 most relevant
                prompt_parts.append(f"""
Document {i+1}:
Title: {doc.get('title', 'Unknown')}
Content: {doc.get('content', '')[:500]}...
Relevance Score: {doc.get('score', 0):.2f}
""")
        
        # Add conversation history for context
        if session_history:
            prompt_parts.append("\n=== CONVERSATION HISTORY ===")
            for msg in session_history[-5:]:  # Last 5 messages
                prompt_parts.append(f"User: {msg.user_message}")
                prompt_parts.append(f"Assistant: {msg.assistant_response}")
        
        # Add the current user message
        prompt_parts.append(f"\n=== CURRENT USER QUESTION ===")
        prompt_parts.append(f"User: {message}")
        
        # Response guidelines
        response_guidelines = """

=== RESPONSE GUIDELINES ===
1. Provide a comprehensive, helpful response
2. Include step-by-step instructions when applicable
3. Mention any legal considerations or risks
4. Suggest alternatives if the primary approach might not work
5. Be concise but thorough
6. Include relevant contact information or resources when helpful
7. End with a brief summary of key action items

Please provide your response now:
"""
        prompt_parts.append(response_guidelines)
        
        return "\n".join(prompt_parts)

    async def generate_response(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        session_history: Optional[List[ChatMessage]] = None,
        location: Optional[str] = None,
        language: str = "en"
    ) -> str:
        """Generate a comprehensive response using Gemini AI"""
        try:
            # Create enhanced prompt
            enhanced_prompt = self._create_enhanced_prompt(
                message, context, session_history, location, language
            )
            
            logger.info(f"🤖 Generating response for: {message[:100]}...")
            
            # Generate response with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(enhanced_prompt)
                    
                    if response.text:
                        # Post-process the response
                        processed_response = self._post_process_response(response.text)
                        logger.info(f"✅ Response generated successfully (attempt {attempt + 1})")
                        return processed_response
                    else:
                        logger.warning(f"Empty response received (attempt {attempt + 1})")
                        
                except Exception as e:
                    logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(1)  # Wait before retry
            
            # Fallback response
            return self._get_fallback_response(message)
            
        except Exception as e:
            logger.error(f"❌ Failed to generate response: {str(e)}")
            return self._get_error_response(str(e))

    async def generate_streaming_response(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        chat_id: str = "unknown"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate streaming response for real-time chat experience"""
        try:
            # Create prompt
            enhanced_prompt = self._create_enhanced_prompt(message, context)
            
            logger.info(f"🌊 Starting streaming response for chat {chat_id}")
            
            # Generate full response first (Gemini doesn't support true streaming yet)
            response = self.model.generate_content(enhanced_prompt)
            
            if response.text:
                # Simulate streaming by breaking response into chunks
                words = response.text.split()
                current_chunk = ""
                
                for i, word in enumerate(words):
                    current_chunk += word + " "
                    
                    # Send chunk every 5-10 words or at sentence boundaries
                    if (i + 1) % 7 == 0 or word.endswith('.') or word.endswith('!') or word.endswith('?'):
                        yield {
                            "text": current_chunk.strip(),
                            "is_complete": False,
                            "metadata": {"word_count": i + 1, "total_words": len(words)}
                        }
                        current_chunk = ""
                        await asyncio.sleep(0.1)  # Realistic typing delay
                
                # Send any remaining text
                if current_chunk.strip():
                    yield {
                        "text": current_chunk.strip(),
                        "is_complete": False,
                        "metadata": {"word_count": len(words), "total_words": len(words)}
                    }
                
                # Send completion signal
                yield {
                    "text": "",
                    "is_complete": True,
                    "metadata": {"total_words": len(words), "chat_id": chat_id}
                }
                
                logger.info(f"✅ Streaming completed for chat {chat_id}")
            else:
                yield {
                    "text": "I apologize, but I couldn't generate a response. Please try again.",
                    "is_complete": True,
                    "metadata": {"error": "empty_response"}
                }
                
        except Exception as e:
            logger.error(f"❌ Streaming failed for chat {chat_id}: {str(e)}")
            yield {
                "text": "I'm experiencing technical difficulties. Please try again in a moment.",
                "is_complete": True,
                "metadata": {"error": str(e)}
            }

    async def calculate_confidence(
        self,
        question: str,
        response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate confidence score for the response"""
        try:
            confidence_factors = []
            
            # Factor 1: Context relevance (40% weight)
            if context and context.get("documents"):
                avg_score = sum(doc.get("score", 0) for doc in context["documents"]) / len(context["documents"])
                confidence_factors.append(min(avg_score, 1.0) * 0.4)
            else:
                confidence_factors.append(0.2)  # Lower confidence without context
            
            # Factor 2: Response length and structure (20% weight)
            word_count = len(response.split())
            length_score = min(word_count / 100, 1.0)  # Normalize to 100 words
            structure_score = 1.0 if any(marker in response.lower() for marker in 
                                       ['step', 'first', 'next', 'then', 'finally', '1.', '2.']) else 0.5
            confidence_factors.append((length_score + structure_score) / 2 * 0.2)
            
            # Factor 3: Specific information presence (25% weight)
            specific_info_markers = ['contact', 'office', 'form', 'document', 'procedure', 'rule', 'section']
            specificity_score = sum(1 for marker in specific_info_markers if marker in response.lower()) / len(specific_info_markers)
            confidence_factors.append(specificity_score * 0.25)
            
            # Factor 4: Safety disclaimers and warnings (15% weight)
            safety_markers = ['legal', 'disclaimer', 'consult', 'verify', 'official', 'authorized']
            safety_score = min(sum(1 for marker in safety_markers if marker in response.lower()) / 2, 1.0)
            confidence_factors.append(safety_score * 0.15)
            
            final_confidence = sum(confidence_factors)
            logger.info(f"📊 Calculated confidence score: {final_confidence:.2f}")
            
            return round(final_confidence, 2)
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate confidence: {str(e)}")
            return 0.6  # Default moderate confidence

    def _post_process_response(self, response: str) -> str:
        """Post-process the AI response for better formatting and safety"""
        try:
            # Clean up formatting
            response = re.sub(r'\n{3,}', '\n\n', response)  # Remove excessive newlines
            response = response.strip()
            
            # Add safety disclaimer if dealing with sensitive topics
            sensitive_keywords = ['illegal', 'bribe', 'fake', 'fraud', 'circumvent', 'bypass']
            if any(keyword in response.lower() for keyword in sensitive_keywords):
                disclaimer = "\n\n⚠️ **Important Disclaimer**: This information is for educational purposes only. Always follow legal procedures and consult with authorized officials when in doubt."
                if disclaimer not in response:
                    response += disclaimer
            
            # Ensure response isn't too long
            if len(response) > 4000:
                response = response[:3900] + "... [Response truncated for brevity]"
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to post-process response: {str(e)}")
            return response  # Return original if processing fails

    def _get_fallback_response(self, message: str) -> str:
        """Generate a fallback response when AI fails"""
        return f"""I understand you're asking about: "{message[:100]}..."

I'm experiencing some technical difficulties right now, but I'd still like to help! Here are some general suggestions:

1. **Check Official Websites**: Look for information on relevant government or institutional websites
2. **Contact Helplines**: Most services have dedicated helplines or customer support
3. **Visit Local Offices**: Sometimes a personal visit can resolve issues faster
4. **Seek Community Help**: Online forums and local groups often have valuable insights

Please try asking your question again in a few moments, or feel free to rephrase it for a more specific response.

Is there a particular aspect of your query I can help clarify while we resolve this technical issue?"""

    def _get_error_response(self, error: str) -> str:
        """Generate an error response with helpful guidance"""
        return f"""I apologize, but I encountered a technical issue while processing your request.

**What you can do:**
1. Try rephrasing your question in simpler terms
2. Break complex queries into smaller, specific questions  
3. Check if your query contains any unusual characters or formatting
4. Try again in a few moments

**For immediate help:**
- Contact relevant official helplines
- Visit official government websites
- Consult with local experts or authorities

I'm working to resolve this issue. Please feel free to try again!

*Technical note: {error[:100]}...*"""