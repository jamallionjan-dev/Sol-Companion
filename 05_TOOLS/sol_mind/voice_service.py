"""Voice input for Sol: the game's voice button -> Sol Mind records the microphone -> Whisper (Groq) -> Sol chat.

    game  SolVoice_Request.txt   id=<n>  action=start|stop
    mind  SolVoice_State.txt     ack=<n> status=listening|transcribing|done|error  code=...  text=<escaped>

Nothing is recorded except between the player's two presses (max 30 s). The audio stays in memory and goes only to
the speech-to-text service; it is never written to disk.
"""
import io, json, os, threading, time, uuid, wave, urllib.request, urllib.error

REQ, STATE = "SolVoice_Request.txt", "SolVoice_State.txt"
RATE, MAX_SECONDS = 16000, 30
STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
STT_MODEL = "whisper-large-v3-turbo"

def esc(t):
    return "".join(ch if 32 <= ord(ch) < 127 and ch not in "\\|=" else "\\u%04X" % ord(ch) for ch in (t or ""))

class Recorder:
    """Microphone capture through sounddevice (PortAudio). Raises RuntimeError('mic_unavailable') when missing."""
    def __init__(self):
        try:
            import sounddevice as sd
        except Exception:
            raise RuntimeError("mic_unavailable")
        self.sd, self.frames, self.stream, self.started = sd, [], None, 0.0
    def start(self):
        self.frames = []
        def cb(indata, frames, t, status): self.frames.append(bytes(indata))
        try:
            self.stream = self.sd.RawInputStream(samplerate=RATE, channels=1, dtype="int16", callback=cb)
            self.stream.start()
        except Exception:
            self.stream = None; raise RuntimeError("mic_unavailable")
        self.started = time.time()
    def stop(self):
        if self.stream:
            try: self.stream.stop(); self.stream.close()
            except Exception: pass
        self.stream = None
        return b"".join(self.frames)

def wav_bytes(pcm):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(pcm)
    return buf.getvalue()

def transcribe(wav, key, language="ar", timeout=40):
    boundary = "----SolMind" + uuid.uuid4().hex
    def field(name, value): return ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, name, value)).encode()
    body = field("model", STT_MODEL) + field("language", language) + field("response_format", "json") + \
        ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"voice.wav\"\r\nContent-Type: audio/wav\r\n\r\n" % boundary).encode() + \
        wav + ("\r\n--%s--\r\n" % boundary).encode()
    req = urllib.request.Request(STT_URL, data=body, method="POST", headers={
        "Authorization": "Bearer " + key, "Content-Type": "multipart/form-data; boundary=" + boundary, "User-Agent": "SolMind/0.7"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return (json.loads(r.read().decode("utf-8")).get("text") or "").strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError("stt_invalid_key" if e.code == 401 else "stt_rate_limited" if e.code == 429 else "stt_failed")
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise RuntimeError("stt_failed")

class Voice:
    def __init__(self, lua_dir, chat, log=print, recorder=None, stt=None, key=None):
        self.dir, self.chat, self.log = lua_dir, chat, log
        self.recorder_factory = recorder or Recorder
        self.stt = stt or transcribe
        self.key = key
        self.rec, self.last_id, self.ack = None, 0, 0
        self.running = False
    def _key(self):
        if self.key is not None: return self.key
        try:
            import secret_store as S
            return S.get("groq") or ""
        except Exception: return ""
    def state(self, status, code="", text=""):
        tmp = os.path.join(self.dir, STATE + ".tmp")
        try:
            with open(tmp, "w", encoding="ascii", newline="\n") as f:
                f.write("ack=%d\nstatus=%s\ncode=%s\ntext=%s\n" % (self.ack, status, code, esc(text)))
            os.replace(tmp, os.path.join(self.dir, STATE))
        except OSError: pass
    def read_request(self):
        try:
            with open(os.path.join(self.dir, REQ), encoding="ascii", errors="replace") as f:
                return dict(l.split("=", 1) for l in f.read().splitlines() if "=" in l)
        except OSError: return None
    def poll_once(self):
        r = self.read_request()
        if r:
            try: rid = int(r.get("id") or 0)
            except ValueError: rid = 0
            if rid > self.last_id:
                self.last_id = self.ack = rid
                if r.get("action") == "start": self.start()
                elif r.get("action") == "stop": self.stop()
        if self.rec and time.time() - self.rec.started > MAX_SECONDS: self.stop()      # forgotten second press
    def bridge(self):
        """The ChatGPT bridge is the mind -> its dictation is the ear (the player asked: better than Groq)."""
        try:
            import settings_service as SS
            if SS.load_config().get("source") != "bridge": return None
            link = SS.start_link(self.log)
        except Exception: return None
        if link is None: return None
        if link.on_heard is None:
            def heard(text):
                self.state("done", text=text); self.log("voice: dictation %d chars" % len(text))
                self.chat.handle(text)
            link.on_heard = heard
        return link
    def start(self):
        link = self.bridge()
        if link is not None:
            if not link.connected(15): self.state("error", "chatgpt_link_not_connected"); return
            self.dictating = True; link.command("dictate_start"); self.state("listening"); self.log("voice: ChatGPT dictation started"); return
        if self.rec: return
        try:
            self.rec = self.recorder_factory(); self.rec.start()
        except RuntimeError as e:
            self.rec = None; self.state("error", str(e)); self.log("voice: %s" % e); return
        self.state("listening"); self.log("voice: listening")
    def stop(self):
        if getattr(self, "dictating", False):
            self.dictating = False
            link = self.bridge()
            if link is not None: link.command("dictate_stop"); self.state("transcribing"); return
        if not self.rec: return
        pcm = self.rec.stop(); self.rec = None
        if len(pcm) < RATE * 2 * 0.4:                         # under 0.4 s: nothing said
            self.state("error", "too_short"); return
        key = self._key()
        if not key: self.state("error", "no_stt_key"); return
        self.state("transcribing")
        def work():
            try:
                text = self.stt(wav_bytes(pcm), key)
            except RuntimeError as e:
                self.state("error", str(e)); self.log("voice: %s" % e); return
            if not text: self.state("error", "nothing_heard"); return
            self.state("done", text=text); self.log("voice: heard %d chars" % len(text))
            try: self.chat.handle(text)
            except Exception as e: self.log("voice: chat failed %r" % (e,))
        threading.Thread(target=work, daemon=True).start()
    def run(self):
        self.running = True
        while self.running:
            try: self.poll_once()
            except Exception as e: self.log("voice: %r" % (e,))
            time.sleep(0.15)

_voice = None
def start(lua_dir, chat, log=print):
    global _voice
    if _voice is None:
        _voice = Voice(lua_dir, chat, log=log)
        threading.Thread(target=_voice.run, daemon=True).start()
    return _voice
