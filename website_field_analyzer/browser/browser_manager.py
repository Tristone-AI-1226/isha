"""
Browser Manager - Launch and manage Playwright browser.
Implements Step 2: Browser launch in read-only mode.
"""

from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from config.settings import Settings
from config.browser_profiles import BrowserProfiles
from utils.logger import logger


class BrowserManager:
    """Manages Playwright browser lifecycle."""
    
    
    def __init__(self, profile_name: str = 'desktop_chrome', headless: Optional[bool] = None,
                 cookies: Optional[List[Dict]] = None, user_agent: Optional[str] = None):
        """
        Initialize browser manager.
        
        Args:
            profile_name: Browser profile to use
            headless: Override headless setting
            cookies: Optional list of cookies to inject
            user_agent: Optional user agent override
        """
        self.profile_name = profile_name
        self.headless = headless if headless is not None else Settings.HEADLESS
        self.profile = BrowserProfiles.get_profile(profile_name)
        
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        self.cookies = cookies
        self.user_agent_override = user_agent
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.launch()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def launch(self) -> Browser:
        """
        Launch browser instance.
        
        Returns:
            Browser instance
        """
        logger.step(2, "Launching browser (read-only mode)")
        
        self.playwright = await async_playwright().start()
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=self.profile['args']
        )
        
        # Create context with profile settings
        self.context = await self.browser.new_context(
            user_agent=self.user_agent_override or self.profile['user_agent'],
            viewport=self.profile['viewport'],
            extra_http_headers=BrowserProfiles.get_headers(),
        )
        
        if self.cookies:
            await self.context.add_cookies(self.cookies)
        
        logger.success(f"Browser launched ({self.profile_name})")
        return self.browser
    
    async def new_page(self) -> Page:
        """
        Create a new page.
        
        Returns:
            Page instance
        """
        if not self.context:
            await self.launch()
        
        self._page = await self.context.new_page()
        return self._page
    
    async def get_page(self) -> Page:
        """
        Get current page or create new one.
        
        Returns:
            Page instance
        """
        if not self._page:
            return await self.new_page()
        return self._page
    
    async def close(self):
        """Close browser and cleanup."""
        logger.step(14, "Cleanup - Closing browser")
        
        if self._page:
            await self._page.close()
        
        if self.context:
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        logger.success("Browser closed")
    
    def is_running(self) -> bool:
        """Check if browser is running."""
        return self.browser is not None and self.browser.is_connected()
