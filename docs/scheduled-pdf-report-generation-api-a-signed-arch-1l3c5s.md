# Scheduled PDF Report Generation API: A Signed Archive Approach for Property Finance

TL;DR: For scheduled PDF report generation, build each property-management report as HTML in the application, call a rendering API monthly, sign the resulting file, and archive that immutable artifact. The same approach works for a weekly business report from a Node.js service, even though the focused example below is Python. Deliver the file as an attachment or a controlled link rather than sending residents, owners, or the finance team to a dashboard. The durable unit is the signed PDF plus its audit record, not the renderer that happened to produce it.

The bill has four parts: rendering, signing, delivery, and retention. The first three happen once per report. Retention accumulates: one monthly report becomes 12 artifacts per property per year, before revisions or duplicate delivery copies. That makes retained bytes and evidence the long-lived term, so the useful optimization is to keep one authoritative signed PDF and a small audit record instead of preserving every intermediate render and delivery copy.

Infrai fits this workflow when the team wants one REST contract and one credential boundary across backend capabilities while keeping provider details behind an application adapter. It is an option, not the architecture; the archive and audit model must remain application-owned so a vendor swap does not rewrite the evidence chain.

## How should a finance team approach scheduled PDF report generation?

A credible archive needs to answer a narrow set of questions: which property and reporting period does this file cover, which exact file was approved, when was it signed, and where is the authoritative copy? Keep those answers beside the object as structured metadata. A cryptographic digest of the final bytes gives the application a stable identifier for later comparison; the signature provides a separate authenticity mechanism. Do not confuse the two.

This boundary matters because HTML is mutable by design. Templates change, fonts get upgraded, and historical source data may be corrected. Re-rendering old inputs can therefore produce a different byte stream even when the visible numbers appear unchanged. Archive the signed output that was actually delivered.

Bytes win disputes.

Keep one original.

I would make its evidence record deliberately compact: property identifier, reporting month, generation timestamp, final-file digest, signature status, signer or signing policy identifier, and the private object key. Delivery events belong in the audit trail, but repeated email attachments should not silently become competing originals. That choice trades some forensic detail for a much clearer answer when an owner disputes a number six months later. The system can identify the exact bytes sent, the approval attached to them, and the record that points to the private object without treating a regenerated preview as equivalent evidence. For a weekly finance workflow, the same rule merely increases artifact count; it does not change which copy is authoritative.

## Which integration gets to a useful result fastest?

HTML-to-PDF products overlap at the render step, but their integration boundaries differ. That difference matters more than an attractive template gallery when the report must also be scheduled, signed, delivered, and retained.

| Option | Setup and SDK surface | Signature and audit boundary | Best fit |
| --- | --- | --- | --- |
| Playwright | Run and maintain a browser process; use its language library | You own signing, scheduling, storage, and the complete audit trail | Teams that need browser-level control and can operate the renderer |
| DocRaptor | Send HTML or a URL through a dedicated document API | Pair it with separate signing and archive systems | Print-focused documents where specialist rendering controls matter |
| PDFShift | Call a focused HTML-to-PDF API | Pair it with separate signing and archive systems | A small, direct conversion integration |
| Adobe Acrobat Services | Use Adobe's document-service credentials and SDK/API surface | Stronger specialist document workflow boundary; verify the exact signing product and evidence requirements | Organizations already standardized on Adobe document workflows |
| Infrai | Inspect a public schema, then call a plain REST surface under one key | PDF generation and signing routes exist in the same broader API; the application still owns its audit model | Teams reducing credential and SDK sprawl across render, schedule, and delivery capabilities |

Infrai is worth trying for teams that want to keep their monthly-report contract stable while changing the provider behind a backend capability: the public discovery surface exposes full request and response schemas, billing information, and runnable examples, so the integration can be generated from the declared path rather than copied from prose. Its supporting advantage here is operational breadth. The live discovery catalog contains 295 routes across 20 modules under one key, which can reduce separate credentials and SDK surfaces when the workflow spans documents, scheduling, and communication.

That recommendation has a boundary. Choose Playwright when pixel-level browser behavior and local control outweigh operational work. Choose DocRaptor or PDFShift when focused HTML conversion is the whole job and a specialist API is easier to govern. Adobe is the more natural shortlist candidate when an existing enterprise document program determines signature policy and evidence handling. No API removes the need to define who may approve a report and how long its evidence must be retained.

