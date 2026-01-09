"""
Form Detector - Group elements into logical forms.
Implements Steps 8-9: Form grouping and submit detection.
"""

from typing import List, Dict, Optional
from playwright.async_api import Page
from models.field import Field
from models.form import Form
from utils.logger import logger
import hashlib


class FormDetector:
    """Detects and groups fields into logical forms."""
    
    @staticmethod
    async def detect(fields: List[Field], page: Page) -> List[Form]:
        """
        Detect and group fields into forms (Steps 8-9).
        
        Args:
            fields: List of Field objects
            page: Playwright page object
            
        Returns:
            List of Form objects
        """
        # Step 8: Group elements into logical forms
        forms = await FormDetector._group_into_forms(fields, page)
        logger.metric("Forms detected", len(forms))
        
        # Step 9: Identify submit mechanism per form
        await FormDetector._identify_submit_mechanisms(forms, page)
        
        logger.success(f"Form detection complete: {len(forms)} forms")
        return forms
    
    @staticmethod
    async def _group_into_forms(fields: List[Field], page: Page) -> List[Form]:
        """
        Step 8: Group elements into logical forms.
        
        Grouping priority:
        1. Same <form> tag
        2. Same submit button (proximity)
        3. Same container + proximity
        4. Same modal/dialog
        
        Args:
            fields: List of Field objects
            page: Playwright page object
            
        Returns:
            List of Form objects
        """
        logger.step(8, "Grouping elements into logical forms")
        
        # Separate submit buttons from input fields
        input_fields = [f for f in fields if not f.is_submit()]
        submit_buttons = [f for f in fields if f.is_submit()]
        
        # Get form groupings from page
        form_groups = await FormDetector._get_form_groups(page)
        
        forms = []
        assigned_fields = set()
        
        # Priority 1: Group by <form> tag
        for form_selector, form_info in form_groups.items():
            form_fields = []
            
            for field in input_fields:
                if field.parent_container == form_selector or form_selector in field.selector:
                    form_fields.append(field)
                    assigned_fields.add(id(field))
            
            if form_fields:
                form_id = FormDetector._generate_form_id(form_selector)
                forms.append(Form(
                    form_id=form_id,
                    fields=form_fields,
                    container_selector=form_selector,
                    form_tag_selector=form_selector,
                ))
        
        # Priority 2 & 3: Group by proximity and container
        unassigned_fields = [f for f in input_fields if id(f) not in assigned_fields]
        
        if unassigned_fields:
            # Group by parent container
            container_groups: Dict[str, List[Field]] = {}
            
            for field in unassigned_fields:
                container = field.parent_container
                if container not in container_groups:
                    container_groups[container] = []
                container_groups[container].append(field)
            
            # Create forms from container groups
            for container, group_fields in container_groups.items():
                if group_fields:
                    form_id = FormDetector._generate_form_id(container)
                    forms.append(Form(
                        form_id=form_id,
                        fields=group_fields,
                        container_selector=container,
                    ))
        
        # If no forms detected but we have fields, create a default form
        if not forms and input_fields:
            logger.warning("No form structure detected, creating default form")
            forms.append(Form(
                form_id="default_form",
                fields=input_fields,
                container_selector="body",
            ))
        
        return forms
    
    @staticmethod
    async def _get_form_groups(page: Page) -> Dict[str, Dict]:
        """
        Get form elements from page.
        
        Args:
            page: Playwright page object
            
        Returns:
            Dictionary of form selectors and their info
        """
        try:
            form_info = await page.evaluate("""
                () => {
                    const forms = {};
                    const formElements = document.querySelectorAll('form, [role="form"]');
                    
                    formElements.forEach((form, index) => {
                        const selector = form.tagName.toLowerCase() + 
                            (form.id ? '#' + form.id : `.form-${index}`);
                        
                        forms[selector] = {
                            action: form.action || '',
                            method: form.method || 'get',
                            hasSubmit: form.querySelector('button, input[type="submit"]') !== null,
                        };
                    });
                    
                    return forms;
                }
            """)
            return form_info
        except Exception as e:
            logger.debug(f"Failed to get form groups: {e}")
            return {}
    
    @staticmethod
    async def _identify_submit_mechanisms(forms: List[Form], page: Page):
        """
        Step 9: Identify submit mechanism per form.
        
        Args:
            forms: List of Form objects
            page: Playwright page object
        """
        logger.step(9, "Identifying submit mechanisms")
        
        for form in forms:
            # Try to find submit button in form's container
            try:
                submit_info = await page.evaluate(f"""
                    () => {{
                        const container = document.querySelector('{form.container_selector}');
                        if (!container) return null;
                        
                        // Look for submit button
                        const submitBtn = container.querySelector('button[type="submit"], input[type="submit"], button:not([type="button"])');
                        
                        if (submitBtn) {{
                            return {{
                                tag: submitBtn.tagName.toLowerCase(),
                                type: submitBtn.type || 'button',
                                text: submitBtn.textContent?.trim() || submitBtn.value || '',
                                id: submitBtn.id || '',
                                className: submitBtn.className || '',
                            }};
                        }}
                        
                        return null;
                    }}
                """)
                
                if submit_info:
                    form.submit_element = submit_info
                    logger.debug(f"Submit found for {form.form_id}: {submit_info.get('text', 'N/A')}")
                else:
                    logger.debug(f"No submit button found for {form.form_id}")
                    form.notes.append("No explicit submit button found")
                    
            except Exception as e:
                logger.debug(f"Failed to identify submit for {form.form_id}: {e}")
                form.notes.append("Submit detection failed")
    
    @staticmethod
    def _generate_form_id(selector: str) -> str:
        """
        Generate unique form ID from selector.
        
        Args:
            selector: CSS selector
            
        Returns:
            Form ID string
        """
        # Use hash of selector for unique ID
        hash_obj = hashlib.md5(selector.encode())
        return f"form_{hash_obj.hexdigest()[:8]}"
