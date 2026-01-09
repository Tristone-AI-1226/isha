"""
Form model - Grouped fields structure.
Represents a logical form with its fields and submit mechanism.
"""

from dataclasses import dataclass, asdict, field as dataclass_field
from typing import List, Optional, Dict, Any
from .field import Field


@dataclass
class Form:
    """Form grouping schema (Step 8 output)."""
    
    # Identification
    form_id: str                              # Generated or from DOM
    
    # Fields
    fields: List[Field] = dataclass_field(default_factory=list)
    
    # Submit mechanism
    submit_element: Optional[Dict[str, Any]] = None  # Button/submit info
    
    # Classification
    form_purpose: str = "unknown"             # login, signup, search, listing, mixed
    
    # DOM reference
    container_selector: str = ""              # Parent container
    form_tag_selector: Optional[str] = None   # If has <form> tag
    
    # Metadata
    has_required_fields: bool = False
    notes: List[str] = dataclass_field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert Field objects to dicts
        data['fields'] = [f.to_dict() if isinstance(f, Field) else f for f in self.fields]
        return data
    
    def get_required_fields(self) -> List[Field]:
        """Get all required fields."""
        return [f for f in self.fields if f.classification == 'required']
    
    def get_optional_fields(self) -> List[Field]:
        """Get all optional fields."""
        return [f for f in self.fields if f.classification == 'optional']
    
    def get_hidden_fields(self) -> List[Field]:
        """Get all hidden fields (tokens, etc.)."""
        return [f for f in self.fields if f.classification == 'hidden']
    
    def get_visible_fields(self) -> List[Field]:
        """Get all visible fields."""
        return [f for f in self.fields if f.visible]
    
    def has_password_field(self) -> bool:
        """Check if form has a password field."""
        return any(f.is_password() for f in self.fields)
    
    def has_email_field(self) -> bool:
        """Check if form has an email field."""
        return any(
            f.input_type == 'email' or 
            'email' in (f.name or '').lower() or
            'email' in (f.id or '').lower()
            for f in self.fields
        )
    
    def field_count(self) -> int:
        """Get total field count."""
        return len(self.fields)
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Form(id={self.form_id}, purpose={self.form_purpose}, "
            f"fields={len(self.fields)}, required={len(self.get_required_fields())})"
        )
