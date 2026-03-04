# IronFist — Architecture

## Overview

IronFist is structured in six layers, each with a distinct responsibility. The design prioritizes clean separation so that any layer can be replaced or upgraded independently — including the AI backend.

```
Ingestion → CMDB → Normalization → Prioritization → AI Assistant → [Actions: Phase 2]
```

---

## Layer 1: Ingestion — Connector Framework

The ingestion layer is built as a **connector framework**, not a set of hardcoded integrations. Each data source is a discrete connector module that can be added, removed, or paused independently.

### Current connectors (planned)
| Connector | Type | Auth | TLS |
|-----------|------|------|-----|
| Tenable.sc / .io | Pull (API) | API key | ✅ Native |
| CISA KEV Feed | Pull (JSON feed) | None | ✅ Native |
| Container Scanner | Pull (API) | API key | ✅ Native |
| NVD / NIST | Pull (API) | API key | ✅ Native |
| Vendor Advisory RSS | Pull (RSS) | None | ⚠️ Verify per source |

### Connector interface
Each connector must implement:
- `fetch()` — retrieve raw data from source
- `normalize()` — transform to internal CVE schema
- `schedule` — cron expression for polling frequency
- `tls_verified` — boolean flag; connectors without TLS are flagged in UI

### Adding a new connector
New sources are added by implementing the connector interface and registering in the connector config — no changes to core platform logic required.

---

## Layer 2: CMDB — Asset Backbone

The CMDB is the most operationally critical layer. A vulnerability without asset context is noise. The CMDB provides the mapping that makes vulnerabilities actionable.

### Data model (key fields)
- `asset_id` — internal UUID
- `ip_address` — primary identifier for correlation
- `hostname` — resolved hostname
- `system_owner` — team or individual responsible
- `fisma_boundary` — which FISMA system boundary the asset belongs to
- `criticality` — LOW / MEDIUM / HIGH (used in risk scoring)
- `last_seen` — timestamp from agent; staleness alert if > 4 hours
- `tags` — freeform for env (prod/dev/staging), role, etc.

### CMDB agent
A local agent runs inside the agency network and populates the CMDB via an encrypted channel. The agent is responsible for:
- Discovering assets (network scan or integration with existing CMDB/IPAM)
- Resolving IP → hostname
- Mapping assets to FISMA boundaries
- Flagging stale records

**The quality of the CMDB directly determines the quality of the platform.** An incomplete or stale CMDB produces unmapped vulnerabilities. Target: >95% of vulnerability findings mapped to a known asset.

---

## Layer 3: Normalization & Correlation Engine

The same CVE will appear from multiple sources simultaneously (e.g., Tenable scan + CISA KEV + NVD). Without deduplication, this creates false volume and noise.

### Deduplication logic
1. Incoming findings are keyed on `(cve_id, asset_id)`
2. If a record already exists for that pair, sources are merged and enrichment data updated
3. Severity is taken from the highest-confidence source (CVSS from NVD preferred over scanner-reported)
4. KEV membership is cross-referenced on every ingest cycle

### Enrichment
Each CVE record is enriched with:
- CVSS v3.1 base score (from NVD)
- KEV membership flag + due date (from CISA)
- CWE classification
- Affected product CPEs

### Unmapped asset handling
If a finding's IP address cannot be matched to a CMDB record, it is flagged as **unmapped** and surfaced in the normalization log for manual CMDB reconciliation. This is the primary data quality feedback loop.

---

## Layer 4: Prioritization

Risk scoring combines multiple signals into a single prioritized view:

```
risk_score = cvss_base * asset_criticality_weight * kev_multiplier * boundary_multiplier
```

| Factor | Description |
|--------|-------------|
| `cvss_base` | NVD CVSS v3.1 base score (0–10) |
| `asset_criticality_weight` | HIGH=1.5, MED=1.0, LOW=0.7 |
| `kev_multiplier` | 2.0 if in CISA KEV catalog, else 1.0 |
| `boundary_multiplier` | HVA assets get 1.3x multiplier |

### BOD 22-01 SLA Engine
For KEV-listed vulnerabilities, the SLA engine tracks:
- Required remediation date (per CISA KEV catalog)
- Days remaining / days overdue
- Compliance status per FISMA boundary

