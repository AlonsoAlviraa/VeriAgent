# Product Backlog & Roadmap: VeriAgent MVP (3 Meses)

**Documento de Planificación - Versión 1.0**
**Technical Product Owner:** Antigravity
**Objetivo:** Lanzamiento del MVP "Auditor Fiscal Proactivo" conforme a Ley Crea y Crece / VeriFactu.

## Glosario de Equipos
*   **[TEAM-A] (/core_engine):** Responsable del Backend, Criptografía, Bases de Datos, Integraciones API Deterministas (AEAT, Redtrust) y Schemas.
*   **[TEAM-B] (/ai_agents):** Responsable de la Lógica de Negocio Probabilística, Prompts, LangGraph, RAG y Vector DB.

---

## Roadmap del MVP (6 Sprints)

| Sprint | Fechas (Est.) | Objetivo Principal | Entregables Clave (Team A) | Entregables Clave (Team B) | Dependencias & Bloqueos | Hito de Integración (Git Flow) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | Semanas 1-2 | **Cimientos & Arquitectura** | - [CORE-001] Repo & CI/CD Setup<br>- [CORE-002] Definir Shared Pydantic Schemas<br>- [CORE-003] Setup DB (PostgreSQL) | - [AGENT-001] Setup LangGraph Environment<br>- [AGENT-002] Configuración Vector DB (Regulaciones) | **BLOQUEO:** Team B necesita `[CORE-002]` (Schemas) para estructurar los outputs de los agentes. | **Viernes Sem 2:** Merge de Schemas y Setup Básico a `develop`. |
| **2** | Semanas 3-4 | **Ingesta & Digitalización** | - [CORE-004] API Endpoints para Carga de Archivos<br>- [CORE-005] Integración librerías OCR Base | - [AGENT-003] Agente de Ingesta (Extraction Prompting)<br>- [AGENT-004] Validación de Extracción JSON vs Schemas | **CRÍTICO:** Ingest Agent depende de que el API de carga disponga los archivos. | **Viernes Sem 4:** PRs de Ingesta (A) y Agente (B) integrados. |
| **3** | Semanas 5-6 | **Motor de Cumplimiento** | - [CORE-006] Generación XML Facturae (Determinista)<br>- [CORE-007] Lógica de Hash VeriFactu (Encadenamiento) | - [AGENT-005] Agente Compliance (RAG vs Normativa)<br>- [AGENT-006] Reglas de Negocio en Grafo | **BLOQUEO:** El Agente no puede validar "Sintaxis" si el generador XML no existe. | **Viernes Sem 6:** Core Validation Logic unificada con Agente. |
| **4** | Semanas 7-8 | **Transacciones & Firmas** | - [CORE-008] Implementación Firma Digital (XAdES)<br>- [CORE-009] Mock Server API AEAT | - [AGENT-007] Transaction Handler Agent<br>- [AGENT-008] Lógica de Decisión (Sign/Reject) | Team B espera las funciones de firma (`signing_utils`) en `/core_engine`. | **Viernes Sem 8:** Flujo completo (Ingesta -> Validación -> Firma) en `develop`. |
| **5** | Semanas 9-10 | **Orquestación & UI API** | - [CORE-010] API REST de cara al Frontend<br>- [CORE-011] Webhooks de Estado (Async) | - [AGENT-009] **Orquestador LangGraph Completo** (Human-in-the-loop)<br>- [AGENT-010] Gestión de Estados Globales | **CRÍTICO:** Team A debe exponer endpoints que activen el Grafo de Team B. | **Viernes Sem 10:** End-to-End funcional disponible en Staging. |
| **6** | Semanas 11-12 | **Hardening & Launch** | - [CORE-012] Auditoría de Seguridad & GDPR<br>- [CORE-013] Scripts de Despliegue Producción | - [AGENT-011] Eval Framework (LLM-as-a-judge)<br>- [AGENT-012] Optimización de Costes (Tokens) | Sin bloqueos mayores. Polish final. | **Viernes Sem 12:** Release Candidate (`main`) + Tag v1.0. |

---

## Product Backlog Detallado (Prioridad Alta)

### SPRINT 1: Arquitectura

