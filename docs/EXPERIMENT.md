# Experimental Methodology

Language: English | [Русский](EXPERIMENT.ru.md)

## Purpose

This document describes the experimental methodology used in the PQC CI/CD pipeline prototype.

The experiment compares three TLS profiles in the same reproducible CI/CD environment:

- `classical` — classical TLS 1.3 baseline;
- `hybrid` — TLS 1.3 with classical and post-quantum key establishment;
- `pqc` — maximum-supported post-quantum key establishment profile.

The goal is to evaluate the engineering integration of cryptographic profiles into a delivery pipeline, not to benchmark an isolated cryptographic primitive.

## Compared profiles

| Profile | Key exchange group | Certificate type | Role |
|---|---|---|---|
| `classical` | `X25519` | ECDSA / P-256 | Baseline TLS 1.3 profile |
| `hybrid` | `X25519MLKEM768` | ECDSA / P-256 | Migration profile with classical + PQC key establishment |
| `pqc` | `MLKEM768` | ECDSA / P-256 | Maximum-supported PQC key establishment profile |

The `pqc` profile intentionally keeps a classical ECDSA certificate. Therefore, it is treated as a maximum-supported PQC profile rather than a fully post-quantum TLS/X.509 configuration.

## Experimental environment

The environment is defined by Docker and the repository configuration.

Main components:

- Ubuntu 24.04 based Docker image;
- OpenSSL 3.5.6 built inside the Docker image;
- Docker Compose test stand;
- `openssl s_server` as TLS server;
- `openssl s_client` as TLS client;
- Bash scripts for orchestration;
- Python scripts for aggregation;
- GitHub Actions for CI execution.

## Pipeline stages

For each profile, the pipeline performs the same sequence:

1. checks or builds Docker images;
2. generates temporary CA and server certificates;
3. starts the TLS server;
4. performs repeated TLS client handshakes;
5. writes raw CSV metrics;
6. generates Markdown, CSV and JSON reports;
7. cleans up the Docker Compose environment.

The profile-specific parameters are stored in `configs/profiles/*.yml`. The pipeline logic remains shared across all profiles.

## TLS verification

Each profile restricts TLS negotiation to exactly one key exchange group:

- `classical`: `X25519`;
- `hybrid`: `X25519MLKEM768`;
- `pqc`: `MLKEM768`.

The pipeline verifies:

- TLS connection success;
- observed TLS version;
- certificate verification result;
- expected and actual key exchange group;
- OpenSSL exit code;
- error output if the test fails.

If OpenSSL does not print the negotiated temporary key, but the connection succeeds with TLS 1.3, certificate verification succeeds and both sides are restricted to a single configured group, the pipeline records the group with the evidence value:

```text
restricted-single-group
```

## Metrics, reports and charts

Raw handshake metrics are saved to:

```text
artifacts/metrics/raw-<profile>.csv
```

Pipeline stage duration metrics are saved to:

```text
artifacts/metrics/stages-<profile>.csv
```

Runtime and resource metrics are saved to:

```text
artifacts/metrics/runtime-<profile>.csv
artifacts/metrics/container-stats-<profile>.csv
```

Per-profile summaries are saved to:

```text
artifacts/reports/summary-<profile>.md
artifacts/reports/summary-<profile>.csv
artifacts/reports/summary-<profile>.json
```

Combined summaries are saved to:

```text
artifacts/reports/summary-all.md
artifacts/reports/summary-all.csv
artifacts/reports/summary-all.json
```

Charts are generated as SVG files under:

```text
artifacts/reports/charts/
```

Main interpreted indicators:

| Indicator                    | Meaning                                                  |
| ---------------------------- | -------------------------------------------------------- |
| `success_rate`               | Reliability of the profile in repeated TLS handshakes    |
| `avg_handshake_ms`           | Average TLS handshake time                               |
| `median_handshake_ms`        | Median TLS handshake time                                |
| `total_pipeline_duration_ms` | Total duration of the profile pipeline run               |
| `test_duration_ms`           | Duration of the integration test stage                   |
| `server_cpu_max_percent`     | Maximum sampled CPU usage of the TLS server container    |
| `server_memory_max_mib`      | Maximum sampled memory usage of the TLS server container |
| `dominant_actual_group`      | Most frequently observed or inferred key exchange group  |
| `dominant_group_evidence`    | Evidence used to confirm the actual group                |
| `cert_chain_size_bytes`      | Combined size of the CA and server certificates          |
| `server_key_size_bytes`      | Size of the generated server key                         |

## Reproduction

Build images:

```bash
make build
```

Run all profiles:

```bash
make run-all
```

Run the full local project check:

```bash
make check
```

Inspect OpenSSL/PQC capabilities:

```bash
make crypto-capabilities
```

## Expected result

A successful experiment should produce:

* 30 successful handshakes for `classical`;
* 30 successful handshakes for `hybrid`;
* 30 successful handshakes for `pqc`;
* `TLSv1.3` as the observed TLS version;
* `X25519`, `X25519MLKEM768` and `MLKEM768` as actual groups for the corresponding profiles;
* Markdown, CSV and JSON reports.

## Limitations

* The test stand uses `openssl s_server` and `openssl s_client` instead of a full application server.
* The `pqc` profile uses ML-KEM key establishment but keeps a classical ECDSA certificate.
* CPU and memory metrics are not collected as first-class report fields.
* The measured handshake time includes command execution and container networking overhead.
* The prototype is intended for research and educational use, not for production cryptographic deployment.
