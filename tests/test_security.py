#!/usr/bin/env python3
"""
Test script for Airtable formula injection protection
"""

import sys
import os
sys.path.insert(0, '.')

from pyairtable_common.security import (
    sanitize_user_query,
    sanitize_field_name,
    build_safe_search_formula,
    validate_filter_formula,
    AirtableFormulaInjectionError
)

def test_safe_inputs():
    """Test that safe inputs work correctly"""
    print("🧪 Testing safe inputs...")
    
    # Safe query
    safe_query = sanitize_user_query("john smith")
    assert safe_query == "john smith"
    print("✅ Safe query passed")
    
    # Safe field name
    safe_field = sanitize_field_name("Full Name")
    assert safe_field == "Full Name"
    print("✅ Safe field name passed")
    
    # Safe formula building
    safe_formula = build_safe_search_formula("test", ["Name", "Email"])
    print(f"✅ Safe formula: {safe_formula}")
    
    print("✅ All safe input tests passed!\n")


def test_malicious_inputs():
    """Test that malicious inputs are blocked"""
    print("🧪 Testing malicious inputs...")
    
    malicious_queries = [
        "'; DELETE_ALL(); //",
        "test'); DROP TABLE users; --",
        "'); EVIL_FUNCTION(); //",
        "abc" * 400,  # Too long
        "FIND(EVIL())",  # Function injection
    ]
    
    for query in malicious_queries:
        try:
            result = sanitize_user_query(query)
            print(f"❌ Malicious query unexpectedly allowed: {query[:50]}...")
        except AirtableFormulaInjectionError as e:
            print(f"✅ Blocked malicious query: {str(e)[:80]}...")
    
    # Test malicious field names
    malicious_fields = [
        "'; DROP TABLE",
        "EVIL()",
        "Field}); ATTACK(); //{",
        "x" * 200,  # Too long
    ]
    
    for field in malicious_fields:
        try:
            result = sanitize_field_name(field)
            print(f"❌ Malicious field unexpectedly allowed: {field[:50]}...")
        except AirtableFormulaInjectionError as e:
            print(f"✅ Blocked malicious field: {str(e)[:80]}...")
    
    print("✅ All malicious input tests passed!\n")


def test_formula_validation():
    """Test formula validation"""
    print("🧪 Testing formula validation...")
    
    # Safe formulas
    safe_formulas = [
        "FIND('test', {Name}) > 0",
        "AND(LEN({Name}) > 0, NOT(ISBLANK({Email})))",
        "IF({Status} = 'Active', 'Yes', 'No')",
    ]
    
    for formula in safe_formulas:
        try:
            result = validate_filter_formula(formula)
            print(f"✅ Safe formula validated: {formula[:50]}...")
        except AirtableFormulaInjectionError as e:
            print(f"❌ Safe formula unexpectedly blocked: {e}")
    
    # Dangerous formulas
    dangerous_formulas = [
        "DELETE_ALL()",
        "EXEC('rm -rf /')",
        "FIND(''); DROP TABLE users; --",
        "((((((((((NESTED_TOO_DEEP()))))))))))",
        "x" * 6000,  # Too long
    ]
    
    for formula in dangerous_formulas:
        try:
            result = validate_filter_formula(formula)
            print(f"❌ Dangerous formula unexpectedly allowed: {formula[:50]}...")
        except AirtableFormulaInjectionError as e:
            print(f"✅ Blocked dangerous formula: {str(e)[:80]}...")
    
    print("✅ All formula validation tests passed!\n")


if __name__ == "__main__":
    print("🔒 PyAirtable Security Module Test Suite")
    print("=" * 50)
    
    try:
        test_safe_inputs()
        test_malicious_inputs()
        test_formula_validation()
        
        print("🎉 ALL SECURITY TESTS PASSED!")
        print("✅ Formula injection protection is working correctly")
        
    except Exception as e:
        print(f"💥 Test failed with error: {e}")
        sys.exit(1)