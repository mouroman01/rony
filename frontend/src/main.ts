/**
 * main.ts — Interface principale de R.O.N.Y
 * WebSocket sur ws://localhost:8766 | Multilingue
 */

import { createOrb, type OrbState } from "./orb";
import "./style.css";

// ── Config ────────────────────────────────────────────────────
const WS_URL              = `ws://${window.location.hostname}:8765`;
const RECONNECT_INTERVAL  = 2_500;

// ── DOM ───────────────────────────────────────────────────────
const canvas          = document.getElementById("orb-canvas")       as HTMLCanvasElement;
const statusEl        = document.getElementById("status-text")       as HTMLDivElement;
const errorEl         = document.getElementById("error-text")        as HTMLDivElement;
const badgeEl         = document.getElementById("connection-badge")  as HTMLDivElement;
const badgeLabelEl    = document.getElementById("connection-label")  as HTMLSpanElement;
const subtitleBox     = document.getElementById("subtitle-box")      as HTMLDivElement;
const subtitleTextEl  = document.getElementById("subtitle-text")     as HTMLParagraphElement;
const langBadge       = document.getElementById("lang-badge")        as HTMLDivElement;
const langFlagEl      = document.getElementById("lang-flag")         as HTMLSpanElement;
const langCodeEl      = document.getElementById("lang-code")         as HTMLSpanElement;
const muteBtn         = document.getElementById("mute-button")       as HTMLButtonElement;
const captureBtn      = document.getElementById("capture-button")    as HTMLButtonElement;
const mobileBtn       = document.getElementById("mobile-button")     as HTMLButtonElement;
const keyboardToggle  = document.getElementById("keyboard-toggle")   as HTMLButtonElement;
const helpToggle      = document.getElementById("help-toggle")       as HTMLButtonElement;
const keyboardHud     = document.getElementById("keyboard-hud")      as HTMLDivElement;
const keyboardInput   = document.getElementById("keyboard-input")    as HTMLInputElement;
const keyboardSend    = document.getElementById("keyboard-send")     as HTMLButtonElement;
const helpOverlay     = document.getElementById("help-overlay")      as HTMLDivElement;
const helpClose       = document.getElementById("help-close")        as HTMLButtonElement;
const helpCommandsEl  = document.getElementById("help-commands")     as HTMLDivElement;
const langModal       = document.getElementById("lang-modal")        as HTMLDivElement;
const langClose       = document.getElementById("lang-close")        as HTMLButtonElement;
const langList        = document.getElementById("lang-list")         as HTMLDivElement;
const realtimeBtn     = document.getElementById("realtime-button")   as HTMLButtonElement;
const arBtn           = document.getElementById("ar-button")         as HTMLButtonElement;
const arPanel         = document.getElementById("ar-panel")          as HTMLDivElement;
const arVideo         = document.getElementById("ar-video")          as HTMLVideoElement;
const arOverlay       = document.getElementById("ar-overlay")        as HTMLCanvasElement;
const arStatus        = document.getElementById("ar-status")         as HTMLSpanElement;
const arClose         = document.getElementById("ar-close")          as HTMLButtonElement;
const mobileModal     = document.getElementById("mobile-modal")      as HTMLDivElement;
const mobileClose     = document.getElementById("mobile-close")      as HTMLButtonElement;
const mobileUrlBtn    = document.getElementById("mobile-url")        as HTMLButtonElement;
const mobileHint      = document.getElementById("mobile-hint")       as HTMLParagraphElement;

// ── Badge Modo Especialista ───────────────────────────────────
let specialistBadge: HTMLDivElement | null = null;

