# Data sources

All sources below are free and require no paid key.

| Source | Endpoint | Auth | Rate limit | Format | Cadence | License |
|---|---|---|---|---|---|---|
| NVD CVE API 2.0 | `https://services.nvd.nist.gov/rest/json/cves/2.0` | optional free key (`apiKey` header) | 5 req/30 s anonymous; 50 req/30 s with key | JSON | continuous | NIST public domain — no endorsement |
| NVD CVE feeds | `https://nvd.nist.gov/feeds/json/cve/2.0/nvdcve-2.0-{YYYY\|modified\|recent}.json.gz` | none | poll ≤ ~200/day; check `.meta` first | JSON (gz) + `.meta` | year=daily; modified ≈ 2 h | same |
| FIRST EPSS API | `https://api.first.org/data/v1/epss?cve=` | none | lookup only — not for bulk | JSON | daily | free |
| FIRST EPSS CSV | `https://epss.empiricalsecurity.com/epss_scores-current.csv.gz` | none | n/a | gzip CSV (`cve,epss,percentile`) | daily | free |
| CISA KEV | `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` | none | none published | JSON | near-daily batches | CC0 1.0 |
| MITRE ATT&CK | `https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json` | none | n/a (~51 MB file) | STIX 2.1 | ~2×/year | © MITRE, royalty-free with attribution |
| CVSS v4.0 spec | `https://www.first.org/cvss/v4.0/specification-document` | none | n/a | spec | static | FIRST, attribution required |
| CWE | `https://cwe.mitre.org/top25/` | none | n/a | JSON/CSV | ~annual | MITRE royalty-free |

## Ingestion strategy

1. **Join key is `cveID`** — it ties NVD ⟷ EPSS ⟷ KEV together.
2. **Bootstrap:** pull NVD 2.0 JSON feeds once into the store.
3. **Steady state:** poll the NVD *modified* window (≤ 120 days, at most every 2 hours)
   with a free API key; refresh EPSS/KEV daily.
4. **CVSS fallback:** prefer `cvssMetricV40` → `cvssMetricV31` → `cvssMetricV30` → `cvssMetricV2`,
   and always store which version was used. NVD's v4.0 coverage is currently sparse.
5. **ATT&CK:** pin a release version, stream-parse the bundle, drop `revoked` and
   `x_mitre_deprecated` objects, and cache it locally.

## Endpoint notes

- NVD date ranges are capped at 120 days; ISO-8601 `+` offsets must be URL-encoded as `%2B`.
- NVD pagination: `resultsPerPage` max 2000, `startIndex` zero-based; iterate until
  `startIndex ≥ totalResults`.
- EPSS API is **lookup-only** — bulk joins come from the daily CSV.
- The ATT&CK bundle is ~51 MB; prefer it over the TAXII server (50 req/10 min per IP).
- KEV carries an undocumented `forensicTriage` field on some records — parse defensively.

## Attribution (shown in the UI)

- "This product uses the NVD API but is not endorsed or certified by the NVD."
- CVSS is owned by FIRST and used by permission; scores are published with their vector string.
- "© 2026 The MITRE Corporation. This work is reproduced and distributed with the permission of The MITRE Corporation."
- CISA KEV data is CC0 1.0.

## Limitations

- Absence from KEV means "not yet confirmed exploited", **not** "safe".
- EPSS does not score every CVE; a missing score is *unknown*, not zero.
- EPSS scores shift at model-version boundaries for methodological reasons.
- NVD enrichment (CVSS/CPE/CWE) can lag publication by days to weeks.
