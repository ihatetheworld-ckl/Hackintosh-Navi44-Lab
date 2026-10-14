"""Audited local-only migration helper. Never fetches, pushes or reads credentials.

preview/init/stage/commit are separate explicit operations. All paths are checked;
Git global/system config, templates, filters, signing and hooks are disabled.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m7_safety as safe

ROOT = safe.ROOT
OUT = ROOT / "reports/m85"
SECRET_RULES = {
    "github_token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b",
    "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
    "aws_access_key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "credential_url": rb"https?://[^/\s:@]+:[^/\s@]+@",
    "secret_assignment": rb"""["'](?:access_token|refresh_token|client_secret|password|private_key)["']\s*[:=]\s*["'][^"'\s]{8,}["']""",
    "windows_machine_sid": rb"S-1-5-21-\d+-\d+-\d+-\d+",
}
BAD_SUFFIXES = {".exe", ".dll", ".sys", ".obj", ".o", ".pdb", ".zip", ".rom",
                ".vbios", ".pem", ".key", ".p12", ".pfx", ".a", ".so", ".dylib"}

def inventory():
    paths = []
    stack = [ROOT]
    while stack:
        directory = safe.checked(stack.pop())
        for path in sorted(directory.iterdir()):
            safe.checked(path)
            if path.name == ".git":
                continue  # Preserve nested Git histories; never stage metadata.
            if path.is_dir():
                stack.append(path)
            elif path.is_file():
                paths.append(path.relative_to(ROOT).as_posix())
    return sorted(paths)

