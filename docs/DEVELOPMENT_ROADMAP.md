# Andromeda-v2 development roadmap

- Roadmap ID: ROADMAP-001
- Revision: 1
- Date: 2026-11-08
- Owner: architect
- Method: risk-driven spiral development with mini-V increments
- Current spiral: Spiral 0 — mission and architecture framing
- Status: preliminary; sequence approved, scope and dates not yet baselined

## 1. Purpose

This roadmap develops the Andromeda-v2 system through repeated, evidence-driven
architecture increments. It gives first priority to mission definition and the
overall architecture while starting targeted prototypes immediately to test the
assumptions on which architecture decisions depend.

The governing method is defined in
`architecture/decisions/ADR-001-spiral-mini-v-development.md`. The roadmap does
not treat the current 120 mm diameter, 2.15 m length, K570 motor, component
locations, or provisional mass and CG as frozen. They are current hypotheses
and model inputs until the relevant trade and verification evidence support a
controlled baseline.

No calendar commitments are invented in this revision. Each spiral is released
as a bounded backlog after its entry evidence and resources are known.

## 2. Product intent and current hypothesis

The current CONOPS describes a reusable experimental sounding rocket and
technology demonstrator with:

- a nominal 3,000 m AGL mission and an aspirational/configurable design envelope
  up to 10,000 m AGL;
- stable flight, authorized-volume containment, safe recovery, and retrieval;
- independent essential functions for recovery, navigation recording, and
  narrowband telemetry;
- narrowband telemetry and command plus wideband real-time video;
- onboard navigation, event detection, health monitoring, and recording;
- an integrated ground station and traceable post-flight reconstruction.

Spiral 0 shall determine which of these are mandatory for the first flight,
which are primary demonstrations, and which are later growth objectives.

## 3. Mini-V operating loop

Every roadmap increment follows the same loop:

| Mini-V step | Required output |
|---|---|
| Mission question | Named need, risk, assumptions, and applicable requirement IDs |
| Candidate definition | Requirement, interface, budget, architecture hypothesis, and predicted result |
| Test definition | Pass/fail criteria, verification method, configuration, safety controls, and evidence plan |
| Model or prototype | Smallest artifact capable of answering the question |
| Verification | Results compared with the predefined criteria |
| Mission validation | Finding on whether the result supports the intended use |
| Architecture update | Accepted decision, rejected option, retained TBD, impact review, and next increment |

Mini-V increments may overlap when their interfaces are explicit and neither
depends on an unrecorded result from the other. They do not bypass mandatory
cross-domain reviews or safety approvals.

## 4. Roadmap spirals

| Spiral | Architecture objective | Concurrent evidence prototypes | Exit baseline / evidence | Current status |
|---|---|---|---|---|
| 0. Mission and architecture framing | Define first-flight mission success; design-reference missions; mandatory versus growth capabilities; diameter and propulsion trades; top-level functional architecture; preliminary mass, volume, power, data, RF, thermal, and cost/resource budgets | Parametric flight-sizing sweep; full-scale internal-diameter/packaging mockup; recovery-volume packing trial; component-envelope survey; existing ground-display replay; cabled RF feasibility planning | Mission baseline v0.1, architecture trade record, selected or explicitly retained diameter options, architecture diagrams, top risks, and Spiral 1 backlog | **In progress** |
| 1. Feasibility architecture | Select the feasible physical and logical architecture; allocate subsystem requirements and interfaces; establish budget margins and fault-containment boundaries | Representative tube/avionics-stack mockup; recovery deployment concept rig; power/load breadboard; software OFDM reference and channel model; NB packet and ground-pipeline prototype; sensor/time-sync bench | Architecture baseline v0.2 and feasibility review showing no unidentified critical interface or impossible budget | Planned |
| 2. Subsystem breadboards | Mature subsystem designs against allocated requirements and close the highest subsystem risks | Recovery ground tests; avionics and power engineering unit; NB end-to-end link; one-Pluto cabled loopback; video encode/transport/decode; navigation and event-detection bench; structural coupons | Verified subsystem breadboards, updated budgets and ICDs, and an approved integrated-engineering-model configuration | Planned |
| 3. Integrated engineering model | Demonstrate cross-domain behavior using a non-flight or explicitly non-operational integrated article | Full avionics stack in representative structure; mission hardware-in-the-loop; RF coexistence; thermal/endurance run; fault injection; integrated recovery rig; mass-property measurement | Integrated architecture baseline v0.3, closed critical interface issues, and qualification configuration proposal | Planned |
| 4. Qualification and flight configuration | Establish that the controlled flight configuration satisfies its allocated requirements and operating limits | Structural and environmental evidence; launcher fit and departure analysis; recovery qualification; power/endurance test; full RF/video/telemetry/nav ground mission; rehearsals and readiness checks | Released flight baseline, verification matrix, approved operating envelope, and flight-readiness evidence | Planned |
| 5. Incremental flight demonstrations | Validate the architecture in representative flight while limiting each flight to an approved evidence objective | First flight prioritizes mandatory safe-flight, recovery, essential telemetry, navigation, and recording; later flights add or expand WB video, multi-camera, FPGA PHY, and extended-envelope objectives | Post-flight reconstruction, validated findings, anomaly dispositions, and next-spiral architecture update | Planned |

