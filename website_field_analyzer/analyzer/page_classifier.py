"""
Page Classifier - Infer form purpose and page type.
Implements Steps 11-12: Form purpose and page type detection.
"""

from typing import List
from models.form import Form
from models.page import PageAnalysis
from utils.logger import logger


class PageClassifier:
    """Classifies forms and pages based on patterns."""
    
    @staticmethod
    def classify(url: str, forms: List[Form]) -> PageAnalysis:
        """
        Classify forms and page (Steps 11-12).
        
        Args:
            url: Page URL
            forms: List of Form objects
            
        Returns:
            PageAnalysis object
        """
        # Step 11: Infer form purpose
        PageClassifier._classify_forms(forms)
        
        # Step 12: Infer page type
        page_type = PageClassifier._classify_page(forms)
        
        # Calculate statistics
        total_fields = sum(len(form.fields) for form in forms)
        total_required = sum(
            len(form.get_required_fields()) for form in forms
        )
        
        # Create PageAnalysis
        analysis = PageAnalysis(
            url=url,
            page_type=page_type,
            forms=forms,
            total_fields=total_fields,
            total_required=total_required,
            total_forms=len(forms),
        )
        
        logger.success(f"Page classified as: {page_type}")
        return analysis
    
    @staticmethod
    def _classify_forms(forms: List[Form]):
        """
        Step 11: Infer form purpose.
        
        Patterns:
        - email + password → login
        - email + password + confirm → signup
        - single text input → search
        - multiple dropdowns → listing/filter
        
        Args:
            forms: List of Form objects (modified in-place)
        """
        logger.step(11, "Inferring form purposes")
        
        for form in forms:
            purpose = PageClassifier._detect_form_purpose(form)
            form.form_purpose = purpose
            logger.debug(f"Form {form.form_id} classified as: {purpose}")
    
    @staticmethod
    def _detect_form_purpose(form: Form) -> str:
        """
        Detect purpose of a single form.
        
        Args:
            form: Form object
            
        Returns:
            Purpose string: login, signup, search, listing, mixed, unknown
        """
        visible_fields = form.get_visible_fields()
        field_count = len(visible_fields)
        
        has_email = form.has_email_field()
        has_password = form.has_password_field()
        
        # Count password fields
        password_count = sum(1 for f in visible_fields if f.is_password())
        
        # Login: email/username + password (1 password field)
        if has_password and password_count == 1:
            if has_email or any(
                'username' in (f.name or '').lower() or 
                'user' in (f.name or '').lower()
                for f in visible_fields
            ):
                return 'login'
        
        # Signup: email + multiple passwords (confirm password)
        if has_email and password_count >= 2:
            return 'signup'
        
        # Search: single text input + submit
        if field_count == 1 and visible_fields[0].input_type in ('text', 'search'):
            return 'search'
        
        # Search: has search-related field
        if any(
            'search' in (f.name or '').lower() or
            'search' in (f.placeholder or '').lower() or
            f.input_type == 'search'
            for f in visible_fields
        ):
            return 'search'
        
        # Listing/Filter: multiple selects/dropdowns
        select_count = sum(1 for f in visible_fields if f.tag_name == 'select')
        if select_count >= 2:
            return 'listing'
        
        # Mixed: many different field types
        if field_count > 5:
            return 'mixed'
        
        # Unknown
        return 'unknown'
    
    @staticmethod
    def _classify_page(forms: List[Form]) -> str:
        """
        Step 12: Infer page type based on all forms.
        
        Args:
            forms: List of Form objects
            
        Returns:
            Page type: login, signup, search, listing, mixed, unknown
        """
        logger.step(12, "Inferring page type")
        
        if not forms:
            return 'unknown'
        
        # Count form purposes
        purposes = [form.form_purpose for form in forms]
        unique_purposes = set(purposes)
        
        # Single purpose
        if len(unique_purposes) == 1:
            return purposes[0]
        
        # Multiple forms with different purposes
        if 'login' in purposes and 'search' in purposes:
            return 'mixed'
        
        if 'login' in purposes:
            return 'login'
        
        if 'signup' in purposes:
            return 'signup'
        
        if 'search' in purposes:
            return 'search'
        
        if 'listing' in purposes:
            return 'listing'
        
        return 'mixed'
