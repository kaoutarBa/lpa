// Salma's "ear": continuous French speech recognition in the browser (Web Speech API), plus the call bar UI.
//
// Talks to Python through Streamlit components v2:
//   Python → JS : `data` (listen on/off, current screen, labels, last line, call duration)
//   JS → Python : setTriggerValue("speech", text)   one final phrase, after ~1 s of silence
//                 setTriggerValue("idle", screen)    20 s without action or speech on a screen
//                 setTriggerValue("unsupported", true) no Web Speech API, or microphone refused
// Streamlit calls the default export again every time `data` changes (without cleanup in between),
// so all state lives in one object on `window` and the function only updates it.

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const S = (window.__salmaEar = window.__salmaEar || {
  rec: null, listening: false, wantListen: false, nudge: false, thinking: false, thinkingSince: 0,
  finals: "", interim: "", silenceTimer: null, idleSince: Date.now(), lastAudio: 0, nextStart: 0,
  errors: 0, nudged: {}, screen: null, turn: null, startMs: Date.now(), loop: null, alive: 0,
  supported: !!SR, data: null, root: null, setTriggerValue: null,
});

function playingAudio() {
  return [...document.querySelectorAll("audio")].some((a) => !a.paused && !a.ended && a.currentTime > 0);
}

function send(kind, value) {
  S.thinking = true;
  S.thinkingSince = Date.now();
  S.setTriggerValue && S.setTriggerValue(kind, value);
}

function flush() {
  const text = (S.finals + " " + S.interim).trim();
  S.finals = "";
  S.interim = "";
  if (text.length >= 2) {
    send("speech", text);
    stopRec(); // start a fresh recognition session next time, so nothing is sent twice
  }
}

function markUnsupported(reason) {
  if (S.reported) return;
  S.reported = true;
  S.supported = false;
  // Slightly later, so it is not lost during the very first mount. Python prints the reason in the terminal.
  setTimeout(() => S.setTriggerValue && S.setTriggerValue("unsupported", reason || "no Web Speech API"), 300);
}

function retryMic() {
  // Tap on the call bar after allowing the microphone: try listening again.
  if (!SR || S.supported) return;
  S.supported = true;
  S.reported = false;
  S.errors = 0;
  S.nextStart = 0;
}

function startRec() {
  if (!SR || Date.now() < S.nextStart) return;
  if (!S.rec) {
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
      S.silenceTimer = setTimeout(flush, 1000); // ~1 s of silence ends the phrase
    };
    r.onspeechstart = () => (S.idleSince = Date.now());
    r.onend = () => {
      S.listening = false;
      S.nextStart = Date.now() + 300;
    };
    r.onerror = (e) => {
      if (["not-allowed", "service-not-allowed", "audio-capture"].includes(e.error)) markUnsupported(e.error);
      else if (e.error !== "no-speech" && e.error !== "aborted" && ++S.errors >= 5) markUnsupported(e.error);
    };
    S.rec = r;
  }
  try {
    S.rec.start();
    S.listening = true;
  } catch (e) {
    /* already started */
  }
}

function stopRec() {
  clearTimeout(S.silenceTimer);
  if (S.rec && S.listening) {
    try { S.rec.abort(); } catch (e) { /* ignore */ }
  }
  S.listening = false;
}

function tick() {
  if (!S.root || !S.data) return;
  const L = S.data.labels;
  const playing = playingAudio();
  if (playing) {
    S.lastAudio = Date.now();
    S.idleSince = Date.now();
  }
  if (S.thinking && Date.now() - S.thinkingSince > 30000) S.thinking = false; // safety
  // Pause recognition while Salma speaks (no echo), resume shortly after she stops.
  const shouldListen = S.wantListen && S.supported && !S.thinking && !playing && Date.now() - S.lastAudio > 500;
  if (shouldListen && !S.listening) startRec();
  if (!shouldListen && S.listening) stopRec();

  // One gentle nudge per screen after `idle_secs` without any action or speech.
  const idleMs = (S.data.idle_secs || 20) * 1000;
  if (S.nudge && !S.thinking && !playing && !S.nudged[S.screen] && Date.now() - S.idleSince > idleMs) {
    S.nudged[S.screen] = true;
    send("idle", S.screen);
  }

  const status = S.thinking ? L.thinking : playing ? L.speaking : S.listening ? L.listening
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
      '<span class="t1"></span></div><div class="status"></div><div class="line"></div></div>';
    root.addEventListener("click", retryMic);
    parentElement.appendChild(root);
  }
  S.root = root;
  root.querySelector(".t1").textContent = data.labels.title;
  root.querySelector(".line").textContent = data.last_line || "";
  root.querySelector(".line").style.display = data.last_line ? "" : "none";

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
  S.wantListen = !!data.listen;
  S.nudge = !!data.nudge;
  if (!SR) markUnsupported("no Web Speech API in this browser");
  if (!S.wantListen) stopRec();

  if (!S.loop) {
    S.loop = setInterval(tick, 250);
    for (const ev of ["pointerdown", "keydown", "input"]) {
      document.addEventListener(ev, () => (S.idleSince = Date.now()), true);
    }
  }
  tick();

  // Unmounted (hang up, page change): stop listening unless Streamlit mounts us again right away.
  const mountedAt = S.alive;
  return () => setTimeout(() => {
    if (S.alive === mountedAt) {
      S.wantListen = false;
      S.nudge = false;
      stopRec();
    }
  }, 1500);
}
