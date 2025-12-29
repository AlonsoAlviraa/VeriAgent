import sys
import os
import shutil
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_engine.main import app, UPLOAD_DIR

client = TestClient(app)

def setup_module(module):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def teardown_module(module):
    # Cleanup uploads after tests
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR)
        os.makedirs(UPLOAD_DIR)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "core_engine"}

def test_upload_file():
    filename = "test_invoice.txt"
    content = b"Simulated invoice content"
    
    files = {"file": (filename, content, "text/plain")}
    response = client.post("/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert data["filename"] == filename
    assert os.path.exists(data["saved_path"])
    
    print("Upload Test Passed: File saved at", data["saved_path"])

if __name__ == "__main__":
    test_health_check()
    test_upload_file()
