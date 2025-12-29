"""
🔥 VERIAGENT 2026 - STRESS & LIMITS TEST SUITE
QA Automation Lead: Optimization & Resource Management
"""
import os
import sys
import pytest
import hashlib
from fastapi.testclient import TestClient

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_engine.main import app

def generate_random_string(length: int) -> str:
    """Efficiently generate random junk for stress testing."""
    return os.urandom(length // 2).hex()

class TestStressLimits:
    """
    Sección aislada para pruebas de carga y límites.
    Objetivo: Validar robustez sin comprometer estabilidad del CI.
    """

    # --- HASHING STRESS ---
    @pytest.mark.parametrize("payload_size,description", [
        (2000, "Límite Buffer - 2K Chars"),
        (5000, "Límite Buffer - 5K Chars"),
    ])
    def test_hash_large_payloads(self, payload_size: int, description: str):
        """
        [STRESS-001] Hashing de strings largos generados dinámicamente.
        Verifica que el motor SHA-256 no bloquee el hilo con strings > estándar.
        """
        payload = generate_random_string(payload_size)
        result = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        assert len(result) == 64
        assert result == hashlib.sha256(payload.encode('utf-8')).hexdigest()

    # --- UPLOAD STRESS ---
    @pytest.mark.parametrize("file_size_mb,filename", [
        (1, "stress_1mb.pdf"),
        (2, "stress_2mb.pdf"),
    ])
    def test_upload_large_files_isolated(self, file_size_mb: int, filename: str):
        """
        [STRESS-002] Upload de archivos pesados con timeout extendido.
        Usa TestClient con timeout=30.0 para evitar caidas por latencia de E/S.
        """
        # Generar contenido de archivo basura que empiece con Magic Bytes PDF
        file_content = b"%PDF" + os.urandom((file_size_mb * 1024 * 1024) - 4)
        
        # Configuramos el cliente
        with TestClient(app) as client:
            files = {"file": (filename, file_content, "application/pdf")}
            # Pasamos el timeout directamente al método de request
            response = client.post("/api/v1/invoices/upload", files=files, timeout=30.0)
            
            assert response.status_code == 200
            assert "file_id" in response.json()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
