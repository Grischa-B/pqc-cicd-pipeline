SHELL := /usr/bin/env bash

.PHONY: help build test-profiles crypto-capabilities check run-classical run-hybrid run-pqc run-all clean down status

help:
	@echo "PQC CI/CD Pipeline Prototype"
	@echo
	@echo "Available targets:"
	@echo "  make build          Build Docker images"
	@echo "  make test-profiles  Validate profile configuration files"
	@echo "  make crypto-capabilities  Show OpenSSL/PQC capabilities in the crypto image"
	@echo "  make check          Run full local project smoke-test"
	@echo "  make run-classical  Run classical TLS 1.3 profile"
	@echo "  make run-hybrid     Run hybrid TLS 1.3 + PQC profile"
	@echo "  make run-pqc        Run maximum-supported PQC profile"
	@echo "  make run-all        Run all profiles and generate combined report"
	@echo "  make down           Stop Docker Compose environment"
	@echo "  make clean          Remove generated runtime artifacts"
	@echo "  make status         Show Docker Compose status"

build:
	./scripts/build/build-images.sh

test-profiles:
	python3 -m unittest tests/test_profiles.py

crypto-capabilities:
	./scripts/crypto/list-capabilities.sh

check:
	./scripts/check-project.sh

run-classical:
	./scripts/run-pipeline.sh classical

run-hybrid:
	./scripts/run-pipeline.sh hybrid

run-pqc:
	./scripts/run-pipeline.sh pqc

run-all:
	./scripts/run-all.sh

down:
	./scripts/deploy/down.sh

clean:
	./scripts/deploy/down.sh
	rm -rf artifacts/certs/* artifacts/logs/* artifacts/metrics/* artifacts/reports/* results/*
	touch artifacts/certs/.gitkeep artifacts/logs/.gitkeep artifacts/metrics/.gitkeep artifacts/reports/.gitkeep results/.gitkeep

status:
	docker compose ps