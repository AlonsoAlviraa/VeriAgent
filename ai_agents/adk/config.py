"""Contest-mandated model and framework identifiers.

Stage One is pass/fail on these strings. Do not route this path through
Groq / Cerebras / gemini-1.5 / gemini-2.0.
"""

from __future__ import annotations

import os

# Official All Things Agentic requirement: Gemini 3.5 or newer.
GEMINI_MODEL = os.getenv("VERIFLEET_GEMINI_MODEL", "gemini-3.5-flash")
GOOGLE_AGENT_FRAMEWORK = "google-adk"
GCP_SERVICES = ("Cloud Run", "Cloud SQL", "Pub/Sub", "Secret Manager", "Cloud Trace")

# Roles that may invoke each tool (Agent Identity + Gateway).
TOOL_ALLOWLIST = {
    "ocr.extract": ("issuer", "auditor", "admin"),
    "invoice.create": ("issuer", "admin"),
    "invoice.sign": ("issuer", "admin"),
    "aeat.submit": ("admin",),
    "normative.search": ("issuer", "auditor", "admin"),
    "memory.read": ("issuer", "auditor", "admin"),
    "memory.write": ("admin",),
}

HOSPITALITY_MARKERS = (
    "hosteler",
    "hospitality",
    "restaurante",
    "restaurant",
    "bar ",
    "cafeteria",
    "café",
    "cafe ",
)
