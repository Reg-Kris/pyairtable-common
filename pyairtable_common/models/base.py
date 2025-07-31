"""Base model classes for PyAirtable."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel as PydanticBaseModel, Field


class BaseModel(PydanticBaseModel):
    """Base model class with common configuration."""
    
    class Config:
        # Use enum values instead of enum objects in JSON
        use_enum_values = True
        # Allow population by field name and alias
        populate_by_name = True
        # Validate default values
        validate_default = True
        # Strict mode for better validation
        str_strip_whitespace = True


class TimestampedModel(BaseModel):
    """Base model with automatic timestamps."""
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()