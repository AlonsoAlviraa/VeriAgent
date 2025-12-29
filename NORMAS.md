# 🛡️ PROTOCOLO DE INTEGRIDAD Y COLABORACIÓN (GIT FLOW)
**Proyecto:** VeriAgent 2026
**Estado:** OBLIGATORIO
**Versión:** 1.0

---

## 1. INTRODUCCIÓN Y FILOSOFÍA DE "NO-ROTURA"
Este proyecto combina dos paradigmas opuestos:
1.  **Equipo A (Core/Cripto):** Código Determinista (Python puro, Hashes, XML). **Tolerancia a fallos: 0%.**
2.  **Equipo B (IA/Agentes):** Código Probabilístico (CrewAI, LLMs). **Tolerancia a fallos: Flexible (Human-in-the-loop).**

Para evitar que un equipo bloquee al otro, se establece el siguiente **Régimen de Separación de Poderes y Control de Versiones**. El incumplimiento de estas normas resultará en el rechazo inmediato del código (Pull Request Rejected).

---

## 2. ARQUITECTURA DE CARPETAS (LA ZONA DESMILITARIZADA)
Se prohíbe terminantemente modificar archivos fuera de la jurisdicción de tu equipo sin consenso previo.

```text
/project_root
├── /core_engine          <-- ⛔ PROPIEDAD EQUIPO A (Motor VeriFactu, Hashing, XML)
│   ├── /crypto           (Nadie del Equipo B toca esto)
│   └── /signatures
│
├── /ai_agents            <-- 🤖 PROPIEDAD EQUIPO B (CrewAI, Prompts, Tools)
│   ├── /config           (Configuración de agentes y tareas)
│   └── /tools            (Herramientas custom)
│
├── /shared               <-- 🤝 ZONA COMÚN (Solo Pydantic Models y Constantes)
│   ├── schemas.py        (Contratos de datos: Input/Output)
│   └── constants.py      (Configuraciones globales)
│
├── /api                  <-- 🔌 ZONA DE INTEGRACIÓN (FastAPI)
│   └── routes.py         (Donde los agentes y el core se exponen al mundo)
│
└── main.py               <-- ⛔ SOLO ARQUITECTOS (Punto de entrada)