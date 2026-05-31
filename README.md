# PQC CI/CD Pipeline Prototype

Open-source prototype of a CI/CD pipeline for software delivery with support for post-quantum cryptography profiles.

The project demonstrates how classical, hybrid and post-quantum cryptographic configurations can be integrated into an automated software delivery process: environment preparation, certificate generation, TLS server/client deployment, integration testing, metrics collection and report generation.

## Purpose

The prototype is developed as part of a graduation research project on:

> Development of a software delivery pipeline with support for post-quantum cryptography.

The main goal is not to test an isolated cryptographic primitive, but to verify the full engineering cycle of integrating cryptographic profiles into a reproducible CI/CD workflow.

The pipeline supports:

* classical TLS 1.3 profile;
* hybrid TLS 1.3 profile with classical and post-quantum key establishment;
* maximum-supported post-quantum TLS profile.

## Technology stack

* Ubuntu 24.04 LTS
* Docker
* Docker Compose
* GitHub Actions
* Bash
* Python 3
* OpenSSL 3.5.6

OpenSSL is built inside the Docker image to avoid depending on the system OpenSSL version installed on the host machine.

## Repository structure

```text
pqc-cicd-pipeline/
├── .github/workflows/
│   └── pipeline.yml
├── configs/
│   ├── profiles/
│   │   ├── classical.yml
│   │   ├── hybrid.yml
│   │   └── pqc.yml
│   ├── tls/
│   │   └── openssl.cnf
│   └── ci/
│       └── defaults.env
├── docker/
│   ├── crypto/
│   │   └── Dockerfile
│   ├── server/
│   │   └── Dockerfile
│   └── client/
│       └── Dockerfile
├── scripts/
│   ├── build/
│   │   └── build-images.sh
│   ├── certs/
│   │   └── generate-certs.sh
│   ├── deploy/
│   │   ├── up.sh
│   │   └── down.sh
│   ├── test/
│   │   ├── run-handshake-test.sh
│   │   └── run-profile-tests.sh
│   ├── metrics/
│   │   ├── collect-metrics.sh
│   │   └── aggregate-results.py
│   ├── run-pipeline.sh
│   └── run-all.sh
├── src/
│   ├── server/
│   │   └── README.md
│   └── client/
│       └── README.md
├── tests/
│   └── test_profiles.py
├── artifacts/
│   ├── certs/
│   ├── logs/
│   ├── metrics/
│   └── reports/
├── results/
├── docker-compose.yml
├── README.md
└── LICENSE
```

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

Equivalent direct script commands are also available:

```bash
./scripts/build/build-images.sh
./scripts/run-pipeline.sh classical
./scripts/run-pipeline.sh hybrid
./scripts/run-pipeline.sh pqc
./scripts/run-all.sh
```

## Local test commands

Validate profile configuration files:

```bash
make test-profiles
```

Inspect OpenSSL/PQC capabilities inside the Docker image:

```bash
make crypto-capabilities
```

Equivalent direct command:

```bash
python3 -m unittest tests/test_profiles.py
```

Stop the Docker Compose environment manually:

```bash
make down
```

Equivalent direct command:

```bash
./scripts/deploy/down.sh
```

Show Docker Compose service status:

```bash
make status
```

Remove generated runtime artifacts:

```bash
make clean
```

Force Docker image rebuild during a pipeline run:

```bash
FORCE_REBUILD=1 ./scripts/run-pipeline.sh classical
```

## Output artifacts

Runtime artifacts are generated under `artifacts/`.

```text
artifacts/
├── certs/
│   ├── classical/
│   ├── hybrid/
│   └── pqc/
├── logs/
│   ├── classical/
│   ├── hybrid/
│   └── pqc/
├── metrics/
│   ├── raw-classical.csv
│   ├── raw-hybrid.csv
│   └── raw-pqc.csv
└── reports/
    ├── summary-classical.json
    ├── summary-classical.csv
    ├── summary-classical.md
    ├── summary-hybrid.json
    ├── summary-hybrid.csv
    ├── summary-hybrid.md
    ├── summary-pqc.json
    ├── summary-pqc.csv
    ├── summary-pqc.md
    ├── summary-all.json
    ├── summary-all.csv
    └── summary-all.md
```

