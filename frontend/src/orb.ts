/**
 * orb.ts — Orbe 3D de partículas animadas (Three.js)
 * R.O.N.Y — Estados:
 *   veille    → cinza escuro pulsando lentamente (modo espera)
 *   idle      → azul-índigo profundo
 *   listening → ciano elétrico
 *   thinking  → âmbar / dourado
 *   speaking  → violeta pulsante
 */

import * as THREE from "three";

export type OrbState = "veille" | "idle" | "listening" | "thinking" | "speaking";

interface OrbConfig {
  particleCount: number;
  radius: number;
  rotationSpeed: number;
}

const CONFIG: OrbConfig = {
  particleCount: 3200,
  radius: 1.6,
  rotationSpeed: 0.003,
};

// ── Palettes de couleurs par état ─────────────────────────────
const STATE_COLORS: Record<OrbState, { core: number; mid: number; outer: number }> = {
  veille: {
    core:  0x1e1e2e,   // quase preto — dormindo
    mid:   0x2a2a3e,
    outer: 0x111118,
  },
  idle: {
    core:  0x4f46e5,   // indigo
    mid:   0x6366f1,   // violet-bleu
    outer: 0x1e1b4b,   // indigo sombre
  },
  listening: {
    core:  0x06b6d4,   // cyan vif
    mid:   0x0ea5e9,   // bleu ciel
    outer: 0x0c4a6e,   // bleu profond
  },
  thinking: {
    core:  0xf59e0b,   // ambre
    mid:   0xfbbf24,   // or
    outer: 0x78350f,   // brun foncé
  },
  speaking: {
    core:  0xa855f7,   // violet
    mid:   0xd946ef,   // fuchsia
    outer: 0x4a044e,   // violet sombre
  },
};

const STATE_SPEEDS: Record<OrbState, number> = {
  veille:    0.001,   // quase parado
  idle:      0.003,
  listening: 0.012,
  thinking:  0.007,
  speaking:  0.018,
};

const STATE_SCALES: Record<OrbState, number> = {
  veille:    0.82,   // menor — recolhido
  idle:      1.0,
  listening: 1.08,
  thinking:  1.04,
  speaking:  1.12,
};

