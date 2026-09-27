// Salma's "ear": the user just talks, like on a phone call. Also draws the call bar (avatar, timer, status).
//
// Two engines (Python chooses):
//  - "whisper" (default when a Groq key is set): the page opens the microphone, detects when the person
//    starts and stops talking (volume above the room noise, then ~0.9 s of silence), records that phrase
//    and sends the audio to Python, which transcribes it with Groq Whisper. Works in every modern browser.
//  - "browser": the browser's own speech recognition (Web Speech API, Chrome/Edge only).
//
// Talks to Python through Streamlit components v2:
//   Python → JS : `data` (listen on/off, engine, current screen, labels, call duration)
//   JS → Python : setTriggerValue("voice", {audio, mime})  one recorded phrase (engine "whisper")
//                 setTriggerValue("speech", text)          one recognized phrase (engine "browser")
//                 setTriggerValue("idle", screen)          20 s without action or speech on a screen
//                 setTriggerValue("unsupported", reason)   microphone refused or not available
// Streamlit calls the default export again every time `data` changes (without cleanup in between),
// so all state lives in one object on `window` and the function only updates it.

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const S = (window.__salmaEar = window.__salmaEar || {
  engine: "whisper", wantListen: false, nudge: false, thinking: false, thinkingSince: 0,
  idleSince: Date.now(), lastAudio: 0, nudged: {}, screen: null, turn: null, startMs: Date.now(),
  loop: null, vadLoop: null, alive: 0, supported: true, reported: false, data: null, root: null,
  setTriggerValue: null,
  // whisper engine
  stream: null, ctx: null, analyser: null, buf: null, opening: false, noise: 0, above: 0,
  rec: null, recStart: 0, lastVoice: 0, listenNow: false,
  // browser engine
  sr: null, srOn: false, finals: "", interim: "", silenceTimer: null, nextStart: 0, errors: 0,
});

function playingAudio() {
  return [...document.querySelectorAll("audio")].some((a) => !a.paused && !a.ended && a.currentTime > 0);
}

function send(kind, value) {
  S.thinking = true;
  S.thinkingSince = Date.now();
  S.setTriggerValue && S.setTriggerValue(kind, value);
}

function markUnsupported(reason) {
  if (S.reported) return;
  S.reported = true;
  S.supported = false;
  // Slightly later, so it is not lost during the very first mount. Python prints the reason in the terminal.
  setTimeout(() => S.setTriggerValue && S.setTriggerValue("unsupported", String(reason)), 300);
}

function retryMic() {
  // Tap on the call bar after allowing the microphone: try again.
  if (S.supported) return;
  S.supported = true;
  S.reported = false;
  S.errors = 0;
  S.nextStart = 0;
  releaseMic();
}

// ---------------- engine "whisper": voice detection + recording ----------------
async function openMic() {
  if (S.stream || S.opening) return;
  if (!navigator.mediaDevices || !window.MediaRecorder) return markUnsupported("no microphone API");
  S.opening = true;
  try {
    S.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    const AC = window.AudioContext || window.webkitAudioContext;
    S.ctx = new AC();
    S.analyser = S.ctx.createAnalyser();
    S.analyser.fftSize = 1024;
    S.ctx.createMediaStreamSource(S.stream).connect(S.analyser);
    S.buf = new Float32Array(S.analyser.fftSize);
    S.noise = 0;
  } catch (e) {
    S.stream = null;
    markUnsupported(e.name || "microphone refused");
  }
  S.opening = false;
}

function releaseMic() {
  if (S.rec) stopRecording(false);
  if (S.stream) S.stream.getTracks().forEach((t) => t.stop());
  if (S.ctx) S.ctx.close().catch(() => {});
  S.stream = S.ctx = S.analyser = null;
}

function level() {
  S.analyser.getFloatTimeDomainData(S.buf);
  let sum = 0;
  for (const v of S.buf) sum += v * v;
  return Math.sqrt(sum / S.buf.length);
}

function startRecording() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  const mime = types.find((m) => MediaRecorder.isTypeSupported(m));
  const rec = new MediaRecorder(S.stream, mime ? { mimeType: mime } : undefined);
  const chunks = [];
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  rec.onstop = () => {
    if (!rec.keep) return;
    const blob = new Blob(chunks, { type: rec.mimeType || mime || "audio/webm" });
    const reader = new FileReader();
    reader.onload = () => send("voice", { audio: String(reader.result).split(",")[1], mime: blob.type });
    reader.readAsDataURL(blob);
  };
  rec.start();
  S.rec = rec;
  S.recStart = S.lastVoice = Date.now();
}

function stopRecording(keep) {
  const rec = S.rec;
  S.rec = null;
  rec.keep = keep;
  try { rec.stop(); } catch (e) { /* already stopped */ }
}

function vad() {
  if (!S.analyser) return;
  if (S.ctx.state === "suspended") S.ctx.resume().catch(() => {});
  const lv = level();
  if (!S.rec) S.noise = S.noise ? Math.min(lv, S.noise * 0.995 + lv * 0.005) || lv : lv; // room noise
  const threshold = Math.max(0.012, S.noise * 3);
  if (!S.listenNow) {
    if (S.rec) stopRecording(false); // Salma started talking: drop what was being recorded
    S.above = 0;
    return;
  }
  if (!S.rec) {
    S.above = lv > threshold ? S.above + 50 : 0;
    if (S.above >= 100) startRecording(); // 0.1 s of voice: the person starts talking
    return;
  }
  S.idleSince = Date.now();
  if (lv > threshold * 0.7) S.lastVoice = Date.now();
  const spoken = S.lastVoice - S.recStart;
  if (Date.now() - S.lastVoice > 900 || Date.now() - S.recStart > 15000) {
    stopRecording(spoken > 300); // ~0.9 s of silence ends the phrase; ignore short noises
  }
}

