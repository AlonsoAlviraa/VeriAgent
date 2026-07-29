from typing import TypedDict, Optional
import json
from langgraph.graph import StateGraph, END
from shared.schemas import Invoice
from ai_agents.config import config

# Define State
class IngestionState(TypedDict):
    input_text: str
    extracted_json: Optional[dict]
    validated_invoice: Optional[Invoice]
    error: Optional[str]

# Define Nodes
def extract_node(state: IngestionState):
    """
    [AGENT-003] Mockable extraction node. 
    In prod, this calls LLM with the input_text and Schema.
    """
    text = state["input_text"]
    
    # Simulating LLM Extraction
    # logic: if text contains "FACTURA", we return a dummy valid JSON
    if "FACTURA" in text.upper():
        mock_data = {
            "number": "001",
            "series": "F24", 
            "issue_date": "2024-01-01",
            "issuer_tax_id": "B12345674",
            "customer": {
                "tax_id": "A11111119",
                "name": "Test Client",
                "address": {"street":"S","city":"C","postal_code":"00","country":"ES"}
            },
            "lines": [],
            "taxes": [],
            "total_base": 100.0,
            "total_tax": 21.0, 
            "total_amount": 121.0
        }
        return {"extracted_json": mock_data}
    else:
        return {"error": "No Invoice detected in text"}

def validate_node(state: IngestionState):
    """
    [AGENT-004] Validates the extracted JSON against Pydantic Schema.
    """
    data = state.get("extracted_json")
    if not data:
        return {"error": "Missing JSON data"}
        
    try:
        # Pydantic validation
        invoice = Invoice(**data)
        return {"validated_invoice": invoice}
    except Exception as e:
        return {"error": f"Validation Failed: {str(e)}"}

# Define Graph
workflow = StateGraph(IngestionState)

workflow.add_node("extract", extract_node)
workflow.add_node("validate", validate_node)

workflow.set_entry_point("extract")

def should_continue(state: IngestionState):
    if state.get("error"):
        return END
    return "validate"

workflow.add_conditional_edges(
    "extract",
    should_continue,
    {
        "validate": "validate",
        END: END
    }
)

workflow.add_edge("validate", END)

ingestion_app = workflow.compile()
