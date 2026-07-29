"""LangGraph graphs for VeriAgent agents.

Exports:
- ingestion_app: invoice extraction + validation graph (AGENT-003).
- ProductGraph build helpers + state (AGENT-013).
"""

__all__ = ["build_product_graph", "ProductGraphState", "initial_state", "ingestion_app"]


def __getattr__(name: str):
    if name in ("build_product_graph", "ProductGraphState", "initial_state"):
        from .product_graph import (
            ProductGraphState,
            build_product_graph,
            initial_state,
        )

        return {
            "build_product_graph": build_product_graph,
            "ProductGraphState": ProductGraphState,
            "initial_state": initial_state,
        }[name]
    if name == "ingestion_app":
        from .ingestion_graph import ingestion_app

        return ingestion_app
    raise AttributeError(name)
