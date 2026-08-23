"use strict";

const byId = (id) => document.getElementById(id);
const finite = (value, fallback = null) => Number.isFinite(Number(value)) ? Number(value) : fallback;
const fmt = (value, digits = 1) => value == null ? "—" : Number(value).toFixed(digits);
const clamp = (value, lo, hi) => Math.max(lo, Math.min(hi, value));
const app = {
  state: null, receivedAt: 0, lastSequence: null, altitudeHistory: [], track: [], origin: null,
  maxAltitude: null, connected: false, renderer: null
};

function missionClock(seconds) {
  if (seconds == null) return "T− 00:00:00.000";
  const sign = seconds < 0 ? "T−" : "T+";
  let value = Math.abs(seconds);
  const hours = Math.floor(value / 3600); value -= hours * 3600;
  const minutes = Math.floor(value / 60); value -= minutes * 60;
  return `${sign} ${String(hours).padStart(2,"0")}:${String(minutes).padStart(2,"0")}:${value.toFixed(3).padStart(6,"0")}`;
}

function quaternionEuler(q) {
  if (!q) return null;
  const w=finite(q.w), x=finite(q.x), y=finite(q.y), z=finite(q.z);
  if ([w,x,y,z].some(v => v == null)) return null;
  const roll = Math.atan2(2*(w*x+y*z), 1-2*(x*x+y*y));
  const pitch = Math.asin(clamp(2*(w*y-z*x), -1, 1));
  const yaw = Math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z));
  return [roll,pitch,yaw].map(v => v*180/Math.PI);
}

function setConnection(state, label) {
  const node = byId("connection-state");
  node.dataset.state = state;
  node.querySelector("span").textContent = label;
}

function setBanner(kind, title, detail) {
  const node = byId("critical-banner");
  node.classList.toggle("active", Boolean(kind));
  node.classList.toggle("warning", kind === "warning");
  if (kind) { byId("critical-title").textContent = title; byId("critical-detail").textContent = detail; }
}

function sourceName(frame, mode) {
  const raw = frame?.source;
  const type = typeof raw === "string" ? raw : raw?.type;
  return (type || mode || "waiting").toUpperCase().replaceAll("_", " ");
}

function addHistory(frame) {
  if (!frame || frame.sequence === app.lastSequence) return;
  app.lastSequence = frame.sequence;
  const position = frame.position || {};
  const altitude = finite(position.altitude_m);
  if (altitude != null) {
    app.altitudeHistory.push(altitude);
    if (app.altitudeHistory.length > 180) app.altitudeHistory.shift();
    app.maxAltitude = app.maxAltitude == null ? altitude : Math.max(app.maxAltitude, altitude);
  }
  if (position.valid && finite(position.latitude_deg) != null && finite(position.longitude_deg) != null) {
    if (!app.origin) app.origin = {lat: Number(position.latitude_deg), lon: Number(position.longitude_deg)};
    const north = (Number(position.latitude_deg)-app.origin.lat)*111320;
    const east = (Number(position.longitude_deg)-app.origin.lon)*111320*Math.cos(app.origin.lat*Math.PI/180);
    app.track.push({east,north});
    if (app.track.length > 1500) app.track.shift();
  }
}

function setVector(prefix, vector, axes, scale) {
  axes.forEach(axis => {
    const value = finite(vector?.[axis]);
    byId(`${prefix}-${axis}`).textContent = fmt(value, 1);
    const bar = byId(`${prefix}-${axis}-bar`);
    const width = clamp(Math.abs(value || 0) / scale * 50, 0, 50);
    bar.style.width = `${width}%`;
    bar.style.left = value != null && value < 0 ? `${50-width}%` : "50%";
  });
}

