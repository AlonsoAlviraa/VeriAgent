"""
API integration tests for core_engine.

Actualizados al contrato real de la API (core_engine/main.py v0.3.0):
- /health ahora incluye "version".
- El endpoint de upload es /api/v1/invoices/upload y devuelve file_id (no saved_path).
- Solo se permiten extensiones .pdf/.xml con validación de magic bytes para .pdf.
"""
import sys
import os
import shutil
from fastapi.testclient import TestClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_engine.main import app, UPLOAD_DIR

client = TestClient(app)

ALLOWED_EXTENSIONS = {".pdf", ".xml"}


def setup_module(module):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)


def teardown_module(module):
    # Limpia uploads tras los tests
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR)
        os.makedirs(UPLOAD_DIR)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "core_engine"
    assert "version" in body  # el endpoint expone la versión desde 0.3.0


def test_upload_pdf_file():
    """Upload de un PDF válido (magic bytes %PDF) → 200 con file_id."""
    filename = "test_invoice.pdf"
    content = b"%PDF-1.4 simulated invoice content"
    files = {"file": (filename, content, "application/pdf")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert data["filename"] == filename
    assert data["status"] == "UPLOADED"


def test_upload_xml_file():
    """Upload de un XML válido → 200 con file_id."""
    filename = "facturae.xml"
    content = b"<?xml version='1.0'?><Facturae><x/></Facturae>"
    files = {"file": (filename, content, "application/xml")}
    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert data["filename"] == filename


def test_upload_rejects_disallowed_extension():
    """Extensiones no permitidas (.txt) → 400."""
    files = {"file": ("notallowed.txt", b"plain text", "text/plain")}
    response = client.post("/api/v1/invoices/upload", files=files)
    assert response.status_code == 400


def test_upload_rejects_pdf_with_bad_magic_bytes():
    """Un .pdf sin magic bytes %PDF → 400."""
    files = {"file": ("fake.pdf", b"this is not really a pdf", "application/pdf")}
    response = client.post("/api/v1/invoices/upload", files=files)
    assert response.status_code == 400


def test_upload_missing_file():
    """POST sin archivo → 422 (FastAPI valida File(...))."""
    response = client.post("/api/v1/invoices/upload")
    assert response.status_code == 422


if __name__ == "__main__":
    test_health_check()
    test_upload_pdf_file()
    test_upload_xml_file()
    test_upload_rejects_disallowed_extension()
    test_upload_rejects_pdf_with_bad_magic_bytes()
    test_upload_missing_file()
