// Enregistrement micro (MediaRecorder) — amélioration progressive.
// Sans MediaRecorder ou sans autorisation, l'import de fichier (formulaire classique) reste disponible.
(() => {
  "use strict";

  const root = document.querySelector("[data-recorder]");
  if (!root || !window.MediaRecorder || !navigator.mediaDevices?.getUserMedia) return;

  const maxSeconds = Number(root.dataset.maxSeconds);
  const maxBytes = Number(root.dataset.maxBytes);
  const uploadUrl = root.dataset.uploadUrl;
  const $ = (sel) => root.querySelector(sel);
  const toggle = $("[data-rec-toggle]");
  const label = $("[data-rec-label]");
  const timer = $("[data-rec-timer]");
  const review = $("[data-rec-review]");
  const preview = $("[data-rec-preview]");
  const sendBtn = $("[data-rec-send]");
  const redoBtn = $("[data-rec-redo]");
  const noImage = $("[data-rec-no-image]");
  const status = $("[data-rec-status]");

  // Chrome / Firefox : webm/opus ; Safari : mp4/aac. Le serveur vérifie le vrai type de toute façon.
  const CANDIDATES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  const mimeType = CANDIDATES.find((type) => MediaRecorder.isTypeSupported(type)) || "";
  const extension = mimeType.startsWith("audio/mp4") ? "m4a" : mimeType.startsWith("audio/ogg") ? "ogg" : "webm";

  let recorder = null;
  let stream = null;
  let chunks = [];
  let blob = null;
  let startedAt = 0;
  let tick = null;

  const say = (message) => { status.textContent = message; };
  const format = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  const csrf = () => document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";

  root.hidden = false;

  function stopTracks() {
    stream?.getTracks().forEach((track) => track.stop());
    stream = null;
  }

  function setRecording(on) {
    toggle.setAttribute("aria-pressed", String(on));
    label.textContent = on ? "Arrêter" : "Enregistrer";
  }

  async function start() {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      say(error.name === "NotAllowedError"
        ? "L'accès au micro a été refusé. Autorisez-le dans votre navigateur, ou importez un fichier ci-dessous."
        : "Aucun micro utilisable n'a été trouvé. Vous pouvez importer un fichier ci-dessous.");
      return;
    }
    chunks = [];
    blob = null;
    review.hidden = true;
    recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorder.addEventListener("dataavailable", (event) => { if (event.data.size) chunks.push(event.data); });
    recorder.addEventListener("stop", finish);
    recorder.start(1000);
    startedAt = performance.now();
    setRecording(true);
    say("Enregistrement en cours. Racontez votre rêve.");
    tick = setInterval(() => {
      const elapsed = (performance.now() - startedAt) / 1000;
      timer.textContent = format(elapsed);
      if (Math.floor(elapsed) === maxSeconds - 15) say("Encore 15 secondes.");
      if (elapsed >= maxSeconds) stop("Durée maximale atteinte : l'enregistrement s'est arrêté.");
    }, 250);
  }

  function stop(message) {
    clearInterval(tick);
    if (recorder && recorder.state !== "inactive") recorder.stop();
    stopTracks();
    setRecording(false);
    if (message) say(message);
  }

  function finish() {
    blob = new Blob(chunks, { type: recorder.mimeType || mimeType || "audio/webm" });
    const seconds = (performance.now() - startedAt) / 1000;
    if (seconds < 1 || blob.size === 0) {
      say("L'enregistrement est trop court. Réessayez.");
      return;
    }
    if (blob.size > maxBytes) {
      say("L'enregistrement est trop volumineux. Réessayez en plus court.");
      return;
    }
    preview.src = URL.createObjectURL(blob);
    review.hidden = false;
    say(`Enregistrement terminé (${format(seconds)}). Réécoutez-le, puis envoyez-le.`);
    sendBtn.focus();
  }

  async function send() {
    if (!blob) return;
    sendBtn.disabled = true;
    redoBtn.disabled = true;
    say("Envoi en cours…");
    const data = new FormData();
    data.append("audio", blob, `reve.${extension}`);
    if (noImage.checked) data.append("image_disabled", "on");
    try {
      const response = await fetch(uploadUrl, {
        method: "POST",
        body: data,
        headers: { "X-CSRFToken": csrf(), "HX-Request": "true" },
        credentials: "same-origin",
      });
      const redirect = response.headers.get("HX-Redirect");
      if (redirect) {
        window.location.assign(redirect);
        return;
      }
      // Erreurs de validation (422) ou quota (429) : le serveur renvoie le formulaire avec le message.
      document.getElementById("record-form").innerHTML = await response.text();
      say("L'envoi a été refusé : voir le message ci-dessous.");
    } catch {
      say("La connexion a échoué. Votre enregistrement est toujours là : réessayez.");
    }
    sendBtn.disabled = false;
    redoBtn.disabled = false;
  }

  toggle.addEventListener("click", () => {
    if (recorder && recorder.state === "recording") stop();
    else start();
  });
  sendBtn.addEventListener("click", send);
  redoBtn.addEventListener("click", () => {
    review.hidden = true;
    timer.textContent = "0:00";
    blob = null;
    say("");
    toggle.focus();
  });
  window.addEventListener("pagehide", () => stop());
})();
