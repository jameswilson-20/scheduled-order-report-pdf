from pathlib import Path

from report_pdf_service import Order, PdfClient, build_report, render_and_archive


class FakeClient:
    def generate(self, markdown: str):
        assert "Shipped: 1" in markdown
        return {"ok": True, "data": {"document": "stored-report"}}


def test_report_counts_fulfillment_and_archives_response(tmp_path: Path):
    orders = [Order("1", "A", 10, "shipped", True), Order("2", "B", 20, "processing", False)]
    report = build_report(orders)
    assert "Gross total: $30.00" in report
    archived = render_and_archive(orders, tmp_path, FakeClient())
    assert archived.exists()
    assert "stored-report" in archived.read_text()


def test_generate_uses_explicit_pdf_endpoint(monkeypatch):
    seen = {}
    def fake_request(self, method, path, body=None):
        seen.update(method=method, path=path, body=body)
        return {"ok": True, "data": {}}
    monkeypatch.setattr(PdfClient, "_request", fake_request)
    PdfClient("from-env").generate("# report")
    assert seen["method"] == "POST"
    assert seen["path"] == "/v1/pdf/generate"
    assert set(seen["body"]) == {"markdown", "page_size", "orientation", "store"}
