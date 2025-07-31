"""Airtable-specific models for PyAirtable microservices."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import Field, validator
from .base import BaseModel


class AirtableField(BaseModel):
    """Model for Airtable field definition."""
    
    id: str = Field(..., description="Field ID")
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type")
    description: Optional[str] = Field(None, description="Field description")
    options: Optional[Dict[str, Any]] = Field(None, description="Field-specific options")


class AirtableView(BaseModel):
    """Model for Airtable view definition."""
    
    id: str = Field(..., description="View ID")
    name: str = Field(..., description="View name")
    type: Optional[str] = Field(None, description="View type")


class AirtableTable(BaseModel):
    """Model for Airtable table definition."""
    
    id: str = Field(..., description="Table ID")
    name: str = Field(..., description="Table name")
    description: Optional[str] = Field(None, description="Table description")
    fields: List[AirtableField] = Field(default_factory=list, description="Table fields")
    views: List[AirtableView] = Field(default_factory=list, description="Table views")
    
    @property
    def field_count(self) -> int:
        """Number of fields in the table."""
        return len(self.fields)
    
    @property
    def view_count(self) -> int:
        """Number of views in the table."""
        return len(self.views)
    
    def get_field_by_name(self, name: str) -> Optional[AirtableField]:
        """Get field by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None


class AirtableRecord(BaseModel):
    """Model for Airtable record."""
    
    id: str = Field(..., description="Record ID")
    fields: Dict[str, Any] = Field(..., description="Record fields")
    created_time: Optional[datetime] = Field(None, description="Record creation time")
    
    @validator('id')
    def validate_record_id(cls, v: str) -> str:
        """Validate Airtable record ID format."""
        if not v.startswith('rec') or len(v) != 17:
            raise ValueError('Invalid Airtable record ID format')
        return v
    
    def get_field(self, field_name: str, default: Any = None) -> Any:
        """Get field value by name."""
        return self.fields.get(field_name, default)
    
    def set_field(self, field_name: str, value: Any) -> None:
        """Set field value."""
        self.fields[field_name] = value


class AirtableBase(BaseModel):
    """Model for Airtable base definition."""
    
    id: str = Field(..., description="Base ID")
    name: str = Field(..., description="Base name")
    permission_level: Optional[str] = Field(None, description="User permission level")
    tables: List[AirtableTable] = Field(default_factory=list, description="Base tables")
    
    @validator('id')
    def validate_base_id(cls, v: str) -> str:
        """Validate Airtable base ID format."""
        if not v.startswith('app') or len(v) != 17:
            raise ValueError('Invalid Airtable base ID format')
        return v
    
    @property
    def table_count(self) -> int:
        """Number of tables in the base."""
        return len(self.tables)
    
    @property
    def total_fields(self) -> int:
        """Total number of fields across all tables."""
        return sum(table.field_count for table in self.tables)
    
    def get_table_by_name(self, name: str) -> Optional[AirtableTable]:
        """Get table by name."""
        for table in self.tables:
            if table.name == name:
                return table
        return None
    
    def get_table_by_id(self, table_id: str) -> Optional[AirtableTable]:
        """Get table by ID."""
        for table in self.tables:
            if table.id == table_id:
                return table
        return None


class AirtableRecordList(BaseModel):
    """Model for Airtable record list response."""
    
    records: List[AirtableRecord] = Field(..., description="List of records")
    offset: Optional[str] = Field(None, description="Pagination offset")
    
    @property
    def record_count(self) -> int:
        """Number of records."""
        return len(self.records)
    
    @property
    def has_more(self) -> bool:
        """Whether more records are available."""
        return self.offset is not None


class AirtableBatchOperation(BaseModel):
    """Model for batch operations on Airtable."""
    
    operation_type: str = Field(..., description="Operation type (create, update, delete)")
    records: List[Dict[str, Any]] = Field(..., description="Records to operate on")
    
    @validator('operation_type')
    def validate_operation_type(cls, v: str) -> str:
        """Validate operation type."""
        allowed = {'create', 'update', 'delete'}
        if v not in allowed:
            raise ValueError(f'Operation type must be one of: {allowed}')
        return v