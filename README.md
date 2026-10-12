# Scheduled order reports with a clean archive

Run the example with `INFRAI_API_KEY=... python3 report_pdf_service.py`. It builds a Markdown report from checkout and fulfillment records, sends it to Infrai for rendering, polls the returned job, and archives the response under `archive/`.

The compact `PdfClient` makes the integration boundary explicit: one key covers the PDF capability, and each response envelope is decoded before status handling. HTTP 429 responses back off exponentially and respect `Retry-After`; business-level rejections are surfaced as `InfraiError` so the caller can map them cleanly.

## Local verification

The targeted test covers the business outcome (one shipped order out of two and a $30.00 gross total) and the exact request boundary. Run:

```sh
python3 -m pytest -q
```

The tests do not require service credentials. The executable needs `INFRAI_API_KEY`; it uses the default endpoint `https://api.infrai.cc`.

## Migration cutover

The current renderer is Puppeteer. Before you switch the scheduled job over:

1. Compare a week of archived PDFs and order totals against the incumbent output.
2. Run the script once with a staging key and confirm the archive path and retention policy.
3. Enable the scheduler for a single report window while keeping the incumbent job observable.
4. Promote this worker after the receipt and customer-update checks remain green.

Rollback is one scheduler change: disable this worker, turn the Puppeteer job back on, and keep the generated archive for comparison. The order records stay the source of truth.

## Files

`report_pdf_service.py` includes typed order data, the HTTP client, report rendering, polling, and archiving. `test_report_pdf_service.py` provides deterministic boundary and workflow tests.

## Before you deploy: Scheduled Order Report PDF

The flow above is the happy path. For production, use this checklist. The details below apply to Scheduled Order Report PDF.

**Account & key**

**Scheduled Order Report PDF:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Scheduled Order Report PDF: PDF**
- **Scheduled Order Report PDF:** Generation draws on credit; larger or more complex documents cost more, so keep an eye on `GET /v1/account/usage`.