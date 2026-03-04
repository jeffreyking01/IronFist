# IronFist
### Federal Vulnerability Management Platform

A custom-built vulnerability management platform designed for federal agency use. Built to replace commercial platforms with a purpose-built, agency-controlled solution that integrates natively with federal compliance requirements (FISMA, BOD 22-01, CISA KEV).

---

## Status
> 🟡 **Design phase** — Wireframes and architecture complete. Development not yet started.

---

## What This Is

IronFist is a multi-source vulnerability management platform designed around four core problems commercial tools don't solve well for federal agencies:

1. **Multi-source ingestion with a connector framework** — Tenable, container scanners, CISA KEV, NVD, and vendor advisories all feed into a single normalized view, with an extensible connector architecture for future sources.
2. **Asset-backed correlation** — A local CMDB agent populates asset inventory (IP → hostname → owner → FISMA boundary), which becomes the backbone for deduplication and prioritization.
3. **Federal compliance surfacing** — BOD 22-01 SLA tracking, CISA KEV cross-reference, and FISMA boundary views are first-class features, not afterthoughts.
4. **Model-agnostic AI assistant** — A natural language query interface backed by a model router, defaulting to a self-hosted LLM (Llama 3.1) in GovCloud with no data egress.

---

## Repository Structure

```
IronFist/
├── README.md
├── wireframes/
│   └── vuln-mgmt-wireframe-v4.html   # Interactive UI wireframe (open in browser)
└── docs/
    ├── ARCHITECTURE.md               # Full platform architecture decisions
    └── REQUIREMENTS.md               # Functional and security requirements
```

---

## Roadmap

### Phase 1 — Data Surfacing (current focus)
- [ ] Tenable API connector
- [ ] CISA KEV feed connector
- [ ] Container scanner connector
- [ ] NVD/NIST enrichment connector
- [ ] CMDB agent integration
- [ ] Normalization & deduplication engine
- [ ] Core dashboard UI
- [ ] KEV Watch / BOD 22-01 SLA view
- [ ] Entra ID SSO integration
- [ ] Global search (keyword + conversational AI)

### Phase 2 — Action Layer
- [ ] Ticketing integration (Jira / ServiceNow)
- [ ] POA&M workflow
- [ ] SLA notifications
- [ ] Remediation tracking

---

## Tech Stack (Planned)

| Layer | Technology |
|-------|-----------|
| Backend | Python + FastAPI |
| Database | PostgreSQL (FedRAMP-authorized RDS) |
| Frontend | React |
| Auth | Microsoft Entra ID (OAuth 2.0 / OIDC) |
| Hosting | AWS GovCloud |
| AI Backend | Llama 3.1 70B (self-hosted, GovCloud) |
| Orchestration | Python cron → Apache Airflow (later) |
| Containers | Docker |

---

## Security Posture

- **Authentication:** Microsoft Entra ID SSO + MFA (no local passwords)
- **Data at rest:** AES-256 (encrypted RDS + EBS volumes)
- **Data in transit:** TLS 1.3 enforced at all layers including connector ingestion
- **Hosting:** AWS GovCloud (FedRAMP High authorized)
- **AI data handling:** Self-hosted model — zero data egress by default
- **Audit logging:** All user actions and data access logged
- **Classification banner:** UNCLASSIFIED // CUI with U.S. Government system notice

---

## Viewing the Wireframe

Open `wireframes/vuln-mgmt-wireframe-v4.html` in any browser. No dependencies or build steps required.

The wireframe is interactive:
- Click **Sign in with Microsoft Entra ID** to enter the app
- Click **⊞** (top right) to open Workspace Preferences, including the model router
- Use the **search bar** in the topbar for keyword lookups or conversational AI queries
- Toggle panels and model backends in the Preferences panel

---

*This project is in active design. Not for production use.*
