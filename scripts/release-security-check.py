"""Offline release scan. Report locations/rule IDs, never matched values."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    'user-directory': re.compile(r'(?:[A-Za-z]:[/\\]Users[/\\](?!<USER>)[^/\\\s]+|/(?:Users|home)/(?!<USER>)[^/\s]+)', re.I),
    'old-host-path': re.compile(r'D:[/\\]agent-memory-os|C:[/\\]Users[/\\]Admin', re.I),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'api-key': re.compile(r'(?:sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16})'),
    'github-token': re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})'),
    'bearer': re.compile(r'Bearer\s+[A-Za-z0-9._-]{12,}', re.I),
    'credential-assignment': re.compile(r'''(?:password|passwd|cookie|token|api[_-]?key)\s*["']?\s*[:=]\s*["']([^"'\n]{12,})["']''', re.I),
}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def scan(data, label, findings):
    text = data.decode('utf-8', errors='replace')
    for name, pattern in RULES.items():
        for match in pattern.finditer(text):
            # Only the exact, deliberately fake metadata fixture is exempt.
            if (name == 'credential-assignment' and label.endswith('tests/test_memory.py')
                    and match.group(1) == 'fictional-value'):
                continue
            findings.append(dict(location=label, line=text.count('\n', 0, match.start()) + 1, rule=name))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--history', action='store_true', help='Scan every object, including local unreachable objects')
    args = p.parse_args()
    findings = []
    files = git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')
    for raw in sorted(set(files)):
        if not raw:
            continue
        name = raw.decode('utf-8')
        path = ROOT / name
        if path.name == '.env' or path.name.startswith('.env.'):
            findings.append(dict(location=name, rule='env-file'))
            continue  # Do not read potential secrets.
        if path.is_file():
            scan(path.read_bytes(), name, findings)
    count = 0
    if args.history:
        history = git('rev-list', '--objects', '--all').decode().splitlines()
        names = {line.partition(' ')[0]: line.partition(' ')[2] for line in history}
        # A batch avoids one Git subprocess per object; no values are printed.
        raw = git('cat-file', '--batch-all-objects', '--batch')
        pos = 0
        while pos < len(raw):
            end = raw.index(b'\n', pos)
            oid, kind, size = raw[pos:end].split()
            size = int(size)
            data = raw[end + 1:end + 1 + size]
            pos = end + size + 2
            count += 1
            if kind in (b'blob', b'commit'):
                scan(data, 'git-object:' + oid.decode() + ':' + names.get(oid.decode(), ''), findings)
        for line in history:
            _, _, name = line.partition(' ')
            if Path(name).name == '.env' or Path(name).name.startswith('.env.'):
                findings.append(dict(location='history:' + name, rule='env-file'))
    print(json.dumps(dict(status='FAIL' if findings else 'PASS', findings=findings,
                          history_objects=count, scope='publishable files and Git history; ignored runtime stores excluded')))
    return 1 if findings else 0


if __name__ == '__main__':
    raise SystemExit(main())
