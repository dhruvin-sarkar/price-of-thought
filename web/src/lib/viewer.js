import {
  BufferAttribute,
  BufferGeometry,
  Color,
  DirectionalLight,
  HemisphereLight,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshLambertMaterial,
  PerspectiveCamera,
  Scene,
  Vector3,
  WebGLRenderer,
} from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

/** The dark theme's length ramp, the one the title plate and the poster use on the black field. */
export const RAMP = ["#4a1a08", "#b23a10", "#eb6834", "#f7cfae"];
/** The range the ramp spans, as in pipeline/hero_render.py. */
export const LENGTH_RANGE_UM = [200, 1000];
const VALUE_CEILING = 15;
const TISSUE = 0x37392f;
const OTHER = new Color("#6d6c66");
const PITCH_DEG = 18;
const FOV_DEG = 28;
const MARGIN = 1.08;
const TYPED = { float32: Float32Array, uint32: Uint32Array, uint16: Uint16Array, uint8: Uint8Array };

const stops = RAMP.map((hex) => new Color(hex));

export function rampColor(t) {
  const x = Math.min(Math.max(t, 0), 1) * (stops.length - 1);
  const i = Math.min(Math.floor(x), stops.length - 2);
  return stops[i].clone().lerp(stops[i + 1], x - i);
}

const clamp01 = (v) => Math.min(Math.max(v, 0), 1);

function unpack(header) {
  const raw = atob(header.data);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
  return (key) => {
    const spec = header.arrays[key];
    return new TYPED[spec.dtype](bytes.buffer, spec.offset, spec.length);
  };
}

/**
 * Quantized coordinates turned back into micrometres, centred on the bounding box and with the voxel frame's
 * downward y and inward z turned to face the reader, as the still render does.
 */
function placed(quantized, header) {
  const { min, max } = header.bounds_um;
  const scale = [0, 1, 2].map((k) => (max[k] - min[k]) / header.steps);
  const centre = [0, 1, 2].map((k) => (min[k] + max[k]) / 2);
  const out = new Float32Array(quantized.length);
  for (let i = 0; i < quantized.length; i += 3) {
    out[i] = min[0] + quantized[i] * scale[0] - centre[0];
    out[i + 1] = -(min[1] + quantized[i + 1] * scale[1] - centre[1]);
    out[i + 2] = -(min[2] + quantized[i + 2] * scale[2] - centre[2]);
  }
  return out;
}

/**
 * Draw the neuropil shell and every neck-crossing connection into `container`.
 * `nodes` is the price table, indexed by the scene's wire_node, so a wire can be coloured by its cell type's value.
 * Returns handles for the overlay, the selection and the disposal of the view.
 */
