# 🛡️ VeriAgent: AI-Powered Fiscal Compliance (VeriFactu)

VeriAgent es un sistema de auditoría inteligente diseñado para cumplir con la normativa **VeriFactu** de la AEAT. Utiliza agentes de IA (CrewAI) para validar facturas y un motor criptográfico (FastAPI) para asegurar la integridad de los datos.

## 🚀 Guía de Inicio Rápido

### Requerimientos de Sistema
- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 15** (opcional para local, obligatorio para prod)
- **Tesseract OCR**: Necesario para leer PDFs.
  - *Windows*: Descargar el instalador de UB Mannheim.
  - *Linux*: `sudo apt install tesseract-ocr`

### 1. Backend (FastAPI)
```bash
# Desde la raíz del proyecto
pip install -r requirements.txt
# Crear archivo .env basado en .env.example
# Añadir tu OPENAI_API_KEY
python -m uvicorn core_engine.main:app --reload --port 8000
```

### 2. Frontend (Next.js 14)
```bash
cd frontend
npm install
# Crear frontend/.env.local con:
# AUTH_SECRET=tu_secreto_generado
npm run dev
```

## 🎨 Funcionalidades Implementadas
- **Dashboard "Smart Audit"**: Interfaz interactiva para carga de archivos y seguimiento de estados en tiempo real.
- **Auditoría con Agentes**: `Fiscal Auditor` (IA) que valida OCR, matemáticas y normativa.
- **Seguridad Bifásica**: 2FA (TOTP) y gestión de "Trusted Devices" (30 días).
- **Recuperación de Cuenta**: Generación de códigos de emergencia y flujo de reset por TOTP.
- **Encadenamiento Hash**: Cada factura incluye el hash de la anterior (requisito VeriFactu).

## ⚠️ Problemas Pendientes y Desafíos Técnicos
1. **Configuración de DB en Docker**: El orquestador necesita ser refinado para asegurar que el volumen de PostgreSQL persista correctamente entre reinicios.
2. **XAdES Signing**: Actualmente la firma digital está simulada. Se requiere integrar una librería de firma XAdES real (como `signxml`) compatible con certificados de la FNMT.
3. **Conexión Real con AEAT**: El endpoint de envío a Hacienda está en modo `MOCK`. Falta implementar el cliente SOAP para conectar con los servidores de la Agencia Tributaria.
4. **Persistencia de 2FA**: El estado de 2FA se guarda en sesión (JWT). Se recomienda migrar a una tabla `sessions` en la DB para mayor robustez.

## 🧪 Pruebas integrales
Para verificar todo el flujo desde terminal sin usar el navegador:
```bash
python scripts/verify_integration_e2e.py
```

---
*Desarrollado con ❤️ para la modernización del cumplimiento fiscal.*
