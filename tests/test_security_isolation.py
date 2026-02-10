import pytest
from unittest.mock import MagicMock
import sys

# Mock heavy dependencies before they are imported
sys.modules["faiss"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["ollama"] = MagicMock()
sys.modules["psutil"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["torch"] = MagicMock()

# IMPORTANT: Mock the Orchestrator to avoid loading the entire AI stack
mock_orch_module = MagicMock()
sys.modules["backend.orchestrator"] = mock_orch_module

from fastapi.testclient import TestClient
from backend.server import app, memory_store
import uuid

client = TestClient(app)

def test_user_isolation():
    # Setup: Two distinct users
    user_a = "user_a_" + uuid.uuid4().hex
    user_b = "user_b_" + uuid.uuid4().hex
    
    # 1. User A creates a session (implicitly via chat for lazy creation, or explicitly)
    # Let's try explicit creation first to get an ID easily, reusing existing logic
    resp_a = client.post("/api/conversation", headers={"X-User-Id": user_a})
    assert resp_a.status_code == 200
    session_a = resp_a.json()["session_id"]
    
    # 2. User B tries to access User A's session
    resp_b_access = client.get(f"/api/conversation?session_id={session_a}", headers={"X-User-Id": user_b})
    assert resp_b_access.status_code == 403
    
    # 3. User B tries to list conversations - should NOT see User A's session
    resp_b_list = client.get("/api/conversations", headers={"X-User-Id": user_b})
    assert resp_b_list.status_code == 200
    conversations_b = resp_b_list.json()["conversations"]
    assert not any(c["session_id"] == session_a for c in conversations_b)
    
    # 4. User A accesses their own session -> OK
    resp_a_access = client.get(f"/api/conversation?session_id={session_a}", headers={"X-User-Id": user_a})
    assert resp_a_access.status_code == 200
    assert resp_a_access.json()["session_id"] == session_a

def test_lazy_creation_claim():
    # Setup: User creates a random ID client-side and sends a message
    user_c = "user_c_" + uuid.uuid4().hex
    random_session_id = f"sess_lazy_{uuid.uuid4().hex}"
    
    # 1. Send message to NON-EXISTENT session
    # Using ensure_session logic in server.py
    resp = client.post(
        "/api/chat",
        headers={"X-User-Id": user_c},
        json={
            "message": "Hello Lazy World",
            "session_id": random_session_id,
            "preferences": {}
        }
    )
    
    # Expectation: 200 OK (Created and claimed)
    # Note: If ensure_session works, it creates the session.
    # If it fails, it returns 403.
    assert resp.status_code == 200
    
    # 2. Verify ownership
    assert memory_store.check_ownership(random_session_id, user_c) == True
    
    # 3. Verify User D cannot access it
    user_d = "user_d_" + uuid.uuid4().hex
    assert memory_store.check_ownership(random_session_id, user_d) == False