export function createViewer(container, header, nodes, { reducedMotion = false } = {}) {
  const array = unpack(header);
  const { min, max } = header.bounds_um;
  const extent = Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2]);

  const renderer = new WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const scene = new Scene();
  const camera = new PerspectiveCamera(FOV_DEG, 1, extent / 200, extent * 20);
  // The still render pitches the specimen 18 degrees about the left-right axis and looks along the remaining
  // depth axis, which puts the brain above the nerve cord. In the flipped frame `placed` builds, that view is
  // reached from below the axis; pitching the other way folds the cord back over the brain.
  const pitch = (-PITCH_DEG * Math.PI) / 180;
  const forward = new Vector3(0, Math.sin(pitch), Math.cos(pitch));
  const up = new Vector3(0, Math.cos(pitch), -Math.sin(pitch));
  camera.up.set(0, 1, 0);

  scene.add(new HemisphereLight(0xffffff, 0x1a1b18, 1.5));
  const sun = new DirectionalLight(0xffffff, 1.1);
  sun.position.set(-0.4, 0.6, 1);
  scene.add(sun);

  const shellPositions = placed(array("shell_positions"), header);
  const shellGeometry = new BufferGeometry();
  shellGeometry.setAttribute("position", new BufferAttribute(shellPositions, 3));
  shellGeometry.setIndex(new BufferAttribute(array("shell_indices"), 1));
  shellGeometry.computeVertexNormals();
  const shell = new Mesh(
    shellGeometry,
    new MeshLambertMaterial({ color: TISSUE, transparent: true, opacity: 0.85, depthWrite: false }),
  );
  scene.add(shell);

  const lengthScale = (header.length_range_um[1] - header.length_range_um[0]) / header.steps;
  const quantizedLengths = array("wire_length");
  const lengths = new Float32Array(quantizedLengths.length);
  for (let i = 0; i < lengths.length; i += 1) lengths[i] = header.length_range_um[0] + quantizedLengths[i] * lengthScale;

  const rich = array("wire_rich_partner");
  const wireNode = array("wire_node");
  const count = lengths.length;
  const colors = new Float32Array(count * 8);
  const wireGeometry = new BufferGeometry();
  const wirePositions = placed(array("wire_positions"), header);
  wireGeometry.setAttribute("position", new BufferAttribute(wirePositions, 3));
  const colorAttribute = new BufferAttribute(colors, 4);
  wireGeometry.setAttribute("color", colorAttribute);
  // Straight alpha, as in the still render: 37,000 overlapping segments summed additively burn out to white.
  const wires = new LineSegments(
    wireGeometry,
    new LineBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false }),
  );
  wires.renderOrder = 1;
  scene.add(wires);

  let mode = "length";
  let selected = null;

  function paint() {
    for (let i = 0; i < count; i += 1) {
      const t = clamp01((lengths[i] - LENGTH_RANGE_UM[0]) / (LENGTH_RANGE_UM[1] - LENGTH_RANGE_UM[0]));
      let color;
      let alpha;
      if (mode === "length") {
        color = rampColor(t);
        alpha = 0.022 + 0.052 * t;
      } else if (mode === "rich") {
        color = rich[i] ? stops[2] : OTHER;
        alpha = rich[i] ? 0.1 : 0.016;
      } else {
        const value = nodes[wireNode[i]]?.value ?? 0;
        color = value > 0 ? rampColor(0.3 + 0.7 * clamp01(value / VALUE_CEILING)) : OTHER;
        alpha = value > 0 ? 0.115 : 0.014;
      }
      if (selected) alpha = selected.has(wireNode[i]) ? 0.85 : 0.008;
      for (let v = 0; v < 2; v += 1) {
        const o = i * 8 + v * 4;
        colors[o] = color.r;
        colors[o + 1] = color.g;
        colors[o + 2] = color.b;
        colors[o + 3] = alpha;
      }
    }
    colorAttribute.needsUpdate = true;
  }

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.enablePan = false;
  // The view turns slowly until the reader takes hold of it, and never turns for a reader who asked for less motion.
  controls.autoRotate = !reducedMotion;
  controls.autoRotateSpeed = 0.55;
  let touched = false;
  controls.addEventListener("start", () => {
    touched = true;
    controls.autoRotate = false;
  });

  // Every vertex reduced to what framing needs: how far along the view it lies, and how far off the axis it sits
  // sideways and vertically. Depth matters because a perspective camera magnifies whatever is nearest to it.
  const axial = (() => {
    const total = (shellPositions.length + wirePositions.length) / 3;
    const out = { depth: new Float32Array(total), side: new Float32Array(total), rise: new Float32Array(total) };
    const span = { x: [Infinity, -Infinity], y: [Infinity, -Infinity] };
    let n = 0;
    for (const points of [shellPositions, wirePositions]) {
      for (let i = 0; i < points.length; i += 3) {
        const x = points[i];
        const y = up.y * points[i + 1] + up.z * points[i + 2];
        out.depth[n] = forward.y * points[i + 1] + forward.z * points[i + 2];
        out.side[n] = x;
        out.rise[n] = y;
        n += 1;
        if (x < span.x[0]) span.x[0] = x;
        if (x > span.x[1]) span.x[1] = x;
        if (y < span.y[0]) span.y[0] = y;
        if (y > span.y[1]) span.y[1] = y;
      }
    }
    return { ...out, count: total, centre: [(span.x[0] + span.x[1]) / 2, (span.y[0] + span.y[1]) / 2] };
  })();

  const target = up.clone().multiplyScalar(axial.centre[1]);
  target.x = axial.centre[0];
  const targetDepth = forward.y * target.y + forward.z * target.z;

  /** Back the camera off until every vertex sits inside the frame, with a margin around the outline. */
  function frameView() {
    const tanV = Math.tan(((FOV_DEG / 2) * Math.PI) / 180);
    const tanH = tanV * Math.max(camera.aspect, 0.2);
    let distance = 0;
    for (let i = 0; i < axial.count; i += 1) {
      const depth = axial.depth[i] - targetDepth;
      const need = depth + Math.max(Math.abs(axial.rise[i] - axial.centre[1]) / tanV,
                                    Math.abs(axial.side[i] - axial.centre[0]) / tanH);
      if (need > distance) distance = need;
    }
    distance *= MARGIN;
    camera.position.copy(target).addScaledVector(forward, distance);
    controls.target.copy(target);
    controls.minDistance = distance * 0.3;
    controls.maxDistance = distance * 2.4;
    controls.update();
  }

  function resize() {
    const { clientWidth, clientHeight } = container;
    if (!clientWidth || !clientHeight) return;
    renderer.setSize(clientWidth, clientHeight, false);
    camera.aspect = clientWidth / clientHeight;
    camera.updateProjectionMatrix();
    // Reframing would fight a reader who has already moved the view, so it stops once they take hold.
    if (!touched) frameView();
  }

  const observer = new ResizeObserver(resize);
  observer.observe(container);
  resize();
  frameView();
  paint();

  let frame = 0;
  let running = true;
  function tick() {
    if (!running) return;
    frame = requestAnimationFrame(tick);
    controls.update();
    renderer.render(scene, camera);
  }
  tick();

  // The view keeps its place but stops drawing while it is off screen.
  const visibility = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting && !running) {
      running = true;
      tick();
    } else if (!entry.isIntersecting) {
      running = false;
      cancelAnimationFrame(frame);
    }
  });
  visibility.observe(container);

  return {
    wires: count,
    setMode(next) {
      mode = next;
      paint();
    },
    /** Show one cell type's wiring alone; pass null to show every connection again. */
    select(nodeIndex) {
      selected = nodeIndex == null ? null : new Set([nodeIndex]);
      paint();
    },
    dispose() {
      running = false;
      cancelAnimationFrame(frame);
      observer.disconnect();
      visibility.disconnect();
      controls.dispose();
      shellGeometry.dispose();
      shell.material.dispose();
      wireGeometry.dispose();
      wires.material.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
