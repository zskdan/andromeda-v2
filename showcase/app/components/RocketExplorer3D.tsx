"use client";

import { useEffect, useRef, useState, type CSSProperties } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type ViewMode = "exterior" | "xray" | "exploded";
type ExperienceMode = "guided" | "explore";

type ComponentInfo = {
  title: string;
  group: string;
  status: string;
  description: string;
  station: string;
  accent: string;
};

const COMPONENTS: Record<string, ComponentInfo> = {
  vehicle: { title: "Complete vehicle", group: "Configuration v0.2", status: "Preliminary", description: "A 2.15 m modular flight-test platform with three structural sections and replaceable internal allocations.", station: "0–2,150 mm", accent: "#b7ff3c" },
  nose: { title: "Nose + recovery shell", group: "Structure", status: "Provisional geometry", description: "Von Kármán nose volume containing the main recovery allocation and the forward separation interface.", station: "0–550 mm", accent: "#d9dfdc" },
  parachute: { title: "Main parachute envelope", group: "Recovery", status: "Conflict open", description: "The current 104 × 180 mm packed envelope conflicts radially with the trial ogive station by 2.749 mm.", station: "370–550 mm", accent: "#ff5b5b" },
  separation: { title: "Separation module", group: "Mechanisms", status: "Conceptual", description: "An 80 mm allocation at the section 1–2 interface. Mechanism, harness and structural load path remain unresolved.", station: "550–630 mm", accent: "#f2b53d" },
  battery: { title: "Battery bay", group: "Power", status: "Allocation only", description: "A protected internal volume. Cell selection, restraint, isolation, venting and energy budget remain TBD.", station: "730–910 mm", accent: "#7b8582" },
  compute: { title: "K26 compute disk", group: "Avionics", status: "Envelope modeled", description: "Published K26 SOM envelope on the replaceable compute disk for embedded processing and high-rate workloads.", station: "x = 1,030 mm", accent: "#4bd37b" },
  rf: { title: "RF support disk", group: "Communications", status: "Conceptual", description: "Support allocation for the PlutoSDR and RF interfaces ahead of the navigation and antenna region.", station: "x = 1,130 mm", accent: "#3faee8" },
  pluto: { title: "PlutoSDR envelope", group: "Wideband RF", status: "Published envelope", description: "Longitudinal 117 × 79 × 24 mm enclosure. Connector service volume, mounts and thermal path remain TBD.", station: "1,180–1,297 mm", accent: "#4389ff" },
  ins: { title: "INS + dual GNSS disk", group: "Navigation", status: "Relocated · verification open", description: "The complete navigation node moved 240 mm aft to shorten GNSS feed paths. Installed mass, depth and thermal load remain TBD.", station: "x = 1,320 mm", accent: "#b473df" },
  antenna: { title: "GNSS antenna region", group: "RF-transparent bay", status: "Candidate allocation", description: "Two candidate ring-feed stations inside the fiberglass bay. Antenna design, feeds and coexistence are not verified.", station: "1,350–1,550 mm", accent: "#4fd5da" },
  motor: { title: "CTI Pro54 K570", group: "Propulsion", status: "Reference motor", description: "A 54 × 488 mm motor envelope in the aft module. Retention, thermal and integrated loads remain unverified.", station: "1,672–2,160 mm", accent: "#ef573f" },
  fins: { title: "Four-fin set", group: "Aerostructure", status: "Provisional geometry", description: "Four trapezoidal fins from the OpenRocket reference model. Flutter, stiffness and separation loads remain open.", station: "1,830–2,130 mm", accent: "#e85f45" },
};

const TREE = ["nose", "parachute", "separation", "battery", "compute", "pluto", "ins", "antenna", "motor", "fins"];

const CHAPTERS = [
  { number: "01", title: "Meet Andromeda", component: "vehicle", mode: "exterior" as ViewMode, explode: 0, copy: "Start with the complete 2.15 m modular flight-test vehicle." },
  { number: "02", title: "Inside the stack", component: "compute", mode: "exploded" as ViewMode, explode: 34, copy: "Separate the airframe to see replaceable disks, power, compute and RF allocations." },
  { number: "03", title: "Navigation move", component: "ins", mode: "xray" as ViewMode, explode: 18, copy: "Inspect the INS and dual-GNSS node relocated 240 mm aft to shorten RF paths." },
  { number: "04", title: "Wideband video", component: "pluto", mode: "xray" as ViewMode, explode: 12, copy: "Follow the PlutoSDR allocation that supports the experimental high-rate downlink." },
  { number: "05", title: "Return safely", component: "parachute", mode: "xray" as ViewMode, explode: 10, copy: "End at the recovery envelope—and the fit conflict still requiring resolution." },
];

