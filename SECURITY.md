# Security policy

## Supported versions

Only the current major release gets fixes.

| Version | Supported |
| --- | --- |
| 1.x | Yes |

## Scope

succinct ships Markdown instructions, JSON manifests, and six hook, plugin, and extension scripts: `hooks/always-on.sh`, `hooks/always-on.ps1`, `hooks/toggle.sh`, `hooks/toggle.ps1`, the OpenCode plugin, and the Pi and OMP extension. They read a local SKILL.md file and print or inject it, and `/succinct on` or `/succinct off` creates or deletes one empty `.succinct-always` flag file in the agent's configuration directory. Nothing executes on install; nothing makes network calls; nothing collects data.

## Reporting a vulnerability

Use GitHub's private security advisory ("Report a vulnerability" on the Security tab) rather than a public issue. Include the runtime (Claude Code, Codex, OpenCode, Pi, OMP, or another agent), the install route, and the file involved.

## What is in scope

- A hook or plugin script reading or executing files outside the checked-out repository.
- Injection through the flag file path or the plugin root environment.
- A manifest that makes an agent execute anything at install time.

## What is not in scope

- Prompt-injection behavior of the ruleset itself; the skill instructs models, and models remain responsible for what they do with instructions.
- Vulnerabilities in the agent runtimes (report those upstream).