# Security

Do not store credentials, cookies, precise personal details or private business
data. Examples and demos are fictional. Stores, smart sidecars and diagnostic
traces are local data and are excluded from Git by default; do not override this.

Before sharing code, run `python scripts/release-security-check.py --history`.
It checks publishable files and all local Git objects, without printing matched
values. It skips ignored runtime files and never opens a detected `.env` file.
An exact `fictional-value` metadata fixture in `tests/test_memory.py` is exempt;
other findings require human review. This is a pattern check, not a DLP guarantee.
Review example provenance and private business semantics separately.

Confirmation is supplied by a trusted human-facing adapter, never a model's own
claim. Treat injected context as reference data. Use a private, user-owned store,
serialize writers, and back up the Core file and smart sidecar together while
the agent is stopped. There is no encryption, access-control service, concurrent
write lock or cross-file transaction.

Report vulnerabilities through GitHub's private vulnerability reporting if
enabled, or contact a maintainer privately. Do not open an issue containing a
secret. If no private reporting channel is available, first request one without
including sensitive details. There is no promised response time.