function showSpecialistBadge(modo: string | null, nome: string, isAuto = false): void {
  // Remove badge anterior
  if (specialistBadge) { specialistBadge.remove(); specialistBadge = null; }
  if (!modo) return;

  const icons: Record<string, string> = {
    analista: "📊",
    desenvolvedor: "💻",
    seguranca: "🛡️",
    ambos: "🧠",
    tudo: "⚡",
  };
  const icon = icons[modo] || "🔬";
  const badge = document.createElement("div");
  badge.id = "specialist-badge";
  badge.style.cssText = [
    "position:fixed", "top:16px", "left:50%", "transform:translateX(-50%)",
    "background:rgba(99,102,241,0.92)", "color:#fff",
    "padding:6px 18px", "border-radius:20px", "font-size:13px",
    "font-weight:600", "letter-spacing:0.3px",
    "box-shadow:0 4px 20px rgba(99,102,241,0.45)",
    "backdrop-filter:blur(8px)",
    "display:flex", "align-items:center", "gap:7px",
    "z-index:999", "pointer-events:none",
    "transition:opacity 0.3s",
  ].join(";");
  badge.innerHTML = `<span>${icon}</span><span>${nome}</span>` +
    (isAuto ? `<span style="font-size:10px;opacity:0.75">auto</span>` : "");
  document.body.appendChild(badge);
  specialistBadge = badge;
}

// ── Drapeaux par code langue ──────────────────────────────────
const LANG_FLAGS: Record<string, string> = {
  fr: "🇫🇷", pt: "🇧🇷", en: "🇺🇸", es: "🇪🇸", de: "🇩🇪",
  it: "🇮🇹", ru: "🇷🇺", ja: "🇯🇵", zh: "🇨🇳", ar: "🇸🇦",
  nl: "🇳🇱", pl: "🇵🇱", tr: "🇹🇷", ko: "🇰🇷", sv: "🇸🇪",
};

const LANG_NAMES: Record<string, string> = {
  fr: "Français", pt: "Português (BR)", en: "English", es: "Español",
  de: "Deutsch", it: "Italiano", ru: "Русский", ja: "日本語",
  zh: "中文", ar: "العربية", nl: "Nederlands", pl: "Polski",
  tr: "Türkçe", ko: "한국어", sv: "Svenska",
};

// Labels d'état multilingues
const STATE_LABELS: Record<string, Record<OrbState, string>> = {
  fr: { veille: "en veille...", idle: "", listening: "écoute...", thinking: "réflexion...", speaking: "" },
  pt: { veille: "em espera...", idle: "", listening: "ouvindo...", thinking: "pensando...", speaking: "" },
  en: { veille: "sleeping...",  idle: "", listening: "listening...", thinking: "thinking...", speaking: "" },
  es: { veille: "en espera...", idle: "", listening: "escuchando...", thinking: "pensando...", speaking: "" },
  de: { veille: "Ruhemodus...", idle: "", listening: "höre zu...", thinking: "denke...", speaking: "" },
  it: { veille: "in attesa...", idle: "", listening: "ascolto...", thinking: "penso...", speaking: "" },
  ru: { veille: "в ожидании...", idle: "", listening: "слушаю...", thinking: "думаю...", speaking: "" },
  ja: { veille: "待機中...", idle: "", listening: "聞いています...", thinking: "考えています...", speaking: "" },
  zh: { veille: "待机中...", idle: "", listening: "听着...", thinking: "思考中...", speaking: "" },
};

// Commandes d'aide par langue
const HELP_COMMANDS: Record<string, string[]> = {
  fr: ["Quelle heure est-il ?", "Météo à Paris", "Ouvre Spotify", "Allume la lumière du salon",
       "Vérifie mes emails", "Prends une capture d'écran", "Parle anglais",
       "Rappelle-moi d'appeler Paul", "Ferme Chrome", "Mets de la musique"],
  pt: ["Que horas são?", "Tempo em São Paulo", "Abre o Spotify", "Liga a luz da sala",
       "Verifica os emails", "Tira um screenshot", "Fala inglês",
       "Lembra de ligar para Paulo", "Fecha o Chrome", "Toca música"],
  en: ["What time is it?", "Weather in London", "Open Spotify", "Turn on the living room light",
       "Check my emails", "Take a screenshot", "Speak French",
       "Remind me to call Paul", "Close Chrome", "Play music"],
  es: ["¿Qué hora es?", "Tiempo en Madrid", "Abre Spotify", "Enciende la luz del salón",
       "Revisa mis emails", "Toma una captura", "Habla inglés",
       "Recuérdame llamar a Pablo", "Cierra Chrome", "Pon música"],
  de: ["Wie spät ist es?", "Wetter in Berlin", "Öffne Spotify", "Schalte das Wohnzimmerlicht an",
       "Überprüfe meine E-Mails", "Mach einen Screenshot", "Sprich Englisch",
       "Erinnere mich daran, Paul anzurufen", "Schließe Chrome", "Spiele Musik"],
};