export function createOrb(canvas: HTMLCanvasElement) {
  // ── Scène Three.js ────────────────────────────────────────
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x000000, 0);

  const scene  = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100);
  camera.position.z = 4.5;

  // ── Géométrie sphérique de particules ────────────────────
  const geo      = new THREE.BufferGeometry();
  const positions = new Float32Array(CONFIG.particleCount * 3);
  const colors    = new Float32Array(CONFIG.particleCount * 3);
  const sizes     = new Float32Array(CONFIG.particleCount);
  const offsets   = new Float32Array(CONFIG.particleCount);

  for (let i = 0; i < CONFIG.particleCount; i++) {
    // Distribution sphérique uniforme
    const theta  = Math.random() * Math.PI * 2;
    const phi    = Math.acos(2 * Math.random() - 1);
    const r      = CONFIG.radius * (0.6 + Math.random() * 0.4);

    positions[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);

    colors[i * 3]     = 0.3;
    colors[i * 3 + 1] = 0.3;
    colors[i * 3 + 2] = 1.0;

    sizes[i]   = 0.015 + Math.random() * 0.025;
    offsets[i] = Math.random() * Math.PI * 2;
  }

  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("color",    new THREE.BufferAttribute(colors,    3));
  geo.setAttribute("size",     new THREE.BufferAttribute(sizes,     1));

  const mat = new THREE.PointsMaterial({
    size:          0.04,
    vertexColors:  true,
    transparent:   true,
    opacity:       0.9,
    sizeAttenuation: true,
    blending:      THREE.AdditiveBlending,
    depthWrite:    false,
  });

  const points = new THREE.Points(geo, mat);
  scene.add(points);

  // ── Sphère centrale lumineuse ─────────────────────────────
  const coreGeo  = new THREE.SphereGeometry(0.45, 32, 32);
  const coreMat  = new THREE.MeshBasicMaterial({ color: 0x4f46e5, transparent: true, opacity: 0.6 });
  const coreMesh = new THREE.Mesh(coreGeo, coreMat);
  scene.add(coreMesh);

  // Halo interne
  const haloGeo  = new THREE.SphereGeometry(0.65, 32, 32);
  const haloMat  = new THREE.MeshBasicMaterial({
    color: 0x6366f1, transparent: true, opacity: 0.15, side: THREE.BackSide,
  });
  const haloMesh = new THREE.Mesh(haloGeo, haloMat);
  scene.add(haloMesh);

  // ── Anneau orbital ────────────────────────────────────────
  const ringGeo  = new THREE.TorusGeometry(1.85, 0.008, 8, 120);
  const ringMat  = new THREE.MeshBasicMaterial({ color: 0x4f46e5, transparent: true, opacity: 0.25 });
  const ringMesh = new THREE.Mesh(ringGeo, ringMat);
  ringMesh.rotation.x = Math.PI / 5;
  scene.add(ringMesh);

  // ── État courant ──────────────────────────────────────────
  let currentState: OrbState = "idle";
  let targetScale  = 1.0;
  let currentScale = 1.0;
  let rotSpeed     = CONFIG.rotationSpeed;
  let volume       = 0.0;
  let frame        = 0;

  function applyColors(state: OrbState): void {
    const palette   = STATE_COLORS[state];
    const coreColor = new THREE.Color(palette.core);
    const midColor  = new THREE.Color(palette.mid);
    const outerColor= new THREE.Color(palette.outer);
    const col = geo.attributes.color as THREE.BufferAttribute;

    for (let i = 0; i < CONFIG.particleCount; i++) {
      const t = (positions[i * 3 + 1] / CONFIG.radius + 1) / 2;
      const c = t < 0.5
        ? coreColor.clone().lerp(midColor, t * 2)
        : midColor.clone().lerp(outerColor, (t - 0.5) * 2);
      col.setXYZ(i, c.r, c.g, c.b);
    }
    col.needsUpdate = true;

    (coreMat as THREE.MeshBasicMaterial).color.set(palette.core);
    (haloMat as THREE.MeshBasicMaterial).color.set(palette.mid);
    (ringMat as THREE.MeshBasicMaterial).color.set(palette.core);
  }

  // ── Redimensionnement ─────────────────────────────────────
  function resize(): void {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(canvas);
  resize();

  // ── Boucle d'animation ────────────────────────────────────
  function animate(): void {
    requestAnimationFrame(animate);
    frame++;

    const t    = frame * 0.01;
    const beat = currentState === "speaking"
      ? 1 + volume * 0.4 * Math.sin(t * 8)
      : 1 + 0.02 * Math.sin(t * 1.5);

    targetScale  = STATE_SCALES[currentState] * beat;
    currentScale += (targetScale - currentScale) * 0.08;
    points.scale.setScalar(currentScale);
    coreMesh.scale.setScalar(currentScale * 0.95);
    haloMesh.scale.setScalar(currentScale * 0.98);

    rotSpeed += (STATE_SPEEDS[currentState] - rotSpeed) * 0.04;
    points.rotation.y   += rotSpeed;
    points.rotation.x   += rotSpeed * 0.3;
    ringMesh.rotation.z += rotSpeed * 0.5;

    // Scintillement des particules
    if (frame % 3 === 0) {
      const pos = geo.attributes.position as THREE.BufferAttribute;
      for (let i = 0; i < CONFIG.particleCount; i += 20) {
        const idx = i * 3;
        const noise = 0.008 * Math.sin(t * 3 + offsets[i]);
        pos.setX(i, positions[idx]     + noise);
        pos.setY(i, positions[idx + 1] + noise * 0.7);
        pos.setZ(i, positions[idx + 2] + noise * 0.5);
      }
      pos.needsUpdate = true;
    }

    // Opacité du halo selon l'état
    const haloTarget = currentState === "idle" ? 0.10 : 0.22;
    haloMat.opacity += (haloTarget - haloMat.opacity) * 0.05;

    renderer.render(scene, camera);
  }

  animate();
  applyColors("idle");

  // ── API publique ──────────────────────────────────────────
  return {
    setState(state: OrbState): void {
      if (state === currentState) return;
      currentState = state;
      applyColors(state);
    },
    setVolume(v: number): void {
      volume = v;
    },
    getState(): OrbState {
      return currentState;
    },
  };
}
