# Repository Guidelines (AGENTS.md)

## Project Structure & Module Organization
- `pay-ledger-api/`: Shared RPC contracts, DTOs, enums, and constants (no implementation logic).
- `pay-ledger-server/`: Spring Boot application (`src/main/java`, `src/main/resources/mapper`, `src/test/java`).

## Build & Verification Commands
- `mvn clean verify` — compile all modules and run unit tests.
- `mvn -pl pay-ledger-server -am test -Dtest=*Test` — run targeted module tests.

## Coding & Safety Conventions
- Follow existing package boundaries; preserve suffixes (`Controller`, `Service`, `Mapper`, `Facade`, `Req`, `Resp`).
- Add regression tests for balance mutations, refunds, locking, idempotency, and mapper SQL.
- Never commit credentials, keys, or production endpoints.

# Agent Instructions
Read and follow `.ai/AI_CONTEXT.md` and `.ai/MEMORY_POLICY.md` before starting work.
