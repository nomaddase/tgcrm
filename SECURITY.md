# Security Policy

## Secrets Management

- Store **TELEGRAM_BOT_TOKEN**, **OPENAI_API_KEY**, and database credentials exclusively in secret stores (for example HashiCorp Vault, AWS Secrets Manager, or GitHub Actions secrets). Never commit real values to the repository.
- Provide secrets to containers via environment variables or orchestrator secret mounts. Avoid hard-coding them in Compose files.
- Rotate API keys regularly and immediately after suspected compromise.
- When sharing configuration examples, use placeholders and never reuse production credentials for testing.

## Local Development

- Create a `.env` file from `.env.example` and keep it outside of version control. Restrict file permissions so that only the necessary user accounts can read it.
- Use distinct API keys and bot tokens for development to reduce blast radius.

## Incident Response

If you discover a security vulnerability, please notify the maintainers at `security@example.com`. Provide a detailed description so we can reproduce and address the issue quickly. Avoid filing public issues before contacting us privately.
