# CIVIL-OS Sprint Roadmap v0.2
## From Phase-1 Prototype to Production System

---
Document ID: ROADMAP-001-v0.2
Date: 2026-08-31
Status: APPROVED
Based on: TSD-001 v0.1 + Phase-1 Implementation Review
---

## Legend

| Field | Meaning |
|-------|---------|
| **Story ID** | Unique identifier (PHASE-SPRINT-NUMBER) |
| **Points** | Fibonacci estimate (1, 2, 3, 5, 8, 13, 21) |
| **Priority** | Must / Should / Could / Won't (MoSCoW) |
| **AC** | Acceptance Criteria (Gherkin-style Given/When/Then) |
| **Deps** | Dependencies on other stories |

---

## Phase 1 — Hardening & Production Readiness (Sprints 1–4)
*Goal: Fix review findings, add missing foundational pieces, prepare for scale.*

### Sprint 1: Schema Hardening & Persistence (Weeks 1–2)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P1-S1-01 | Fix datetime round-trip in JSON persistence | 3 | Must | Given a project with created_at=2026-08-31T12:00:00+00:00, When exported to JSON and re-imported, Then created_at equals original exactly | — |
| P1-S1-02 | Implement true SHA-256 content hashing for ECP | 3 | Must | Given an ECP assembled twice with identical content, When version is computed, Then both versions are identical (idempotent) | — |
| P1-S1-03 | Populate ConfidenceSummary during ECP assembly | 5 | Must | Given a site with soil profiles having confidence levels A,C,E, When ECP is assembled, Then confidence_summary shows level_a_count=1, level_c_count=1, level_e_count=1 | P1-S1-02 |
| P1-S1-04 | Add thread-safe registry with RLock | 3 | Should | Given two threads registering projects simultaneously, When both complete, Then both projects exist with unique IDs | — |

### Sprint 2: CPO Service Decomposition (Weeks 3–4)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P1-S2-01 | Extract ProjectService from CPO | 5 | Must | Given project CRUD operations, When called through ProjectService, Then all operations succeed without CPO involvement | — |
| P1-S2-02 | Extract ECPService from CPO | 5 | Must | Given ECP assembly and retrieval, When called through ECPService, Then assembly rules r.1–r.5 execute correctly | P1-S2-01 |
| P1-S2-03 | Extract TaskService from CPO | 5 | Must | Given task lifecycle operations, When called through TaskService, Then state machine transitions execute correctly | P1-S2-01 |
| P1-S2-04 | Add event bus for state changes | 5 | Should | Given a task transitions to APPROVED, When the event bus is active, Then a TaskApprovedEvent is emitted with task_id and timestamp | P1-S2-03 |

### Sprint 3: Audit Trail & Rejection Flows (Weeks 5–6)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P1-S3-01 | Add project-level audit trail | 3 | Must | Given a project is updated, When audit log is queried, Then the update action, actor, before/after state are recorded | P1-S2-01 |
| P1-S3-02 | Add ECP-level audit trail | 3 | Must | Given an ECP is reassembled, When audit log is queried, Then version bump and change reason are recorded | P1-S2-02 |
| P1-S3-03 | Implement reject_task() and rework_task() | 3 | Must | Given a task under review with defects, When reject_task() is called, Then status becomes READY and rejection reason is logged | P1-S2-03 |
| P1-S3-04 | Implement BLOCKED state handling | 3 | Should | Given a task with unresolved blocking issues, When state is checked, Then status is BLOCKED and unblock conditions are listed | P1-S3-03 |

### Sprint 4: MCP Resources & Prompts (Weeks 7–8)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P1-S4-01 | Implement MCP resource endpoints | 5 | Must | Given a resource URI resource://project/{id}/site, When requested through MCP, Then site data is returned with proper schema | — |
| P1-S4-02 | Implement MCP prompt templates | 5 | Must | Given a prompt URI prompt://feasibility_study, When requested, Then a populated template with project variables is returned | P1-S4-01 |
| P1-S4-03 | Add MCP transport abstraction (stdio/HTTP) | 8 | Should | Given an MCP server configured for HTTP, When a tool is called via HTTP POST, Then the correct handler executes and returns JSON | P1-S4-01 |
| P1-S4-04 | Add dependency enforcement (lag_days) | 3 | Should | Given task B depends on task A with lag_days=3, When start_task(B) is called before A completes + 3 days, Then StateMachineError is raised | P1-S3-03 |

---

## Phase 2 — Site Intelligence (Sprints 5–8)
*Goal: GIS, climate, hazard data integration.*

