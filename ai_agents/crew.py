from crewai import Agent, Task, Crew, Process
from .tools.signer_tool import CallCoreSigner
from .tools.search_tool import SearchRegulationTool

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
    verbose=True,
    allow_delegation=False,
    memory=True,
    # [PR-001] Defensive System Prompting Layer
    system_template=(
        "Comportamiento de Seguridad Obligatorio:\n"
        "1. Regla de Oro: Nunca asumas un dato. Si detectas que el OCR tiene una confianza < 90% "
        "en el NIF o el Importe Total, DETENTE inmediatamente y solicita 'HumanReview'.\n"
        "2. Protocolo de Firma: Solo invocarás la herramienta 'core_signer' (CallCoreSigner) "
        "si y solo si has validado matemáticamente que Base + IVA = Total (con tolerancia de 0.01€).\n"
        "3. Reacción a Errores: Si CallCoreSigner devuelve un error relacionado con el Hash o la cadena "
        "de continuidad, no lo reintentes. Marca la factura inmediatamente como FATAL_ERROR y escala "
        "al humano para auditoría forense."
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