The combined report is available at:

```text
artifacts/reports/summary-all.md
artifacts/reports/summary-all.csv
artifacts/reports/summary-all.json
```

## Collected metrics

The pipeline collects the following metrics:

* profile name;
* iteration number;
* handshake status;
* TLS handshake time in milliseconds;
* expected key exchange group;
* actual key exchange group;
* group verification evidence;
* observed TLS version;
* OpenSSL exit code;
* error message, if any;
* server key size;
* server certificate size;
* CA certificate size.

## Experimental methodology

The experimental methodology is described in:

```text
docs/EXPERIMENT.md
```

## Cryptographic verification

Each profile restricts TLS negotiation to a single configured group. This makes the profile verification deterministic:

* `classical` allows only `X25519`;
* `hybrid` allows only `X25519MLKEM768`;
* `pqc` allows only `MLKEM768`.

If OpenSSL prints the negotiated temporary key, the parser uses that value directly. If OpenSSL does not print the temporary key, but the TLS 1.3 connection succeeds with a single restricted group and certificate verification succeeds, the pipeline records the configured group with the evidence value:

```text
restricted-single-group
```

This behavior is reflected in raw CSV metrics and Markdown/JSON summaries.

## GitHub Actions

The project includes a GitHub Actions workflow:

```text
.github/workflows/pipeline.yml
```

The workflow runs on:

* `push`;
* `pull_request`;
* manual `workflow_dispatch`.

Manual runs support selecting one of the following options:

* `all`;
* `classical`;
* `hybrid`;
* `pqc`.

The workflow validates profile configuration files, builds Docker images, runs the pipeline and uploads logs, metrics and reports as artifacts.

## Security notes

Generated private keys, certificates, logs, metrics and reports are runtime artifacts.

They must not be committed to Git.

The repository `.gitignore` excludes:

* generated certificates;
* private keys;
* CSRs;
* logs;
* metrics;
* reports;
* local result files.

The generated certificates are intended only for the local experimental TLS stand and CI/CD verification.

## Troubleshooting

### Docker Hub download fails

Example error:

```text
failed to resolve source metadata for docker.io/library/ubuntu:24.04
failed to fetch anonymous token
```

This usually indicates a temporary Docker Hub or network issue. Retry the build later.

If the base image already exists locally, run the pipeline without forcing rebuild:

```bash
./scripts/run-pipeline.sh classical
```

### Need to rebuild OpenSSL image

Use:

```bash
FORCE_REBUILD=1 ./scripts/run-pipeline.sh classical
```

Or build images directly:

```bash
./scripts/build/build-images.sh
```

### TLS server is still running

Stop the environment:

```bash
./scripts/deploy/down.sh
```

### A profile fails because a TLS group is unsupported

Check available KEM algorithms:

```bash
docker run --rm pqc-crypto-base:local openssl list -kem-algorithms
```

Expected important entries include:

```text
MLKEM768
X25519MLKEM768
```

### Generated reports are missing

Run a profile first:

```bash
./scripts/run-pipeline.sh classical
```

Or run all profiles:

```bash
./scripts/run-all.sh
```

## Current limitations

* The prototype uses `openssl s_server` and `openssl s_client` instead of a full application server. This is intentional: the goal is to evaluate TLS/PQC integration, not business logic.
* The `pqc` profile uses ML-KEM key establishment but keeps a classical ECDSA certificate for compatibility and stability.
* CPU and memory metrics are not yet collected as first-class report fields.
* The project is an experimental research prototype and is not intended for production cryptographic deployment.

## License

MIT License.
