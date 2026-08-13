# ATA demo freeze — 50 synthetic invoices

**Frozen:** 2026-08-13  
**Seed:** `20260813`  
**Regenerate:** `python scripts/gen_invoice_corpus.py --count 50 --seed 20260813 --out demo/corpus/freeze --write-human-fixture`  
**Do not submit Devpost from this tree.** That step is human-only.

This freeze is the judge-facing 50-invoice subset of the one-month corpus campaign. Corpus volumes above 50 live under `demo/corpus/v1/` (gitignored). Samples (20) stay in `demo/corpus/samples/`.

## Sweep (committed fixtures)

| Fixture | Path | Expected |
| --- | --- | --- |
| Valid JSON / JSON-in-PDF | `demo/fixtures/valid_invoice.json`, `valid_invoice.pdf` | **SIGNED** |
| Math error | `demo/fixtures/math_error.json` | **ESCALATED**, never signed |
| Prompt injection | `demo/fixtures/injection.json` | **BLOCKED** |
| Hospitality | `demo/fixtures/hospitality.json` on tenant `enterprise-demo` | **ESCALATED** (Memory Bank) |

Replay: `python scripts/run_fixture_fleet.py`

## Human PDF (SIGNED path)

| File | Expected |
| --- | --- |
| `demo/fixtures/human_invoice.pdf` (+ `human_invoice.json` sidecar) | Extractor reads labeled `NIF` / `Base` / `IVA` / `Total`. Fleet **SIGNED** via `file_id`. |

Visible extractable labels: `NIF: B12345674`, `Cliente NIF: A11111119`, `Base: 101.00`, `IVA: 21.21 (21%)`, `Total: 122.21`, `Numero: H001`.

The LLM never fills a NIF. Low-confidence PDFs omit required fields and the auditor escalates.

## Public live PDF (ESCALATED, honest)

| File | Source | Expected |
| --- | --- | --- |
| `demo/fixtures/live/qualityhosting-de-vat.pdf` | Public invoice2data fixture (see `live/SOURCES.md`) | **ESCALATED**, `signed=false`. German VAT is not VeriFactu; extractor does not invent a Spanish NIF. |

Also covered by tests: `coolblue-nl-vat.pdf`, `netpresse-fr-vat.pdf`. No real-company invoices were scraped.

## 50-invoice synthetic subset

Manifest: `demo/corpus/freeze/manifest.json`  
Classes (seed `20260813`, count 50):

| class | n | expected |
| --- | --- | --- |
| valid | 37 | SIGNED |
| math_error | 5 | ESCALATED, 0 signatures |
| bad_nif | 2 | ESCALATED |
| hospitality | 2 | ESCALATED on `enterprise-demo` |
| injection | 2 | BLOCKED, 0 signatures |
| wrong_chain | 2 | ESCALATED |

IDs:

`00000-hospitality`, `00001-wrong_chain`, `00002-valid`, `00003-valid`, `00004-math_error`, `00005-valid`, `00006-valid`, `00007-valid`, `00008-valid`, `00009-valid`, `00010-valid`, `00011-valid`, `00012-valid`, `00013-valid`, `00014-math_error`, `00015-valid`, `00016-valid`, `00017-math_error`, `00018-bad_nif`, `00019-valid`, `00020-valid`, `00021-valid`, `00022-valid`, `00023-valid`, `00024-valid`, `00025-valid`, `00026-valid`, `00027-valid`, `00028-injection`, `00029-valid`, `00030-math_error`, `00031-valid`, `00032-valid`, `00033-bad_nif`, `00034-hospitality`, `00035-valid`, `00036-valid`, `00037-valid`, `00038-wrong_chain`, `00039-valid`, `00040-math_error`, `00041-valid`, `00042-valid`, `00043-valid`, `00044-valid`, `00045-valid`, `00046-injection`, `00047-valid`, `00048-valid`, `00049-valid`

Replay:

```text
python scripts/run_corpus_fleet.py --manifest demo/corpus/freeze/manifest.json --limit 50 --out-name ata-freeze --skip-llm
```

## Cloud Run

`PROJECT_ID` was not set in this workspace. Hosted deploy is a **human GAP** (`export PROJECT_ID=…` then `bash infra/deploy.sh`). This freeze does not invent a live `*.run.app` URL.
