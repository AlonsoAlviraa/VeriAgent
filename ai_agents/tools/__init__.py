"""Agent tools — lazy imports to avoid hard deps during unit tests."""

__all__ = [
    "SearchRegulationTool",
    "search_regulations",
    "CallCoreSigner",
    "WebSearchTool",
    "web_search",
]


def __getattr__(name: str):
    if name == "SearchRegulationTool" or name == "search_regulations":
        from .search_tool import SearchRegulationTool, search_regulations

        return SearchRegulationTool if name == "SearchRegulationTool" else search_regulations
    if name == "CallCoreSigner":
        from .signer_tool import CallCoreSigner

        return CallCoreSigner
    if name == "WebSearchTool" or name == "web_search":
        from .web_search_tool import WebSearchTool, search as web_search

        return WebSearchTool if name == "WebSearchTool" else web_search
    raise AttributeError(name)