SLA status is a top-line KPI and surfaced prominently in the CISO dashboard.

---

## Layer 5: AI Assistant — Model Router

The AI assistant provides a natural language interface over the platform's data. It is designed to be **model-agnostic** — the underlying model can be swapped via configuration without code changes.

### Model router
The router is a thin abstraction layer that:
- Accepts a query + context (relevant data from the platform)
- Routes to the configured backend
- Returns a structured or free-text response

### Supported backends
| Backend | Type | Data egress | Status |
|---------|------|-------------|--------|
| Llama 3.1 70B | Self-hosted (GovCloud) | None | ✅ Default |
| Mistral Large | Self-hosted (GovCloud) | None | ✅ Available |
| OpenAI GPT-4o | External API | Yes — requires AO approval | ⚠️ External |
| Anthropic Claude | External API | Yes — currently restricted per agency policy | 🔴 Restricted |

### Query routing
- **Keyword / structured queries** (CVE ID, hostname, boundary name) → direct database query, no AI round-trip
- **Conversational queries** (natural language) → model router → LLM with relevant context injected

### Use cases (Phase 1)
- Natural language search: "show me hosts running OpenSSL 3.0"
- Compliance queries: "which KEV vulnerabilities are past due in HVA-Core?"
- Plain language explanations: "explain CVE-2024-21762 in plain language"
- Draft generation (Phase 2): POA&M entries, notification memos, BOD status reports

---

## Layer 6: Actions (Phase 2)

Deferred pending stable data surfacing layer. Planned integrations:
- Jira / ServiceNow ticket creation
- POA&M workflow with status tracking
- SLA breach notifications (email / Teams)
- Remediation verification loop

---

## Security Architecture

### Authentication & Authorization
- **Provider:** Microsoft Entra ID (OAuth 2.0 / OIDC)
- **No local passwords** — all authentication delegated to Entra
- **MFA:** Inherited from agency Entra MFA policy
- **Role mapping:** Entra group membership → platform role (e.g., ISSO group → read-only, CISO group → full access)
- **Session:** JWT with configurable expiry; refresh via Entra

### Encryption
- **At rest:** AES-256 via RDS encrypted storage + encrypted EBS volumes
- **In transit:** TLS 1.3 enforced at all layers
  - Browser → application
  - Application → database
  - Connector layer → data sources (verified per connector; flagged if not supported)
  - CMDB agent → platform (mutual TLS preferred)

### Audit Logging
All events logged with: timestamp, user identity (from Entra), action, affected resource, source IP. Log retention per agency policy. Logs are append-only and stored separately from application database.

### Hosting
- AWS GovCloud (us-gov-east-1 or us-gov-west-1)
- FedRAMP High authorized
- All AI model inference runs in-region with no external API calls (default config)

### UI Security
- U.S. Government system notice banner displayed at login (ATO requirement)
- Classification bar: UNCLASSIFIED // CUI (parameterized per environment)
- No session persistence across browser close (configurable)

---

## Database Schema (Key Tables)

```sql
-- Assets (from CMDB agent)
assets (asset_id, ip_address, hostname, system_owner, fisma_boundary, criticality, last_seen, tags)

-- Vulnerabilities (normalized across sources)
vulnerabilities (vuln_id, cve_id, asset_id, cvss_score, severity, kev_member, kev_due_date, first_detected, last_seen, status)

-- Sources (per-finding source tracking)
vuln_sources (vuln_id, source_name, raw_data, ingested_at)

-- Connector config
connectors (connector_id, name, type, schedule, tls_verified, enabled, last_sync, last_count)

-- Audit log
audit_log (event_id, timestamp, user_id, action, resource_type, resource_id, source_ip)
```

---

## Development Approach

**MVP scope (Phase 1):** Tenable ingestion → CMDB integration → normalization → dashboard with KEV watch. Target: 8–12 weeks with 1–2 developers.

**Staffing note:** This platform requires someone to own it operationally. API version changes from Tenable, schema migrations, connector failures — these don't maintain themselves. Plan for a part-time developer or contractor with Python/FastAPI and React experience.
