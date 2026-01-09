"""
Page model - Page-level analysis structure.
Represents the complete analysis result for a webpage.
"""

from dataclasses import dataclass, asdict, field as dataclass_field
from typing import List, Dict, Any
from datetime import datetime
import json
from .form import Form


@dataclass
class PageAnalysis:
    """Page-level analysis schema (Step 13 output)."""
    
    # URL
    url: str
    
    # Classification
    page_type: str = "unknown"  # login, signup, search, listing, mixed, unknown
    
    # Forms
    forms: List[Form] = dataclass_field(default_factory=list)
    
    # Statistics
    total_fields: int = 0
    total_required: int = 0
    total_forms: int = 0
    
    # Metadata
    notes: List[str] = dataclass_field(default_factory=list)
    timestamp: str = dataclass_field(default_factory=lambda: datetime.now().isoformat())
    
    # Analysis metadata
    analysis_duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert Form objects to dicts
        data['forms'] = [f.to_dict() if isinstance(f, Form) else f for f in self.forms]
        return data
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save_to_file(self, filepath: str):
        """Save analysis to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
    
    def get_all_fields(self) -> List:
        """Get all fields from all forms."""
        all_fields = []
        for form in self.forms:
            all_fields.extend(form.fields)
        return all_fields
    
    def has_login_form(self) -> bool:
        """Check if page has a login form."""
        return any(f.form_purpose == 'login' for f in self.forms)
    
    def has_search_form(self) -> bool:
        """Check if page has a search form."""
        return any(f.form_purpose == 'search' for f in self.forms)
    
    def summary(self) -> str:
        """Get a human-readable summary."""
        return (
            f"Page Analysis Summary\n"
            f"{'='*50}\n"
            f"URL: {self.url}\n"
            f"Page Type: {self.page_type}\n"
            f"Total Forms: {self.total_forms}\n"
            f"Total Fields: {self.total_fields}\n"
            f"Required Fields: {self.total_required}\n"
            f"Analysis Time: {self.analysis_duration_ms:.2f}ms\n"
            f"{'='*50}\n"
        )
    
    def __repr__(self) -> str:
        """String representation."""
        return (
            f"PageAnalysis(url={self.url}, type={self.page_type}, "
            f"forms={len(self.forms)}, fields={self.total_fields})"
        )
