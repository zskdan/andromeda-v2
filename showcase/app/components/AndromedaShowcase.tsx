"use client";

import { useState } from "react";
import { RocketExplorer3D } from "./RocketExplorer3D";

type SystemId = "navigation" | "telemetry" | "video" | "ground";

const systems: Record<SystemId, { label: string; title: string; description: string; chain: string[]; metric: string; status: string }> = {
  navigation: {
    label: "NAV", title: "Navigation + common time",
    description: "A colocated INS and dual-GNSS node produces timestamped state estimates and distributes a qualified timing reference.",
    chain: ["IMU + sensors", "Navigation node", "Flight compute", "Mission record"], metric: "x = 1,320 mm", status: "Allocation defined",
  },
  telemetry: {
    label: "NB", title: "Essential telemetry + command",
    description: "The resilient narrowband service carries vehicle health, position and events while accepting a small authorized command set.",
    chain: ["Vehicle state", "NB modem", "RF channel", "Ground decoder"], metric: "≤ 100 ms", status: "Implementation TBD",
  },
  video: {
    label: "WB", title: "Wideband live video",
    description: "A selectable CP-OFDM link is intended to carry encoded multi-camera video with software-first validation before FPGA migration.",
    chain: ["H.265 cameras", "Packetizer", "OFDM PHY", "Ground video"], metric: "~50 Mbps", status: "Architecture input",
  },
  ground: {
    label: "GND", title: "Integrated mission control",
    description: "The ground segment receives, visualizes and records synchronized telemetry, trajectory, attitude, video and command evidence.",
    chain: ["RF receivers", "Data services", "Operator display", "Evidence archive"], metric: "20 Hz demo", status: "Prototype implemented",
  },
};

const requirementStatus = [
  ["SYS-RF-001", "Telemetry reception", "Not verified"], ["SYS-VIDEO-001", "Onboard video", "Not verified"],
  ["SYS-TC-001", "Ground telemetry", "Partially verified"], ["SYS-TC-002", "Authorized commands", "Not verified"],
  ["SYS-STRUCT-001", "Launcher compatibility", "Not verified"], ["SYS-FLIGHT-001", "Flight stability", "Not verified"],
  ["SYS-MASS-001", "Mass budget", "Not verified"],
];

function ArrowIcon() { return <span aria-hidden="true">↗</span>; }

