# Experimental Methodology

## Purpose

This document describes the experimental methodology used in the PQC CI/CD pipeline prototype.

The goal of the experiment is to compare several cryptographic TLS profiles in the same reproducible CI/CD environment:

- classical TLS 1.3 profile;
- hybrid TLS 1.3 profile with classical and post-quantum key establishment;
- maximum-supported post-quantum TLS profile.

The experiment evaluates not an isolated cryptographic primitive, but the full engineering cycle of integrating a cryptographic profile into a software delivery pipeline.

## Compared profiles

| Profile | Key exchange group | Certificate type | Role |
|---|---|---|---|
| `classical` | `X25519` | ECDSA / P-256 | Baseline TLS 1.3 profile |
| `hybrid` | `X25519MLKEM768` | ECDSA / P-256 | Migration profile with classical + PQC key establishment |
| `pqc` | `MLKEM768` | ECDSA / P-256 | Maximum-supported PQC key establishment profile |

The `pqc` profile intentionally keeps a classical ECDSA certificate. This makes the profile a maximum-supported PQC profile rather than a fully post-quantum TLS/X.509 configuration. The design choice is documented as a limitation and allows the prototype to focus on stable automated verification of post-quantum key establishment.

## Experimental environment

The environment is defined by the repository and Docker configuration.

Main components:

- Ubuntu 24.04 based Docker image;
- OpenSSL 3.5.6 built inside the Docker image;
- Docker Compose test stand;
- `openssl s_server` as TLS server;
- `openssl s_client` as TLS client;
- Bash scripts for orchestration;
- Python scripts for result aggregation;
- GitHub Actions workflow for CI/CD execution.

OpenSSL is built inside the Docker image to avoid dependency on the host system OpenSSL version.

## Pipeline stages

For each profile, the pipeline executes the same sequence:

1. verify or build Docker images;
2. generate temporary CA and server certificates;
3. stop any previous Docker Compose environment;
4. start the TLS server;
5. run repeated TLS client handshakes;
6. collect raw CSV metrics;
7. aggregate Markdown, CSV and JSON reports;
8. clean up the Docker Compose environment.

The key principle is that profile-specific differences are stored in `configs/profiles/*.yml`, while the pipeline logic remains shared.

## TLS verification approach

Each profile restricts TLS negotiation to exactly one configured key exchange group:

- `classical`: `X25519`;
- `hybrid`: `X25519MLKEM768`;
- `pqc`: `MLKEM768`.

The pipeline checks:

- TLS connection success;
- observed TLS version;
- certificate verification result;
- expected key exchange group;
- actual key exchange group;
- OpenSSL exit code;
- error output if the test fails.

If OpenSSL prints the negotiated temporary key, the parser uses that output directly.

If OpenSSL does not print the temporary key, but the connection succeeds with TLS 1.3, certificate verification is successful, and both server and client are restricted to a single configured group, the pipeline records the configured group with the evidence value:

```text
restricted-single-group
```

This allows the experiment to remain deterministic even when OpenSSL CLI output format changes between versions.

## Metrics

Raw metrics are saved to:

```text
artifacts/metrics/raw-<profile>.csv
```

The raw CSV contains:

* `profile`;
* `iteration`;
* `status`;
* `handshake_ms`;
* `expected_group`;
* `actual_group`;
* `group_evidence`;
* `tls_version`;
* `openssl_exit_code`;
* `error`.

Aggregated per-profile reports are saved to:

```text
artifacts/reports/summary-<profile>.md
artifacts/reports/summary-<profile>.csv
artifacts/reports/summary-<profile>.json
```

Combined reports are saved to:

```text
artifacts/reports/summary-all.md
artifacts/reports/summary-all.csv
artifacts/reports/summary-all.json
```

## Main interpreted indicators

The main indicators are:

| Indicator                 | Meaning                                                 |
| ------------------------- | ------------------------------------------------------- |
| `success_rate`            | Reliability of the profile in repeated TLS handshakes   |
| `avg_handshake_ms`        | Average TLS handshake time                              |
| `median_handshake_ms`     | Median TLS handshake time                               |
| `dominant_actual_group`   | Most frequently observed or inferred key exchange group |
| `dominant_group_evidence` | Evidence used to confirm the actual group               |
| `server_cert_size_bytes`  | Size of the generated server certificate                |
| `server_key_size_bytes`   | Size of the generated server key                        |

## Reproducing the experiment

Build images:

```bash
make build
```

Run all profiles:

```bash
make run-all
```

Run the full local smoke-test:

```bash
make check
```

Inspect OpenSSL/PQC capabilities:

```bash
make crypto-capabilities
```

## Expected successful result

A successful experiment should produce:

* 30 successful handshakes for `classical`;
* 30 successful handshakes for `hybrid`;
* 30 successful handshakes for `pqc`;
* `TLSv1.3` as the observed TLS version for all profiles;
* `X25519` as the actual group for `classical`;
* `X25519MLKEM768` as the actual group for `hybrid`;
* `MLKEM768` as the actual group for `pqc`;
* generated Markdown, CSV and JSON reports.

## Limitations

The prototype has the following limitations:

1. The test stand uses `openssl s_server` and `openssl s_client` instead of a full application server.
2. The `pqc` profile uses post-quantum ML-KEM key establishment but keeps a classical ECDSA certificate.
3. CPU and memory metrics are not collected as first-class report fields.
4. The experiment focuses on reproducible CI/CD integration rather than production cryptographic deployment.
5. The measured handshake time includes command execution and container networking overhead, so it should be interpreted as an engineering pipeline metric rather than a pure cryptographic benchmark.

## Use in research

The generated reports can be used as source material for the experimental part of the graduation thesis. They demonstrate:

* reproducible profile selection;
* automated certificate generation;
* automated TLS deployment;
* repeated integration testing;
* structured metric collection;
* comparison of classical, hybrid and post-quantum configurations;
* CI/CD integration through GitHub Actions.
