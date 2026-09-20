import {
  BufferAttribute,
  BufferGeometry,
  Color,
  DirectionalLight,
  DoubleSide,
  HemisphereLight,
  LineBasicMaterial,
  LineSegments,
  Mesh,
  MeshPhongMaterial,
  PerspectiveCamera,
  Raycaster,
  Scene,
  Vector2,
  Vector3,
  WebGLRenderer,
} from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

/** The dark theme's length ramp, the one the title plate and the poster use on the black field. */
export const RAMP = ["#4a1a08", "#b23a10", "#eb6834", "#f7cfae"];
/** The range the ramp spans, as in pipeline/hero_render.py. */
export const LENGTH_RANGE_UM = [200, 1000];
const VALUE_CEILING = 15;
/** Tissue in the connection modes, where the anatomy is only a frame of reference for the wiring. */
const QUIET_TISSUE = new Color("#41433a");
const OTHER = new Color("#6d6c66");
const LIT = new Color("#ffffff");
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
 * Draw the neuropils and every neck-crossing connection into `container`.
 *
 * The atlas mode gives each neuropil a solid surface shaded by the share of the wiring budget that ends in it;
 * the connection modes drop the anatomy to a translucent frame and let the wires carry the colour. `nodes` is
 * the price table, indexed by the scene's wire_node. `onHover` receives the neuropil under the pointer, or null.
 *
 * Returns handles for the overlay, the selection and the disposal of the view.
 */
export function createViewer(container, header, nodes, { reducedMotion = false, onHover } = {}) {
  const array = unpack(header);
  const { min, max } = header.bounds_um;
  const extent = Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2]);
  const regions = header.neuropils ?? [];

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

  // Kept deliberately contrasty: the neuropils are packed against each other, and it is the shading that tells
  // one lobe from the next when neighbours hold a similar share of the wire and take a similar colour.
  scene.add(new HemisphereLight(0xffffff, 0x14150f, 0.5));
  const key = new DirectionalLight(0xffffff, 1.5);
  key.position.set(-0.45, 0.7, 1);
  scene.add(key);
  // A dim warm light from behind and below keeps the far side of each lobe from going flat black.
  const rim = new DirectionalLight(0xffd7bb, 0.45);
  rim.position.set(0.7, -0.45, -0.7);
  scene.add(rim);

  const shellPositions = placed(array("shell_positions"), header);
  const shellGroup = array("shell_group");
  const shellGeometry = new BufferGeometry();
  shellGeometry.setAttribute("position", new BufferAttribute(shellPositions, 3));
  shellGeometry.setIndex(new BufferAttribute(array("shell_indices"), 1));
  shellGeometry.computeVertexNormals();
  const shellColors = new Float32Array(shellPositions.length);
  shellGeometry.setAttribute("color", new BufferAttribute(shellColors, 3));

  // Each neuropil takes its colour from its share of the wiring budget, on a square-root scale: the shares run
  // from nothing to a tenth, so a linear ramp would leave every region but a handful at the dark end.
  const topShare = Math.max(1e-9, ...regions.map((r) => r.wire_share ?? 0));
  const regionColor = regions.map((r) => rampColor(Math.sqrt((r.wire_share ?? 0) / topShare)));

  const shellMaterial = new MeshPhongMaterial({
    vertexColors: true,
    transparent: true,
    side: DoubleSide,
    specular: 0x2e241d,
    shininess: 16,
  });
  const shell = new Mesh(shellGeometry, shellMaterial);
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

  let mode = "atlas";
  let selected = null;
  let lit = -1;

  function paintShell() {
    const atlas = mode === "atlas";
    // Solid in the atlas, so the lobes read as separate bodies; a frame elsewhere, so the wires stay visible
    // through it. Writing depth in the atlas is what keeps the far side of the specimen from showing through.
    shellMaterial.opacity = atlas ? 1 : 0.15;
    shellMaterial.depthWrite = atlas;
    shell.renderOrder = atlas ? 0 : 2;
    for (let v = 0; v < shellGroup.length; v += 1) {
      const region = shellGroup[v];
      let color = atlas ? regionColor[region] ?? OTHER : QUIET_TISSUE;
      if (region === lit) color = color.clone().lerp(LIT, atlas ? 0.32 : 0.6);
      else if (atlas && lit >= 0) color = color.clone().multiplyScalar(0.38);
      shellColors[v * 3] = color.r;
      shellColors[v * 3 + 1] = color.g;
      shellColors[v * 3 + 2] = color.b;
    }
    shellGeometry.attributes.color.needsUpdate = true;
  }

  function paintWires() {
    const atlas = mode === "atlas";
    for (let i = 0; i < count; i += 1) {
      const t = clamp01((lengths[i] - LENGTH_RANGE_UM[0]) / (LENGTH_RANGE_UM[1] - LENGTH_RANGE_UM[0]));
      let color;
      let alpha;
      if (atlas) {
        // The solid neuropils swallow all but the stretch between them. Faint enough that the loose ends in the
        // cell-body rind stay below notice and only the neck, where thousands of them run together, shows.
        color = rampColor(t);
        alpha = 0.008 + 0.022 * t;
      } else if (mode === "rich") {
        color = rich[i] ? stops[2] : OTHER;
        alpha = rich[i] ? 0.1 : 0.016;
      } else if (mode === "value") {
        const value = nodes[wireNode[i]]?.value ?? 0;
        color = value > 0 ? rampColor(0.3 + 0.7 * clamp01(value / VALUE_CEILING)) : OTHER;
        alpha = value > 0 ? 0.115 : 0.014;
      } else {
        color = rampColor(t);
        alpha = 0.022 + 0.052 * t;
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

  function paint() {
    paintShell();
    paintWires();
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

  // Pointing at the specimen names the neuropil under the cursor and lights it. Only the anatomy is picked, and
  // only once per drawn frame: the merged shell carries around a hundred thousand triangles.
  const raycaster = new Raycaster();
  const pointer = new Vector2();
  let aim = null;

  function trackPointer(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    aim = [((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1];
  }

  function settle(next) {
    if (next === lit) return;
    lit = next;
    paintShell();
    onHover?.(next >= 0 ? regions[next] : null);
  }

  function resolvePointer() {
    if (!aim) return;
    pointer.set(aim[0], aim[1]);
    aim = null;
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster.intersectObject(shell, false)[0];
    settle(hit ? shellGroup[hit.face.a] : -1);
  }

  function releasePointer() {
    aim = null;
    settle(-1);
  }

  renderer.domElement.addEventListener("pointermove", trackPointer);
  renderer.domElement.addEventListener("pointerleave", releasePointer);

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
    resolvePointer();
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
    regions,
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
      renderer.domElement.removeEventListener("pointermove", trackPointer);
      renderer.domElement.removeEventListener("pointerleave", releasePointer);
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
