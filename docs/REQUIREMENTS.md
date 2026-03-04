# IronFist — Requirements

## Functional Requirements

### FR-1: Multi-Source Vulnerability Ingestion
- The platform SHALL ingest vulnerability data from Tenable.sc / Tenable.io via API
- The platform SHALL ingest the CISA Known Exploited Vulnerabilities (KEV) catalog
- The platform SHALL ingest container scan findings
- The platform SHALL ingest NVD/NIST data for CVE enrichment
- The platform SHALL support vendor advisory RSS feeds as an optional connector
- The platform SHALL provide a connector framework allowing new sources to be added without modifying core platform logic
- Each connector SHALL display last sync time, record count, and TLS status in the UI

### FR-2: Asset Management (CMDB)
- The platform SHALL maintain an asset inventory populated by a local CMDB agent
- Each asset record SHALL include: IP address, hostname, system owner, FISMA boundary, criticality rating, and last-seen timestamp
- The platform SHALL flag assets as stale if not updated within a configurable threshold (default: 4 hours)
- The platform SHALL surface unmapped vulnerability findings (findings with no matching CMDB asset) for manual reconciliation
- The platform SHALL display CMDB coverage as a top-line metric (% of vulnerability findings mapped to known assets)

### FR-3: Normalization & Deduplication
- The platform SHALL deduplicate vulnerability findings across sources, keying on CVE ID + Asset ID
- The platform SHALL merge source attribution when the same CVE appears from multiple sources
- The platform SHALL enrich each CVE with NVD CVSS v3.1 score, CWE, and CPE data
- The platform SHALL cross-reference all findings against the CISA KEV catalog on every ingest cycle
- The platform SHALL log deduplication metrics (duplicates collapsed, unmapped assets) per cycle

### FR-4: Prioritization & Compliance
- The platform SHALL calculate a risk score for each vulnerability incorporating: CVSS score, asset criticality, KEV membership, and FISMA boundary
- The platform SHALL track BOD 22-01 remediation deadlines for all KEV-listed vulnerabilities
- The platform SHALL display days remaining / days overdue for each KEV finding
- The platform SHALL surface BOD 22-01 SLA compliance as a top-line KPI
- The platform SHALL provide a FISMA boundary view grouping vulnerabilities by system boundary

### FR-5: AI Assistant
- The platform SHALL provide a natural language query interface for vulnerability data
- The platform SHALL support a model router allowing the AI backend to be changed via configuration
- The platform SHALL default to a self-hosted LLM with no external data egress
- The platform SHALL distinguish between structured queries (direct DB lookup) and conversational queries (AI inference) and route accordingly
- The platform SHALL surface the active AI backend visibly in the UI

### FR-6: Search
- The platform SHALL provide a persistent global search bar accessible from all views
- The search bar SHALL support keyword lookups (CVE ID, hostname, FISMA boundary)
- The search bar SHALL support conversational natural language queries routed to the AI assistant
- Keyword matches SHALL return results without an AI round-trip

### FR-7: Reporting
- The platform SHALL provide a CISO-level dashboard with top-line KPIs
- The platform SHALL support POA&M export (Phase 2)
- The platform SHALL support OMB-formatted reporting (Phase 2)

### FR-8: UI Customization
- The platform SHALL allow upload of an agency logo replacing the default VulnOps mark
- The platform SHALL allow users to show, hide, and reorder dashboard panels
- The platform SHALL allow selection of accent color theme
- The platform SHALL persist user preferences per user account

---

## Security Requirements

### SR-1: Authentication
- The platform SHALL authenticate all users via Microsoft Entra ID (OAuth 2.0 / OIDC)
- The platform SHALL NOT maintain local user passwords
- The platform SHALL enforce MFA via the agency's existing Entra MFA policy
- The platform SHALL map Entra group membership to platform roles
- The platform SHALL display session expiry time and enforce session timeout

### SR-2: Encryption
- All data at rest SHALL be encrypted using AES-256
- All data in transit SHALL be encrypted using TLS 1.3 minimum
- The connector layer SHALL enforce TLS for all data source connections
- Connectors that cannot verify TLS SHALL be flagged in the UI
- The CMDB agent communication channel SHALL use mutual TLS (preferred)

### SR-3: Audit Logging
- The platform SHALL log all user authentication events
- The platform SHALL log all data access events (views, exports, searches)
- The platform SHALL log all configuration changes
- Audit logs SHALL be append-only and stored separately from application data
- Audit log retention SHALL comply with agency log retention policy

### SR-4: Hosting & Compliance
- The platform SHALL be hosted in AWS GovCloud or Azure Government
- The hosting environment SHALL be FedRAMP High authorized
- The platform SHALL display a U.S. Government system notice banner at login
- The platform SHALL display a classification/handling banner (e.g., UNCLASSIFIED // CUI) on all authenticated pages
- The AI inference backend SHALL default to in-region, self-hosted with no external API calls

### SR-5: Access Control
- The platform SHALL implement role-based access control (RBAC)
- Minimum roles: Read-Only (ISSO), Analyst, Administrator (CISO/staff)
- Role assignments SHALL be managed via Entra group membership
- Future: FISMA boundary-scoped access (users see only their boundary's data)

---

## Non-Functional Requirements

### NFR-1: Performance
- Dashboard SHALL load within 3 seconds under normal operating conditions
- Keyword search results SHALL return within 500ms
- AI assistant responses SHALL return within 10 seconds (self-hosted model)

### NFR-2: Availability
- Target uptime: 99.5% (non-critical internal tool)
- Scheduled maintenance windows permitted with 24-hour advance notice

### NFR-3: Maintainability
- All connector logic SHALL be modular and independently testable
- The AI backend SHALL be swappable via environment variable without code changes
- The platform SHALL use containerized deployment (Docker) for portability

### NFR-4: Data Freshness
- Tenable scan data SHALL be ingested at minimum every 24 hours
- CISA KEV catalog SHALL be checked for updates every 6 hours
- CMDB agent SHALL sync at minimum every 4 hours
- NVD enrichment data SHALL be refreshed weekly

---

## Out of Scope (Phase 1)
- Ticketing system integration (Jira, ServiceNow)
- POA&M workflow and tracking
- SLA breach notifications
- Remediation verification
- Mobile interface
- Classified network deployment (future ATO consideration)