function updateDisplay(state) {
  app.state = state;
  app.receivedAt = performance.now();
  const frame = state?.latest;
  const age = state?.data_age_ms;
  addHistory(frame);
  if (!frame) {
    setConnection("offline", "WAITING");
    setBanner("critical", "TELEMETRY UNAVAILABLE", "Waiting for the first valid frame");
    return;
  }

  const mode = String(state.mode || "unknown").toLowerCase();
  const badge = byId("source-badge");
  badge.className = `badge ${mode === "demo" ? "demo" : mode === "live" ? "live" : mode === "replay" ? "replay" : "neutral"}`;
  badge.textContent = mode === "demo" ? "SYNTHETIC" : mode.toUpperCase();
  badge.title = sourceName(frame, mode);
  byId("phase").textContent = String(frame.phase || "UNKNOWN").replaceAll("_", " ");
  byId("mission-time").textContent = missionClock(finite(frame.mission_time_s));
  byId("schema-version").textContent = `v${frame.schema_version ?? "—"}`;
  byId("sequence").textContent = frame.sequence ?? "—";
  byId("frame-time").textContent = frame.timestamp ? new Date(frame.timestamp).toISOString().slice(11,23) : "—";

  const stale = Boolean(state.stale);
  setConnection(stale ? "stale" : "online", stale ? "STALE" : "RECEIVING");
  const attitude = frame.attitude || {};
  const position = frame.position || {};
  const attitudeValid = Boolean(attitude.valid) && !stale;
  const positionValid = Boolean(position.valid) && !stale;
  const validity = byId("attitude-validity");
  validity.dataset.state = attitudeValid ? "valid" : "invalid";
  validity.querySelector("span").textContent = attitudeValid ? "SOLUTION VALID" : stale ? "STALE SOLUTION" : "INVALID SOLUTION";
  byId("attitude-age").textContent = age == null ? "—" : `${age} ms`;
  byId("position-age").textContent = age == null ? "AGE —" : `AGE ${age} ms`;
  byId("position-validity").textContent = positionValid ? "VALID FIX" : "NO VALID FIX";
  byId("position-validity").classList.toggle("valid", positionValid);
  byId("track-invalid").classList.toggle("active", !positionValid);

  const q = attitude.quaternion;
  const euler = quaternionEuler(q);
  byId("quaternion").textContent = q ? [q.w,q.x,q.y,q.z].map(v => fmt(finite(v),3)).join("  ") : "—";
  byId("roll").textContent = euler ? `${fmt(euler[0],1)}°` : "—";
  byId("pitch").textContent = euler ? `${fmt(euler[1],1)}°` : "—";
  byId("yaw").textContent = euler ? `${fmt(euler[2],1)}°` : "—";
  app.renderer?.setAttitude(q, attitudeValid);

  const altitude = finite(position.altitude_m);
  const velocity = frame.velocity_ned_m_s || {};
  const vertical = finite(velocity.down) == null ? null : -Number(velocity.down);
  byId("altitude").textContent = altitude == null ? "—" : Math.round(altitude).toLocaleString("en-US");
  byId("max-altitude").textContent = app.maxAltitude == null ? "—" : `${Math.round(app.maxAltitude).toLocaleString("en-US")} m`;
  byId("vertical-speed").textContent = fmt(vertical,1);
  const speedBar = byId("vertical-speed-bar");
  const speedWidth = clamp(Math.abs(vertical || 0)/160*50,0,50);
  speedBar.style.width = `${speedWidth}%`; speedBar.style.left = vertical != null && vertical < 0 ? `${50-speedWidth}%` : "50%";
  setVector("accel", frame.acceleration_body_m_s2, ["x","y","z"], 40);
  setVector("velocity", {n: velocity.north, e: velocity.east, d: velocity.down}, ["n","e","d"], 250);

  byId("latitude").textContent = positionValid ? `${fmt(finite(position.latitude_deg),6)}°` : "—";
  byId("longitude").textContent = positionValid ? `${fmt(finite(position.longitude_deg),6)}°` : "—";
  const vn=finite(velocity.north), ve=finite(velocity.east);
  const ground = vn == null || ve == null ? null : Math.hypot(vn,ve);
  const heading = ground == null ? null : (Math.atan2(ve,vn)*180/Math.PI+360)%360;
  byId("ground-speed").textContent = ground == null ? "—" : `${fmt(ground,1)} m/s`;
  byId("heading").textContent = heading == null ? "—" : `${fmt(heading,1)}°`;

  byId("packet-count").textContent = `${state.received_count || 0} RX`;
  byId("packet-errors").textContent = `${state.dropped_frames || 0} / ${state.out_of_order_frames || 0}`;
  const link = frame.link || {};
  const linkHealth = byId("link-health"); linkHealth.textContent = stale ? "STALE" : String(link.state || "RECEIVING"); linkHealth.dataset.state = stale ? "bad" : "good";
  byId("rssi").textContent = finite(link.rssi_dbm) == null ? "—" : `${fmt(link.rssi_dbm,0)} dBm`;
  byId("packet-rate").textContent = finite(link.packet_rate_hz) == null ? "—" : `${fmt(link.packet_rate_hz,1)} Hz`;
  const recording = byId("recording"); recording.innerHTML = `<i></i>${state.recording ? "ACTIVE" : "DISABLED"}`; recording.dataset.state = state.recording ? "good" : "bad";

  const health = frame.health || {};
  const overall = String(health.overall || "UNKNOWN"); byId("health-overall").textContent = overall; byId("health-overall").dataset.state = overall === "NOMINAL" ? "nominal" : "warning";
  byId("bus-voltage").textContent = finite(health.bus_voltage_v) == null ? "—" : `${fmt(health.bus_voltage_v,2)} V`;
  byId("board-temp").textContent = finite(health.board_temperature_c) == null ? "—" : `${fmt(health.board_temperature_c,1)} °C`;
  byId("cpu-load").textContent = finite(health.cpu_load_percent) == null ? "—" : `${fmt(health.cpu_load_percent,0)} %`;
  byId("storage-free").textContent = finite(health.storage_free_percent) == null ? "—" : `${fmt(health.storage_free_percent,0)} %`;
  byId("reset-count").textContent = health.reset_count ?? "—";
  const videoState = String(frame.video?.state || "UNKNOWN"); byId("video-state").textContent = videoState; byId("video-dot").className = ["STREAMING","RECORDING","STANDBY"].includes(videoState) ? "good" : "";
  byId("command-ack").textContent = String(frame.command?.last_ack || "NONE");

  renderEvents(frame.events || []);
  renderWarnings(frame.warnings || []);
  drawSparkline(); drawTrack();
  if (stale) setBanner("critical", "TELEMETRY STALE", `No fresh frame for ${age ?? "—"} ms; last values are retained`);
  else if (!attitude.valid) setBanner("critical", "ATTITUDE INVALID", "3D orientation is frozen at the last valid solution");
  else if (!position.valid) setBanner("warning", "POSITION INVALID", "Ground track is showing the last valid position");
  else if (mode === "demo") setBanner("warning", "SYNTHETIC DISPLAY DATA", "Deterministic UI exercise only — not a validated flight model or flight evidence");
  else setBanner(null);
}

