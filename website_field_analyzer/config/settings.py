"""
Configuration settings for the Website Field Analyzer.
Controls timeouts, browser behavior, and analysis rules.
"""

from typing import Dict, Any


class Settings:
    """Central configuration for the analyzer."""
    
    # Browser settings
    HEADLESS: bool = True
    BROWSER_TYPE: str = "chromium"
    
    # Timeouts (in milliseconds)
    PAGE_LOAD_TIMEOUT: int = 30000  # 30 seconds
    NETWORK_IDLE_TIMEOUT: int = 2000  # 2 seconds
    JS_EXECUTION_BUFFER: int = 1000  # 1 second additional wait for JS frameworks
    
    # Viewport settings
    VIEWPORT_WIDTH: int = 1920
    VIEWPORT_HEIGHT: int = 1080
    
    # Analysis thresholds
    PROXIMITY_DISTANCE: int = 300  # pixels - for grouping elements
    MIN_VISIBILITY_THRESHOLD: float = 0.1  # 10% visible area
    
    # Element filtering rules
    IGNORE_TAGS: set = {
        'script', 'style', 'meta', 'link', 'noscript'
    }
    
    # Hidden field patterns to KEEP (CSRF, session tokens)
    KEEP_HIDDEN_PATTERNS: set = {
        'csrf', 'token', 'session', 'authenticity', 
        '_token', 'csrfmiddlewaretoken', '__requestverificationtoken'
    }
    
    # Analytics/tracking patterns to REMOVE
    REMOVE_TRACKING_PATTERNS: set = {
        'ga', 'gtm', 'analytics', 'tracking', 'pixel',
        'facebook', 'fb', 'twitter', 'linkedin'
    }
    
    # Common required field patterns
    REQUIRED_FIELD_PATTERNS: set = {
        'email', 'username', 'user', 'login', 'password',
        'pass', 'pwd', 'signin', 'sign-in'
    }
    
    # Logging
    LOG_LEVEL: str = "INFO"
    DEBUG_MODE: bool = False
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('_') and not callable(value)
        }
    
    @classmethod
    def update(cls, **kwargs):
        """Update settings dynamically."""
        for key, value in kwargs.items():
            if hasattr(cls, key.upper()):
                setattr(cls, key.upper(), value)
