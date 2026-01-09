"""
Field Classifier - Classify fields as required/optional.
Implements Step 10: Required vs Optional classification.
"""

from typing import List
from models.form import Form
from models.field import Field
from config.settings import Settings
from utils.logger import logger


class FieldClassifier:
    """Classifies fields as required, optional, or hidden."""
    
    @staticmethod
    def classify(forms: List[Form]):
        """
        Classify all fields in all forms (Step 10).
        
        Args:
            forms: List of Form objects (modified in-place)
        """
        logger.step(10, "Classifying fields (required/optional/hidden)")
        
        total_required = 0
        total_optional = 0
        total_hidden = 0
        
        for form in forms:
            for field in form.fields:
                classification = FieldClassifier._classify_field(field)
                field.classification = classification
                
                if classification == 'required':
                    total_required += 1
                elif classification == 'optional':
                    total_optional += 1
                elif classification == 'hidden':
                    total_hidden += 1
            
            # Update form metadata
            form.has_required_fields = any(
                f.classification == 'required' for f in form.fields
            )
        
        logger.metric("Required fields", total_required)
        logger.metric("Optional fields", total_optional)
        logger.metric("Hidden fields", total_hidden)
        logger.success("Field classification complete")
    
    @staticmethod
    def _classify_field(field: Field) -> str:
        """
        Classify a single field.
        
        Classification rules:
        - Required if: has 'required' attribute, is password, matches required patterns
        - Hidden if: type is hidden, not visible
        - Optional: everything else
        
        Args:
            field: Field object
            
        Returns:
            Classification string: 'required', 'optional', or 'hidden'
        """
        # Hidden fields (tokens, etc.)
        if field.input_type == 'hidden' or not field.visible:
            return 'hidden'
        
        # Explicit required attribute
        if field.required:
            return 'required'
        
        # Password fields are always required
        if field.is_password():
            return 'required'
        
        # Check name/id against required patterns
        name_lower = (field.name or '').lower()
        id_lower = (field.id or '').lower()
        label_lower = (field.get_label() or '').lower()
        
        for pattern in Settings.REQUIRED_FIELD_PATTERNS:
            if (pattern in name_lower or 
                pattern in id_lower or 
                pattern in label_lower):
                return 'required'
        
        # Email type is usually required
        if field.input_type == 'email':
            return 'required'
        
        # Checkboxes and radios are usually optional
        if field.input_type in ('checkbox', 'radio'):
            return 'optional'
        
        # Select dropdowns - context dependent
        if field.tag_name == 'select':
            # If it looks like a filter, it's optional
            if any(word in label_lower for word in ['filter', 'sort', 'category', 'type']):
                return 'optional'
            # Otherwise, could be required
            return 'optional'  # Default to optional for selects
        
        # Text inputs - check for hints in placeholder
        if field.placeholder:
            placeholder_lower = field.placeholder.lower()
            if 'optional' in placeholder_lower:
                return 'optional'
            if 'required' in placeholder_lower or '*' in field.placeholder:
                return 'required'
        
        # Default: optional
        return 'optional'