### Sprint 5: GIS Data Layer (Weeks 9–10)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P2-S5-01 | Implement GeoJSON validation for Site.boundary | 3 | Must | Given a GeoJSON Polygon, When assigned to Site.boundary, Then it validates as proper GeoJSON | — |
| P2-S5-02 | Integrate GDAL for coordinate transformations | 5 | Must | Given coordinates in EPSG:4326, When transformed to EPSG:32637, Then result matches GDAL reference | — |
| P2-S5-03 | Implement DEM ingestion and slope calculation | 8 | Must | Given a GeoTIFF DEM, When ingested, Then slope map is generated with percent-slope values | P2-S5-02 |
| P2-S5-04 | Create mcp-gis server skeleton | 3 | Must | Given mcp-gis server started, When list_tools() is called, Then 5+ GIS tools are registered | — |

### Sprint 6: Satellite & Imagery (Weeks 11–12)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P2-S6-01 | Integrate satellite imagery API (Sentinel/AWS) | 8 | Must | Given lat/lon and date range, When imagery is requested, Then a GeoTIFF is retrieved and stored | P2-S5-04 |
| P2-S6-02 | Implement land-use classification from imagery | 13 | Should | Given satellite imagery, When classified, Then land-use categories match >80% ground truth | P2-S6-01 |
| P2-S6-03 | Implement drainage path extraction from DEM | 5 | Must | Given a DEM, When processed, Then flow accumulation and drainage paths are extracted | P2-S5-03 |

### Sprint 7: Climate & Hazard (Weeks 13–14)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P2-S7-01 | Implement mcp-climate server | 5 | Must | Given location coordinates, When wind_parameters requested, Then design wind speed with full derivation chain is returned | — |
| P2-S7-02 | Integrate seismic hazard database (USGS/GSHAP) | 8 | Must | Given coordinates, When seismic_parameters requested, Then PGA, soil class, and zone are returned | P2-S7-01 |
| P2-S7-03 | Implement flood frequency analysis | 8 | Must | Given rainfall records, When flood_frequency calculated, Then 100-year flood discharge is computed with confidence intervals | P2-S7-01 |
| P2-S7-04 | Implement hazard derivation chain logging | 3 | Must | Given any hazard value, When retrieved, Then full chain (Location→DataSource→Model→Standard→ReturnPeriod→Value) is recorded | P2-S7-01 |

### Sprint 8: Site Characterization Engine (Weeks 15–16)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P2-S8-01 | Implement automated site report generation | 8 | Must | Given project coordinates, When site_characterization_report is requested, Then a complete report with all hazards and data gaps is produced | P2-S6-03, P2-S7-03 |
| P2-S8-02 | Implement data gap analysis with investigation recommendations | 5 | Must | Given a site with missing data, When analyzed, Then prioritized investigation list with cost estimates is generated | P2-S8-01 |
| P2-S8-03 | Integrate survey data (GNSS, total station, LiDAR) | 5 | Should | Given survey point data, When ingested, Then coordinate transformation and accuracy assessment are performed | P2-S5-02 |

---

## Phase 3 — First Engineering Domain: Site Development (Sprints 9–16)
*Goal: End-to-end site development design workflow.*

### Sprint 9: Geotechnical Engine (Weeks 17–18)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P3-S9-01 | Implement structured SoilProfile schema | 3 | Must | Given borehole data, When ingested, Then layers with properties and confidence labels are validated | — |
| P3-S9-02 | Implement bearing capacity calculator (Terzaghi/Meyerhof) | 8 | Must | Given soil profile and foundation dimensions, When calculated, Then q_ult and q_all are computed with safety factor | P3-S9-01 |
| P3-S9-03 | Implement settlement calculator | 5 | Must | Given soil profile and loading, When calculated, Then immediate and consolidation settlement are computed | P3-S9-01 |
| P3-S9-04 | Create mcp-geotech server with 5+ tools | 3 | Must | Given mcp-geotech started, When tools listed, Then bearing_capacity, settlement, slope_stability are available | P3-S9-02 |

### Sprint 10: Slope Stability & Earthworks (Weeks 19–20)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P3-S10-01 | Implement Bishop simplified slope stability | 8 | Must | Given slope geometry and soil profile, When analyzed, Then factor of safety and critical slip surface are returned | P3-S9-04 |
| P3-S10-02 | Implement cut-and-fill optimization | 8 | Should | Given terrain model and design grades, When optimized, Then earthworks balance is achieved with minimal haul distance | P2-S5-03 |
| P3-S10-03 | Implement volume calculation from DEM | 3 | Must | Given two surfaces, When volumes calculated, Then cut and fill volumes match manual calculation within 2% | P2-S5-03 |

