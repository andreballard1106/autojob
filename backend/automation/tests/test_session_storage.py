import pytest
import tempfile
import shutil
from pathlib import Path

from automation.session_storage import (
    SessionStorage,
    ApplicationSession,
    PageSnapshot,
    AutofillResult,
)


@pytest.fixture
def temp_storage_dir():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def storage(temp_storage_dir):
    return SessionStorage(storage_dir=temp_storage_dir)


class TestPageSnapshot:
    def test_create_snapshot(self):
        snapshot = PageSnapshot(
            url="https://example.com/apply",
            title="Job Application",
            filtered_html="<form>...</form>",
            inputs=[{"id": "name", "type": "text"}],
            buttons=[{"id": "submit", "text": "Submit"}],
            forms=[{"id": "form1"}],
        )
        
        assert snapshot.url == "https://example.com/apply"
        assert len(snapshot.inputs) == 1
        assert snapshot.page_number == 1
    
    def test_to_dict(self):
        snapshot = PageSnapshot(
            url="https://test.com",
            title="Test",
            filtered_html="<p>test</p>",
            inputs=[],
            buttons=[],
            forms=[],
        )
        
        data = snapshot.to_dict()
        
        assert data["url"] == "https://test.com"
        assert "timestamp" in data
    
    def test_from_dict(self):
        data = {
            "url": "https://test.com",
            "title": "Test",
            "filtered_html": "<p>test</p>",
            "inputs": [{"id": "test"}],
            "buttons": [],
            "forms": [],
            "timestamp": "2024-01-01T00:00:00",
            "page_number": 2,
        }
        
        snapshot = PageSnapshot.from_dict(data)
        
        assert snapshot.url == "https://test.com"
        assert snapshot.page_number == 2


class TestApplicationSession:
    def test_create_session(self):
        session = ApplicationSession(
            job_id="job-123",
            profile_id="profile-456",
            url="https://example.com",
        )
        
        assert session.job_id == "job-123"
        assert session.status == "active"
        assert session.current_page == 1
    
    def test_add_page_snapshot(self):
        session = ApplicationSession(
            job_id="job-123",
            profile_id="profile-456",
            url="https://example.com",
        )
        
        snapshot = PageSnapshot(
            url="https://example.com/page1",
            title="Page 1",
            filtered_html="",
            inputs=[],
            buttons=[],
            forms=[],
        )
        
        session.add_page_snapshot(snapshot)
        
        assert len(session.page_snapshots) == 1
        assert session.current_page == 1
        assert session.page_snapshots[0].page_number == 1
    
    def test_add_autofill_result(self):
        session = ApplicationSession(
            job_id="job-123",
            profile_id="profile-456",
            url="https://example.com",
        )
        
        result = AutofillResult(
            field_name="Email",
            selector="#email",
            action="type_text",
            value="test@example.com",
            success=True,
        )
        
        session.add_autofill_result(result)
        
        assert len(session.autofill_results) == 1
    
    def test_add_navigation(self):
        session = ApplicationSession(
            job_id="job-123",
            profile_id="profile-456",
            url="https://example.com",
        )
        
        session.add_navigation("https://example.com/step2")
        
        assert "https://example.com/step2" in session.navigation_history
    
    def test_to_dict(self):
        session = ApplicationSession(
            job_id="job-123",
            profile_id="profile-456",
            url="https://example.com",
        )
        
        data = session.to_dict()
        
        assert data["job_id"] == "job-123"
        assert data["status"] == "active"
    
    def test_from_dict(self):
        data = {
            "job_id": "job-123",
            "profile_id": "profile-456",
            "url": "https://example.com",
            "status": "completed",
            "current_page": 3,
            "page_snapshots": [],
            "autofill_results": [],
            "navigation_history": ["https://example.com"],
        }
        
        session = ApplicationSession.from_dict(data)
        
        assert session.job_id == "job-123"
        assert session.status == "completed"
        assert session.current_page == 3


class TestSessionStorage:
    def test_create_session(self, storage):
        session = storage.create_session(
            job_id="job-123",
            profile_id="profile-456",
            url="https://example.com",
        )
        
        assert session.job_id == "job-123"
        assert len(session.navigation_history) == 1
    
    def test_get_session(self, storage):
        storage.create_session("job-123", "profile-456", "https://example.com")
        
        session = storage.get_session("job-123")
        
        assert session is not None
        assert session.job_id == "job-123"
    
    def test_get_session_not_found(self, storage):
        session = storage.get_session("nonexistent")
        
        assert session is None
    
    def test_update_session(self, storage):
        session = storage.create_session("job-123", "profile-456", "https://example.com")
        
        session.status = "completed"
        storage.update_session(session)
        
        loaded = storage.get_session("job-123")
        assert loaded.status == "completed"
    
    def test_add_page_snapshot(self, storage):
        storage.create_session("job-123", "profile-456", "https://example.com")
        
        snapshot = storage.add_page_snapshot("job-123", {
            "url": "https://example.com/form",
            "title": "Form Page",
            "filtered_html": "<form></form>",
            "inputs": [{"id": "name"}],
            "buttons": [],
            "forms": [],
        })
        
        assert snapshot is not None
        
        session = storage.get_session("job-123")
        assert len(session.page_snapshots) == 1
    
    def test_add_autofill_results(self, storage):
        storage.create_session("job-123", "profile-456", "https://example.com")
        
        storage.add_autofill_results("job-123", [
            {"field_name": "Name", "selector": "#name", "action": "type_text", "value": "John", "success": True},
            {"field_name": "Email", "selector": "#email", "action": "type_text", "value": "john@test.com", "success": True},
        ])
        
        session = storage.get_session("job-123")
        assert len(session.autofill_results) == 2
    
    def test_set_session_status(self, storage):
        storage.create_session("job-123", "profile-456", "https://example.com")
        
        storage.set_session_status("job-123", "error", "Something went wrong")
        
        session = storage.get_session("job-123")
        assert session.status == "error"
        assert session.error_message == "Something went wrong"
    
    def test_delete_session(self, storage):
        storage.create_session("job-123", "profile-456", "https://example.com")
        
        result = storage.delete_session("job-123")
        
        assert result == True
        assert storage.get_session("job-123") is None
    
    def test_get_all_active_sessions(self, storage):
        storage.create_session("job-1", "profile-1", "https://example.com/1")
        storage.create_session("job-2", "profile-1", "https://example.com/2")
        
        storage.set_session_status("job-2", "completed")
        
        active = storage.get_all_active_sessions()
        
        assert len(active) == 1
        assert active[0].job_id == "job-1"
    
    def test_persistence(self, storage):
        storage.create_session("job-123", "profile-456", "https://example.com")
        
        storage._sessions.clear()
        
        session = storage.get_session("job-123")
        
        assert session is not None
        assert session.job_id == "job-123"