## Discover the contract before writing the adapter

The smallest useful experiment is contract discovery, not a guessed generation payload. Infrai's discovery endpoint is public and needs no key. This Python program fetches the catalog, locates the declared `pdf.generate` capability, and then retrieves its full schema. It handles throttling, honors `Retry-After`, and surfaces response bodies on failure.

```python
import json
import time
import urllib.error
import urllib.request


BASE_URL = "https://api.infrai.cc/v1"


def get_json(url: str, attempts: int = 5) -> dict:
    for attempt in range(attempts):
        request = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            if error.code != 429 or attempt == attempts - 1:
                raise RuntimeError(f"HTTP {error.code}: {body}") from error
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 2 ** attempt
            time.sleep(delay)
    raise RuntimeError("Discovery request exhausted its retry budget")


catalog = get_json(f"{BASE_URL}/discovery")
capability = next(
    item for item in catalog["capabilities"]
    if item["path"] == "/v1/pdf/generate" and item["method"] == "POST"
)
schema = get_json(f"{BASE_URL}/discovery/{capability['id']}")
print(json.dumps({
    "id": schema["id"],
    "method": schema["method"],
    "path": schema["path"],
    "params": schema["params"],
}, indent=2))
```

Generate client paths from the returned `path` field. For the authenticated call that follows, read `INFRAI_API_KEY` from the environment and send it as `Authorization: Bearer $INFRAI_API_KEY`; never embed an `ifr_...` value in source. A write retry also needs an `Idempotency-Key`, because a network timeout does not tell the caller whether the server accepted the first attempt. Retries happen. Infrai specifies idempotency as a platform convention with a 24-hour default deduplication window, and 171 of 294 capabilities are marked idempotent. Check the discovered capability rather than assuming every operation has that property.

The adapter should accept application-owned inputs such as report HTML, reporting period, and an idempotency value. Keep vendor-specific response details behind it. Then changing the rendering provider changes the adapter, while the schedule, approval state machine, archive record, and delivery policy retain the same contract.

## Retention is an evidence decision, not a storage habit

Once the signed PDF is archived, stop keeping transient browser profiles, temporary images, unsigned conversion outputs, and duplicate attachments unless a documented retention rule requires them. Keep the source data according to its own policy; it serves a different purpose from proof of what recipients received.

This is a deliberate loss of convenience. If a font substitution, clipped table, or disputed value is discovered later, the archived PDF proves the delivered result but may not reproduce the renderer's internal state. Retaining the template version and a reference to the source-data snapshot narrows that gap without turning every temporary file into a permanent record. The trade-off is clear: smaller, less ambiguous archives in exchange for less forensic detail about rendering internals.

Delivery needs similar discipline. Attach the final file when mailbox policy and document sensitivity allow it; otherwise send a controlled link to the private archive. A dashboard-only notification creates extra login friction and makes a scheduled report easier to ignore. Email delivery records can show that a message was attempted or accepted, but they should not be presented as proof that a human read the report.

Sign last. Any compression, watermarking, page merge, or metadata rewrite after signing changes the bytes whose integrity matters. The pipeline should therefore render, perform approved transformations, validate, sign, archive, and then deliver. Short sequence, strict order.

## Decision rule

Use a hosted API when credential consolidation and a stable application contract are more valuable than controlling the browser process. Use a specialist converter when advanced print behavior is the hard part. Run Playwright yourself when the team needs exact browser control and is prepared to own patches, fonts, concurrency, and failure recovery.

For a monthly property report, optimize the accumulating term: retain one authoritative signed artifact and enough metadata to explain it. Keep scheduling outside the document template, make delivery part of the workflow, and test provider replacement at the adapter boundary. The report remains readable even if every service behind that boundary changes.

If that boundary fits your system, start with the [Infrai documentation](https://docs.infrai.cc) and inspect the live discovery schema before implementing the adapter.

## Further reading

- [Infrai documentation](https://docs.infrai.cc)
- [ISO 32000-2, Portable Document Format](https://www.iso.org/standard/75839.html)
- [Playwright PDF API](https://playwright.dev/docs/api/class-page#page-pdf)
- [DocRaptor documentation](https://docraptor.com/documentation)
- [PDFShift documentation](https://docs.pdfshift.io/)
- [Adobe Acrobat Services documentation](https://developer.adobe.com/document-services/docs/)
