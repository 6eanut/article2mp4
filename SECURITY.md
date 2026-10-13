# Security Policy

## Supported versions

This project is at an early stage; only the latest `main` branch is supported.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Instead, report
them privately using GitHub's
[private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
feature on the repository's **Security** tab.

Please include:

- a description of the issue and its impact,
- steps to reproduce it,
- any relevant configuration or environment details.

You can expect an initial response within a few days. Once a fix is available,
we will coordinate disclosure with you.

## Scope notes

- The tool treats the configured LLM endpoint as trusted infrastructure and reads
  all settings from environment variables / `.env`. Never commit a real `.env`;
  only `.env.example` is tracked.
- Downloaded speech models are fetched over HTTPS from a GitHub release via public
  mirrors and verified against the server-announced `Content-Length`. No model
  binaries are stored in the repository.