### Sprint 11: Hydraulics & Drainage (Weeks 21–22)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P3-S11-01 | Implement rational method hydrology | 5 | Must | Given catchment and rainfall, When runoff calculated, Then peak discharge is computed per standard | P2-S7-03 |
| P3-S11-02 | Implement open-channel design (Manning) | 5 | Must | Given Q, slope, and roughness, When designed, Then channel dimensions satisfy velocity constraints | P3-S11-01 |
| P3-S11-03 | Implement culvert design | 5 | Must | Given Q and headwater constraint, When designed, Then culvert diameter and inlet type are selected | P3-S11-02 |
| P3-S11-04 | Implement stormwater network design | 8 | Should | Given catchment and outfall, When network designed, Then pipe sizes and invert levels are computed | P3-S11-03 |

### Sprint 12: Road Alignment (Weeks 23–24)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P3-S12-01 | Implement horizontal alignment geometry | 5 | Must | Given PI coordinates and curve radii, When alignment computed, Then stationing, PC, PT coordinates are correct | — |
| P3-S12-02 | Implement vertical alignment (grades, curves) | 5 | Must | Given PVI stations and grades, When profile computed, Then K-values and sight distances satisfy standards | P3-S12-01 |
| P3-S12-03 | Implement cross-section generation | 3 | Must | Given alignment and terrain, When section generated, Then cut/fill areas are computed at each station | P3-S10-03 |

### Sprint 13: Cost & Schedule (Weeks 25–26)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P3-S13-01 | Implement quantity takeoff from design parameters | 5 | Must | Given earthworks volumes and pipe lengths, When QTO generated, Then quantities match manual calculation | P3-S10-03, P3-S11-04 |
| P3-S13-02 | Implement cost estimation with location factors | 5 | Must | Given quantities and location (SA), When estimated, Then total cost is within 15% of RS Means reference | P3-S13-01 |
| P3-S13-03 | Implement CPM scheduling | 8 | Must | Given WBS and activity list, When scheduled, Then critical path, float, and early/late dates are computed | — |
| P3-S13-04 | Create mcp-cost and mcp-schedule servers | 3 | Must | Given servers started, When tools listed, Then QTO, estimate, WBS, CPM tools are available | P3-S13-02, P3-S13-03 |

### Sprint 14: Code Compliance (Weeks 27–28)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P3-S14-01 | Expand codes registry to 20+ jurisdictions | 5 | Must | Given coordinates in any of 20 countries, When resolved, Then applicable codes are returned | P1-S1-04 |
| P3-S14-02 | Implement clause retrieval by reference | 5 | Must | Given "EC7-1:2024 Section 6.5", When retrieved, Then clause text and requirements are returned | P3-S14-01 |
| P3-S14-03 | Implement automated code checking | 8 | Should | Given a design and applicable code, When checked, Then pass/fail per clause is reported with deviations | P3-S14-02 |

### Sprint 15: BIM Foundation (Weeks 29–30)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P3-S15-01 | Integrate IfcOpenShell for IFC creation | 8 | Must | Given site elements, When IFC generated, Then file passes IFC schema validation | — |
| P3-S15-02 | Implement basic 3D site model generation | 8 | Must | Given terrain and design elements, When model generated, Then 3D geometry is viewable | P3-S15-01 |
| P3-S15-03 | Create mcp-bim server | 3 | Must | Given server started, When tools listed, Then create_ifc, query_elements, extract_quantities are available | P3-S15-02 |

### Sprint 16: Site Development Integration (Weeks 31–32)

| ID | Story | Points | Priority | AC | Deps |
|----|-------|--------|----------|-----|------|
| P3-S16-01 | Implement end-to-end site development workflow | 13 | Must | Given project requirements and site data, When workflow executed, Then complete design package (drawings, specs, cost, schedule) is produced | P3-S13-04, P3-S14-03, P3-S15-03 |
| P3-S16-02 | Implement interdisciplinary coordination checks | 5 | Should | Given drainage and road designs, When coordinated, Then conflicts are identified with resolution options | P3-S16-01 |
| P3-S16-03 | Pilot project execution with real data | 8 | Must | Given a real site development project, When executed, Then design package is produced with full traceability | P3-S16-01 |

---

## Summary Timeline

```
2026        2027                                            2028
|----Phase 1----|----Phase 2----|--------Phase 3--------|
S1  S2  S3  S4  S5  S6  S7  S8  S9  S10 S11 S12 S13 S14 S15 S16
^ Phase 1 complete (hardened prototype)
^ MVP production ready
```

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Commercial calculation engine licensing costs | Medium | High | Prioritize open-source; document API abstraction layer |
| GIS data source availability | Medium | Medium | Multi-source fallbacks; local caching |
| Code database completeness | High | Medium | Start with major jurisdictions; crowdsource expansion |
| Performance at scale (10k+ tasks) | Medium | High | Load testing in Sprint 4; Neo4j migration planned |
| Civil engineering SME availability | Medium | High | Structured review gates per sprint |