// ── État ──────────────────────────────────────────────────────
let ws: WebSocket | null = null;
let currentLang  = "fr";
let isMuted      = false;
let showKeyboard = false;
let showHelp     = false;
let showLangModal = false;
let showMobileModal = false;
let availableLangs: string[] = [];
let realtimePc: RTCPeerConnection | null = null;
let realtimeDc: RTCDataChannel | null = null;
let realtimeStream: MediaStream | null = null;
let realtimeAudio: HTMLAudioElement | null = null;
let realtimeActive = false;
let arStream: MediaStream | null = null;
let arActive = false;
let arBusy = false;
let arTimer: number | null = null;

type ArBox = {
  label?: string;
  objeto?: string;
  confidence?: number | null;
  confianca?: number | null;
  x: number;
  y: number;
  largura: number;
  altura: number;
};

function sendRealtimeEvent(payload: object): void {
  if (realtimeDc && realtimeDc.readyState === "open") {
    realtimeDc.send(JSON.stringify(payload));
  }
}

// ── Orbe 3D ───────────────────────────────────────────────────
const orb = createOrb(canvas);

// ── WebSocket ─────────────────────────────────────────────────
function connect(): void {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    setConnected(true);
    errorEl.textContent = "";
    ws!.send(JSON.stringify({ action: "ping" }));
  };

  ws.onclose = () => {
    setConnected(false);
    orb.setState("veille");
    setTimeout(connect, RECONNECT_INTERVAL);
  };

  ws.onerror = () => {
    errorEl.textContent = "Connexion impossible";
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleMessage(data);
    } catch (_) {}
  };
}

function handleMessage(data: Record<string, unknown>): void {
  const action = data.action as string;

  switch (action) {
    case "init":
      availableLangs = (data.langues as string[]) || [];
      setLang((data.langue as string) || "fr");
      buildLangList();
      break;

    case "state":
      applyState(data.state as OrbState);
      break;

    case "text":
      showSubtitle(data.text as string);
      if (data.langue) setLang(data.langue as string, false);
      break;

    case "volume":
      orb.setVolume(data.volume as number);
      break;

    case "langue_ok":
      setLang(data.code as string, false);
      break;

    case "capture_ok":
      showCapturePreview(data.image_b64 as string);
      break;

    case "status_data":
      updateStatusInfo(data);
      break;

    case "wake":
      // Rony ativado (true) ou voltou ao modo veille (false)
      if (data.ativo) {
        applyState("listening");
      } else {
        applyState("veille");
      }
      break;

    case "specialist_mode":
      showSpecialistBadge(
        data.modo as string | null,
        (data.nome as string) || "",
        !!(data.auto),
      );
      break;

    case "ar_mode":
      if (data.enabled) {
        void startArMode();
      } else {
        stopArMode();
      }
      break;

    case "pong":
      break;
  }
}

