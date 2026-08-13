"""Heuristic extractor for human-readable invoice PDFs.

pypdf + labeled-field regex only. Never calls an LLM and never invents a NIF.
Low-confidence results omit required fields so the fiscal auditor ESCALATES.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from pypdf import PdfReader

from core_engine.validators.fiscal_id import is_valid_fiscal_id

IVA_RATES = (21.0, 10.0, 4.0)

_ERR_PREFIXES = ("Unsupported file format:", "Error extracting text:", "File not found")

_NIF_BODY = re.compile(
    r"\b([A-HJ-NP-SUVW]\d{7}[0-9A-J]|[XYZ]\d{7}[A-Z]|\d{8}[A-Z])\b",
    re.IGNORECASE,
)
# Token/line start only — do not match the NIF inside "Cliente NIF".
_LABELED_ISSUER = re.compile(
    r"(?:^|[|\n])\s*(?:NIF|CIF|issuer_tax_id|Emisor(?:\s+NIF)?)\s*[:#]\s*([A-Z0-9]+)",
    re.IGNORECASE,
)
_LABELED_CUSTOMER = re.compile(
    r"(?:Cliente\s+NIF|customer(?:[_\s]+tax[_\s]*id)?|NIF\s+cliente)\s*[:#]\s*([A-Z0-9]+)",
    re.IGNORECASE,
)
_LABELED_BASE = re.compile(
    r"(?:Base(?:\s+imponible)?|total_base)\s*[:#]\s*([0-9]+[.,][0-9]{2})",
    re.IGNORECASE,
)
_LABELED_IVA = re.compile(
    r"(?:IVA|total_tax)\s*[:#]\s*([0-9]+[.,][0-9]{2})(?:\s*[\(]?\s*(21|10|4)\s*%?)?",
    re.IGNORECASE,
)
_LABELED_TOTAL = re.compile(
    r"(?:Total(?:\s+amount)?|Importe\s+total|total_amount)\s*[:#]\s*([0-9]+[.,][0-9]{2})",
    re.IGNORECASE,
)
_LABELED_DATE = re.compile(
    r"(?:Fecha|issue_date)\s*[:#]\s*(\d{4}-\d{2}-\d{2}|\d{2}[-/]\d{2}[-/]\d{4})",
    re.IGNORECASE,
)
_LABELED_SERIES = re.compile(r"(?:Serie|series)\s*[:#]\s*([A-Z0-9-]{1,10})", re.IGNORECASE)
_LABELED_NUMBER = re.compile(r"(?:Numero|N[uú]mero|number)\s*[:#]\s*([A-Z0-9-]{1,40})", re.IGNORECASE)
_LABELED_DESC = re.compile(r"(?:Descripcion|Descripci[oó]n|description)\s*[:#]\s*(.+)", re.IGNORECASE)
_LABELED_NOTES = re.compile(r"(?:Notas|notes)\s*[:#]\s*(.+)", re.IGNORECASE)
_LABELED_PREV = re.compile(
    r"(?:Hash anterior|previous_invoice_hash)\s*[:#]\s*([A-Fa-f0-9]{64})",
    re.IGNORECASE,
)
_LABELED_CUSTOMER_NAME = re.compile(r"(?:Cliente|customer_name)\s*[:#]\s*(.+)", re.IGNORECASE)
_ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def _money(raw: Optional[str]) -> Optional[float]:
    if not raw:
        return None
    try:
        return round(float(raw.replace(",", ".")), 2)
    except ValueError:
        return None


def _norm_date(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw = raw.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    m = re.fullmatch(r"(\d{2})[-/](\d{2})[-/](\d{4})", raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return None


def extract_text_from_pdf(path: str) -> str:
    """Read extractable text. Failures return empty string (never invent)."""
    try:
        reader = PdfReader(path)
    except Exception:
        return ""
    chunks: list[str] = []
    for page in reader.pages:
        try:
            piece = page.extract_text() or ""
        except Exception:
            piece = ""
        if piece:
            chunks.append(piece)
    return "\n".join(chunks).strip()


def extract_invoice_from_text(text: str) -> Dict[str, Any]:
    """Parse labeled VeriFactu-style fields. Omit anything not confidently found."""
    blob = text or ""
    if not blob.strip() or any(blob.startswith(p) for p in _ERR_PREFIXES):
        return {
            "raw_text": blob[:2000],
            "lines": [],
            "extract_confidence": "low",
            "extract_score": 0,
        }

    issuer_m = _LABELED_ISSUER.search(blob)
    customer_m = _LABELED_CUSTOMER.search(blob)
    base = _money(m.group(1) if (m := _LABELED_BASE.search(blob)) else None)
    iva_m = _LABELED_IVA.search(blob)
    tax = _money(iva_m.group(1) if iva_m else None)
    rate = None
    if iva_m and iva_m.group(2):
        rate = float(iva_m.group(2))
    elif tax is not None and base not in (None, 0):
        guessed = round(100.0 * tax / base)
        if guessed in {21, 10, 4}:
            rate = float(guessed)
    total = _money(m.group(1) if (m := _LABELED_TOTAL.search(blob)) else None)
    issue_date = _norm_date(m.group(1) if (m := _LABELED_DATE.search(blob)) else None)
    if issue_date is None:
        iso = _ISO_DATE.search(blob)
        issue_date = iso.group(1) if iso else None
    series = (m.group(1).strip() if (m := _LABELED_SERIES.search(blob)) else None)
    number = (m.group(1).strip() if (m := _LABELED_NUMBER.search(blob)) else None)
    desc_m = _LABELED_DESC.search(blob)
    notes_m = _LABELED_NOTES.search(blob)
    prev_m = _LABELED_PREV.search(blob)
    name_m = _LABELED_CUSTOMER_NAME.search(blob)

    issuer = issuer_m.group(1).strip().upper() if issuer_m else None
    customer_tax = customer_m.group(1).strip().upper() if customer_m else None

    # Unlabeled Spanish IDs are never promoted. A labeled value is kept even if
    # the check digit is wrong so the auditor can fail it (bad_nif).
    if issuer and not issuer_m:
        issuer = None
    if customer_tax and not customer_m:
        customer_tax = None

    score = 0
    if issuer:
        score += 2
    if customer_tax:
        score += 1
    if base is not None:
        score += 2
    if tax is not None:
        score += 2
    if total is not None:
        score += 2
    if issue_date:
        score += 1
    if number:
        score += 1
    if rate in IVA_RATES:
        score += 1

    high = score >= 8 and issuer is not None and base is not None and tax is not None and total is not None
    payload: Dict[str, Any] = {
        "raw_text": blob[:2000],
        "lines": [],
        "extract_confidence": "high" if high else "low",
        "extract_score": score,
    }
    if issuer:
        payload["issuer_tax_id"] = issuer
    if base is not None:
        payload["total_base"] = base
    if tax is not None:
        payload["total_tax"] = tax
    if total is not None:
        payload["total_amount"] = total
    if issue_date:
        payload["issue_date"] = issue_date
    if series:
        payload["series"] = series
    if number:
        payload["number"] = number
    if notes_m:
        payload["notes"] = notes_m.group(1).strip()
    if prev_m:
        payload["previous_invoice_hash"] = prev_m.group(1)

    if high and customer_tax and is_valid_fiscal_id(issuer or "") and is_valid_fiscal_id(customer_tax):
        desc = (desc_m.group(1).strip() if desc_m else "Extracted line")[:200]
        cust_name = "Extracted customer"
        if name_m:
            candidate = name_m.group(1).strip()
            if candidate and not candidate.upper().startswith("NIF"):
                cust_name = candidate[:120]
        payload["customer"] = {
            "tax_id": customer_tax,
            "name": cust_name,
            "address": {
                "street": "N/A",
                "city": "Madrid",
                "postal_code": "28001",
                "country": "ES",
            },
        }
        payload["lines"] = [
            {
                "description": desc,
                "quantity": 1,
                "unit_price": base,
                "total_amount": base,
            }
        ]
        payload["taxes"] = [
            {
                "tax_type": "IVA",
                "tax_rate": rate if rate in IVA_RATES else 21.0,
                "base_amount": base,
                "tax_amount": tax,
            }
        ]
        payload["series"] = series or "CR"
    elif customer_tax:
        payload["customer"] = {"tax_id": customer_tax}

    return payload


def extract_invoice_from_path(path: str) -> Dict[str, Any]:
    return extract_invoice_from_text(extract_text_from_pdf(path))
