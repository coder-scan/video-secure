import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PlaybackSession:
    session_id: str
    user_id: str
    video_id: str
    ip: str
    created_at: float
    last_ping: float
    status: str  # ACTIVE, TERMINATED, EXPIRED
    termination_reason: Optional[str] = None


class SessionConcurrencyManager:
    """
    In-memory session concurrency manager with thread/async lock safety.
    Enforces single-device / max-concurrent stream limits per user account.
    """

    def __init__(self, session_ttl_seconds: int = 75):
        self._sessions: Dict[str, PlaybackSession] = {}
        self._user_to_sessions: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
        self.session_ttl_seconds = session_ttl_seconds

    async def register_session(
        self,
        user_id: str,
        video_id: str,
        ip: str,
        max_concurrent: int = 1,
    ) -> str:
        async with self._lock:
            now = time.time()
            session_id = str(uuid.uuid4())

            # Cleanup expired sessions for this user
            existing_session_ids = self._user_to_sessions.get(user_id, [])
            active_ids = []
            for s_id in existing_session_ids:
                s = self._sessions.get(s_id)
                if s and s.status == "ACTIVE":
                    if (now - s.last_ping) > self.session_ttl_seconds:
                        s.status = "EXPIRED"
                        s.termination_reason = "SESSION_TIMEOUT"
                    else:
                        active_ids.append(s_id)

            # If active count exceeds max_concurrent, evict/terminate oldest session
            while len(active_ids) >= max_concurrent:
                oldest_id = active_ids.pop(0)
                oldest_s = self._sessions.get(oldest_id)
                if oldest_s:
                    oldest_s.status = "TERMINATED"
                    oldest_s.termination_reason = "CONCURRENT_STREAM_DETECTED"
                    logger.info(
                        f"Evicted active session {oldest_id} for user {user_id} due to concurrency limit."
                    )

            # Register new session
            new_session = PlaybackSession(
                session_id=session_id,
                user_id=user_id,
                video_id=video_id,
                ip=ip,
                created_at=now,
                last_ping=now,
                status="ACTIVE",
            )
            self._sessions[session_id] = new_session
            active_ids.append(session_id)
            self._user_to_sessions[user_id] = active_ids

            return session_id

    async def validate_and_touch_session(self, session_id: str) -> Tuple[bool, str]:
        """
        Validates session state and updates last_ping.
        Returns (is_valid, status_or_reason).
        """
        async with self._lock:
            s = self._sessions.get(session_id)
            if not s:
                return False, "SESSION_NOT_FOUND"

            now = time.time()
            if s.status != "ACTIVE":
                reason = s.termination_reason or s.status
                return False, reason

            if (now - s.last_ping) > self.session_ttl_seconds:
                s.status = "EXPIRED"
                s.termination_reason = "SESSION_TIMEOUT"
                return False, "SESSION_TIMEOUT"

            s.last_ping = now
            return True, "ACTIVE"

    async def is_session_active(self, session_id: str) -> bool:
        async with self._lock:
            s = self._sessions.get(session_id)
            if not s or s.status != "ACTIVE":
                return False
            now = time.time()
            if (now - s.last_ping) > self.session_ttl_seconds:
                s.status = "EXPIRED"
                s.termination_reason = "SESSION_TIMEOUT"
                return False
            return True

    async def terminate_session(self, session_id: str, reason: str = "MANUAL_TERMINATION"):
        async with self._lock:
            s = self._sessions.get(session_id)
            if s:
                s.status = "TERMINATED"
                s.termination_reason = reason


# Singleton global manager
session_manager = SessionConcurrencyManager()