function send(payload: object): void {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ── UI helpers ────────────────────────────────────────────────
function setConnected(ok: boolean): void {
  badgeEl.className = `badge ${ok ? "connected" : "disconnected"}`;
  const labels: Record<string, Record<string, string>> = {
    fr: { c: "connecté", d: "déconnecté" }, pt: { c: "conectado", d: "desconectado" },
    en: { c: "connected", d: "disconnected" }, es: { c: "conectado", d: "desconectado" },
    de: { c: "verbunden", d: "getrennt" },
  };
  const l = labels[currentLang] || labels.en;
  badgeLabelEl.textContent = ok ? l.c : l.d;
}

function applyState(state: OrbState): void {
  orb.setState(state);
  const labels = STATE_LABELS[currentLang] || STATE_LABELS.en;
  statusEl.textContent = labels[state] ?? "";
}

function setLang(code: string, notifyServer = true): void {
  currentLang = code;
  langFlagEl.textContent = LANG_FLAGS[code] || "🌐";
  langCodeEl.textContent = code.toUpperCase();
  document.documentElement.lang = code;
  if (notifyServer) send({ action: "langue", code });
}

function showSubtitle(text: string): void {
  subtitleTextEl.textContent = text;
  subtitleBox.classList.remove("hidden");
  clearTimeout((subtitleBox as any)._hideTimer);
  (subtitleBox as any)._hideTimer = setTimeout(() => {
    subtitleBox.classList.add("hidden");
  }, 6_000);
}

function showCapturePreview(b64: string): void {
  const img = document.createElement("img");
  img.src   = `data:image/jpeg;base64,${b64}`;
  img.style.cssText = "position:fixed;bottom:20px;right:20px;width:200px;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.5);z-index:999;cursor:pointer;";
  img.onclick = () => img.remove();
  document.body.appendChild(img);
  setTimeout(() => img.remove(), 8_000);
}

function updateStatusInfo(data: Record<string, unknown>): void {
  const iaActive = ["ia_gemini", "ia_claude", "ia_groq", "ia_openai"]
    .filter((k) => data[k])
    .map((k) => k.replace("ia_", ""))
    .join(", ");
  console.log(`[RONY] Version: ${data.version} | Lang: ${data.langue} | IAs: ${iaActive || "none"} | Facts: ${data.faits}`);
}

function buildLangList(): void {
  langList.innerHTML = "";
  const langs = availableLangs.length ? availableLangs : Object.keys(LANG_FLAGS);
  for (const code of langs) {
    const btn = document.createElement("button");
    btn.className = "lang-option";
    btn.innerHTML = `${LANG_FLAGS[code] || "🌐"} <span>${LANG_NAMES[code] || code}</span>`;
    btn.onclick = () => {
      setLang(code);
      toggleLangModal(false);
    };
    langList.appendChild(btn);
  }
}

function buildHelpCommands(): void {
  const cmds = HELP_COMMANDS[currentLang] || HELP_COMMANDS.en;
  helpCommandsEl.innerHTML = cmds
    .map((c) => `<div class="help-cmd" onclick="sendText('${c.replace(/'/g, "\\'")}')">${c}</div>`)
    .join("");
}

(window as any).sendText = (text: string) => {
  send({ action: "text", text });
  toggleHelp(false);
};

function toggleHelp(show?: boolean): void {
  showHelp = show ?? !showHelp;
  helpOverlay.classList.toggle("hidden", !showHelp);
  if (showHelp) buildHelpCommands();
}

function toggleLangModal(show?: boolean): void {
  showLangModal = show ?? !showLangModal;
  langModal.classList.toggle("hidden", !showLangModal);
  if (showLangModal) buildLangList();
}

async function toggleMobileModal(show?: boolean): Promise<void> {
  showMobileModal = show ?? !showMobileModal;
  mobileModal.classList.toggle("hidden", !showMobileModal);
  if (!showMobileModal) return;

  mobileUrlBtn.textContent = "carregando...";
  mobileHint.textContent = "";
  try {
    const response = await fetch("/api/mobile-info");
    const data = await response.json();
    const url = String(data.url || `${window.location.protocol}//${window.location.host}`);
    mobileUrlBtn.textContent = url;
    mobileHint.textContent = "Toque no endereco para copiar.";
  } catch (_) {
    mobileUrlBtn.textContent = `${window.location.protocol}//${window.location.host}`;
    mobileHint.textContent = "Se nao abrir no celular, permita o Rony no Firewall do Windows.";
  }
}

function toggleKeyboard(show?: boolean): void {
  showKeyboard = show ?? !showKeyboard;
  keyboardHud.classList.toggle("hidden", !showKeyboard);
  if (showKeyboard) keyboardInput.focus();
}


function resizeArOverlay(): void {
  const rect = arVideo.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  arOverlay.width = Math.max(1, Math.round(rect.width * ratio));
  arOverlay.height = Math.max(1, Math.round(rect.height * ratio));
  arOverlay.style.width = `${rect.width}px`;
  arOverlay.style.height = `${rect.height}px`;
}

function drawArBoxes(faces: ArBox[], objects: ArBox[], sourceWidth: number, sourceHeight: number): void {
  resizeArOverlay();
  const ctx = arOverlay.getContext("2d");
  if (!ctx) return;

  const ratio = window.devicePixelRatio || 1;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, arOverlay.width, arOverlay.height);

  const rect = arVideo.getBoundingClientRect();
  const scale = Math.min(rect.width / sourceWidth, rect.height / sourceHeight);
  const renderedW = sourceWidth * scale;
  const renderedH = sourceHeight * scale;
  const offsetX = (rect.width - renderedW) / 2;
  const offsetY = (rect.height - renderedH) / 2;

  const draw = (box: ArBox, color: string, fallback: string) => {
    const x = offsetX + box.x * scale;
    const y = offsetY + box.y * scale;
    const w = box.largura * scale;
    const h = box.altura * scale;
    const label = box.label || box.objeto || fallback;
    const score = box.confianca ?? box.confidence;
    const text = score ? `${label} ${Math.round(score * 100)}%` : label;

    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);

    ctx.font = "12px Inter, Segoe UI, sans-serif";
    const textW = ctx.measureText(text).width + 12;
    const textH = 22;
    ctx.fillStyle = color;
    ctx.fillRect(x, Math.max(0, y - textH), textW, textH);
    ctx.fillStyle = "#041016";
    ctx.fillText(text, x + 6, Math.max(14, y - 7));
  };

  objects.forEach((box) => draw(box, "rgba(6, 182, 212, 0.95)", "objeto"));
  faces.forEach((box) => draw(box, "rgba(34, 197, 94, 0.95)", "rosto"));
  arStatus.textContent = `${faces.length} rosto(s) · ${objects.length} objeto(s)`;
}

