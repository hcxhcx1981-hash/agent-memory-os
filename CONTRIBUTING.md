# Contributing

Open a small issue describing the problem before a substantial change. Keep
Core agent-neutral and deterministic; changes to adapters must not bypass the
Gate, invent human confirmation or directly edit stores. Use fictional fixtures.
Do not submit chat histories, stores, credentials or real host paths.

Run these from the repository root with Python 3.11 or newer:

```sh
python -m unittest discover -v
python examples/demo.py
python scripts/release-security-check.py --history
git diff --check
```

Describe behavior, compatibility and validation in the pull request. No external
model API is needed. Contributions intentionally submitted for inclusion are
under Apache-2.0 unless explicitly agreed otherwise; disclose third-party
origins and licenses. Do not copy restricted source code.
