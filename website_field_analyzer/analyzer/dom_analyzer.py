"""
DOM Analyzer - Extract, normalize, and filter elements.
Implements Steps 4-7: Snapshot, Extract, Normalize, Filter.
"""

from typing import List, Dict, Any
from playwright.async_api import Page, ElementHandle
from models.field import Field
from config.settings import Settings
from utils.dom_utils import DOMUtils
from utils.logger import logger


class DOMAnalyzer:
    """Analyzes DOM and extracts interactive elements."""
    
    @staticmethod
    async def analyze(page: Page) -> List[Field]:
        """
        Complete DOM analysis pipeline (Steps 4-7).
        
        Args:
            page: Playwright page object
            
        Returns:
            List of normalized and filtered Field objects
        """
        # Step 4: Capture DOM snapshot
        logger.step(4, "Capturing DOM snapshot")
        # (Implicit - page is already loaded and stabilized)
        
        # Step 5: Extract interactive elements
        elements = await DOMAnalyzer._extract_elements(page)
        logger.metric("Elements extracted", len(elements))
        
        # Step 6: Normalize elements
        fields = await DOMAnalyzer._normalize_elements(elements, page)
        logger.metric("Fields normalized", len(fields))
        
        # Step 7: Filter irrelevant elements
        filtered_fields = DOMAnalyzer._filter_elements(fields)
        logger.metric("Fields after filtering", len(filtered_fields))
        
        logger.success(f"DOM analysis complete: {len(filtered_fields)} fields")
        return filtered_fields
    
    @staticmethod
    async def _extract_elements(page: Page) -> List[ElementHandle]:
        """
        Step 5: Extract ALL interactive elements.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of element handles
        """
        logger.step(5, "Extracting interactive elements")
        
        # Query for all interactive elements
        elements = await page.query_selector_all("""
            input,
            textarea,
            select,
            button,
            [contenteditable="true"],
            [role="button"],
            [role="textbox"],
            [onclick],
            [type="submit"]
        """)
        
        logger.debug(f"Found {len(elements)} interactive elements")
        return elements
    
    @staticmethod
    async def _normalize_elements(elements: List[ElementHandle], page: Page) -> List[Field]:
        """
        Step 6: Normalize each element to Field object.
        
        Args:
            elements: List of element handles
            page: Playwright page object
            
        Returns:
            List of Field objects
        """
        logger.step(6, "Normalizing elements to Field objects")
        
        fields = []
        
        for element in elements:
            try:
                # Get comprehensive element info
                info = await DOMUtils.get_element_info(element)
                
                if not info:
                    continue
                
                # Check visibility
                is_visible = await DOMUtils.is_visible(element)
                
                # Get CSS selector
                selector = await DOMUtils.get_css_selector(element, page)
                
                # Get label
                label_text = await DOMUtils.get_label_for_input(element, page)
                
                # Get parent container
                parent_container = await DOMUtils.get_parent_container(element, page)
                
                # Create Field object
                field = Field(
                    tag_name=info.get('tagName', ''),
                    input_type=info.get('type', info.get('tagName', '')),
                    name=info.get('name') or None,
                    id=info.get('id') or None,
                    placeholder=info.get('placeholder') or None,
                    aria_label=info.get('ariaLabel') or None,
                    label_text=label_text,
                    required=info.get('required', False),
                    disabled=info.get('disabled', False),
                    readonly=info.get('readonly', False),
                    visible=is_visible,
                    selector=selector,
                    parent_container=parent_container,
                    value=info.get('value') or None,
                    options=info.get('options') or None,
                    autocomplete=info.get('autocomplete') or None,
                    pattern=info.get('pattern') or None,
                    min_length=info.get('minLength'),
                    max_length=info.get('maxLength'),
                )
                
                fields.append(field)
                
            except Exception as e:
                logger.debug(f"Failed to normalize element: {e}")
                continue
        
        return fields
    
    @staticmethod
    def _filter_elements(fields: List[Field]) -> List[Field]:
        """
        Step 7: Filter irrelevant elements.
        
        Removes:
        - Disabled elements
        - Decorative elements
        - Analytics/tracking inputs
        
        Keeps:
        - Hidden tokens (CSRF, session)
        - All visible interactive elements
        
        Args:
            fields: List of Field objects
            
        Returns:
            Filtered list of Field objects
        """
        logger.step(7, "Filtering irrelevant elements")
        
        filtered = []
        
        for field in fields:
            # Remove disabled elements
            if field.disabled:
                logger.debug(f"Filtered (disabled): {field.get_label()}")
                continue
            
            # Check if it's a tracking/analytics field
            if DOMAnalyzer._is_tracking_field(field):
                logger.debug(f"Filtered (tracking): {field.get_label()}")
                continue
            
            # Keep hidden tokens (CSRF, session, etc.)
            if field.input_type == 'hidden':
                if DOMAnalyzer._is_important_hidden_field(field):
                    logger.debug(f"Kept (hidden token): {field.get_label()}")
                    filtered.append(field)
                else:
                    logger.debug(f"Filtered (hidden non-token): {field.get_label()}")
                continue
            
            # Keep all other visible interactive elements
            filtered.append(field)
        
        return filtered
    
    @staticmethod
    def _is_tracking_field(field: Field) -> bool:
        """
        Check if field is for analytics/tracking.
        
        Args:
            field: Field object
            
        Returns:
            True if tracking field, False otherwise
        """
        name_lower = (field.name or '').lower()
        id_lower = (field.id or '').lower()
        
        for pattern in Settings.REMOVE_TRACKING_PATTERNS:
            if pattern in name_lower or pattern in id_lower:
                return True
        
        return False
    
    @staticmethod
    def _is_important_hidden_field(field: Field) -> bool:
        """
        Check if hidden field is important (CSRF, session, etc.).
        
        Args:
            field: Field object
            
        Returns:
            True if important, False otherwise
        """
        name_lower = (field.name or '').lower()
        id_lower = (field.id or '').lower()
        
        for pattern in Settings.KEEP_HIDDEN_PATTERNS:
            if pattern in name_lower or pattern in id_lower:
                return True
        
        return False