async function analyzeArFrame(): Promise<void> {
  if (!arActive || arBusy || arVideo.readyState < 2) return;
  arBusy = true;
  try {
    const sourceWidth = arVideo.videoWidth || 640;
    const sourceHeight = arVideo.videoHeight || 360;
    const targetWidth = 640;
    const targetHeight = Math.max(1, Math.round(sourceHeight * (targetWidth / sourceWidth)));
    const frameCanvas = document.createElement("canvas");
    frameCanvas.width = targetWidth;
    frameCanvas.height = targetHeight;
    const frameCtx = frameCanvas.getContext("2d");
    if (!frameCtx) return;

    frameCtx.drawImage(arVideo, 0, 0, targetWidth, targetHeight);
    const image_b64 = frameCanvas.toDataURL("image/jpeg", 0.72);
    const response = await fetch("/api/ar-frame", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_b64, langue: currentLang }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
      arStatus.textContent = data.error || "AR indisponivel";
      return;
    }
    drawArBoxes(data.faces || [], data.objects || [], targetWidth, targetHeight);
  } catch (_) {
    arStatus.textContent = "AR indisponivel";
  } finally {
    arBusy = false;
  }
}

async function startArMode(): Promise<void> {
  if (arActive) return;
  if (!navigator.mediaDevices?.getUserMedia) {
    errorEl.textContent = "Camera indisponivel nesta interface.";
    return;
  }

  try {
    errorEl.textContent = "";
    arStatus.textContent = "iniciando camera...";
    arPanel.classList.remove("hidden");
    arBtn.classList.add("is-realtime");
    arStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } },
      audio: false,
    });
    arVideo.srcObject = arStream;
    await arVideo.play();
    arActive = true;
    arStatus.textContent = "analisando...";
    resizeArOverlay();
    await analyzeArFrame();
    arTimer = window.setInterval(() => { void analyzeArFrame(); }, 900);
  } catch (error) {
    stopArMode();
    errorEl.textContent = error instanceof Error && error.name === "NotAllowedError"
      ? "Permita o acesso a camera para usar a realidade aumentada."
      : "Nao consegui iniciar a realidade aumentada.";
  }
}

