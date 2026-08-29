# Security policy

## Reporting a vulnerability

Please use the repository's private GitHub security-advisory form instead of opening a
public issue. Include affected endpoints or versions, reproduction steps, impact, and any
suggested mitigation.

Do not include live passwords, JWTs, database URLs, or personal information in reports.

## Supported version

Security fixes are applied to the latest commit on `main`. This portfolio project does
not currently publish long-term-support release branches.

## Deployment responsibilities

Operators must replace every placeholder in `.env`, terminate TLS at a trusted proxy,
restrict the metrics endpoint at the network layer, rotate secrets, back up PostgreSQL,
and review audit data according to their retention policy.
