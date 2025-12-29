import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock cryptography to avoid need for real .p12 file in CI env
sys.modules['cryptography'] = MagicMock()
sys.modules['cryptography.hazmat'] = MagicMock()
sys.modules['cryptography.hazmat.primitives'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.serialization'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.serialization.pkcs12'] = MagicMock()

from core_engine.services.signature import SignatureService

class TestSignature(unittest.TestCase):
    @patch('core_engine.services.signature.pkcs12.load_key_and_certificates')
    @patch('os.path.exists')
    @patch('builtins.open')
    def test_load_certificate(self, mock_open, mock_exists, mock_load):
        mock_exists.return_value = True
        mock_load.return_value = (MagicMock(), MagicMock(), [])
        
        service = SignatureService("cert.p12", "pass")
        self.assertIsNotNone(service.private_key)
        print("Certificate loaded mock successfully")

if __name__ == '__main__':
    unittest.main()
