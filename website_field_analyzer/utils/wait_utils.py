"""
Smart waiting strategies for page stabilization.
Implements Step 3: Wait for DOM, JS, and network to stabilize.
"""

import asyncio
from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from config.settings import Settings
from utils.logger import logger


class WaitUtils:
    """Smart wait utilities for page stabilization."""
    
    @staticmethod
    async def wait_for_stability(page: Page, timeout: Optional[int] = None) -> bool:
        """
        Wait for page to stabilize (Step 3).
        
        Waits for:
        1. DOM to load
        2. Network to become idle
        3. JS execution to finish
        
        Args:
            page: Playwright page object
            timeout: Optional timeout in ms
            
        Returns:
            True if page stabilized, False if timeout
        """
        timeout = timeout or Settings.PAGE_LOAD_TIMEOUT
        
        try:
            # Wait for network idle
            logger.debug("Waiting for network idle...")
            await page.wait_for_load_state('networkidle', timeout=timeout)
            
            # Additional buffer for JS frameworks (React, Vue, etc.)
            logger.debug(f"Waiting {Settings.JS_EXECUTION_BUFFER}ms for JS execution...")
            await asyncio.sleep(Settings.JS_EXECUTION_BUFFER / 1000)
            
            # Wait for any pending DOM mutations
            await WaitUtils.wait_for_dom_mutations(page)
            
            logger.success("Page stabilized")
            return True
            
        except PlaywrightTimeoutError:
            logger.warning(f"Page stabilization timeout after {timeout}ms")
            return False
    
    @staticmethod
    async def wait_for_network_idle(
        page: Page, 
        timeout: Optional[int] = None,
        idle_time: Optional[int] = None
    ) -> bool:
        """
        Wait for network to become idle.
        
        Args:
            page: Playwright page object
            timeout: Total timeout in ms
            idle_time: Time to consider network idle in ms
            
        Returns:
            True if network became idle, False if timeout
        """
        timeout = timeout or Settings.PAGE_LOAD_TIMEOUT
        idle_time = idle_time or Settings.NETWORK_IDLE_TIMEOUT
        
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            logger.warning(f"Network idle timeout after {timeout}ms")
            return False
    
    @staticmethod
    async def wait_for_dom_mutations(page: Page, max_wait: int = 2000) -> bool:
        """
        Wait for DOM mutations to settle.
        
        Uses MutationObserver to detect when DOM stops changing.
        
        Args:
            page: Playwright page object
            max_wait: Maximum time to wait in ms
            
        Returns:
            True if DOM settled, False if timeout
        """
        try:
            # Inject mutation observer
            await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        let timeout;
                        const observer = new MutationObserver(() => {
                            clearTimeout(timeout);
                            timeout = setTimeout(() => {
                                observer.disconnect();
                                resolve(true);
                            }, 500); // 500ms of no mutations = settled
                        });
                        
                        observer.observe(document.body, {
                            childList: true,
                            subtree: true,
                            attributes: true
                        });
                        
                        // Initial timeout
                        timeout = setTimeout(() => {
                            observer.disconnect();
                            resolve(true);
                        }, 500);
                    });
                }
            """)
            return True
        except Exception as e:
            logger.debug(f"DOM mutation wait failed: {e}")
            return False
    
    @staticmethod
    async def wait_with_timeout(
        condition_func,
        timeout: int = 5000,
        interval: int = 100
    ) -> bool:
        """
        Generic wait with timeout.
        
        Args:
            condition_func: Async function that returns True when condition met
            timeout: Timeout in ms
            interval: Check interval in ms
            
        Returns:
            True if condition met, False if timeout
        """
        elapsed = 0
        while elapsed < timeout:
            try:
                if await condition_func():
                    return True
            except Exception:
                pass
            
            await asyncio.sleep(interval / 1000)
            elapsed += interval
        
        return False
    
    @staticmethod
    async def wait_for_selector(
        page: Page,
        selector: str,
        timeout: int = 5000,
        state: str = 'visible'
    ) -> bool:
        """
        Wait for a selector to appear.
        
        Args:
            page: Playwright page object
            selector: CSS selector
            timeout: Timeout in ms
            state: Element state (visible, attached, hidden)
            
        Returns:
            True if element found, False if timeout
        """
        try:
            await page.wait_for_selector(selector, timeout=timeout, state=state)
            return True
        except PlaywrightTimeoutError:
            return False