#### [TEAM-A] Core Engineering
*   **[TEAM-A][CORE-001] Inicialización de Repositorio y CI/CD**
    *   *Descripción:* Configurar repo con carpetas `/core_engine`, `/ai_agents`, `/shared`. Configurar pre-commit hooks (Black, Isort).
    *   *Criterio de Aceptación:* Pipeline en verde, estructura de carpetas según NORMAS.md.
*   **[TEAM-A][CORE-002] Definición de Pydantic Schemas (/shared)**
    *   *Descripción:* Crear modelos de datos para `Invoice`, `Customer`, `TaxLine` en `/shared/schemas.py`.
    *   *Criterio de Aceptación:* Modelos cubren campos obligatorios de VeriFactu. Importables por ambos equipos.

#### [TEAM-B] AI & Agents
*   **[TEAM-B][AGENT-001] Configuración Base LangGraph**
    *   *Descripción:* Crear estructura básica de grafos en `/ai_agents/graphs`.
    *   *Criterio de Aceptación:* "Hello World" de un grafo ejecutándose.
*   **[TEAM-B][AGENT-002] Ingesta de Normativa en Vector DB**
    *   *Descripción:* Script para chunking y embedding de "Ley Crea y Crece" y documentos técnicos VeriFactu.
    *   *Criterio de Aceptación:* Consultas de prueba devuelven contextos relevantes.

### SPRINT 2: Ingesta

#### [TEAM-A] Core Engineering
*   **[TEAM-A][CORE-004] Servicio de Gestión de Archivos**
    *   *Descripción:* Endpoint `POST /upload` que guarda PDFs/Imágenes en sistema de ficheros seguro/S3.
    *   *Criterio de Aceptación:* Archivo subido, UUID retornado.

#### [TEAM-B] AI & Agents
*   **[TEAM-B][AGENT-003] Prompt Engineering - Agente de Ingesta**
    *   *Descripción:* Diseñar prompts para extraer JSON acorde a `[CORE-002]` desde texto OCR.
    *   *Criterio de Aceptación:* Precisión > 90% en campos clave (Fecha, Importe, NIF).

### SPRINT 3: Cumplimiento

#### [TEAM-A] Core Engineering
*   **[TEAM-A][CORE-006] Generador XML Facturae**
    *   *Descripción:* Utilidad para convertir objeto `Invoice` (Pydantic) a XML estándar Facturae.
    *   *Criterio de Aceptación:* XML valida contra XSD oficial.
*   **[TEAM-A][CORE-007] Implementación Chaining Hash**
    *   *Descripción:* Función que calcula hash de factura actual + hash anterior (Blockchain-like concept para VeriFactu).
    *   *Criterio de Aceptación:* Hash generado correctamente SHA-256.

#### [TEAM-B] AI & Agents
*   **[TEAM-B][AGENT-005] Agente Auditor (Compliance)**
    *   *Descripción:* Nodo del grafo que recibe JSON, consulta Vector DB y verifica reglas (ej: "Operación > 1000€ requiere identificación completa").
    *   *Criterio de Aceptación:* Detecta facturas inválidas en tests.

### SPRINT 4: Transacción

#### [TEAM-A] Core Engineering
*   **[TEAM-A][CORE-008] Módulo de Firma Digital**
    *   *Descripción:* Integración con certificado digital para firmar el XML.
    *   *Criterio de Aceptación:* XML firmado verifica firma correctamente.

#### [TEAM-B] AI & Agents
*   **[TEAM-B][AGENT-007] Agente Transaccional**
    *   *Descripción:* Gestiona el estado de envío. Si `Compliance == OK` -> Solicita Firma -> Envía a Mock AEAT.
    *   *Criterio de Aceptación:* Flujo exitoso de principio a fin en entorno de pruebas.

---

## Normas de Gestión (Recordatorio)
*   **Ramas:** `feature/TEAM-A/nombre-ticket` y `feature/TEAM-B/nombre-ticket` nacen y mueren en `develop`.
*   **Commits:** Usar Conventional Commits (`feat:`, `fix:`, `chore:`).
*   **Code Review:** Team A revisa código de Team A (Tecnico) y Team B (Integración). Team B revisa lógica de Negocio.