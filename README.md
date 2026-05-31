# PQC CI/CD Pipeline Prototype

Open-source prototype of a CI/CD pipeline for software delivery with support for post-quantum cryptography profiles.

## Goal

The project demonstrates how classical, hybrid, and post-quantum cryptographic profiles can be integrated into an automated software delivery process.

The pipeline is intended to:

- build a reproducible container environment;
- generate temporary test keys and certificates;
- run a TLS server and TLS client;
- verify the selected TLS profile;
- collect logs and metrics;
- save structured experiment results.

## Target profiles

- `classical` — classical TLS 1.3 baseline;
- `hybrid` — TLS 1.3 with hybrid classical + PQC key exchange;
- `pqc` — post-quantum or maximum-supported PQC profile.

## Quick start

```bash
./scripts/build/build-images.sh
./scripts/run-pipeline.sh classical
./scripts/run-pipeline.sh hybrid
./scripts/run-pipeline.sh pqc
```
## Security note

Generated keys, certificates, logs, metrics, and reports are runtime artifacts. They must not be committed to Git.
