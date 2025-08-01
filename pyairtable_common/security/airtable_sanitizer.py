"""
Airtable Formula Sanitization Module

Provides security utilities to prevent formula injection attacks in Airtable operations.
"""

import re
from typing import List, Optional


class AirtableFormulaInjectionError(Exception):
    """Raised when potentially malicious formula injection is detected."""
    pass


# Allowed Airtable formula functions (whitelist approach)
ALLOWED_FUNCTIONS = {
    # Text functions
    "FIND", "SEARCH", "LEN", "LEFT", "RIGHT", "MID", "LOWER", "UPPER", "TRIM",
    "CONCATENATE", "SUBSTITUTE", "REPLACE", "REPT", "VALUE", "T", "EXACT",
    
    # Logical functions  
    "IF", "AND", "OR", "NOT", "BLANK", "ERROR", "ISERROR", "ISBLANK",
    
    # Math functions
    "ABS", "CEILING", "FLOOR", "INT", "MOD", "POWER", "ROUND", "SQRT",
    "EXP", "LOG", "LOG10", "SUM", "AVERAGE", "MIN", "MAX", "COUNT",
    
    # Date functions
    "NOW", "TODAY", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND",
    "WEEKDAY", "WEEKNUM", "WORKDAY", "DATEADD", "DATEDIF", "DATETIME_DIFF",
    "DATETIME_FORMAT", "DATETIME_PARSE",
    
    # Lookup functions (safe ones)
    "RECORD_ID", "CREATED_TIME", "LAST_MODIFIED_TIME",
}

# Dangerous patterns that should be blocked
DANGEROUS_PATTERNS = [
    # Script injection attempts
    r"<script",
    r"javascript:",
    r"eval\s*\(",
    r"setTimeout\s*\(",
    r"setInterval\s*\(",
    
    # Formula breaking attempts
    r"['\"];.*['\"]",  # Quote breaking
    r"\)\s*;\s*",      # Statement termination
    r"}\s*;\s*",       # Bracket breaking
    
    # Suspicious function patterns
    r"DELETE|DROP|ALTER|CREATE|INSERT|UPDATE",  # SQL-like commands
    r"EXEC|SYSTEM|CMD",  # System commands
    
    # Excessive nesting (potential DoS)
    r"\(\s*\(\s*\(\s*\(\s*\(",  # 5+ nested parentheses
]

# Field name validation pattern
VALID_FIELD_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s_\-\.]{1,100}$')


def sanitize_user_query(query: str) -> str:
    """
    Sanitize user search query for safe use in Airtable formulas.
    
    Args:
        query: User-provided search query
        
    Returns:
        Sanitized query safe for formula injection
        
    Raises:
        AirtableFormulaInjectionError: If malicious content is detected
    """
    if not query or not isinstance(query, str):
        return ""
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, query, re.IGNORECASE):
            raise AirtableFormulaInjectionError(
                f"Potentially malicious pattern detected in query: {pattern}"
            )
    
    # Escape single quotes (primary injection vector)
    sanitized = query.replace("'", "''")
    
    # Remove or escape other special characters
    sanitized = re.sub(r'[{}();]', '', sanitized)  # Remove dangerous chars
    sanitized = sanitized.replace('"', '""')       # Escape double quotes
    
    # Limit length to prevent DoS
    if len(sanitized) > 1000:
        raise AirtableFormulaInjectionError("Query too long (max 1000 characters)")
    
    # Additional validation - no formula function names in user input
    for func in ALLOWED_FUNCTIONS:
        if func in sanitized.upper():
            # If it looks like a function call, be extra careful
            if re.search(rf'{func}\s*\(', sanitized, re.IGNORECASE):
                raise AirtableFormulaInjectionError(
                    f"Function-like pattern detected in user query: {func}"
                )
    
    return sanitized


