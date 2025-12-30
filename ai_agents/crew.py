import os
from crewai import Agent, Task, Crew, Process, LLM
from .tools.signer_tool import CallCoreSigner
from .tools.search_tool import SearchRegulationTool

# ============================================================================
# ZERO-COST LLM CONFIGURATION (Multi-Provider Router)
# ============================================================================

def get_zero_cost_llm() -> LLM:
    """
    Configura el LLM usando proveedores gratuitos en orden de prioridad.
    Detecta automaticamente que API keys estan disponibles.
    
    Capacidad total: 120+ RPM GRATIS
    - Groq: 60 RPM (Llama 3.3 70B)
    - Cerebras: 30 RPM (Llama 3.1 70B)
    - Gemini: 30+ RPM (Gemini 2.0 Flash)
    """
    
    # Priority order: Groq > Cerebras > Gemini > OpenRouter > OpenAI (fallback)
    providers = [
        ("GROQ_API_KEY", "groq/llama-3.3-70b-versatile", "Groq"),
        ("CEREBRAS_API_KEY", "cerebras/llama-3.3-70b", "Cerebras"),  # Fixed
        ("GEMINI_API_KEY", "gemini/gemini-1.5-flash", "Gemini"),  # Fixed
        ("OPENROUTER_API_KEY", "openrouter/google/gemini-2.0-flash-thinking-exp:free", "OpenRouter"),
        ("OPENAI_API_KEY", "gpt-4o-mini", "OpenAI"),  # Fallback de pago
    ]
    
    for env_key, model, name in providers:
        if os.getenv(env_key):
            print(f"[VeriAgent] Usando LLM gratuito: {name} ({model})")
            return LLM(model=model)
    
    # Si no hay ninguna key, usar un modelo local o fallar
    print("[VeriAgent] ADVERTENCIA: No hay API keys configuradas. Los agentes no funcionaran.")
    return LLM(model="groq/llama-3.3-70b-versatile")  # Fallback que fallara si no hay key


# Obtener el LLM configurado
ZERO_COST_LLM = get_zero_cost_llm()

# ============================================================================
# AGENTS DEFINITION
# ============================================================================

Fiscal_Auditor = Agent(
    role="Senior Fiscal Auditor & Compliance Expert",
    goal="Ensure 100% compliance with VeriFactu and AEAT regulations for every invoice.",
    backstory=(
        "You are a paranoid auditor with 20 years of experience in the Spanish Tax Agency (AEAT). "
        "You have seen every trick in the book and you trust NO ONE. Your reputation depends on "
        "detecting even the smallest discrepancy. You treat every piece of data as a potential "
        "fraud until proven otherwise. You are obsessed with mathematical precision and "
        "regulatory strictness."
    ),
    tools=[SearchRegulationTool(), CallCoreSigner()],
    llm=ZERO_COST_LLM,  # Usar LLM gratuito
    verbose=True,
    allow_delegation=False,
    memory=True,
    # [PR-001] Defensive System Prompting Layer
    system_template=(
        "Comportamiento de Seguridad Obligatorio:\n"
        "1. Regla de Oro: Nunca asumas un dato. Si detectas que el OCR tiene una confianza < 90% "
        "en el NIF o el Importe Total, DETENTE inmediatamente y solicita 'HumanReview'.\n"
        "2. Protocolo de Firma: Solo invocaras la herramienta 'core_signer' (CallCoreSigner) "
        "si y solo si has validado matematicamente que Base + IVA = Total (con tolerancia de 0.01).\n"
        "3. Reaccion a Errores: Si CallCoreSigner devuelve un error relacionado con el Hash o la cadena "
        "de continuidad, no lo reintentes. Marca la factura inmediatamente como FATAL_ERROR y escala "
        "al humano para auditoria forense."
    )
)

AEAT_Connector = Agent(
    role="AEAT Communication Specialist",
    goal="Handle technical communication with AEAT endpoints securely.",
    backstory=(
        "You specialize in the technical protocols of the Spanish Tax Agency. "
        "You ensure that all data is formatted correctly before submission and "
        "handle API responses with extreme care."
    ),
    llm=ZERO_COST_LLM,  # Usar LLM gratuito
    verbose=True,
    allow_delegation=False
)

# ============================================================================
# TASKS DEFINITION
# ============================================================================

audit_invoice_task = Task(
    description=(
        "Audit the extracted invoice data: {invoice_data}. "
        "1. Verify NIF formats and mathematical consistency (Base + Tax = Total). "
        "2. Check if the expenses are deductible according to current regulations using your search tool. "
        "3. If everything is perfect, call the core_signer to register the invoice. "
        "4. If there is ANY doubt (accuracy < 90%) or mathematical error, reject it."
    ),
    expected_output="Final status of the invoice (SIGNED/REJECTED/FATAL_ERROR) and the generated hash if successful.",
    agent=Fiscal_Auditor
)

# ============================================================================
# CREW DEFINITION
# ============================================================================

veriagent_crew = Crew(
    agents=[Fiscal_Auditor, AEAT_Connector],
    tasks=[audit_invoice_task],
    process=Process.sequential,
    verbose=True
)