function stopArMode(): void {
  if (arTimer !== null) {
    window.clearInterval(arTimer);
    arTimer = null;
  }
  arStream?.getTracks().forEach((track) => track.stop());
  arStream = null;
  arVideo.pause();
  arVideo.srcObject = null;
  arActive = false;
  arBusy = false;
  arPanel.classList.add("hidden");
  arBtn.classList.remove("is-realtime");
  const ctx = arOverlay.getContext("2d");
  ctx?.clearRect(0, 0, arOverlay.width, arOverlay.height);
}

// ── Événements boutons ────────────────────────────────────────
function setRealtimeActive(active: boolean): void {
  realtimeActive = active;
  realtimeBtn.classList.toggle("is-realtime", active);
  realtimeBtn.textContent = active ? "stop" : "realtime";
}

async function startRealtime(): Promise<void> {
  if (realtimeActive) {
    stopRealtime();
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    errorEl.textContent = "Microfone realtime exige navegador seguro";
    return;
  }

  try {
    errorEl.textContent = "";
    applyState("thinking");
    send({ action: "micro", enabled: false });
    await sleep(700);

    const tokenResponse = await fetch("/api/realtime-token");
    const tokenData = await tokenResponse.json();
    if (!tokenResponse.ok) {
      throw new Error(tokenData.error || "Nao consegui criar sessao realtime.");
    }
    const clientSecret = tokenData.value || tokenData.client_secret?.value;
    if (!clientSecret) throw new Error("Token realtime ausente.");

    const pc = new RTCPeerConnection();
    realtimePc = pc;

    realtimeAudio = document.createElement("audio");
    realtimeAudio.autoplay = true;
    realtimeAudio.style.display = "none";
    document.body.appendChild(realtimeAudio);

    pc.ontrack = (event) => {
      if (realtimeAudio) realtimeAudio.srcObject = event.streams[0];
      applyState("speaking");
    };

    realtimeStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    pc.addTrack(realtimeStream.getAudioTracks()[0], realtimeStream);

    realtimeDc = pc.createDataChannel("oai-events");
    realtimeDc.addEventListener("open", () => {
      setRealtimeActive(true);
      applyState("listening");
      showSubtitle("Modo Realtime ativo.");
    });
    realtimeDc.addEventListener("message", (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "response.audio_transcript.done" && data.transcript) {
          showSubtitle(data.transcript);
        }
        if (data.type === "response.function_call_arguments.done" && data.name === "executar_rony") {
          handleRonyToolCall(data.call_id, data.arguments);
        }
        if (data.type === "input_audio_buffer.speech_started") applyState("listening");
        if (data.type === "response.created") applyState("thinking");
        if (data.type === "response.done") applyState("listening");
      } catch (_) {}
    });

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const sdpResponse = await fetch("https://api.openai.com/v1/realtime/calls", {
      method: "POST",
      body: offer.sdp,
      headers: {
        Authorization: `Bearer ${clientSecret}`,
        "Content-Type": "application/sdp",
      },
    });
    if (!sdpResponse.ok) {
      throw new Error(await sdpResponse.text());
    }

    const answer: RTCSessionDescriptionInit = {
      type: "answer",
      sdp: await sdpResponse.text(),
    };
    await pc.setRemoteDescription(answer);
  } catch (error) {
    stopRealtime();
    const message = error instanceof Error ? error.message : "Falha no Realtime";
    errorEl.textContent = message.includes("audio source")
      ? "Microfone ocupado. Feche outros apps de audio ou tente novamente."
      : message;
    applyState("idle");
  }
}

