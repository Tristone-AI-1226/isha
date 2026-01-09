"""
Page Loader - Load URL and wait for stabilization.
Implements Step 3: Page load & stabilization.
"""

from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from config.settings import Settings
from utils.wait_utils import WaitUtils
from utils.logger import logger


class PageLoader:
    """Handles page loading and stabilization."""
    
    @staticmethod
    async def load(
        page: Page,
        url: str,
        wait_for_stability: bool = True,
        timeout: Optional[int] = None
    ) -> Page:
        """
        Load URL and wait for page stabilization (Step 3).
        
        Args:
            page: Playwright page object
            url: URL to load (as-is, no modification)
            wait_for_stability: Whether to wait for page stability
            timeout: Optional timeout override
            
        Returns:
            Loaded and stabilized page
        """
        logger.step(1, f"Accepting URL: {url}")
        
        # Validate URL (basic check)
        if not url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL: {url}. Must start with http:// or https://")
        
        logger.step(3, "Loading page and waiting for stabilization")
        
        timeout = timeout or Settings.PAGE_LOAD_TIMEOUT
        
        try:
            # Navigate to URL
            logger.debug(f"Navigating to {url}")
            await page.goto(
                url,
                wait_until='domcontentloaded',
                timeout=timeout
            )
            
            if wait_for_stability:
                # Wait for page to stabilize
                stabilized = await WaitUtils.wait_for_stability(page, timeout)
                
                if not stabilized:
                    logger.warning("Page may not be fully stabilized")
                else:
                    logger.success("Page loaded and stabilized")
            else:
                logger.info("Page loaded (stability wait skipped)")
            
            return page
            
        except PlaywrightTimeoutError as e:
            logger.error(f"Page load timeout: {url}")
            raise TimeoutError(f"Failed to load {url} within {timeout}ms") from e
        
        except Exception as e:
            logger.error(f"Page load failed: {str(e)}")
            raise
    
    @staticmethod
    async def reload(page: Page, wait_for_stability: bool = True) -> Page:
        """
        Reload current page.
        
        Args:
            page: Playwright page object
            wait_for_stability: Whether to wait for stability
            
        Returns:
            Reloaded page
        """
        logger.info("Reloading page")
        
        await page.reload(wait_until='domcontentloaded')
        
        if wait_for_stability:
            await WaitUtils.wait_for_stability(page)
        
        return page
    
    @staticmethod
    async def get_page_info(page: Page) -> dict:
        """
        Get basic page information.
        
        Args:
            page: Playwright page object
            
        Returns:
            Dictionary with page info
        """
        try:
            info = await page.evaluate("""
                () => {
                    return {
                        url: window.location.href,
                        title: document.title,
                        readyState: document.readyState,
                        hasForm: document.querySelector('form') !== null,
                        hasInputs: document.querySelectorAll('input, textarea, select').length > 0,
                    };
                }
            """)
            return info
        except Exception as e:
            logger.error(f"Failed to get page info: {e}")
            return {}
