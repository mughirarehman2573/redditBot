# backend/app/utils/rate_limiter.py
import time
from datetime import datetime, timedelta
from typing import Dict
import threading


class RateLimiter:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RateLimiter, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self):
        self.rate_limits: Dict[str, Dict] = {}
        self.request_counts: Dict[str, int] = {}
        self.last_reset: Dict[str, datetime] = {}

    def check_rate_limit(self, account_id: str, action: str = "api_call") -> bool:
        """Check if rate limit is exceeded for an account."""
        key = f"{account_id}_{action}"
        current_time = datetime.now()

        # Reset counter if more than 1 minute passed
        if key not in self.last_reset or (current_time - self.last_reset[key]) > timedelta(minutes=1):
            self.request_counts[key] = 0
            self.last_reset[key] = current_time

        # Reddit rate limit: ~60 requests per minute
        if self.request_counts[key] >= 55:  # Safe threshold
            wait_time = 60 - (current_time - self.last_reset[key]).seconds
            if wait_time > 0:
                time.sleep(wait_time)
                self.request_counts[key] = 0
                self.last_reset[key] = datetime.now()

        self.request_counts[key] += 1
        return True

    def get_wait_time(self, account_id: str, action: str = "api_call") -> int:
        """Get remaining wait time if rate limited."""
        key = f"{account_id}_{action}"
        current_time = datetime.now()

        if key in self.last_reset:
            time_since_reset = (current_time - self.last_reset[key]).seconds
            if time_since_reset < 60 and self.request_counts.get(key, 0) >= 60:
                return 60 - time_since_reset

        return 0