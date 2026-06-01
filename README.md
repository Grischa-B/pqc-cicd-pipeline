# PQC CI/CD Pipeline Prototype

Language: English | [Русский](README.ru.md)

Open-source prototype of a CI/CD pipeline for software delivery with support for classical, hybrid and post-quantum cryptographic profiles.

The project demonstrates how cryptographic profile selection, TLS certificate generation, TLS server/client deployment, integration testing, metrics collection and report generation can be integrated into an automated software delivery process.

## Purpose

The prototype was developed as part of a graduation research project on:

> Development of a software delivery pipeline with support for post-quantum cryptography.

The goal is not to benchmark an isolated cryptographic primitive, but to verify the full engineering cycle of integrating cryptographic profiles into a reproducible CI/CD workflow.

The pipeline supports:

* classical TLS 1.3 profile;
* hybrid TLS 1.3 profile with classical and post-quantum key establishment;
* maximum-supported post-quantum TLS profile.

## Technology stack

* Ubuntu 24.04 LTS
* Docker and Docker Compose
* GitHub Actions
* Bash
* Python 3
* OpenSSL 3.5.6

OpenSSL is built inside the Docker image so that the experiment does not depend on the OpenSSL version installed on the host machine.

## Cryptographic profiles

Profile definitions are stored in `configs/profiles/`.

| Profile     | Purpose                                                   | Key exchange group | Certificate type |
| ----------- | --------------------------------------------------------- | ------------------ | ---------------- |
| `classical` | Classical TLS 1.3 baseline                                | `X25519`           | ECDSA / P-256    |
| `hybrid`    | Transition profile with classical + PQC key establishment | `X25519MLKEM768`   | ECDSA / P-256    |
| `pqc`       | Maximum-supported PQC profile                             | `MLKEM768`         | ECDSA / P-256    |

The `pqc` profile uses post-quantum ML-KEM key establishment while keeping a classical ECDSA certificate for TLS/X.509 stability. Full PQC certificate support with ML-DSA or SLH-DSA can be added as a future extension.

## Quick start

Build Docker images:

```bash
make build
```

Run one profile:

```bash
make run-classical
make run-hybrid
make run-pqc
```

Run all profiles and generate a combined report:

```bash
make run-all
```

Run the full local project check:

```bash
make check
```

Inspect OpenSSL/PQC capabilities inside the Docker image:

```bash
make crypto-capabilities
```

Equivalent direct script commands are also available:

```bash
./scripts/build/build-images.sh
./scripts/run-pipeline.sh classical
./scripts/run-pipeline.sh hybrid
./scripts/run-pipeline.sh pqc
./scripts/run-all.sh
```

## Output artifacts

Runtime results are generated under `artifacts/`.

Important files:

```text
artifacts/metrics/raw-classical.csv
artifacts/metrics/raw-hybrid.csv
artifacts/metrics/raw-pqc.csv

artifacts/reports/summary-classical.md
artifacts/reports/summary-hybrid.md
artifacts/reports/summary-pqc.md

artifacts/reports/summary-all.md
artifacts/reports/summary-all.csv
artifacts/reports/summary-all.json
```

The combined reports compare all profiles by success rate, TLS handshake time, negotiated key exchange group and certificate/key sizes.

## Collected metrics

The pipeline collects:

* profile name;
* iteration number;
* handshake status;
* TLS handshake time in milliseconds;
* expected and actual key exchange group;
* group verification evidence;
* observed TLS version;
* OpenSSL exit code;
* error message, if present;
* server key and certificate sizes.

## Cryptographic verification

Each profile restricts TLS negotiation to a single configured group:

* `classical`: `X25519`;
* `hybrid`: `X25519MLKEM768`;
* `pqc`: `MLKEM768`.

If OpenSSL prints the negotiated temporary key, the parser uses that value directly. If OpenSSL does not print it, but the TLS 1.3 connection succeeds with a single restricted group and certificate verification succeeds, the pipeline records the configured group with the evidence value:

```text
restricted-single-group
```

This makes profile verification reproducible even when OpenSSL CLI output differs between versions.

## Experimental methodology

The experimental methodology is described in:

```text
docs/EXPERIMENT.md
```

Russian version:

```text
docs/EXPERIMENT.ru.md
```

## GitHub Actions

The repository includes a GitHub Actions workflow:

```text
.github/workflows/pipeline.yml
```

The workflow validates profile configuration files, builds Docker images, runs the pipeline and uploads logs, metrics and reports as CI artifacts.

It runs on:

* `push`;
* `pull_request`;
* manual `workflow_dispatch`.

Manual runs allow selecting `all`, `classical`, `hybrid` or `pqc`.

## Security and limitations

Generated private keys, certificates, logs, metrics and reports are runtime artifacts and must not be committed to Git.

Current limitations:

* the test stand uses `openssl s_server` and `openssl s_client` instead of a full application server;
* the `pqc` profile uses ML-KEM key establishment but keeps a classical ECDSA certificate;
* CPU and memory metrics are not collected as first-class report fields;
* the project is a research prototype and is not intended for production cryptographic deployment.

## Version

Current prototype version:

```text
v0.1.0
```

See `CHANGELOG.md` for release notes.

## License

MIT License.