function renderEvents(events) {
  byId("event-count").textContent = `${events.length} EVENT${events.length===1?"":"S"}`;
  const root = byId("event-timeline");
  if (!events.length) { root.innerHTML = '<li class="empty-event"><time>—</time><i></i><div><strong>WAITING FOR MISSION EVENTS</strong><span>Events received with telemetry appear here</span></div></li>'; return; }
  root.replaceChildren(...events.slice(-8).map(event => {
    const li=document.createElement("li"), time=document.createElement("time"), dot=document.createElement("i"), div=document.createElement("div"), strong=document.createElement("strong"), span=document.createElement("span");
    time.textContent=missionClock(finite(event.mission_time_s)); strong.textContent=String(event.name||"EVENT").replaceAll("_"," "); span.textContent=event.detail||"Telemetry event"; div.append(strong,span); li.append(time,dot,div); return li;
  }));
}

function renderWarnings(warnings) {
  byId("warning-count").textContent = warnings.length;
  const root=byId("warnings-list"); root.replaceChildren();
  if (!warnings.length) { const p=document.createElement("p"); p.className="empty-state"; p.textContent="NO ACTIVE WARNINGS"; root.append(p); return; }
  warnings.forEach(warning => { const p=document.createElement("p"); p.textContent=typeof warning === "string" ? warning : warning.message || JSON.stringify(warning); root.append(p); });
}