// ---------------- engine "browser": Web Speech API ----------------
function flush() {
  const text = (S.finals + " " + S.interim).trim();
  S.finals = S.interim = "";
  if (text.length >= 2) {
    send("speech", text);
    stopSR();
  }
}

function startSR() {
  if (!SR) return markUnsupported("no Web Speech API in this browser");
  if (Date.now() < S.nextStart) return;
  if (!S.sr) {
    const r = new SR();
    r.lang = "fr-FR";
    r.continuous = true;
    r.interimResults = true;
    r.onresult = (e) => {
      S.errors = 0;
      S.idleSince = Date.now();
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) S.finals += e.results[i][0].transcript + " ";
        else interim += e.results[i][0].transcript;
      }
      S.interim = interim;
      clearTimeout(S.silenceTimer);
      S.silenceTimer = setTimeout(flush, 1000);
    };
    r.onspeechstart = () => (S.idleSince = Date.now());
    r.onend = () => {
      S.srOn = false;
      S.nextStart = Date.now() + 300;
    };
    r.onerror = (e) => {
      if (["not-allowed", "service-not-allowed", "audio-capture"].includes(e.error)) markUnsupported(e.error);
      else if (e.error !== "no-speech" && e.error !== "aborted" && ++S.errors >= 5) markUnsupported(e.error);
    };
    S.sr = r;
  }
  try {
    S.sr.start();
    S.srOn = true;
  } catch (e) { /* already started */ }
}

function stopSR() {
  clearTimeout(S.silenceTimer);
  if (S.sr && S.srOn) {
    try { S.sr.abort(); } catch (e) { /* ignore */ }
  }
  S.srOn = false;
}

// ---------------- main loop: who listens, status, idle nudge ----------------
function tick() {
  if (!S.root || !S.data) return;
  const L = S.data.labels;
  const playing = playingAudio();
  if (playing) {
    S.lastAudio = Date.now();
    S.idleSince = Date.now();
  }
  if (S.thinking && Date.now() - S.thinkingSince > 30000) S.thinking = false; // safety
  // Listen only when Salma is quiet and not thinking (no echo, no talking over her).
  const canListen = S.wantListen && S.supported && !S.thinking && !playing && Date.now() - S.lastAudio > 500;
  let listening = false;
  if (S.engine === "whisper") {
    if (S.wantListen && S.supported && !S.stream) openMic();
    if (!S.wantListen && S.stream) releaseMic();
    S.listenNow = canListen && !!S.analyser;
    listening = S.listenNow;
  } else {
    if (canListen && !S.srOn) startSR();
    if (!canListen && S.srOn) stopSR();
    listening = S.srOn;
  }

  // One gentle nudge per screen after `idle_secs` without any action or speech.
  const idleMs = (S.data.idle_secs || 20) * 1000;
  if (S.nudge && !S.thinking && !playing && !S.rec && !S.nudged[S.screen] && Date.now() - S.idleSince > idleMs) {
    S.nudged[S.screen] = true;
    send("idle", S.screen);
  }

  const status = S.thinking ? L.thinking : playing ? L.speaking : S.rec ? L.hearing : listening ? L.listening
    : S.supported === false ? L.nomic : L.paused;
  S.root.querySelector(".status").textContent = status;
  S.root.querySelector(".avatar").classList.toggle("speaking", playing);
  const secs = Math.max(0, Math.floor((Date.now() - S.startMs) / 1000));
  S.root.querySelector(".clock").textContent =
    String(Math.floor(secs / 60)).padStart(2, "0") + ":" + String(secs % 60).padStart(2, "0");
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  S.setTriggerValue = setTriggerValue;
  S.data = data;
  S.alive = Date.now();

  let root = parentElement.querySelector(".salma-bar");
  if (!root) {
    root = document.createElement("div");
    root.className = "salma-bar";
    root.innerHTML =
      '<div class="avatar">👩🏽</div><div class="txt"><div class="title">📞 <span class="clock">00:00</span> · ' +
      '<span class="t1"></span></div><div class="status"></div></div>';
    root.addEventListener("click", retryMic);
    parentElement.appendChild(root);
  }
  S.root = root;
  root.querySelector(".t1").textContent = data.labels.title;

  const base = Date.now() - data.elapsed * 1000;
  if (Math.abs(base - S.startMs) > 3000) S.startMs = base;
  if (data.screen !== S.screen) {
    S.screen = data.screen;
    S.idleSince = Date.now();
  }
  if (data.turn !== S.turn) { // Python answered: Salma is no longer thinking
    S.turn = data.turn;
    S.thinking = false;
    S.idleSince = Date.now();
  }
  if (data.engine !== S.engine) {
    releaseMic();
    stopSR();
    S.engine = data.engine;
  }
  S.wantListen = !!data.listen;
  S.nudge = !!data.nudge;

  if (!S.loop) {
    S.loop = setInterval(tick, 250);
    S.vadLoop = setInterval(vad, 50);
    for (const ev of ["pointerdown", "keydown", "input"]) {
      document.addEventListener(ev, () => {
        S.idleSince = Date.now();
        if (S.ctx && S.ctx.state === "suspended") S.ctx.resume().catch(() => {});
      }, true);
    }
  }
  tick();

  // Unmounted (hang up, page change): stop listening unless Streamlit mounts us again right away.
  const mountedAt = S.alive;
  return () => setTimeout(() => {
    if (S.alive === mountedAt) {
      S.wantListen = false;
      S.nudge = false;
      stopSR();
      releaseMic();
    }
  }, 1500);
}