export function AndromedaShowcase() {
  const [missionProgress, setMissionProgress] = useState(13);
  const [activeSystem, setActiveSystem] = useState<SystemId>("video");
  const system = systems[activeSystem];
  const apogeeProgress = 12.7;
  const altitude = missionProgress <= apogeeProgress
    ? 1857 * Math.sin((missionProgress / apogeeProgress) * Math.PI / 2)
    : 1857 * Math.max(0, 1 - (missionProgress - apogeeProgress) / (100 - apogeeProgress));
  const missionTime = (missionProgress / 100) * 144.98;
  const missionPhase = missionProgress < 1 ? "Liftoff" : missionProgress < apogeeProgress ? "Ascent" : missionProgress < 18 ? "Apogee / deployment" : missionProgress < 97 ? "Descent" : "Touchdown";

  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Andromeda home">
          <span className="brand-mark">A</span><span>ANDROMEDA <b>V2</b></span>
        </a>
        <nav aria-label="Primary navigation">
          <a href="#vehicle">Vehicle</a><a href="#mission">Mission</a><a href="#systems">Systems</a><a href="#status">Status</a>
        </nav>
        <a className="header-status" href="#status"><i /> Engineering prototype</a>
      </header>

      <section className="hero" id="top">
        <div className="hero-grid" aria-hidden="true" />
        <div className="hero-copy">
          <div className="kicker"><span>Experimental flight platform</span><span>Revision 0.2</span></div>
          <h1>Built to test<br /><em>beyond the lab.</em></h1>
          <p className="hero-lede">A modular sounding rocket for validating advanced navigation, communications, video and embedded computing in real flight conditions.</p>
          <div className="hero-actions">
            <a className="button button-primary" href="#vehicle">Explore the vehicle <ArrowIcon /></a>
            <a className="button button-quiet" href="#mission">View mission profile</a>
          </div>
          <dl className="hero-metrics">
            <div><dt>Nominal altitude</dt><dd>3,000 <small>m AGL</small></dd></div>
            <div><dt>Design envelope</dt><dd>10 <small>km</small></dd></div>
            <div><dt>Overall length</dt><dd>2.15 <small>m</small></dd></div>
          </dl>
        </div>

        <div className="hero-visual" aria-label="Technical illustration of the Andromeda v2 vehicle">
          <div className="orbit orbit-one" /><div className="orbit orbit-two" />
          <div className="rocket-vertical">
            <div className="rocket-nose" /><div className="rocket-body body-recovery"><span>RECOVERY</span></div><div className="rocket-band" />
            <div className="rocket-body body-avionics"><span>AVIONICS</span><i /><i /><i /></div>
            <div className="rocket-body body-rf"><span>RF</span></div><div className="rocket-body body-motor"><span>PROPULSION</span></div>
            <div className="fin fin-left" /><div className="fin fin-right" /><div className="rocket-nozzle" />
          </div>
          <div className="visual-label label-a"><span>120 mm</span><small>BODY Ø</small></div>
          <div className="visual-label label-b"><span>2,150 mm</span><small>OVERALL</small></div>
          <div className="visual-caption">CONFIGURATION / V0.2<br />NOT FOR FLIGHT</div>
        </div>
        <div className="scroll-cue"><span>Scroll to explore</span><i /></div>
      </section>

      <section className="vehicle-section digital-twin-section" id="vehicle">
        <div className="section-heading">
          <div><span className="section-number">01 / Interactive digital twin</span><h2>Take Andromeda<br />apart in 3D.</h2></div>
          <p>Orbit the complete vehicle, reveal its internal allocations, select components, or separate the architecture into an exploded engineering view.</p>
        </div>
        <RocketExplorer3D />
      </section>

      <section className="mission-section" id="mission">
        <div className="section-heading mission-heading">
          <div><span className="section-number">02 / Flight laboratory</span><h2>Replay the reference<br />mission.</h2></div>
          <div className="data-caveat"><strong>Archived sizing result</strong><span>OpenRocket v0.1 · preliminary · not verification evidence</span></div>
        </div>

        <div className="mission-console">
          <div className="flight-stage">
            <div className="altitude-scale" aria-hidden="true"><span>2,000 m</span><span>1,000 m</span><span>Ground</span></div>
            <div className="flight-chart" aria-label={`Illustrative mission profile at ${missionTime.toFixed(1)} seconds`}>
              <div className="chart-grid" />
              <div className="trajectory-fill" />
              <div className="apogee-line"><span>Historical apogee 1,857 m</span></div>
              <div className="flight-marker" style={{ left: `${missionProgress}%`, bottom: `${8 + (altitude / 2000) * 80}%` }}><i /><span>{missionPhase}</span></div>
            </div>
            <label className="timeline-control">
              <span>T+ {missionTime.toFixed(1)} s</span>
              <input aria-label="Mission timeline" type="range" min="0" max="100" value={missionProgress} onChange={(event) => setMissionProgress(Number(event.target.value))} />
              <span>T+ 145.0 s</span>
            </label>
          </div>

          <aside className="telemetry-panel">
            <div className="telemetry-head"><span>Reference playback</span><i>SIM</i></div>
            <div className="phase-readout"><small>Mission phase</small><strong>{missionPhase}</strong></div>
            <dl className="live-metrics">
              <div><dt>Interpolated altitude</dt><dd>{Math.round(altitude).toLocaleString()} <small>m</small></dd></div>
              <div><dt>Historical max velocity</dt><dd>235.6 <small>m/s</small></dd></div>
              <div><dt>Historical max acceleration</dt><dd>12.0 <small>g</small></dd></div>
              <div><dt>Historical stability</dt><dd>2.39 <small>cal</small></dd></div>
            </dl>
            <p>Altitude between recorded events is an illustrative interpolation. Restore and rerun the current model before using any result for design decisions.</p>
          </aside>
        </div>
      </section>

      <section className="systems-section" id="systems">
        <div className="section-heading">
          <div><span className="section-number">03 / Connected systems</span><h2>From sensor to<br />ground truth.</h2></div>
          <p>Explore the four end-to-end data paths that turn the vehicle into an instrumented flight-test platform.</p>
        </div>
        <div className="system-tabs" role="tablist" aria-label="Andromeda systems">
          {(Object.keys(systems) as SystemId[]).map((id) => <button key={id} role="tab" aria-selected={activeSystem === id} onClick={() => setActiveSystem(id)}><b>{systems[id].label}</b><span>{systems[id].title}</span></button>)}
        </div>
        <div className="system-detail">
          <div className="system-copy"><span>{system.status}</span><h3>{system.title}</h3><p>{system.description}</p><strong>{system.metric}</strong></div>
          <div className="data-chain" aria-label={`${system.title} data path`}>
            {system.chain.map((node, index) => <div className="chain-node" key={node}><small>0{index + 1}</small><b>{node}</b>{index < system.chain.length - 1 && <i aria-hidden="true">→</i>}</div>)}
          </div>
        </div>
      </section>

      <section className="status-section" id="status">
        <div className="section-heading status-heading">
          <div><span className="section-number">04 / Engineering status</span><h2>Evidence over<br />assumption.</h2></div>
          <p>Andromeda distinguishes implementation, verification and validation. A prototype is progress—not proof of flight readiness.</p>
        </div>
        <div className="status-summary">
          <div className="readiness-card"><span>System requirement verification</span><strong>1<small> / 7</small></strong><p>One requirement has partial evidence. No system requirement is fully verified.</p><div className="readiness-track"><i /></div></div>
          <div className="deliverable-grid">
            <article><i className="state-good" /><span>Control plane</span><strong>Implemented</strong><small>24 tests passing · 2 environment skips</small></article>
            <article><i className="state-warn" /><span>Mechanical packaging</span><strong>Preliminary</strong><small>CAD + STEP generated · recovery conflict open</small></article>
            <article><i className="state-warn" /><span>Ground visualization</span><strong>Partial evidence</strong><small>Simulation, replay and ingest prototype</small></article>
            <article><i className="state-off" /><span>Flight configuration</span><strong>Pending rerun</strong><small>Mass and integrated CG remain TBD</small></article>
          </div>
        </div>
        <div className="requirements-table">
          <div className="table-head"><span>Requirement</span><span>Capability</span><span>Integration result</span></div>
          {requirementStatus.map(([id, capability, status]) => <div className="table-row" key={id}><code>{id}</code><span>{capability}</span><b className={status.startsWith("Partially") ? "partial" : "not-verified"}>{status}</b></div>)}
        </div>
      </section>

      <footer>
        <div className="footer-brand"><span className="brand-mark">A</span><div><b>ANDROMEDA V2</b><small>Experimental flight platform</small></div></div>
        <p>Designed as a reusable testbed for communications, navigation, embedded computing and evidence-driven engineering.</p>
        <a href="#top">Back to top ↑</a>
      </footer>
    </main>
  );
}