function canvasSize(canvas) {
  const dpr=Math.min(devicePixelRatio||1,2), rect=canvas.getBoundingClientRect(), w=Math.max(1,Math.round(rect.width*dpr)), h=Math.max(1,Math.round(rect.height*dpr));
  if (canvas.width!==w || canvas.height!==h) { canvas.width=w; canvas.height=h; } return {w,h,dpr};
}

function drawSparkline() {
  const canvas=byId("altitude-sparkline"), {w,h}=canvasSize(canvas), ctx=canvas.getContext("2d"), values=app.altitudeHistory; ctx.clearRect(0,0,w,h); if(values.length<2)return;
  const max=Math.max(10,...values), min=Math.min(0,...values); ctx.beginPath(); values.forEach((v,i)=>{const x=i/(values.length-1)*w,y=h-4-(v-min)/(max-min)*(h-8); i?ctx.lineTo(x,y):ctx.moveTo(x,y);}); ctx.strokeStyle="#33d6e6";ctx.lineWidth=1.5*(devicePixelRatio||1);ctx.stroke();
}

function drawTrack() {
  const canvas=byId("track-canvas"), {w,h,dpr}=canvasSize(canvas), ctx=canvas.getContext("2d"); ctx.clearRect(0,0,w,h); const cx=w/2,cy=h/2;
  ctx.strokeStyle="rgba(120,163,183,.15)";ctx.lineWidth=dpr; for(let i=1;i<=3;i++){ctx.beginPath();ctx.arc(cx,cy,Math.min(w,h)*.13*i,0,Math.PI*2);ctx.stroke();}
  ctx.beginPath();ctx.moveTo(cx,0);ctx.lineTo(cx,h);ctx.moveTo(0,cy);ctx.lineTo(w,cy);ctx.stroke(); if(!app.track.length)return;
  const extent=Math.max(25,...app.track.flatMap(p=>[Math.abs(p.east),Math.abs(p.north)]))*1.2, scale=Math.min(w,h)*.42/extent; byId("track-scale").textContent=`${Math.round(extent/2)} m`;
  ctx.beginPath();app.track.forEach((p,i)=>{const x=cx+p.east*scale,y=cy-p.north*scale;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.strokeStyle="#33d6e6";ctx.lineWidth=2*dpr;ctx.stroke();
  const p=app.track.at(-1),x=cx+p.east*scale,y=cy-p.north*scale;ctx.beginPath();ctx.arc(x,y,5*dpr,0,Math.PI*2);ctx.fillStyle="#ff8d45";ctx.fill();ctx.beginPath();ctx.arc(x,y,10*dpr,0,Math.PI*2);ctx.strokeStyle="rgba(255,141,69,.45)";ctx.stroke();
}

function matMultiply(a,b){const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];return o;}
function perspective(fov,aspect,near,far){const f=1/Math.tan(fov/2),nf=1/(near-far);return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)*nf,-1,0,0,2*far*near*nf,0]);}
function lookAt(e,t,u){let zx=e[0]-t[0],zy=e[1]-t[1],zz=e[2]-t[2],l=Math.hypot(zx,zy,zz);zx/=l;zy/=l;zz/=l;let xx=u[1]*zz-u[2]*zy,xy=u[2]*zx-u[0]*zz,xz=u[0]*zy-u[1]*zx;l=Math.hypot(xx,xy,xz);xx/=l;xy/=l;xz/=l;const yx=zy*xz-zz*xy,yy=zz*xx-zx*xz,yz=zx*xy-zy*xx;return new Float32Array([xx,yx,zx,0,xy,yy,zy,0,xz,yz,zz,0,-(xx*e[0]+xy*e[1]+xz*e[2]),-(yx*e[0]+yy*e[1]+yz*e[2]),-(zx*e[0]+zy*e[1]+zz*e[2]),1]);}
function quatMatrix(q){if(!q)return new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);let w=+q.w,x=+q.x,y=+q.y,z=+q.z,l=Math.hypot(w,x,y,z)||1;w/=l;x/=l;y/=l;z/=l;return new Float32Array([1-2*(y*y+z*z),2*(x*y+w*z),2*(x*z-w*y),0,2*(x*y-w*z),1-2*(x*x+z*z),2*(y*z+w*x),0,2*(x*z+w*y),2*(y*z-w*x),1-2*(x*x+y*y),0,0,0,0,1]);}

