# backend/app/services/session_service.py
import uuid
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import sqlite3
import aiosqlite
from ..models.schemas import ChatSession, ChatMessage, UserFeedback
from ..core.logging import get_logger
from ..core.config import settings

logger = get_logger(__name__)

class SessionService:
    def __init__(self):
        """Initialize session service with SQLite database"""
        self.db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        self.session_cache: Dict[str, ChatSession] = {}
        self.cache_max_size = 1000
        self.cache_ttl = timedelta(hours=2)
        self._init_db()
        logger.info("✅ SessionService initialized")

    def _init_db(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id TEXT PRIMARY KEY,
                        user_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id TEXT PRIMARY KEY,
                        session_id TEXT,
                        user_message TEXT NOT NULL,
                        assistant_response TEXT NOT NULL,
                        confidence_score REAL DEFAULT 0.0,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT,
                        FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS user_feedback (
                        id TEXT PRIMARY KEY,
                        session_id TEXT,
                        message_id TEXT,
                        rating INTEGER,
                        feedback_text TEXT,
                        feedback_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS usage_analytics (
                        id TEXT PRIMARY KEY,
                        date DATE,
                        total_chats INTEGER DEFAULT 0,
                        unique_sessions INTEGER DEFAULT 0,
                        avg_confidence REAL DEFAULT 0.0,
                        avg_response_time REAL DEFAULT 0.0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions (user_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_session_id ON chat_messages (session_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages (timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_feedback_session_id ON user_feedback (session_id)')
                
                conn.commit()
                logger.info("✅ Database tables initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize database: {str(e)}")
            raise

    def is_healthy(self) -> bool:
        """Check if session service is healthy"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Session service health check failed: {str(e)}")
            return False

    async def get_or_create_session(
        self, 
        session_id: Optional[str] = None, 
        user_id: Optional[str] = None
    ) -> ChatSession:
        """Get existing session or create new one"""
        try:
            if session_id and session_id in self.session_cache:
                cached_session = self.session_cache[session_id]
                if datetime.utcnow() - cached_session.updated_at < self.cache_ttl:
                    return cached_session

            if session_id:
                session = await self._get_session_from_db(session_id)
                if session:
                    self._update_cache(session)
                    return session

            # Create new session
            new_session = ChatSession(
                id=session_id or str(uuid.uuid4()),
                user_id=user_id or f"anonymous_{uuid.uuid4().hex[:8]}",
                messages=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                metadata={"total_messages": 0, "avg_confidence": 0.0},
                is_active=True
            )

            await self._save_session_to_db(new_session)
            self._update_cache(new_session)
            
            logger.info(f"✅ Created new session: {new_session.id}")
            return new_session

        except Exception as e:
            logger.error(f"❌ Failed to get/create session: {str(e)}")
            raise

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get session by ID"""
        try:
            # Check cache first
            if session_id in self.session_cache:
                cached_session = self.session_cache[session_id]
                if datetime.utcnow() - cached_session.updated_at < self.cache_ttl:
                    return cached_session

            # Get from database
            session = await self._get_session_from_db(session_id)
            if session:
                self._update_cache(session)
                
            return session

        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {str(e)}")
            return None

    async def add_message_to_session(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        confidence_score: float = 0.0
    ):
        """Add a message exchange to the session"""
        try:
            message_id = str(uuid.uuid4())
            
            # Create message object
            message = ChatMessage(
                id=message_id,
                session_id=session_id,
                user_message=user_message,
                assistant_response=assistant_response,
                confidence_score=confidence_score,
                timestamp=datetime.utcnow(),
                metadata={"length": len(assistant_response), "words": len(assistant_response.split())}
            )
            
            # Save to database
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO chat_messages 
                    (id, session_id, user_message, assistant_response, confidence_score, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message.id,
                    message.session_id,
                    message.user_message,
                    message.assistant_response,
                    message.confidence_score,
                    message.timestamp,
                    json.dumps(message.metadata)
                ))
                await conn.commit()
            
            # Update session in cache
            if session_id in self.session_cache:
                session = self.session_cache[session_id]
                session.messages.append(message)
                session.updated_at = datetime.utcnow()
                session.metadata["total_messages"] = len(session.messages)
                
                # Update average confidence
                total_confidence = sum(msg.confidence_score for msg in session.messages)
                session.metadata["avg_confidence"] = total_confidence / len(session.messages)
                
                await self._update_session_metadata(session_id, session.metadata)
            
            logger.info(f"✅ Added message to session {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to add message to session {session_id}: {str(e)}")
            raise

    async def delete_session(self, session_id: str):
        """Delete a session and all its messages"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # Delete messages first (foreign key constraint)
                await conn.execute('DELETE FROM chat_messages WHERE session_id = ?', (session_id,))
                await conn.execute('DELETE FROM user_feedback WHERE session_id = ?', (session_id,))
                await conn.execute('DELETE FROM chat_sessions WHERE id = ?', (session_id,))
                await conn.commit()
            
            # Remove from cache
            if session_id in self.session_cache:
                del self.session_cache[session_id]
            
            logger.info(f"✅ Deleted session {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to delete session {session_id}: {str(e)}")
            raise

    async def save_feedback(self, feedback: UserFeedback) -> str:
        """Save user feedback"""
        try:
            feedback_id = str(uuid.uuid4())
            
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT INTO user_feedback 
                    (id, session_id, message_id, rating, feedback_text, feedback_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    feedback_id,
                    feedback.session_id,
                    feedback.message_id,
                    feedback.rating,
                    feedback.feedback_text,
                    feedback.feedback_type,
                    datetime.utcnow()
                ))
                await conn.commit()
            
            logger.info(f"✅ Saved feedback: {feedback_id}")
            return feedback_id
            
        except Exception as e:
            logger.error(f"❌ Failed to save feedback: {str(e)}")
            raise

    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage analytics and statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # Total sessions
                cursor = await conn.execute('SELECT COUNT(*) FROM chat_sessions')
                total_sessions = (await cursor.fetchone())[0]
                
                # Total messages
                cursor = await conn.execute('SELECT COUNT(*) FROM chat_messages')
                total_messages = (await cursor.fetchone())[0]
                
                # Average confidence score
                cursor = await conn.execute('SELECT AVG(confidence_score) FROM chat_messages')
                avg_confidence = (await cursor.fetchone())[0] or 0.0
                
                # Sessions by date (last 30 days)
                cursor = await conn.execute('''
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM chat_sessions 
                    WHERE created_at >= date('now', '-30 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                    LIMIT 30
                ''')
                daily_sessions = [{"date": row[0], "count": row[1]} for row in await cursor.fetchall()]
                
                # Most active users
                cursor = await conn.execute('''
                    SELECT user_id, COUNT(*) as message_count
                    FROM chat_sessions s
                    JOIN chat_messages m ON s.id = m.session_id
                    GROUP BY user_id
                    ORDER BY message_count DESC
                    LIMIT 10
                ''')
                top_users = [{"user_id": row[0], "messages": row[1]} for row in await cursor.fetchall()]
                
                # Average session duration (estimated from message timestamps)
                cursor = await conn.execute('''
                    SELECT AVG(
                        (julianday(MAX(timestamp)) - julianday(MIN(timestamp))) * 24 * 60
                    ) as avg_duration_minutes
                    FROM chat_messages
                    GROUP BY session_id
                    HAVING COUNT(*) > 1
                ''')
                result = await cursor.fetchone()
                avg_session_duration = result[0] if result and result[0] else 0.0
                
                # Feedback statistics
                cursor = await conn.execute('''
                    SELECT 
                        AVG(rating) as avg_rating,
                        COUNT(*) as total_feedback,
                        SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive_feedback
                    FROM user_feedback
                    WHERE rating IS NOT NULL
                ''')
                feedback_stats = await cursor.fetchone()
                
                stats = {
                    "overview": {
                        "total_sessions": total_sessions,
                        "total_messages": total_messages,
                        "avg_confidence_score": round(avg_confidence, 2),
                        "avg_session_duration_minutes": round(avg_session_duration, 2)
                    },
                    "daily_activity": daily_sessions,
                    "top_users": top_users,
                    "feedback": {
                        "average_rating": round(feedback_stats[0], 2) if feedback_stats[0] else 0.0,
                        "total_feedback": feedback_stats[1] if feedback_stats[1] else 0,
                        "positive_feedback_rate": round(
                            (feedback_stats[2] / feedback_stats[1] * 100), 1
                        ) if feedback_stats[1] and feedback_stats[1] > 0 else 0.0
                    },
                    "cache_stats": {
                        "cached_sessions": len(self.session_cache),
                        "cache_hit_rate": "Not tracked"  # Could implement this
                    }
                }
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ Failed to get usage stats: {str(e)}")
            raise

    async def cleanup_old_sessions(self, days: int = 30):
        """Clean up old inactive sessions"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            async with aiosqlite.connect(self.db_path) as conn:
                # Get sessions to delete
                cursor = await conn.execute('''
                    SELECT id FROM chat_sessions 
                    WHERE updated_at < ? AND is_active = FALSE
                ''', (cutoff_date,))
                old_sessions = [row[0] for row in await cursor.fetchall()]
                
                if old_sessions:
                    # Delete messages and feedback for old sessions
                    placeholders = ','.join('?' * len(old_sessions))
                    await conn.execute(f'DELETE FROM chat_messages WHERE session_id IN ({placeholders})', old_sessions)
                    await conn.execute(f'DELETE FROM user_feedback WHERE session_id IN ({placeholders})', old_sessions)
                    await conn.execute(f'DELETE FROM chat_sessions WHERE id IN ({placeholders})', old_sessions)
                    await conn.commit()
                    
                    # Remove from cache
                    for session_id in old_sessions:
                        if session_id in self.session_cache:
                            del self.session_cache[session_id]
                    
                    logger.info(f"🧹 Cleaned up {len(old_sessions)} old sessions")
                else:
                    logger.info("🧹 No old sessions to clean up")
                    
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old sessions: {str(e)}")

    # Private helper methods
    async def _get_session_from_db(self, session_id: str) -> Optional[ChatSession]:
        """Get session from database"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # Get session
                cursor = await conn.execute('''
                    SELECT id, user_id, created_at, updated_at, metadata, is_active
                    FROM chat_sessions WHERE id = ?
                ''', (session_id,))
                session_row = await cursor.fetchone()
                
                if not session_row:
                    return None
                
                # Get messages
                cursor = await conn.execute('''
                    SELECT id, session_id, user_message, assistant_response, 
                           confidence_score, timestamp, metadata
                    FROM chat_messages 
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                ''', (session_id,))
                message_rows = await cursor.fetchall()
                
                # Build messages list
                messages = []
                for row in message_rows:
                    message = ChatMessage(
                        id=row[0],
                        session_id=row[1],
                        user_message=row[2],
                        assistant_response=row[3],
                        confidence_score=row[4],
                        timestamp=datetime.fromisoformat(row[5].replace('Z', '+00:00')) if isinstance(row[5], str) else row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
                    messages.append(message)
                
                # Build session
                session = ChatSession(
                    id=session_row[0],
                    user_id=session_row[1],
                    created_at=datetime.fromisoformat(session_row[2].replace('Z', '+00:00')) if isinstance(session_row[2], str) else session_row[2],
                    updated_at=datetime.fromisoformat(session_row[3].replace('Z', '+00:00')) if isinstance(session_row[3], str) else session_row[3],
                    messages=messages,
                    metadata=json.loads(session_row[4]) if session_row[4] else {},
                    is_active=bool(session_row[5])
                )
                
                return session
                
        except Exception as e:
            logger.error(f"❌ Failed to get session from DB {session_id}: {str(e)}")
            return None

    async def _save_session_to_db(self, session: ChatSession):
        """Save session to database"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    INSERT OR REPLACE INTO chat_sessions 
                    (id, user_id, created_at, updated_at, metadata, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    session.id,
                    session.user_id,
                    session.created_at,
                    session.updated_at,
                    json.dumps(session.metadata),
                    session.is_active
                ))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Failed to save session to DB {session.id}: {str(e)}")
            raise

    async def _update_session_metadata(self, session_id: str, metadata: Dict[str, Any]):
        """Update session metadata in database"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute('''
                    UPDATE chat_sessions 
                    SET metadata = ?, updated_at = ?
                    WHERE id = ?
                ''', (json.dumps(metadata), datetime.utcnow(), session_id))
                await conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Failed to update session metadata {session_id}: {str(e)}")

    def _update_cache(self, session: ChatSession):
        """Update session cache with size limit"""
        try:
            # Remove oldest entries if cache is full
            if len(self.session_cache) >= self.cache_max_size:
                oldest_key = min(
                    self.session_cache.keys(),
                    key=lambda k: self.session_cache[k].updated_at
                )
                del self.session_cache[oldest_key]
            
            self.session_cache[session.id] = session
            
        except Exception as e:
            logger.error(f"❌ Failed to update cache for session {session.id}: {str(e)}")

    def _cleanup_cache(self):
        """Remove expired entries from cache"""
        try:
            current_time = datetime.utcnow()
            expired_keys = [
                key for key, session in self.session_cache.items()
                if current_time - session.updated_at > self.cache_ttl
            ]
            
            for key in expired_keys:
                del self.session_cache[key]
                
            if expired_keys:
                logger.info(f"🧹 Cleaned {len(expired_keys)} expired sessions from cache")
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup cache: {str(e)}")