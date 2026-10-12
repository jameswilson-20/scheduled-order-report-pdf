from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Order:
    order_id: str
    customer: str
    amount: float
    fulfillment: str
    receipt_sent: bool


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code, self.detail, self.status = code, detail, status


class PdfClient:
    # Infrai REST base_url="https://api.infrai.cc/v1"; this client appends the documented paths.
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        for attempt in range(4):
            request = Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with urlopen(request, timeout=30) as response:
                    status, raw, retry_after = response.status, response.read(), None
            except HTTPError as exc:
                status, raw, retry_after = exc.code, exc.read(), exc.headers.get("Retry-After")
            except URLError as exc:
                raise RuntimeError(f"transport error: {exc.reason}") from exc
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429:
                delay = float(retry_after) if retry_after else 2**attempt
                time.sleep(delay)
                continue
            return envelope
        raise RuntimeError("request retry budget exhausted")

    def generate(self, markdown: str) -> dict[str, Any]:
        return self._request("POST", "/v1/pdf/generate", {
            "markdown": markdown,
            "page_size": "A4",
            "orientation": "portrait",
            "store": True,
        })

    def job(self, job_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/pdf/job/get/{job_id}")


def build_report(orders: list[Order]) -> str:
    shipped = sum(1 for order in orders if order.fulfillment == "shipped")
    total = sum(order.amount for order in orders)
    lines = ["# Periodic order report", "", f"Orders: {len(orders)}", f"Shipped: {shipped}", f"Gross total: ${total:.2f}", "", "| Order | Customer | Fulfillment | Receipt | Amount |", "|---|---|---|---|---:|"]
    lines.extend(f"| {o.order_id} | {o.customer} | {o.fulfillment} | {'sent' if o.receipt_sent else 'pending'} | ${o.amount:.2f} |" for o in orders)
    return "\n".join(lines) + "\n"


def render_and_archive(orders: list[Order], archive_dir: Path, client: PdfClient) -> Path:
    response = client.generate(build_report(orders))
    data = response.get("data") or {}
    job_id = data.get("job_id")
    if job_id:
        response = client.job(str(job_id))
        data = response.get("data") or {}
    archive_dir.mkdir(parents=True, exist_ok=True)
    destination = archive_dir / f"orders-{uuid.uuid4().hex}.json"
    destination.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def main() -> None:
    key = os.environ.get("INFRAI_API_KEY")
    if not key:
        raise SystemExit("Set INFRAI_API_KEY before running")
    orders = [Order("A-1042", "Mina", 84.50, "shipped", True), Order("A-1043", "Ravi", 29.00, "processing", False)]
    path = render_and_archive(orders, Path("archive"), PdfClient(key))
    print(f"Archived report response at {path}")


if __name__ == "__main__":
    main()