Passing a spiral does not mean every system requirement is verified. It means
the named maturity and evidence criteria are met and remaining uncertainties are
explicitly accepted into the next spiral.

## 5. Spiral 0: active backlog

### 5.1 Architecture definition — priority workstream

| ID | Increment | Decision enabled | Evidence / completion criterion | Owner | Status |
|---|---|---|---|---|---|
| S0-A01 | Mission-success partition | First-flight mandatory, primary, secondary, and growth objectives | Every CONOPS objective classified for the first flight; conflicts and TBD thresholds recorded | architect | Ready |
| S0-A02 | Design-reference missions | Nominal and bounding cases used by every subsystem | Nominal 3 km case, credible off-nominal cases, and the role of the 10 km envelope are defined without inventing launch-site data | architect / flight_dynamics | Blocked by S0-A01 |
| S0-A03 | Diameter and outer-architecture trade | Airframe diameter option(s), section concept, and retained margins | Current 120 mm option and credible alternatives compared on mission performance, usable bore, recovery volume, component fit, structural mass, drag, materials, launcher compatibility, and growth margin | architect / structures_mechanisms | Blocked by S0-A01 and S0-A02 |
| S0-A04 | Propulsion and launcher compatibility | Feasible motor class and launcher constraints for each architecture option | Parametric results and draft launcher ICD identify feasible combinations and unresolved external constraints | flight_dynamics / structures_mechanisms | Blocked by S0-A02 |
| S0-A05 | Functional and fault-containment architecture | Essential versus experimental functions and system boundaries | Functional block diagram, safe-state behavior, power/data dependencies, and failure-containment boundaries traced to `TDO-ISO-001` | architect | Blocked by S0-A01 |
| S0-A06 | Preliminary system budgets | Feasibility and margin visibility | Controlled mass, volume, power, energy, data-rate, storage, RF, thermal, and timing ledgers with sources and explicit TBDs | architect / integrator | Blocked by S0-A03 and S0-A05 |
| S0-A07 | Architecture baseline review | Authorization to enter Spiral 1 | Independent integration check confirms decisions, interfaces, budgets, risks, prototype results, and open issues are traceable | integrator | Blocked by S0-A01 through S0-A06 |

### 5.2 Concurrent risk-retirement prototypes

These prototypes may start before architecture selection because they test
assumptions needed by S0-A03 through S0-A06. Their configurations must not be
presented as selected flight designs.

