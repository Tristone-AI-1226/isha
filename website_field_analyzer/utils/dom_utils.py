"""
DOM analysis utilities.
Helper functions for visibility, proximity, and element analysis.
"""

from typing import Dict, Any, Optional, Tuple
from playwright.async_api import Page, ElementHandle
from config.settings import Settings


class DOMUtils:
    """DOM analysis helper functions."""
    
    @staticmethod
    async def is_visible(element: ElementHandle) -> bool:
        """
        Check if element is visible.
        
        Considers:
        - Display property
        - Visibility property
        - Opacity
        - Dimensions
        
        Args:
            element: Playwright element handle
            
        Returns:
            True if visible, False otherwise
        """
        try:
            is_visible = await element.is_visible()
            if not is_visible:
                return False
            
            # Check bounding box
            box = await element.bounding_box()
            if not box:
                return False
            
            # Check if has meaningful dimensions
            if box['width'] < 1 or box['height'] < 1:
                return False
            
            return True
            
        except Exception:
            return False
    
    @staticmethod
    async def get_element_info(element: ElementHandle) -> Dict[str, Any]:
        """
        Extract comprehensive element information.
        
        Args:
            element: Playwright element handle
            
        Returns:
            Dictionary with element properties
        """
        try:
            info = await element.evaluate("""
                (el) => {
                    const rect = el.getBoundingClientRect();
                    const styles = window.getComputedStyle(el);
                    
                    return {
                        tagName: el.tagName.toLowerCase(),
                        type: el.type || '',
                        name: el.name || '',
                        id: el.id || '',
                        className: el.className || '',
                        placeholder: el.placeholder || '',
                        value: el.value || '',
                        required: el.required || false,
                        disabled: el.disabled || false,
                        readonly: el.readOnly || false,
                        ariaLabel: el.getAttribute('aria-label') || '',
                        autocomplete: el.autocomplete || '',
                        pattern: el.pattern || '',
                        minLength: el.minLength || null,
                        maxLength: el.maxLength || null,
                        role: el.getAttribute('role') || '',
                        onclick: el.onclick !== null,
                        tabindex: el.tabIndex,
                        
                        // Computed styles
                        display: styles.display,
                        visibility: styles.visibility,
                        opacity: styles.opacity,
                        
                        // Position
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        
                        // Content
                        textContent: el.textContent?.trim() || '',
                        innerText: el.innerText?.trim() || '',
                        
                        // Select Options
                        options: el.tagName.toLowerCase() === 'select' ? 
                            Array.from(el.options).map(opt => ({
                                label: opt.text.trim(),
                                value: opt.value,
                                selected: opt.selected
                            })) : null
                    };
                }
            """)
            return info
        except Exception as e:
            return {}
    
    @staticmethod
    async def get_css_selector(element: ElementHandle, page: Page) -> str:
        """
        Generate unique CSS selector for element.
        
        Args:
            element: Playwright element handle
            page: Playwright page object
            
        Returns:
            CSS selector string
        """
        try:
            selector = await page.evaluate("""
                (el) => {
                    // Try ID first
                    if (el.id) {
                        return '#' + el.id;
                    }
                    
                    // Try name
                    if (el.name) {
                        const tag = el.tagName.toLowerCase();
                        return `${tag}[name="${el.name}"]`;
                    }
                    
                    // Build path
                    const path = [];
                    while (el && el.nodeType === Node.ELEMENT_NODE) {
                        let selector = el.tagName.toLowerCase();
                        
                        if (el.className) {
                            const classes = el.className.trim().split(/\\s+/).join('.');
                            selector += '.' + classes;
                        }
                        
                        path.unshift(selector);
                        el = el.parentNode;
                        
                        if (path.length > 5) break; // Limit depth
                    }
                    
                    return path.join(' > ');
                }
            """, element)
            return selector
        except Exception:
            return ""
    
    @staticmethod
    async def get_label_for_input(element: ElementHandle, page: Page) -> Optional[str]:
        """
        Find associated label for an input element.
        
        Args:
            element: Playwright element handle
            page: Playwright page object
            
        Returns:
            Label text if found, None otherwise
        """
        try:
            label_text = await page.evaluate("""
                (el) => {
                    // Check for label with 'for' attribute
                    if (el.id) {
                        const label = document.querySelector(`label[for="${el.id}"]`);
                        if (label) return label.textContent?.trim();
                    }
                    
                    // Check for parent label
                    const parentLabel = el.closest('label');
                    if (parentLabel) return parentLabel.textContent?.trim();
                    
                    // Check for aria-labelledby
                    const labelledBy = el.getAttribute('aria-labelledby');
                    if (labelledBy) {
                        const labelEl = document.getElementById(labelledBy);
                        if (labelEl) return labelEl.textContent?.trim();
                    }
                    
                    return null;
                }
            """, element)
            return label_text
        except Exception:
            return None
    
    @staticmethod
    async def get_proximity(el1: ElementHandle, el2: ElementHandle) -> float:
        """
        Calculate distance between two elements.
        
        Args:
            el1: First element
            el2: Second element
            
        Returns:
            Distance in pixels
        """
        try:
            box1 = await el1.bounding_box()
            box2 = await el2.bounding_box()
            
            if not box1 or not box2:
                return float('inf')
            
            # Calculate center points
            center1_x = box1['x'] + box1['width'] / 2
            center1_y = box1['y'] + box1['height'] / 2
            center2_x = box2['x'] + box2['width'] / 2
            center2_y = box2['y'] + box2['height'] / 2
            
            # Euclidean distance
            distance = ((center2_x - center1_x) ** 2 + (center2_y - center1_y) ** 2) ** 0.5
            return distance
            
        except Exception:
            return float('inf')
    
    @staticmethod
    async def get_parent_container(element: ElementHandle, page: Page) -> str:
        """
        Find logical parent container.
        
        Args:
            element: Playwright element handle
            page: Playwright page object
            
        Returns:
            Container selector
        """
        try:
            container = await page.evaluate("""
                (el) => {
                    // Look for semantic containers
                    const semanticTags = ['form', 'section', 'div[role="form"]', 'dialog', 'aside'];
                    
                    let current = el.parentElement;
                    while (current) {
                        const tag = current.tagName.toLowerCase();
                        const role = current.getAttribute('role');
                        
                        if (tag === 'form' || role === 'form' || role === 'dialog') {
                            return tag + (current.id ? '#' + current.id : '');
                        }
                        
                        current = current.parentElement;
                    }
                    
                    return 'body';
                }
            """, element)
            return container
        except Exception:
            return "body"
    
    @staticmethod
    async def is_in_same_modal(el1: ElementHandle, el2: ElementHandle, page: Page) -> bool:
        """
        Check if two elements are in the same modal/dialog.
        
        Args:
            el1: First element
            el2: Second element
            page: Playwright page object
            
        Returns:
            True if in same modal, False otherwise
        """
        try:
            result = await page.evaluate("""
                ([el1, el2]) => {
                    const findModal = (el) => {
                        let current = el;
                        while (current) {
                            const role = current.getAttribute('role');
                            const ariaModal = current.getAttribute('aria-modal');
                            
                            if (role === 'dialog' || ariaModal === 'true') {
                                return current;
                            }
                            
                            current = current.parentElement;
                        }
                        return null;
                    };
                    
                    const modal1 = findModal(el1);
                    const modal2 = findModal(el2);
                    
                    // Both in same modal or both not in modal
                    return modal1 === modal2;
                }
            """, [el1, el2])
            return result
        except Exception:
            return False