def sanitize_field_name(field_name: str) -> str:
    """
    Sanitize field name for safe use in Airtable formulas.
    
    Args:
        field_name: Field name to sanitize
        
    Returns:
        Sanitized field name
        
    Raises:
        AirtableFormulaInjectionError: If field name is invalid
    """
    if not field_name or not isinstance(field_name, str):
        raise AirtableFormulaInjectionError("Field name cannot be empty")
    
    # Validate field name pattern
    if not VALID_FIELD_NAME_PATTERN.match(field_name):
        raise AirtableFormulaInjectionError(
            f"Invalid field name format: {field_name}. "
            "Field names must contain only alphanumeric characters, spaces, underscores, hyphens, and dots."
        )
    
    # Additional checks for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, field_name, re.IGNORECASE):
            raise AirtableFormulaInjectionError(
                f"Potentially malicious pattern in field name: {pattern}"
            )
    
    return field_name


def sanitize_airtable_formula(formula: str, allowed_functions: Optional[List[str]] = None) -> str:
    """
    Sanitize a complete Airtable formula for safe execution.
    
    Args:
        formula: Raw formula to sanitize
        allowed_functions: Custom list of allowed functions (uses default if None)
        
    Returns:
        Sanitized formula
        
    Raises:
        AirtableFormulaInjectionError: If formula contains dangerous content
    """
    if not formula or not isinstance(formula, str):
        return ""
    
    allowed_funcs = set(allowed_functions) if allowed_functions else ALLOWED_FUNCTIONS
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, formula, re.IGNORECASE):
            raise AirtableFormulaInjectionError(
                f"Dangerous pattern detected in formula: {pattern}"
            )
    
    # Extract function calls and validate against whitelist
    function_pattern = r'([A-Z_][A-Z0-9_]*)\s*\('
    functions_found = re.findall(function_pattern, formula, re.IGNORECASE)
    
    for func in functions_found:
        if func.upper() not in allowed_funcs:
            raise AirtableFormulaInjectionError(
                f"Disallowed function in formula: {func}"
            )
    
    # Check for excessive complexity (DoS prevention)
    if len(formula) > 5000:
        raise AirtableFormulaInjectionError("Formula too complex (max 5000 characters)")
    
    paren_depth = 0
    max_depth = 0
    for char in formula:
        if char == '(':
            paren_depth += 1
            max_depth = max(max_depth, paren_depth)
        elif char == ')':
            paren_depth -= 1
    
    if max_depth > 10:
        raise AirtableFormulaInjectionError("Formula nesting too deep (max 10 levels)")
    
    return formula


def build_safe_search_formula(query: str, fields: Optional[List[str]] = None) -> str:
    """
    Build a safe search formula using sanitized inputs.
    
    Args:
        query: User search query
        fields: Optional list of specific fields to search
        
    Returns:
        Safe Airtable formula for searching
        
    Raises:
        AirtableFormulaInjectionError: If inputs contain malicious content
    """
    sanitized_query = sanitize_user_query(query)
    
    if not sanitized_query:
        raise AirtableFormulaInjectionError("Search query cannot be empty after sanitization")
    
    if fields:
        # Search in specific fields
        sanitized_fields = [sanitize_field_name(field) for field in fields]
        conditions = []
        
        for field in sanitized_fields:
            # Use safe template with sanitized inputs
            condition = f"FIND(LOWER('{sanitized_query}'), LOWER({{{field}}})) > 0"
            conditions.append(condition)
        
        formula = f"OR({', '.join(conditions)})"
    else:
        # Generic search - more limited but safer
        formula = f"SEARCH(LOWER('{sanitized_query}'), LOWER(CONCATENATE(VALUES())))"
    
    # Final validation of the built formula
    return sanitize_airtable_formula(formula)


def validate_filter_formula(formula: str) -> str:
    """
    Validate and sanitize a user-provided filter formula.
    
    Args:
        formula: User-provided filter formula
        
    Returns:
        Validated and sanitized formula
        
    Raises:
        AirtableFormulaInjectionError: If formula is invalid or dangerous
    """
    return sanitize_airtable_formula(formula)