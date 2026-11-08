# ADR-001: Risk-driven spiral development with mini-V increments

- Status: accepted
- Revision: 1
- Date: 2026-11-08
- Owner: architect
- Decision authority: project owner
- Affected requirements: all requirements in `requirements/system.yaml` and all
  technology-demonstration objectives in `docs/requirements/CONOPS.md`

## Context

Andromeda-v2 combines a flight vehicle, recovery system, avionics, navigation,
two radio links, video, software, and ground equipment. Several architecture
choices remain provisional, including the mission-success boundary, airframe
diameter, launcher interface, component set, mass distribution, recovery
volume, power architecture, and RF implementation.

A single-pass V-cycle would defer implementation until a broad requirement and
architecture freeze. That would leave important packaging, recovery, RF,
thermal, power, and integration assumptions untested for too long. Pure feature
agility would create the opposite problem: locally useful prototypes could
silently establish incompatible system architecture or bypass flight-safety
evidence.

## Decision

Use **risk-driven spiral development**, implemented as a sequence of bounded
**mini-V increments**.

Each increment answers one or more explicit architecture questions or retires a
named technical risk. It performs a complete, proportionate systems-engineering
loop:

1. identify the stakeholder or mission need and the architecture hypothesis;
2. allocate candidate requirements, interfaces, budgets, and success criteria;
3. define the verification method before building;
4. implement the smallest useful model, simulation, breadboard, or prototype;
5. verify it against the allocated criteria;
6. validate the result against the mission need;
7. update the architecture, requirements, budgets, risks, and next increment
   from the evidence.

Architecture work remains the program priority. Prototypes are selected by the
architecture uncertainty or risk they resolve, not by feature visibility.

## Baseline policy

The project will use progressive, controlled baselines rather than one global
early freeze:

- **Hypothesis:** open to rapid change; evidence is not yet sufficient for an
  architecture commitment.
- **Allocated baseline:** selected for the next integration increment; changes
  are allowed but require impact assessment and traceable evidence.
- **Flight baseline:** configuration controlled for qualification or flight;
  changes require the applicable reviews and regression evidence.

`TBD` values remain explicit. A prototype result does not become a released
requirement or verified flight capability until it has traceable evidence and
the applicable owner accepts it into a controlled baseline.

## Increment controls

Every mini-V increment shall identify:

- the question, risk, owner, and applicable requirement IDs;
- authoritative inputs and the current baseline state;
- predicted learning and the decision the evidence will support;
- prototype class and limitations;
- pass/fail criteria and verification method;
- interfaces and budgets that may change;
- safety and approval constraints;
- evidence, tool versions, configuration, and results;
- change-impact dispositions and the next architecture decision.

An increment is complete only when evidence has been reviewed and the result is
either incorporated, rejected, or recorded as inconclusive. “The prototype
worked” is not by itself verification or validation.

## Safety tailoring

Early increments prefer software models, simulations, fit mockups, low-energy
bench tests, cabled and attenuated RF tests, and non-flight engineering units.
Hardware programming, radiated RF transmission, energetic deployment,
structural proof tests, motor operations, and launch operations remain
approval-gated. Spiral development does not relax flight-readiness or safety
criteria.

## Alternatives considered

### Single-pass V-cycle

Provides strong decomposition and traceability but exposes this project to late
discovery of physical and cross-domain assumptions. Rejected as the governing
life-cycle model; the V remains useful inside every increment.

### Feature-driven agile development

Provides rapid visible progress but does not by itself ensure system-level
budgets, interfaces, safety, and verification completeness. Rejected as the
sole method.

### Unstructured concurrent prototyping

May create fast local learning, but results are difficult to integrate when
questions, configurations, and decision criteria are not recorded. Rejected.

## Consequences

- Requirements and architecture mature together with empirical evidence.
- Some early prototypes will intentionally be discarded.
- System budgets and interface records must be maintained earlier and more
  frequently.
- The architect selects and sequences architecture questions; subsystem owners
  execute bounded increments; the integrator independently checks traceability,
  interfaces, budgets, and evidence.
- Technical progress is measured by risk retired and decisions enabled, not by
  prototype count.

## References

- NASA Systems Engineering Handbook, system design as iterative and recursive:
  <https://www.nasa.gov/reference/4-0-system-design-processes/>
- NASA Systems Engineering Curriculum, discussion of Agile, Vee, and spiral
  life-cycle models:
  <https://ntrs.nasa.gov/api/citations/20210021839/downloads/SE-Curriculum-Intro.2021-09-20.pdf>
- INCOSE Systems Engineering Agility Primer, iterative incremental development
  and continual integration and test:
  <https://www.incose.org/docs/default-source/enchantment/230510enchchap-sysengagilityaspects.pdf>
