# Changelog

## v0.1.0 - Initial research prototype

### Added

- Reproducible Docker-based TLS test environment.
- OpenSSL 3.5.6 built inside the Docker crypto image.
- Classical TLS 1.3 profile with `X25519`.
- Hybrid TLS 1.3 profile with `X25519MLKEM768`.
- Maximum-supported PQC profile with `MLKEM768`.
- Automated temporary CA and server certificate generation.
- TLS server/client test stand based on `openssl s_server` and `openssl s_client`.
- Repeated TLS handshake testing for each cryptographic profile.
- Raw CSV metrics for each profile.
- Per-profile Markdown, CSV and JSON summaries.
- Combined Markdown, CSV and JSON reports for all profiles.
- GitHub Actions workflow for CI/CD execution.
- Profile configuration tests.
- Docker build context exclusions through `.dockerignore`.
- Makefile targets for common project commands.
- OpenSSL/PQC capability diagnostics.
- Full local smoke-test through `make check`.
- Experimental methodology documentation.

### Notes

- The `pqc` profile is implemented as a maximum-supported PQC profile: it uses ML-KEM key establishment with a classical ECDSA certificate.
- Generated keys, certificates, logs, metrics and reports are runtime artifacts and are excluded from Git.
- The prototype is intended for research and educational use, not for production cryptographic deployment.