def audit(entries):
    findings = []
    sizes = collections.defaultdict(lambda: [0, 0])
    folders = collections.defaultdict(lambda: [0, 0])
    names = {}
    for name, data in entries:
        safe.checked(name)
        if len(data) > 10 * 1024 * 1024:
            findings.append({"path": name, "rule": "file_exceeds_10MiB"})
        if Path(name).suffix.lower() in BAD_SUFFIXES:
            findings.append({"path": name, "rule": "forbidden_payload_extension"})
        if Path(name).suffix.lower() == ".bin" and name != "tests/fixtures/m65-invalid-strtab.bin":
            findings.append({"path": name, "rule": "unexpected_binary"})
        if ".github" in Path(name).parts or ".gitmodules" in Path(name).parts:
            findings.append({"path": name, "rule": "workflow_or_dangling_submodule"})
        if any(part in Path(name).parts for part in ("firmware", ".git")):
            findings.append({"path": name, "rule": "excluded_payload_directory"})
        for rule, pattern in SECRET_RULES.items():
            if re.search(pattern, data):
                findings.append({"path": name, "rule": rule})  # Never log secret contents.
        # Include parent directory components in case/normalization conflict checks.
        parts = Path(name).parts
        for count in range(1, len(parts) + 1):
            partial = "/".join(parts[:count])
            key = unicodedata.normalize("NFC", partial).casefold()
            if key in names and names[key] != partial:
                findings.append({"path": name, "rule": "case_or_unicode_collision"})
            names[key] = partial
        ext = Path(name).suffix or "(extensionless)"
        sizes[ext][0] += 1
        sizes[ext][1] += len(data)
        top = name.split("/")[0]
        folders[top][0] += 1
        folders[top][1] += len(data)
    return {"files": len(entries), "bytes": sum(len(b) for _, b in entries),
            "types": dict(sorted(sizes.items())), "folders": dict(sorted(folders.items())),
            "findings": findings, "secret_scan_scope": "Selected actual bytes; pattern-based, not exhaustive"}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preview", "init", "stage", "verify", "commit"])
    parser.add_argument("--git", required=True)
    parser.add_argument("--name")
    parser.add_argument("--email")
    args = parser.parse_args()
    git = Path(args.git)
    if not git.is_absolute() or not git.is_file():
        raise SystemExit("Existing trusted Git absolute path required")
    safe.mkdir(OUT)
    safe.mkdir("tmp/m85-git")
    safe.mkdir(OUT / "empty-template")
    safe.mkdir(OUT / "empty-hooks")
    safe.write(OUT / "empty-config", "")
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("GIT_", "GCM_"))}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_OPTIONAL_LOCKS="0",
               GIT_TERMINAL_PROMPT="0", TMP=str(ROOT / "tmp/m85-git"),
               TEMP=str(ROOT / "tmp/m85-git"), TMPDIR=str(ROOT / "tmp/m85-git"))
    prefix = [str(git), "-c", "safe.directory=" + str(ROOT),
              "-c", "core.hooksPath=" + str(OUT / "empty-hooks"),
              "-c", "core.attributesFile=" + str(OUT / "empty-config"),
              "-c", "core.excludesFile=" + str(OUT / "empty-config"),
              "-c", "core.fsmonitor=false", "-c", "core.autocrlf=false",
              "-c", "core.safecrlf=false", "-c", "commit.gpgsign=false",
              "-c", "tag.gpgsign=false", "-c", "credential.helper=",
              "-c", "core.pager=cat"]
    previous_log = safe.checked(OUT / "git-commands.json")
    commands = json.loads(previous_log.read_text(encoding="utf-8")) if previous_log.exists() else []
    def run(command, data=None, allowed=(0,)):
        # Every writable Git target remains within the audited local root.
        safe.checked(".git")
        if (ROOT / ".git").is_dir():
            for p in (ROOT / ".git").rglob("*"):
                safe.checked(p)
        result = subprocess.run(prefix + command, cwd=ROOT, env=env, input=data,
                                capture_output=True, timeout=60)
        commands.append({"argv": prefix + command, "exit": result.returncode})
        safe.write(OUT / "git-commands.json", json.dumps(commands, ensure_ascii=False, indent=2))
        if result.returncode not in allowed:
            raise RuntimeError("Local Git command failed: " + command[0] + "\n" +
                               result.stderr.decode("utf-8", errors="replace"))
        return result.stdout

    if args.action == "preview":
        # No Git mutation. Conservative inventory summary; final ignore preview
        # is resolved by real Git after an empty-template init.
        files = inventory()
        shortlist = [n for n in files if not n.startswith(("build/", "tmp/", "tools/",
                     "upstream/AMDRadeonRDNA4/", "upstream/Cobalt64/")) and
                     not any(part in Path(n).parts for part in ("history", "firmware", "emu",
                             "execution", "attempts", "hw-logs", ".github"))]
        result = audit([(n, safe.checked(n).read_bytes()) for n in shortlist])
        safe.write(OUT / "pre-init-review.json", json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps({"candidate_files": result["files"], "findings": result["findings"]},
                         ensure_ascii=False))
        return
    if args.action == "init":
        if (ROOT / ".git").exists() or any((p / ".git").exists() for p in ROOT.parents):
            raise SystemExit("Repository ownership changed; refusing reinitialization")
        if not args.name or not args.email:
            raise SystemExit("Explicit existing identity required; no global config changes")
        run(["init", "--initial-branch=main", "--template=" + str(OUT / "empty-template")])
        for key, value in [
            ("user.name", args.name), ("user.email", args.email),
            ("core.autocrlf", "false"), ("core.hooksPath", "reports/m85/empty-hooks"),
            ("commit.gpgsign", "false"), ("tag.gpgsign", "false"),
            ("core.fsmonitor", "false"),
        ]:
            run(["config", "--local", key, value])
        print("Local main initialized; no remote operations")
        return
    if not (ROOT / ".git").is_dir():
        raise SystemExit("Project root Git must be initialized first")
    if args.action == "stage":
        files = inventory()
        ignored = set(x.decode("utf-8") for x in run(
            ["check-ignore", "--no-index", "-z", "--stdin"],
            ("\0".join(files) + "\0").encode("utf-8"), allowed=(0, 1)).split(b"\0") if x)
        selected = [name for name in files if name not in ignored]
        entries = [(n, safe.checked(n).read_bytes()) for n in selected]
        result = audit(entries)
        safe.write(OUT / "upload-audit.json", json.dumps(result, ensure_ascii=False, indent=2))
        if result["findings"]:
            print(json.dumps(result["findings"], ensure_ascii=False))
            raise SystemExit("Candidate audit failed; no files staged")
        # Exact paths, never git add . or git add -A. No directories/gitlinks.
        for start in range(0, len(selected), 24):
            run(["add", "--", *selected[start:start+24]])
        # Git add silently skips descendants of an embedded repository.
        # Preserve its .git and explicitly stage audited normal blobs in the
        # parent index, without a gitlink or a destructive metadata move.
        present = {n.decode("utf-8") for n in run(["ls-files", "-z"]).split(b"\0") if n}
        missing = [name for name in selected if name not in present]
        index_rows = []
        for name in missing:
            if not name.startswith("development/AMDRadeonRDNA4-Navi44/"):
                raise SystemExit("Unexpected missing path, refusing automatic repair: " + name)
            data = safe.checked(name).read_bytes()
            oid = run(["hash-object", "-w", "--path=" + name, "--stdin"],
                      data).decode("ascii").strip()
            if not re.fullmatch(r"[0-9a-f]{40}", oid):
                raise SystemExit("Invalid Git blob ID")
            index_rows.append(("100644 " + oid + "\t" + name + "\0").encode("utf-8"))
        if index_rows:
            run(["update-index", "-z", "--index-info"], b"".join(index_rows))
        present = {n.decode("utf-8") for n in run(["ls-files", "-z"]).split(b"\0") if n}
        if present != set(selected):
            raise SystemExit("Staged source set differs from reviewed upload manifest")
        safe.write(OUT / "upload-manifest.json", json.dumps(
            [{"path": n, "working_bytes": len(b), "working_sha256": hashlib.sha256(b).hexdigest()}
             for n, b in entries], ensure_ascii=False, indent=2))
        print(json.dumps({"selected_files": len(selected), "bytes": result["bytes"],
                          "findings": result["findings"]}, ensure_ascii=False))
        return
    rows = run(["ls-files", "--stage", "-z"]).split(b"\0")
    entries = []
    manifest = {}
    records = []
    for row in rows:
        if not row: continue
        header, path = row.split(b"\t", 1)
        mode, oid, stage = header.split()
        if mode not in (b"100644", b"100755") or stage != b"0":
            raise SystemExit("Unexpected symlink/gitlink/conflict")
        name = path.decode("utf-8")
        records.append((name, oid.decode("ascii")))
    # One bounded Git batch, no executable filters; actual blob bytes only.
    payload = run(["cat-file", "--batch"],
                  ("\n".join(oid for _, oid in records) + "\n").encode("ascii"))
    if len(payload) > 64 * 1024 * 1024:
        raise SystemExit("Staged blob batch exceeds migration resource budget")
    offset = 0
    for name, oid in records:
        end = payload.find(b"\n", offset)
        if end < 0: raise SystemExit("Truncated Git blob header")
        fields = payload[offset:end].split()
        if len(fields) != 3 or fields[:2] != [oid.encode("ascii"), b"blob"]:
            raise SystemExit("Unexpected Git batch response")
        count = int(fields[2])
        if count < 0 or count > 10 * 1024 * 1024:
            raise SystemExit("Invalid Git blob size")
        begin = end + 1
        end = begin + count
        if end >= len(payload) or payload[end:end+1] != b"\n":
            raise SystemExit("Truncated Git blob")
        data = payload[begin:end]
        offset = end + 1
        entries.append((name, data))
        manifest[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                          "git_blob": oid}
    if offset != len(payload):
        raise SystemExit("Unexpected trailing Git blob bytes")
    result = audit(entries)
    safe.write(OUT / "upload-audit.json", json.dumps(result, ensure_ascii=False, indent=2))
    if result["findings"]:
        raise SystemExit("Staged blob audit failed")
    expected = {item["path"] for item in json.loads(
        (OUT / "upload-manifest.json").read_text(encoding="utf-8"))}
    if set(manifest) != expected:
        raise SystemExit("Reviewed upload manifest and actual index differ")
    if args.action == "verify":
        safe.write(OUT / "staged-content-sha256.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        safe.write(OUT / "staged-stat.txt", run(["diff", "--cached", "--stat"]))
        safe.write(OUT / "staged-review.patch", run(["diff", "--cached", "--no-ext-diff", "--no-textconv"]))
        print(json.dumps({"files": result["files"], "bytes": result["bytes"],
                          "types": result["types"], "findings": result["findings"]}, ensure_ascii=False))
    else:
        if run(["rev-parse", "--verify", "HEAD"], allowed=(0, 128)):
            raise SystemExit("Initial commit already exists; do not rewrite history")
        run(["commit", "--no-verify", "--no-gpg-sign", "-m",
             "Initial import: Navi44 M8 offline development"])
        sha = run(["rev-parse", "HEAD"]).decode("ascii").strip()
        branch = run(["branch", "--show-current"]).decode("ascii").strip()
        status = run(["status", "--short"]).decode("utf-8")
        safe.write(OUT / "local-commit.json", json.dumps(
            {"branch": branch, "commit": sha, "files": result["files"], "bytes": result["bytes"],
             "push": "NOT RUN", "status": status}, ensure_ascii=False, indent=2))
        print(json.dumps({"branch": branch, "commit": sha, "files": result["files"],
                          "bytes": result["bytes"], "status": status}, ensure_ascii=False))

if __name__ == "__main__":
    main()
