import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

# Mock heavy dependencies
sys.modules['faiss'] = MagicMock()
sys.modules['scipy'] = MagicMock()
sys.modules['scipy.optimize'] = MagicMock()

from backend.utils.execution_trace import create_trace, AgentExecutionTrace

def test_trace_metadata_migration():
    """
    Assert that AgentExecutionTrace stores information in system_audit,
    bypassing the missing metadata attribute.
    """
    trace = create_trace("test_sess", "tr_123")
    
    # Simulate mixed query detection
    query_segments = {"scientific": "sodium", "nutritional": "chicken"}
    trace.system_audit["is_mixed_query"] = True
    trace.system_audit["query_segments"] = query_segments
    
    assert trace.system_audit["is_mixed_query"] is True
    assert trace.system_audit["query_segments"] == query_segments
    
    # Ensure it converts to dict correctly and contains the fields
    trace_dict = trace.to_dict()
    assert trace_dict["system_audit"]["is_mixed_query"] is True
    assert trace_dict["system_audit"]["query_segments"] == query_segments

def test_schema_validates_metadata_in_audit():
    """
    Verify that adding fields to system_audit doesn't break schema validation.
    """
    trace = create_trace("test_sess", "tr_456")
    trace.system_audit["is_mixed_query"] = True
    trace.system_audit["query_segments"] = {"scientific": "potassium"}
    
    # to_dict calls _validate_contract internally in v1.2.8
    try:
        trace.to_dict()
        valid = True
    except Exception as e:
        print(f"Validation failed: {e}")
        valid = False
        
    assert valid, "Schema discovery failed for system_audit expansion"