| ID | Prototype question | Minimum artifact | Result consumed by | Safety / limitation | Status |
|---|---|---|---|---|---|
| S0-P01 | How much usable internal volume do candidate diameters provide after real wall, coupler, fastener, connector, and cable allowances? | Full-scale cross-section and short representative tube/stack mockups for each retained diameter | S0-A03, S0-A06 | Fit evidence only; not structural evidence | Ready after candidate diameters are named |
| S0-P02 | Can a credible dual-deploy recovery set fit and be serviced without the recorded ogive conflict? | Inert packed-volume and extraction mockup using representative masses and dimensions | S0-A03, recovery allocation | No energetic deployment in Spiral 0 | Ready after recovery concept bounds are recorded |
| S0-P03 | Which diameter/mass/motor combinations plausibly meet nominal altitude, stability, rail departure, and recovery constraints? | Reproducible parametric simulation with sensitivity ranges, not a single-point result | S0-A02 through S0-A04 | Uses documented assumptions; not flight verification | Ready after design-reference cases are drafted |
| S0-P04 | Can the telemetry schema, recording, replay, and GUI support architecture experiments? | Existing synthetic/replay ground-station path with a documented adapter boundary | S0-A05 and later HIL increments | Already implemented; not flight validated and no command path | Partially complete |
| S0-P05 | Is the proposed WB waveform feasible before committing the flight RF architecture? | Python reference model followed by impairment simulation and a protected, cabled, attenuated one-Pluto loopback | S0-A05, S0-A06 and Spiral 1 RF allocation | Radiated transmission is approval-gated; one-Pluto results do not prove the flight link | Planned under the existing six-phase WB roadmap |
| S0-P06 | Are preliminary power-domain and endurance assumptions credible? | Load inventory plus programmable or representative low-voltage load profile | S0-A05, S0-A06 | Bench evidence only; flight batteries and protection remain unselected | Ready after S0-A01 |

## 6. Architecture decision order

The intended order is:

1. mission-success tiers and design-reference missions;
2. mandatory payload/function set and fault-containment boundaries;
3. candidate diameter, section, propulsion, and launcher combinations;
4. cross-domain feasibility prototypes and parametric trades;
5. preliminary budgets and margins;
6. diameter and architecture decision or a documented reason to retain multiple
   options for another increment;
7. subsystem allocation and deeper prototypes.

This order prevents component selection from silently deciding the architecture,
while allowing prototypes to produce the evidence needed for timely decisions.

## 7. Reviews and change control

- A short architecture review closes each mini-V increment.
- A spiral review approves entry into the next spiral and its bounded backlog.
- Allocated baselines can change when new evidence justifies the change; the
  change must identify affected requirements, interfaces, budgets, models,
  prototypes, and prior evidence.
- Every repository change is assessed against
  `integration/change-impact-rules.json`.
- Flight-driving mechanical or mass changes invoke `XDOM-MECH-SIM-001`.
- Electronics hardware changes invoke `XDOM-ELEC-MECH-001`.
- Verification status remains separate from implementation and validation.

## 8. Program measures

Progress reporting shall include:

- architecture questions answered versus open;
- critical risks retired, reduced, accepted, or increased;
- requirements and interfaces with evidence-backed allocations;
- budget margin and number of unsupported/TBD inputs;
- prototype findings incorporated into decisions;
- verification coverage and unresolved anomalies;
- rework caused by missed interfaces or unrecorded assumptions.

Prototype count and code volume are not program-level progress measures.

## 9. Immediate next action

Execute `S0-A01`: review the CONOPS objectives and produce a first-flight
mission-success partition. In parallel, prepare the input templates for the
diameter trade (`S0-A03`) and packaging/recovery prototypes (`S0-P01` and
`S0-P02`) without selecting a diameter in advance.

## 10. Open issues

- First-flight objective partition is not approved.
- Nominal launch site, authorized flight volume, launcher, wind envelope, and
  regulatory constraints are TBD.
- Diameter alternatives and trade weights are TBD; 120 mm remains provisional.
- Resource, cost, procurement-lead-time, and calendar constraints are TBD.
- Spiral review authority below the project owner and required participants are
  not yet formalized.
- Hardware access beyond the currently recorded single PlutoSDR is TBD.