type SceneEntry = { object: THREE.Object3D; baseX: number; direction: number; internal: boolean };

export function RocketExplorer3D() {
  const mountRef = useRef<HTMLDivElement>(null);
  const entriesRef = useRef<SceneEntry[]>([]);
  const shellsRef = useRef<THREE.MeshStandardMaterial[]>([]);
  const controlsRef = useRef<OrbitControls | null>(null);
  const [selected, setSelected] = useState("vehicle");
  const [mode, setMode] = useState<ViewMode>("exterior");
  const [explode, setExplode] = useState(0);
  const [experience, setExperience] = useState<ExperienceMode>("guided");
  const [activeChapter, setActiveChapter] = useState(0);
  const info = COMPONENTS[selected] ?? COMPONENTS.vehicle;

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#0b1211");
    scene.fog = new THREE.Fog("#0b1211", 4.4, 8);
    const camera = new THREE.PerspectiveCamera(37, 1, 0.01, 30);
    camera.position.set(2.7, 1.25, 2.15);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.minDistance = 1.4;
    controls.maxDistance = 6;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    scene.add(new THREE.HemisphereLight(0xddeee7, 0x101715, 2.2));
    const key = new THREE.DirectionalLight(0xffffff, 4.2);
    key.position.set(-2, 3, 4);
    scene.add(key);
    const lime = new THREE.PointLight(0xb7ff3c, 16, 4);
    lime.position.set(0.2, -0.2, 1.2);
    scene.add(lime);

    const grid = new THREE.GridHelper(8, 40, 0x31423d, 0x182320);
    grid.position.y = -0.48;
    scene.add(grid);

    const vehicle = new THREE.Group();
    vehicle.rotation.z = -0.08;
    scene.add(vehicle);
    const entries: SceneEntry[] = [];
    const shells: THREE.MeshStandardMaterial[] = [];

    const material = (color: string, transparent = false, opacity = 1) => new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0.28, transparent, opacity, depthWrite: opacity > 0.4 });
    const register = (object: THREE.Object3D, id: string, direction: number, internal: boolean) => {
      object.traverse((child) => { child.userData.componentId = id; });
      vehicle.add(object);
      entries.push({ object, baseX: object.position.x, direction, internal });
      return object;
    };
    const cylinder = (id: string, length: number, radius: number, x: number, color: string, direction: number, internal = true) => {
      const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 40, 1, false), material(color));
      mesh.rotation.z = Math.PI / 2;
      mesh.position.x = x;
      return register(mesh, id, direction, internal);
    };

    const noseMaterial = material("#c7cfcc", true, 0.35);
    shells.push(noseMaterial);
    const nose = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.55, 48, 1, true), noseMaterial);
    nose.rotation.z = Math.PI / 2;
    nose.position.x = -0.8;
    register(nose, "nose", -1.35, false);

    const shell = (id: string, length: number, x: number, color: string, direction: number) => {
      const mat = material(color, true, 0.32);
      shells.push(mat);
      const mesh = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, length, 48, 1, true), mat);
      mesh.rotation.z = Math.PI / 2;
      mesh.position.x = x;
      register(mesh, id, direction, false);
    };
    shell("vehicle", 0.8, -0.125, "#9eaaa6", -0.28);
    shell("antenna", 0.2, 0.375, "#53c9cf", 0.45);
    shell("vehicle", 0.6, 0.775, "#818b88", 1.15);

    cylinder("parachute", 0.18, 0.052, -0.615, "#e64f50", -1.15);
    cylinder("separation", 0.08, 0.058, -0.485, "#efb33d", -0.72);
    cylinder("battery", 0.18, 0.05, -0.255, "#515b58", -0.45);

    const diskData: Array<[string, number, string]> = [
      ["separation", -0.425, "#db453f"], ["battery", -0.38, "#e77d36"], ["battery", -0.135, "#e1ba3d"],
      ["compute", -0.09, "#3fb66b"], ["compute", -0.045, "#3fb66b"], ["rf", 0.055, "#3aabd8"], ["ins", 0.245, "#a861cc"],
    ];
    diskData.forEach(([id, x, color]) => cylinder(id, 0.008, 0.055, x, color, Math.sign(x || 1) * 0.35));

    const k26 = new THREE.Mesh(new THREE.BoxGeometry(0.012, 0.077, 0.06), material("#2aa75b"));
    k26.position.x = -0.045;
    register(k26, "compute", -0.25, true);
    const pluto = new THREE.Mesh(new THREE.BoxGeometry(0.117, 0.079, 0.024), material("#397de5"));
    pluto.position.x = 0.164;
    register(pluto, "pluto", 0.25, true);

    [0.32, 0.43].forEach((x) => {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.052, 0.003, 12, 48), material("#4fd5da"));
      ring.rotation.y = Math.PI / 2;
      ring.position.x = x;
      register(ring, "antenna", 0.48, true);
    });

    const motor = cylinder("motor", 0.488, 0.027, 0.841, "#d64635", 1.25);
    const nozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.023, 0.033, 0.055, 32), material("#323a38"));
    nozzle.rotation.z = Math.PI / 2;
    nozzle.position.x = 1.105;
    register(nozzle, "motor", 1.35, true);
    motor.userData.primary = true;

    for (let i = 0; i < 4; i += 1) {
      const fin = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.14, 0.006), material("#cf563e"));
      fin.position.x = 0.905;
      if (i % 2 === 0) { fin.position.y = i === 0 ? 0.115 : -0.115; }
      else { fin.rotation.x = Math.PI / 2; fin.position.z = i === 1 ? 0.115 : -0.115; }
      register(fin, "fins", 1.2, false);
    }

    for (let i = 0; i < 4; i += 1) {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.006, 0.006), material("#aeb7b4"));
      rail.position.set(0.4, Math.cos(i * Math.PI / 2) * 0.052, Math.sin(i * Math.PI / 2) * 0.052);
      register(rail, "antenna", 0.5, true);
    }
    entriesRef.current = entries;
    shellsRef.current = shells;

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const choose = (event: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hit = raycaster.intersectObject(vehicle, true).find((item) => item.object.userData.componentId);
      if (hit) {
        setExperience("explore");
        setSelected(hit.object.userData.componentId);
      }
    };
    renderer.domElement.addEventListener("pointerdown", choose);

    const resize = () => {
      const width = mount.clientWidth;
      const height = mount.clientHeight;
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    resize();

    let frame = 0;
    const animate = () => {
      frame = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      renderer.domElement.removeEventListener("pointerdown", choose);
      controls.dispose();
      vehicle.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry.dispose();
          const mats = Array.isArray(child.material) ? child.material : [child.material];
          mats.forEach((mat) => mat.dispose());
        }
      });
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, []);

  useEffect(() => {
    const amount = mode === "exploded" ? explode / 100 : 0;
    entriesRef.current.forEach(({ object, baseX, direction, internal }) => {
      object.position.x = baseX + direction * amount * (internal ? 0.52 : 0.8);
      object.visible = mode !== "exterior" || !internal;
      object.traverse((child) => {
        if (!(child instanceof THREE.Mesh) || !(child.material instanceof THREE.MeshStandardMaterial)) return;
        const id = child.userData.componentId;
        child.material.emissive.set(id === selected ? COMPONENTS[id]?.accent ?? "#b7ff3c" : "#000000");
        child.material.emissiveIntensity = id === selected ? 0.34 : 0;
      });
    });
    shellsRef.current.forEach((mat) => {
      mat.opacity = mode === "exterior" ? 0.92 : 0.19;
      mat.depthWrite = mode === "exterior";
      mat.needsUpdate = true;
    });
  }, [mode, explode, selected]);

  const selectComponent = (id: string) => {
    setExperience("explore");
    setSelected(id);
    if (id !== "vehicle" && mode === "exterior") setMode("xray");
    const entry = entriesRef.current.find(({ object }) => object.userData.componentId === id || object.children.some((child) => child.userData.componentId === id));
    if (entry && controlsRef.current) controlsRef.current.target.set(entry.object.position.x, 0, 0);
  };

  const openChapter = (index: number) => {
    const chapter = CHAPTERS[index];
    setExperience("guided");
    setActiveChapter(index);
    setSelected(chapter.component);
    setMode(chapter.mode);
    setExplode(chapter.explode);
    const entry = entriesRef.current.find(({ object }) => object.userData.componentId === chapter.component || object.children.some((child) => child.userData.componentId === chapter.component));
    if (entry && controlsRef.current) controlsRef.current.target.set(entry.object.position.x, 0, 0);
  };

  return (
    <div className="experience-shell">
      <div className="experience-bar">
        <div className="experience-mode" role="group" aria-label="Explorer experience mode">
          <button aria-pressed={experience === "guided"} onClick={() => openChapter(activeChapter)}>Guided story</button>
          <button aria-pressed={experience === "explore"} onClick={() => setExperience("explore")}>Free explore</button>
        </div>
        <div className="chapter-copy" aria-live="polite">
          <span>{CHAPTERS[activeChapter].number} / {String(CHAPTERS.length).padStart(2, "0")}</span>
          <div><strong>{experience === "guided" ? CHAPTERS[activeChapter].title : "You are in control"}</strong><p>{experience === "guided" ? CHAPTERS[activeChapter].copy : "Select any component, orbit the rocket, or change the engineering view."}</p></div>
        </div>
        <div className="chapter-controls">
          <button aria-label="Previous chapter" disabled={activeChapter === 0} onClick={() => openChapter(activeChapter - 1)}>←</button>
          <div>{CHAPTERS.map((chapter, index) => <button key={chapter.number} aria-label={`Open chapter ${chapter.number}: ${chapter.title}`} aria-current={experience === "guided" && activeChapter === index ? "step" : undefined} onClick={() => openChapter(index)} />)}</div>
          <button aria-label="Next chapter" disabled={activeChapter === CHAPTERS.length - 1} onClick={() => openChapter(activeChapter + 1)}>→</button>
        </div>
      </div>
      <div className="twin-shell">
      <aside className="component-browser">
        <div className="panel-label">Component tree</div>
        <button className={selected === "vehicle" ? "tree-active" : ""} onClick={() => selectComponent("vehicle")}><b>00</b><span>Complete vehicle</span></button>
        {TREE.map((id, index) => <button key={id} className={selected === id ? "tree-active" : ""} onClick={() => selectComponent(id)}><b>{String(index + 1).padStart(2, "0")}</b><span>{COMPONENTS[id].title}</span></button>)}
      </aside>

      <div className="twin-viewport">
        <div className="viewport-badge"><i /> Live 3D · parametric envelopes</div>
        <div className="viewport-help">Drag to orbit · scroll to zoom · select any part</div>
        <div ref={mountRef} className="three-mount" aria-label="Interactive three-dimensional model of the Andromeda v2 rocket" />
        <div className="viewer-controls">
          <div className="mode-switch" role="group" aria-label="3D view mode">
            {(["exterior", "xray", "exploded"] as ViewMode[]).map((item) => <button key={item} aria-pressed={mode === item} onClick={() => { setExperience("explore"); setMode(item); }}>{item === "xray" ? "X-ray" : item}</button>)}
          </div>
          <label><span>Explode</span><input type="range" min="0" max="100" value={explode} onChange={(event) => { setExperience("explore"); setExplode(Number(event.target.value)); setMode("exploded"); }} /></label>
        </div>
      </div>

      <aside className="component-inspector" style={{ "--component-accent": info.accent } as CSSProperties}>
        <div className="panel-label">Selected component</div>
        <div className="component-index">{String(Math.max(0, TREE.indexOf(selected) + 1)).padStart(2, "0")}</div>
        <span className="component-group">{info.group}</span>
        <h3>{info.title}</h3>
        <p>{info.description}</p>
        <dl><div><dt>Station</dt><dd>{info.station}</dd></div><div><dt>Engineering state</dt><dd>{info.status}</dd></div></dl>
        <div className="model-disclaimer"><i /> Geometry includes published dimensions and conceptual engineering envelopes. It is not manufacturing CAD.</div>
      </aside>
      </div>
    </div>
  );
}
