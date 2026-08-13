"""COMP-04 / COMP-05: Facturae XML, QR, fail-closed AEAT."""

from datetime import date

from core_engine.aeat_connector import (
    build_registro_alta_payload,
    send_invoice_to_aeat,
)
from core_engine.services.facturae import FacturaeService
from shared.schemas import Address, Customer, Invoice, InvoiceLine, TaxLine


def _invoice():
    return Invoice(
        series="F",
        number="99",
        issue_date=date(2026, 1, 15),
        issuer_tax_id="B12345674",
        customer=Customer(
            tax_id="A11111119",
            name="Cliente",
            address=Address(street="S", city="M", postal_code="28001"),
        ),
        lines=[
            InvoiceLine(
                description="Serv", quantity=1, unit_price=100.0, total_amount=100.0
            )
        ],
        taxes=[TaxLine(tax_rate=21.0, base_amount=100.0, tax_amount=21.0)],
        total_base=100.0,
        total_tax=21.0,
        total_amount=121.0,
    )


def test_facturae_xml_and_qr_markers():
    inv = _invoice()
    xml = FacturaeService.generate_xml(inv)
    text = xml.decode("utf-8")
    assert "Facturae" in text
    assert "B12345674" in text
    assert "TaxIdentificationNumber" in text
    assert "VeriFactuHuella" in text
    assert "ImporteTotal" in text
    qr = FacturaeService.build_qr_payload(inv, "ABC123HASH")
    assert "nif=B12345674" in qr or "nif=B12345674".lower() in qr.lower()
    assert "huella=" in qr
    fields = FacturaeService.huella_fields(inv, "PREV")
    assert fields["IDEmisorFactura"] == "B12345674"
    assert fields["Huella"] == "PREV"


def _assert_no_soap(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("live AEAT SOAP must not be called")

    monkeypatch.setattr(
        "core_engine.aeat_connector.AEATConnector.send_invoice", _boom
    )
    monkeypatch.setattr(
        "core_engine.aeat_connector.AEATConnector.__init__",
        lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("AEATConnector must not be constructed")
        ),
    )


def test_aeat_fail_closed_missing_certs(monkeypatch):
    monkeypatch.delenv("AEAT_CERT_PATH", raising=False)
    monkeypatch.delenv("AEAT_KEY_PATH", raising=False)
    _assert_no_soap(monkeypatch)
    out = send_invoice_to_aeat(
        issuer_nif="B12345674",
        issuer_name="Test",
        series="F",
        number="1",
        issue_date="2026-01-15",
        total_amount=121.0,
        invoice_hash="HASH",
        environment="SANDBOX",
    )
    assert out["status"] == "ERROR"
    assert out["error_code"] == "CERTS_MISSING"
    assert out["registro_alta"]["IDFactura"]["IDEmisorFactura"] == "B12345674"
    assert out["registro_alta"]["Huella"] == "HASH"


def test_aeat_prod_gate_disabled():
    out = send_invoice_to_aeat(
        issuer_nif="B12345674",
        issuer_name="Test",
        series="F",
        number="1",
        issue_date="2026-01-15",
        total_amount=121.0,
        invoice_hash="HASH",
        environment="PRODUCTION",
        prod_aeat_enabled=False,
        allow_missing_certs=True,
    )
    assert out["status"] == "ERROR"
    assert out["error_code"] == "PROD_AEAT_DISABLED"


def test_aeat_prod_disabled_even_when_certs_present(monkeypatch, tmp_path):
    """PRODUCTION + PROD_AEAT_ENABLED false → PROD_AEAT_DISABLED. Do not enable prod."""
    cert = tmp_path / "client.pem"
    key = tmp_path / "client.key"
    cert.write_text("-----BEGIN CERTIFICATE-----\nMII\n-----END CERTIFICATE-----\n")
    key.write_text("-----BEGIN PRIVATE KEY-----\nMII\n-----END PRIVATE KEY-----\n")
    monkeypatch.setenv("AEAT_CERT_PATH", str(cert))
    monkeypatch.setenv("AEAT_KEY_PATH", str(key))
    _assert_no_soap(monkeypatch)
    out = send_invoice_to_aeat(
        issuer_nif="B12345674",
        issuer_name="Test",
        series="F",
        number="1",
        issue_date="2026-01-15",
        total_amount=121.0,
        invoice_hash="HASH",
        environment="PRODUCTION",
        prod_aeat_enabled=False,
    )
    assert out["status"] == "ERROR"
    assert out["error_code"] == "PROD_AEAT_DISABLED"
    assert "PROD_AEAT_ENABLED" in out["error_description"]


def test_aeat_prod_flag_default_is_false():
    from core_engine.control_plane.feature_flags import PROD_AEAT_ENABLED
    from core_engine.aeat_connector import send_invoice_to_aeat as send

    assert PROD_AEAT_ENABLED == "PROD_AEAT_ENABLED"
    # Keyword default must stay false — never flip production remittance on.
    import inspect

    assert inspect.signature(send).parameters["prod_aeat_enabled"].default is False


def test_registro_alta_payload_complete():
    p = build_registro_alta_payload(
        "B12345674", "Name", "S", "1", "2026-01-01", 10.0, "H1", "H0"
    )
    assert p["IDVersion"] == "1.0"
    assert p["TipoFactura"] == "F1"
    assert p["SistemaInformatico"]["NombreSistemaInformatico"] == "VeriAgent"