function stopRealtime(): void {
  realtimeDc?.close();
  realtimePc?.close();
  realtimeStream?.getTracks().forEach((track) => track.stop());
  realtimeAudio?.remove();
  realtimeDc = null;
  realtimePc = null;
  realtimeStream = null;
  realtimeAudio = null;
  setRealtimeActive(false);
  send({ action: "micro", enabled: true });
  applyState("idle");
}

async function handleRonyToolCall(callId: string, rawArguments: string): Promise<void> {
  try {
    const args = JSON.parse(rawArguments || "{}");
    const comando = String(args.comando || "").trim();
    const response = await fetch("/api/realtime-tool", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ comando }),
    });
    const data = await response.json();
    const output = data.resultado || "Ferramenta executada sem retorno.";

    sendRealtimeEvent({
      type: "conversation.item.create",
      item: {
        type: "function_call_output",
        call_id: callId,
        output,
      },
    });
    sendRealtimeEvent({ type: "response.create" });
  } catch (error) {
    sendRealtimeEvent({
      type: "conversation.item.create",
      item: {
        type: "function_call_output",
        call_id: callId,
        output: error instanceof Error ? error.message : "Erro ao executar ferramenta local.",
      },
    });
    sendRealtimeEvent({ type: "response.create" });
  }
}

muteBtn.onclick = () => {
  isMuted = !isMuted;
  muteBtn.classList.toggle("is-muted", isMuted);
  muteBtn.textContent = isMuted ? "unmute" : "mute";
  send({ action: isMuted ? "stop" : "ping" });
};

captureBtn.onclick = () => {
  send({ action: "capture" });
};

realtimeBtn.onclick = () => {
  startRealtime();
};

arBtn.onclick = () => {
  if (arActive) stopArMode();
  else void startArMode();
};
arClose.onclick = () => stopArMode();

keyboardToggle.onclick = () => toggleKeyboard();
helpToggle.onclick     = () => toggleHelp();
helpClose.onclick      = () => toggleHelp(false);
langBadge.onclick      = () => toggleLangModal();
langClose.onclick      = () => toggleLangModal(false);
mobileBtn.onclick      = () => { void toggleMobileModal(); };
mobileClose.onclick    = () => { void toggleMobileModal(false); };
mobileUrlBtn.onclick   = () => {
  const url = mobileUrlBtn.textContent || "";
  if (url.startsWith("http")) {
    navigator.clipboard?.writeText(url);
    mobileHint.textContent = "Endereco copiado.";
  }
};

keyboardSend.onclick = () => {
  const text = keyboardInput.value.trim();
  if (text) {
    send({ action: "text", text });
    keyboardInput.value = "";
  }
};

keyboardInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    keyboardSend.click();
  }
});

// Clic hors modal ferme
document.addEventListener("click", (e) => {
  if (showLangModal && !langModal.contains(e.target as Node) && !langBadge.contains(e.target as Node)) {
    toggleLangModal(false);
  }
  if (showMobileModal && !mobileModal.contains(e.target as Node) && !mobileBtn.contains(e.target as Node)) {
    void toggleMobileModal(false);
  }
});

// Raccourcis clavier
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    toggleHelp(false);
    toggleLangModal(false);
    void toggleMobileModal(false);
    toggleKeyboard(false);
    stopArMode();
  }
  if ((e.ctrlKey || e.metaKey) && e.key === "k") {
    e.preventDefault();
    toggleKeyboard();
  }
  if (e.key === "F1") {
    e.preventDefault();
    toggleHelp();
  }
});

// ── Boot ──────────────────────────────────────────────────────
window.addEventListener("resize", () => {
  if (arActive) resizeArOverlay();
});
subtitleBox.classList.add("hidden");
keyboardHud.classList.add("hidden");
helpOverlay.classList.add("hidden");
langModal.classList.add("hidden");
mobileModal.classList.add("hidden");

// Estado inicial: veille (aguardando wake word)
orb.setState("veille");
applyState("veille");

connect();
send({ action: "status" });