function rocketMesh(){const p=[],n=[],c=[],idx=[];const add=(pos,norm,col)=>{p.push(...pos);n.push(...norm);c.push(...col);return p.length/3-1;};
  function cylinder(radius,y0,y1,color,segments=32){for(let i=0;i<segments;i++){const a=i*2*Math.PI/segments,b=(i+1)*2*Math.PI/segments,ca=Math.cos(a),sa=Math.sin(a),cb=Math.cos(b),sb=Math.sin(b);const q=[add([radius*ca,y0,radius*sa],[ca,0,sa],color),add([radius*cb,y0,radius*sb],[cb,0,sb],color),add([radius*cb,y1,radius*sb],[cb,0,sb],color),add([radius*ca,y1,radius*sa],[ca,0,sa],color)];idx.push(q[0],q[1],q[2],q[0],q[2],q[3]);}}
  function cone(radius,y0,y1,color,segments=32){for(let i=0;i<segments;i++){const a=i*2*Math.PI/segments,b=(i+1)*2*Math.PI/segments,mid=(a+b)/2,ny=radius/(y1-y0),q=[add([radius*Math.cos(a),y0,radius*Math.sin(a)],[Math.cos(mid),ny,Math.sin(mid)],color),add([radius*Math.cos(b),y0,radius*Math.sin(b)],[Math.cos(mid),ny,Math.sin(mid)],color),add([0,y1,0],[Math.cos(mid),ny,Math.sin(mid)],color)];idx.push(...q);}}
  function fin(angle,color){const ca=Math.cos(angle),sa=Math.sin(angle), points=[[.28,-1.7,0],[.86,-2.25,0],[.72,-.65,0],[.28,-.45,0]], normal=[-sa,0,ca];const ids=points.map(([x,y,z])=>add([x*ca-z*sa,y,x*sa+z*ca],normal,color));idx.push(ids[0],ids[1],ids[2],ids[0],ids[2],ids[3],ids[2],ids[1],ids[0],ids[3],ids[2],ids[0]);}
  cylinder(.28,-2.15,1.65,[.73,.78,.81]);cylinder(.31,-1.75,-1.35,[.12,.16,.19]);cylinder(.29,.5,.72,[1,.34,.13]);cone(.28,1.65,2.65,[.92,.94,.95]);for(let i=0;i<4;i++)fin(i*Math.PI/2,[1,.28,.12]);return {p:new Float32Array(p),n:new Float32Array(n),c:new Float32Array(c),i:new Uint16Array(idx)};}

