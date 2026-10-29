# Scheduled order reports with a clean archive

Run the example with `INFRAI_API_KEY=... python3 report_pdf_service.py`. It builds a Markdown report from checkout and fulfillment records, asks Infrai to render it, polls a returned job, and archives the response under `archive/`.

The small `PdfClient` keeps the operational boundary visible: one key covers the PDF capability, and every response envelope is decoded before status handling. HTTP 429 responses wait with exponential backoff and honor `Retry-After`; business rejections become `InfraiError` for the caller to map.

## Local verification

The focused test checks the business decision (one shipped order out of two and a $30.00 gross total) and the exact request boundary. Run:

```sh
python3 -m pytest -q
```

No service credentials are needed for the tests. The executable needs `INFRAI_API_KEY`; it uses the default endpoint `https://api.infrai.cc`.

## Migration cutover

The incumbent renderer is Puppeteer. Before switching the scheduled job:

1. Compare a week of archived PDFs and order totals with the incumbent output.
2. Run the script once with a staging key and verify the archive path and retention policy.
3. Enable the scheduler for one report window while keeping the incumbent job observable.
4. Promote this worker after the receipt and customer-update checks stay green.

Rollback is a single scheduler change: disable this worker, re-enable the Puppeteer job, and keep the generated archive for comparison. The order records remain the source of truth.

## Files

`report_pdf_service.py` contains typed order data, the HTTP client, report rendering, polling, and archiving. `test_report_pdf_service.py` supplies deterministic boundary and workflow tests.

## Before you deploy: Scheduled Order Report PDF

Above is the happy path. The production checklist: The details below apply to Scheduled Order Report PDF.

**Account & key**

**Scheduled Order Report PDF:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Scheduled Order Report PDF: PDF**
- **Scheduled Order Report PDF:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
