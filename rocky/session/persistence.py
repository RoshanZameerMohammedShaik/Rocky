"""Session persistence for Rocky.AI."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from rocky.config import get_config
from rocky.session.memory import ConversationMemory
from rocky.utils.logging import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages saving and loading sessions."""
    
    def __init__(self):
        self.config = get_config()
        self.sessions_dir = self.config.paths.sessions
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def save_session(self, memory: ConversationMemory, name: Optional[str] = None) -> str:
        """Save a session to disk. Returns the session name."""
        if name is None:
            name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Sanitize name
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
        
        session_file = self.sessions_dir / f"{safe_name}.json"
        
        data = {
            "name": name,
            "created": datetime.now().isoformat(),
            "memory": memory.to_dict(),
        }
        
        with open(session_file, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved session: {safe_name}")
        return safe_name
    
    def load_session(self, name: str) -> Optional[ConversationMemory]:
        """Load a session from disk."""
        session_file = self.sessions_dir / f"{name}.json"
        
        if not session_file.exists():
            logger.warning(f"Session not found: {name}")
            return None
        
        try:
            with open(session_file) as f:
                data = json.load(f)
            
            memory = ConversationMemory.from_dict(data.get("memory", {}))
            logger.info(f"Loaded session: {name}")
            return memory
            
        except Exception as e:
            logger.error(f"Failed to load session {name}: {e}")
            return None
    
    def list_sessions(self) -> list[dict]:
        """List all saved sessions."""
        sessions = []
        
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file) as f:
                    data = json.load(f)
                
                sessions.append({
                    "name": session_file.stem,
                    "created": data.get("created", "unknown"),
                    "turns": len(data.get("memory", {}).get("turns", [])),
                })
            except Exception as e:
                logger.warning(f"Failed to read session {session_file}: {e}")
        
        # Sort by creation date, newest first
        sessions.sort(key=lambda x: x["created"], reverse=True)
        return sessions
    
    def delete_session(self, name: str) -> bool:
        """Delete a session."""
        session_file = self.sessions_dir / f"{name}.json"
        
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Deleted session: {name}")
            return True
        
        return False
