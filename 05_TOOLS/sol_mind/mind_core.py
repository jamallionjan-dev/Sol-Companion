"""Sol Mind transport core: deterministic brain side of the sol-ai-1 mailbox.

Rules (derived from SCAIRuntime/SCAIMailbox source):
- Game sends one frame at a time and waits for ack(payload.ackSequence == its sequence).
- Inbox holds ONE frame and the game gives no read receipt, so the brain writes
  one frame at a time: a command (tool_request/say) is written first, kept for a
  grace period so the game can poll it, then replaced by the ack.
- A command is proven consumed only when its tool_result arrives. If it does not
  arrive within RESULT_WINDOW game frames it is resent with the SAME requestId;
  the game's requestId cache makes replays side-effect free.
- A new sessionId resets transport state; commands from the old session are dropped.
"""
from collections import deque

from codec import PROTOCOL, SCHEMA, as_map
from mailbox import read_frame, write_frame


def speech_ascii(text):
    """Sol's Lua reads text one byte per character, and her speech bubble knows Arabic only as \\uXXXX escapes."""
    out = []
    for ch in str(text):
        c = ord(ch)
        if c < 128: out.append(ch)
        elif c > 0xFFFF:
            c -= 0x10000; out.append("\\u%04X\\u%04X" % (0xD800 + (c >> 10), 0xDC00 + (c & 0x3FF)))
        else: out.append("\\u%04X" % c)
    return "".join(out)


class MindCore:
    GRACE_MS = 700
    REWRITE_MS = 2000
    RESULT_WINDOW = 4
    MAX_ATTEMPTS = 3

    def __init__(self, inbox, outbox, log=print):
        self.inbox, self.outbox, self.log = inbox, outbox, log
        self.session = self.world = None
        self.last_seq = None
        self.brain_seq = 0
        self.phase = "idle"
        self.pending_ack = None
        self.wrote_at = 0
        self.last_written = None
        self.queue = deque()
        self.inflight = None
        self.results = {}
        self.tools = {}
        self.perception = None
        self.next_id = 0
        self.stats = {"frames": 0, "acks": 0, "commands": 0, "resends": 0, "errors": 0, "sessions": 0}

    # ---------- public API ----------
    def request_tool(self, tool, arguments=None):
        rid = self._rid()
        self.queue.append({"kind": "tool", "requestId": rid, "tool": tool,
                           "arguments": arguments or {}, "attempts": 0})
        self.results[rid] = {"status": "queued"}
        return rid

    def say(self, text):
        rid = self._rid()
        self.queue.append({"kind": "say", "requestId": rid, "text": speech_ascii(text), "attempts": 0})
        self.results[rid] = {"status": "queued"}
        return rid

    def status(self, rid):
        return self.results.get(rid)

    # ---------- main loop step ----------
    def step(self, now):
        frame, _why = read_frame(self.outbox)
        if frame is not None:
            sid = frame.get("sessionId")
            if sid != self.session:
                self._new_session(frame)
            seq = frame.get("sequence")
            if seq != self.last_seq:
                self.last_seq = seq
                self.stats["frames"] += 1
                self._consume(frame)
                self._on_game_frame(seq, now)
        self._advance(now)

    # ---------- internals ----------
    def _rid(self):
        self.next_id += 1
        return "mind-%d" % self.next_id

    def _frame(self, ftype, payload, rid=None, now=0):
        self.brain_seq += 1
        f = {"protocol": PROTOCOL, "schema": SCHEMA, "sessionId": self.session,
             "worldId": self.world, "sequence": self.brain_seq,
             "timestampMs": now, "type": ftype, "payload": payload}
        if rid is not None:
            f["requestId"] = rid
        return f

    def _write(self, frame, now):
        if write_frame(self.inbox, frame):
            self.last_written = frame
            self.wrote_at = now
            return True
        self.log("WARN inbox write failed (locked); will retry")
        return False

    def _new_session(self, frame):
        self.stats["sessions"] += 1
        self.log("SESSION %s (first seen frame seq=%s type=%s)" % (
            frame.get("sessionId"), frame.get("sequence"), frame.get("type")))
        if self.inflight is not None:
            self.results[self.inflight["requestId"]] = {"status": "failed", "reason": "session_changed"}
            self.inflight = None
        self.session, self.world = frame.get("sessionId"), frame.get("worldId")
        self.last_seq = None
        self.phase, self.pending_ack = "idle", None

    def _consume(self, frame):
        t = frame.get("type")
        payload = as_map(frame.get("payload"))
        if t == "hello":
            self.tools = as_map(payload.get("tools"))
            self.log("HELLO tools=%s" % ",".join(sorted(self.tools)))
        elif t == "perception_snapshot":
            self.perception = payload
        elif t == "tool_result":
            rid = str(frame.get("requestId") or payload.get("requestId") or "")
            res = {"status": payload.get("status"), "accepted": payload.get("accepted"),
                   "reason": payload.get("reason"), "tool": payload.get("tool")}
            self.results[rid] = res
            self.log("RESULT %s %s" % (rid, res))
            if self.inflight and self.inflight["requestId"] == rid:
                self.inflight = None
        elif t == "error":
            self.stats["errors"] += 1
            rid = frame.get("requestId")
            self.log("GAME-ERROR code=%s inbound=%s rid=%s" % (
                payload.get("code"), payload.get("inboundType"), rid))
            if rid is not None and self.inflight and self.inflight["requestId"] == str(rid):
                self.results[str(rid)] = {"status": "rejected", "reason": payload.get("code")}
                self.inflight = None

    def _on_game_frame(self, seq, now):
        if self.inflight is not None:
            self.inflight["frames"] += 1
            if self.inflight["frames"] > self.RESULT_WINDOW:
                cmd = self.inflight
                self.inflight = None
                if cmd["attempts"] >= self.MAX_ATTEMPTS:
                    self.results[cmd["requestId"]] = {"status": "failed", "reason": "transport_lost"}
                    self.log("LOST %s after %d attempts" % (cmd["requestId"], cmd["attempts"]))
                else:
                    self.stats["resends"] += 1
                    self.log("RESEND %s (no result after %d frames)" % (cmd["requestId"], self.RESULT_WINDOW))
                    self.queue.appendleft(cmd)
        if self.queue and self.inflight is None:
            cmd = self.queue.popleft()
            cmd["attempts"] += 1
            if cmd["kind"] == "tool":
                f = self._frame("tool_request", {"tool": cmd["tool"], "arguments": cmd["arguments"]},
                                cmd["requestId"], now)
                cmd["frames"] = 0
                self.inflight = cmd
                self.results[cmd["requestId"]] = {"status": "sent", "attempts": cmd["attempts"]}
            else:
                f = self._frame("say", {"text": cmd["text"]}, cmd["requestId"], now)
                self.results[cmd["requestId"]] = {"status": "sent"}
            self.stats["commands"] += 1
            self._write(f, now)
            self.phase, self.pending_ack = "grace", seq
            return
        self._send_ack(seq, now)

    def _send_ack(self, seq, now):
        if self._write(self._frame("ack", {"ackSequence": seq}, None, now), now):
            self.stats["acks"] += 1
            self.phase, self.pending_ack = "acked", None
        else:
            self.phase, self.pending_ack = "grace", seq

    def _advance(self, now):
        if self.phase == "grace" and now - self.wrote_at >= self.GRACE_MS:
            self._send_ack(self.pending_ack, now)
        elif self.phase == "acked" and self.last_written and now - self.wrote_at >= self.REWRITE_MS:
            # identical frame (same sequence): the game de-duplicates it if already read
            self._write(self.last_written, now)