class RocketRenderer {
  constructor(canvas){this.canvas=canvas;this.gl=canvas.getContext("webgl",{antialias:true,alpha:true})||canvas.getContext("experimental-webgl");this.q={w:1,x:0,y:0,z:0};this.valid=false;this.az=.72;this.el=.23;this.distance=7.1;this.drag=null;if(!this.gl){byId("webgl-fallback").hidden=false;return;}this.init();this.bind();requestAnimationFrame(()=>this.render());}
  shader(type,source){const gl=this.gl,s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;}
  init(){const gl=this.gl,vs=this.shader(gl.VERTEX_SHADER,"attribute vec3 aP;attribute vec3 aN;attribute vec3 aC;uniform mat4 uM;uniform mat4 uVP;varying vec3 vN;varying vec3 vC;void main(){vN=mat3(uM)*aN;vC=aC;gl_Position=uVP*uM*vec4(aP,1.0);}"),fs=this.shader(gl.FRAGMENT_SHADER,"precision mediump float;varying vec3 vN;varying vec3 vC;uniform float uValid;void main(){vec3 n=normalize(vN);float l=.24+.76*max(dot(n,normalize(vec3(.5,.8,.7))),0.0);vec3 col=vC*l;if(uValid<.5)col=mix(col,vec3(.45,.15,.18),.45);gl_FragColor=vec4(col,1.0);}");this.program=gl.createProgram();gl.attachShader(this.program,vs);gl.attachShader(this.program,fs);gl.linkProgram(this.program);const mesh=rocketMesh();this.count=mesh.i.length;[["aP",mesh.p],["aN",mesh.n],["aC",mesh.c]].forEach(([name,data])=>{const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);const loc=gl.getAttribLocation(this.program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,3,gl.FLOAT,false,0,0);});const ib=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,ib);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,mesh.i,gl.STATIC_DRAW);this.uM=gl.getUniformLocation(this.program,"uM");this.uVP=gl.getUniformLocation(this.program,"uVP");this.uValid=gl.getUniformLocation(this.program,"uValid");gl.enable(gl.DEPTH_TEST);gl.enable(gl.CULL_FACE);gl.clearColor(0,0,0,0);}
  bind(){this.canvas.addEventListener("pointerdown",e=>{this.drag={x:e.clientX,y:e.clientY};this.canvas.setPointerCapture(e.pointerId);});this.canvas.addEventListener("pointermove",e=>{if(!this.drag)return;this.az+=(e.clientX-this.drag.x)*.008;this.el=clamp(this.el+(e.clientY-this.drag.y)*.006,-1.1,1.1);this.drag={x:e.clientX,y:e.clientY};});this.canvas.addEventListener("pointerup",()=>this.drag=null);this.canvas.addEventListener("wheel",e=>{e.preventDefault();this.distance=clamp(this.distance+e.deltaY*.006,4.5,12);},{passive:false});this.canvas.addEventListener("dblclick",()=>{this.az=.72;this.el=.23;this.distance=7.1;});}
  setAttitude(q,valid){if(valid&&q)this.q=q;this.valid=valid;}
  render(){if(!this.gl)return;const gl=this.gl,{w,h}=canvasSize(this.canvas);gl.viewport(0,0,w,h);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(this.program);const eye=[this.distance*Math.sin(this.az)*Math.cos(this.el),this.distance*Math.sin(this.el),this.distance*Math.cos(this.az)*Math.cos(this.el)],vp=matMultiply(perspective(Math.PI/4,w/h,.1,50),lookAt(eye,[0,0,0],[0,1,0]));gl.uniformMatrix4fv(this.uVP,false,vp);gl.uniformMatrix4fv(this.uM,false,quatMatrix(this.q));gl.uniform1f(this.uValid,this.valid?1:0);gl.drawElements(gl.TRIANGLES,this.count,gl.UNSIGNED_SHORT,0);requestAnimationFrame(()=>this.render());}
}

async function initialLoad(){try{const response=await fetch("/api/state",{cache:"no-store"});if(!response.ok)throw new Error();updateDisplay(await response.json());}catch{setConnection("offline","OFFLINE");setBanner("critical","GROUND SERVER OFFLINE","Unable to load the current telemetry state");}}
function connect(){const stream=new EventSource("/api/stream");stream.addEventListener("telemetry",event=>{app.connected=true;updateDisplay(JSON.parse(event.data));});stream.onopen=()=>app.connected=true;stream.onerror=()=>{app.connected=false;setConnection("offline","RECONNECTING");};}

app.renderer=new RocketRenderer(byId("vehicle-canvas"));
initialLoad();connect();
setInterval(()=>{byId("display-time").textContent=new Date().toISOString().slice(11,23);if(!app.state?.latest)return;const elapsed=Math.round(performance.now()-app.receivedAt),base=app.state.data_age_ms||0,age=base+elapsed,threshold=app.state.stale_threshold_ms||1000;byId("attitude-age").textContent=`${age} ms`;byId("position-age").textContent=`AGE ${age} ms`;if(age>threshold&&!app.state.stale)updateDisplay({...app.state,data_age_ms:age,stale:true});},200);
window.addEventListener("resize",()=>{drawSparkline();drawTrack();});
