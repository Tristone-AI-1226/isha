"""
Browser profiles for realistic user simulation.
Provides user agents, viewport configurations, and browser arguments.
"""

from typing import Dict, List, Any


class BrowserProfiles:
    """Browser configuration profiles."""
    
    # User agents
    USER_AGENTS = {
        'desktop_chrome': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'desktop_firefox': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) '
            'Gecko/20100101 Firefox/121.0'
        ),
        'mobile_chrome': (
            'Mozilla/5.0 (Linux; Android 13) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.6099.144 Mobile Safari/537.36'
        ),
    }
    
    # Viewport presets
    VIEWPORTS = {
        'desktop': {'width': 1920, 'height': 1080},
        'laptop': {'width': 1366, 'height': 768},
        'tablet': {'width': 768, 'height': 1024},
        'mobile': {'width': 375, 'height': 667},
    }
    
    # Browser launch arguments
    BROWSER_ARGS = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
    ]
    
    @classmethod
    def get_profile(cls, profile_name: str = 'desktop_chrome') -> Dict[str, Any]:
        """
        Get a complete browser profile configuration.
        
        Args:
            profile_name: Name of the profile (desktop_chrome, mobile_chrome, etc.)
            
        Returns:
            Dictionary with user_agent, viewport, and args
        """
        viewport_type = 'mobile' if 'mobile' in profile_name else 'desktop'
        
        return {
            'user_agent': cls.USER_AGENTS.get(profile_name, cls.USER_AGENTS['desktop_chrome']),
            'viewport': cls.VIEWPORTS[viewport_type],
            'args': cls.BROWSER_ARGS,
        }
    
    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """Get common HTTP headers."""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
