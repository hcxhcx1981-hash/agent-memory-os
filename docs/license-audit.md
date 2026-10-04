# Release license review

Scope: all original project files and the four-commit cleaned baseline, runtime
imports, build configuration and the exact third-party Actions used by CI.
No vendored third-party implementation or copied Hermes code was found. Project
code was authored for this repository; examples are fictional fixtures. The
reference adapter calls the host and the public CLI rather than embedding host
code. This technical provenance review cannot certify undisclosed ownership.

| Component | Use | License and source | Distribution boundary |
|---|---|---|---|
| Original project code/docs | Application | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | LICENSE and NOTICE included |
| Python >=3.11 standard library | Runtime; only stdlib imports | [PSF License v2 and Python license history](https://docs.python.org/3/license.html) | Interpreter/stdlib are not bundled |
| setuptools >=68 | Isolated build backend | [MIT](https://raw.githubusercontent.com/pypa/setuptools/main/LICENSE) | Build tool, not a runtime dependency; no vendored code |
| actions/checkout v4.2.2 | CI checkout | [MIT at pinned revision](https://github.com/actions/checkout/blob/11bd71901bbe5b1630ceea73d27597364c9af683/LICENSE) | Runs on GitHub; not bundled |
| actions/setup-python v5.6.0 | CI interpreter setup | [MIT at pinned revision](https://github.com/actions/setup-python/blob/a26af69be951a213d495a4c3e4e4022e16d87065/LICENSE) | Runs on GitHub; not bundled |

`dependencies = []`: no installed third-party runtime library is required.
No `build` frontend dependency is declared; pip invokes setuptools through the
standard build interface. Build tools can have their own internal dependencies
and notices; they are not copied into this project's wheel. Re-audit if vendoring,
new dependencies or different Action revisions are introduced.

The permissive licenses above do not create a detected conflict with licensing
the original application under Apache-2.0. Apache-2.0 allows commercial use and
modification, requires applicable license/attribution and change notices on
redistribution, and grants only the contributor patent claims specified in
section 3. That patent grant terminates under the litigation condition in that
section. It is not blanket patent clearance, trademark permission or a warranty.
