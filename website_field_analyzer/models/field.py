"""
Field model - Normalized element structure.
Represents a single interactive element on the page.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List


@dataclass
class Field:
    """Normalized field schema (Step 6 output)."""
    
    # Basic properties
    tag_name: str                    # input, textarea, select, etc.
    input_type: str                  # text, password, hidden, etc.
    
    # Identifiers
    name: Optional[str] = None
    id: Optional[str] = None
    
    # Labels and hints
    placeholder: Optional[str] = None
    aria_label: Optional[str] = None
    label_text: Optional[str] = None
    
    # Attributes
    required: bool = False
    disabled: bool = False
    readonly: bool = False
    
    # Visibility
    visible: bool = True
    
    # DOM reference
    selector: str = ""               # CSS selector
    xpath: str = ""                  # XPath (alternative)
    parent_container: str = ""       # Parent element reference
    
    # Classification
    classification: str = "unknown"  # required/optional/hidden
    
    # Value (for hidden fields, defaults, etc.)
    value: Optional[str] = None
    
    # Select options (label/value pairs)
    options: Optional[List[Dict[str, str]]] = None
    
    # Additional metadata
    autocomplete: Optional[str] = None
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def is_password(self) -> bool:
        """Check if this is a password field."""
        return self.input_type == 'password'
    
    def is_hidden(self) -> bool:
        """Check if this is a hidden field."""
        return self.input_type == 'hidden' or not self.visible
    
    def is_submit(self) -> bool:
        """Check if this is a submit button."""
        return self.input_type == 'submit' or self.tag_name == 'button'
    
    def get_label(self) -> str:
        """Get the best available label for this field."""
        return (
            self.label_text or 
            self.placeholder or 
            self.aria_label or 
            self.name or 
            self.id or 
            f"{self.tag_name}[{self.input_type}]"
        )
    
    def __repr__(self) -> str:
        """String representation."""
        label = self.get_label()
        return f"Field({self.tag_name}[{self.input_type}] - {label})"
