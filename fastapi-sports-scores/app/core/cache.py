from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import json
import os

class Cache:
    def __init__(self, expiration_minutes: int = 5):
        self.expiration_time = timedelta(minutes=expiration_minutes)
        self.cache: Dict[str, Any] = {}
        self.last_updated: Dict[str, datetime] = {}

    def set(self, key: str, value: Any, expiration_minutes: int = None) -> None:
        self.cache[key] = value
        # Use custom expiration or default
        expiration = timedelta(minutes=expiration_minutes) if expiration_minutes else self.expiration_time
        self.last_updated[key] = datetime.now()
        # Store custom expiration time for this key
        if not hasattr(self, 'custom_expirations'):
            self.custom_expirations = {}
        self.custom_expirations[key] = expiration

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Check if we have custom expiration for this key
            expiration_time = getattr(self, 'custom_expirations', {}).get(key, self.expiration_time)
            
            if datetime.now() - self.last_updated[key] < expiration_time:
                return self.cache[key]
            else:
                self.invalidate(key)
        return None

    def invalidate(self, key: str) -> None:
        if key in self.cache:
            del self.cache[key]
            del self.last_updated[key]

    def clear(self) -> None:
        self.cache.clear()
        self.last_updated.clear()