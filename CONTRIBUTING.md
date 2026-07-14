# Contributing

Thanks for improving Kip's public OpenClaw skills. Small, focused contributions are easiest to review and most useful to others adapting these skills to their own setups.

## Before you start

- Search existing issues and pull requests first.
- Use an issue to discuss a new skill or a substantial change before writing it.
- Keep a skill portable. Replace personal paths, hostnames, IDs, credentials, and account-specific assumptions with placeholders or configuration.
- Never include credentials, tokens, private URLs, personal data, or copied private logs.

## Proposing a skill

Explain the problem it solves, its expected inputs and outputs, the tools or permissions it needs, and how another OpenClaw user can validate it. A good proposal includes one realistic example.

## Pull requests

- Keep each pull request limited to one purpose.
- Update `SKILL.md` and any required supporting files together.
- Include setup instructions, safe defaults, and a validation command or manual test.
- State what you tested in the pull request description.
- Do not add network calls, destructive actions, or external side effects without clearly documenting them and making them opt-in.

Automated contributions are welcome when they follow these rules. Please avoid bulk-generated issues or pull requests; a maintainer may close them without review.

## Review and publication

This repository is published from a private working copy after automated sanitization. Contributions may be adapted, delayed, or declined when they cannot be made safe and portable. Merged public changes can be overwritten only by the maintained publishing workflow, so root community files and skill changes are reviewed with that workflow in mind.
