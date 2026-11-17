"""Read-only scan before a repository goes public: personal data and secrets in every blob of the history.
usage: scan_repo_private.py [--head]     --head: only the files of HEAD (fast); default: every blob of every commit
Prints, per kind, how many blobs hit and a few paths; never prints a secret in full."""
import os, re, subprocess, sys, collections
ROOT = r"C:\Users\JAMAL\Desktop\Sol"
for _a in sys.argv[1:]:
    if _a.startswith("--root="): ROOT = _a[len("--root="):]          # scan another repository
PAT = {
    "email (his)": re.compile(re.escape(os.environ.get("SOL_OWNER_EMAIL", "owner@invalid").encode()), re.I),   # his address is not written in the repo
    "email (any gmail/outlook/hotmail)": re.compile(rb"[A-Za-z0-9._%+-]+@(gmail|outlook|hotmail|yahoo)\.com", re.I),
    "Groq key": re.compile(rb"gsk_[A-Za-z0-9]{20,}"),
    "OpenAI-style key": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
    "Anthropic key": re.compile(rb"sk-ant-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(rb"\b(ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}"),
    "Google API key": re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    "private key block": re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "home LAN address": re.compile(rb"\b192\.168\.0\.\d{1,3}\b"),
    "TLS pin sha256//": re.compile(rb"sha256//[A-Za-z0-9+/=]{30,}"),
    "api_key/password assignment": re.compile(rb"(?i)\b(api[_-]?key|apikey|password|passwd|secret|token)\b\s*[:=]\s*[\"'][^\"'\s]{12,}[\"']"),
    "Steam id 7656...": re.compile(rb"\b7656119\d{10}\b"),
}
NAMES = re.compile(r"(?i)(secrets?\.json|config\.json|lan_hosts\.json|\.pem$|\.key$|\.p12$|\.pfx$|mod_approvals\.json|sol_mind_log|\.log$|chat_history)")


def run(*a, inp=None):
    return subprocess.run(["git", "-C", ROOT] + list(a), input=inp, capture_output=True).stdout


head_only = "--head" in sys.argv
if head_only:
    lines = run("ls-tree", "-r", "HEAD").decode("utf-8", "replace").splitlines()
    objs = [(l.split()[2], l.split("\t", 1)[1]) for l in lines if " blob " in l]
else:
    objs = []
    for l in run("rev-list", "--all", "--objects").decode("utf-8", "replace").splitlines():
        p = l.split(" ", 1)
        if len(p) == 2: objs.append((p[0], p[1]))
paths = collections.defaultdict(set)
for sha, path in objs: paths[sha].add(path)
names = sorted({p for _, p in objs if NAMES.search(p)})
print("blobs/paths to scan:", len(paths), "| suspicious file NAMES:", len(names))
for n in names[:40]: print("   name:", n)
hits = collections.defaultdict(set); samples = {}
proc = subprocess.Popen(["git", "-C", ROOT, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
for sha in paths:
    proc.stdin.write(sha.encode() + b"\n"); proc.stdin.flush()
    header = proc.stdout.readline().split()
    if len(header) < 3 or header[1] != b"blob":
        if len(header) >= 3: proc.stdout.read(int(header[2]) + 1)
        continue
    size = int(header[2]); data = proc.stdout.read(size); proc.stdout.read(1)
    if size > 8_000_000 or b"\x00" in data[:4000]: continue
    for k, rx in PAT.items():
        m = rx.search(data)
        if m:
            for p in paths[sha]: hits[k].add(p)
            s = m.group(0).decode("utf-8", "replace"); samples.setdefault(k, s[:6] + "..." + s[-3:] if len(s) > 12 else s[:4] + "...")
proc.stdin.close(); proc.wait()
print("--- content hits (kind: files; sample shortened)")
for k in PAT:
    if hits[k]:
        print("  %-36s %4d files  e.g. %s  [%s]" % (k, len(hits[k]), sorted(hits[k])[:3], samples.get(k)))
    else:
        print("  %-36s none" % k)
