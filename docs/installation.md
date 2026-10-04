# Installation, data and removal

Use Git and **Python >=3.11** from existing installations or approved installers:
[Python downloads](https://www.python.org/downloads/) and
[Git downloads](https://git-scm.com/downloads). On Windows choose per-user Python
installation and enable its PATH option. No winget, Homebrew, administrator
privilege or global package write access is assumed. Clone currently requires
PRIVATE repository access; never paste credentials into clone URLs.

## Windows PowerShell

```powershell
python --version
git clone https://github.com/hcxhcx1981-hash/agent-memory-os.git
cd agent-memory-os
python -m unittest discover -v
python -m cli --help
python examples/demo.py --quickstart-only
```

Optional isolated install without PowerShell activation:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install .
.venv/Scripts/memory.exe --help
python examples/demo.py --command .venv/Scripts/memory.exe
```

The demo resolves a supplied executable path before changing its working directory.

## Linux and macOS

`python3` must be 3.11 or newer. Some system Python installations require a
separate venv support package; direct mode remains available without it. Use
an existing Python or approved installer; no package manager is assumed.

```sh
python3 --version
git clone https://github.com/hcxhcx1981-hash/agent-memory-os.git
cd agent-memory-os
python3 -m unittest discover -v
python3 -m cli --help
python3 examples/demo.py --quickstart-only
```

Optional isolated install (same on both platforms):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
memory --help
python examples/demo.py --command memory
```

Direct mode needs no network after clone. Package build isolation may download
setuptools; it is not a runtime dependency. For offline installation supply
an approved local build-wheel cache or use direct mode. Do not change network
or security policy to install the project.

## Initialize a separate store

Choose a writable, user-owned location. `storage/` is convenient in a checkout
and Git-ignored; an installed package should use an explicit user-owned store.
A missing store is read as empty; the first accepted write creates it:

```sh
python -m cli --store storage/quickstart.json evaluate --candidate examples/theme.json
python -m cli --store storage/quickstart.json add --candidate examples/theme.json
python -m cli --store storage/quickstart.json search default_theme --project Project-Mercury
python -m cli --store storage/quickstart.json inject default_theme --project Project-Mercury
```

After installation replace `python -m cli` with `memory`. Follow the README for
conflict/supersede. Every operation must select the same store. Smart data is
`<store>.smart.json`. Never point either file at host native memory. See
[Hermes setup and removal](hermes-quickstart.md).

## Backup, uninstall and deliberate deletion

Stop all writers. Copy the exact Core store and its `.smart.json` sidecar, if
present, to a private backup directory **together**. Copy router diagnostics
separately if needed. Restore the pair while writers remain stopped. Retire
and supersede retain historical content; they do not delete private data.

Use the venv's `python -m pip uninstall agent-memory-os` for package removal;
it leaves stores intact. Remove the dedicated Hermes Skill first if installed.
For permanent data removal, manually delete only the selected Core file,
matching sidecar and router event file after checking each filename. Also remove
backups and demo stores if desired. Do not delete native Hermes Memory,
unrelated Skills or unrelated directories. This guide does not perform deletion
or promise secure disk erasure.
