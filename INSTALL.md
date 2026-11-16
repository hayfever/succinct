# How to install

succinct supports five harnesses: Claude Code, Codex, OpenCode, Pi, and OMP. Each one uses the same activation model: `/succinct on` creates a `.succinct-always` flag file in the harness's configuration directory, `/succinct off` deletes it, and every session starts from the flag. Any other agent can install the skill with `npx skills add`, or paste the always-on snippet into its rules file.

This repository lives at `https://github.com/hayfever/succinct`. If you forked it, swap `hayfever/succinct` for your own `owner/repo` in every command below. Claude Code also accepts a local path to the repo root.

## Contents

| Section | Section |
|---|---|
| [Claude Code](#claude-code) | [Any skills CLI agent](#agent-skills-harnesses) |
| [Codex](#codex) | [Other agents](#other-agents) |
| [OpenCode](#opencode) | [Always-on snippet](#always-on-snippet) |
| [Pi](#pi) | [How activation works](#how-activation-works) |
| [OMP](#omp) | [Troubleshooting](#troubleshooting) |

<a id="claude-code"></a>
<details>
<summary><strong>Claude Code</strong></summary>

### Install

```bash
claude plugin marketplace add hayfever/succinct
claude plugin install succinct@succinct
```

### Turn it on

```text
/succinct
/succinct on
/succinct off
```

- `/succinct` turns the mode on for this session.
- `/succinct on` turns it on now and creates the flag file `~/.claude/.succinct-always`. Every new session starts on while the flag exists.
- `/succinct off` turns it off now and deletes the flag. Every new session starts off.
- `stop succinct mode` or `normal mode` turns the mode off for this session only. The flag stays.

With a custom Claude configuration directory, the flag is `"$CLAUDE_CONFIG_DIR/.succinct-always"`.

### Verify

```bash
claude plugin list
```

### Update

```bash
claude plugin marketplace update succinct
```

### Uninstall

```bash
claude plugin uninstall succinct
claude plugin marketplace remove succinct
rm -f ~/.claude/.succinct-always
```

Or keep it installed and turn it off: `claude plugin disable succinct`.

### How the hooks work

A `SessionStart` hook loads the ruleset when the flag exists. Otherwise it prints nothing and exits 0 in about 30 ms, so installing the plugin changes nothing by itself. A `UserPromptExpansion` hook runs only when you type `/succinct`, and creates or deletes the flag when you add `on` or `off`.

The hooks need no Node install. They run `hooks/always-on.sh` and `hooks/toggle.sh` with `sh` on macOS and Linux and in Git Bash on Windows. When Git Bash is missing, Claude Code passes the same command lines to PowerShell, and `hooks/always-on.ps1` and `hooks/toggle.ps1` do the work instead.

Claude Code limits one hook's text to 10,000 characters. The core is 8,170 characters, so the hook delivers the whole core. The reference files stay on disk and load only on demand.

</details>

<a id="codex"></a>
<details>
<summary><strong>Codex</strong></summary>

### Install

```bash
codex plugin marketplace add hayfever/succinct --ref main
codex plugin add succinct@succinct
```

The plugin ships a `SessionStart` hook and a `UserPromptSubmit` hook. Codex asks you to review and trust plugin hooks before they run: type `/hooks`, read the hooks, and trust them. Until you do, Codex skips the hooks and prints a warning at startup.

### Turn it on

```text
$succinct
$succinct on
$succinct off
```

- `$succinct` turns the mode on for this session.
- `$succinct on` turns it on now and creates the flag file `~/.codex/.succinct-always`. Every new session starts on while the flag exists.
- `$succinct off` turns it off now and deletes the flag. Every new session starts off.
- `stop succinct mode` or `normal mode` turns the mode off for this session only. The flag stays.

Codex will not activate the skill by itself. With `CODEX_HOME` set, the flag is `"$CODEX_HOME/.succinct-always"`. Codex and Claude Code keep separate flags.

### Verify

```bash
codex plugin list
```

### Update

```bash
codex plugin marketplace upgrade succinct
codex plugin remove succinct
codex plugin add succinct@succinct
```

### Uninstall

```bash
codex plugin remove succinct
codex plugin marketplace remove succinct
rm -f ~/.codex/.succinct-always
```

### How the hooks work

The `SessionStart` hook loads the ruleset when the flag exists. Codex has no per-command hook event, so the `UserPromptSubmit` hook runs on every prompt and exits at once unless the prompt is `$succinct on` or `$succinct off`. Both hooks run `sh` on macOS and Linux and PowerShell on Windows, with no Node install.

Do not want Codex to run plugin hooks at all? Add the [always-on snippet](#always-on-snippet) to `~/.codex/AGENTS.md` instead.

</details>

<a id="opencode"></a>
<details>
<summary><strong>OpenCode</strong></summary>

OpenCode 2 loads this repository as a local plugin. The plugin in `.opencode/plugins/succinct/` registers the `/succinct` command and appends the core ruleset to the system prompt of every model request while the flag file exists. The `skills` entry adds the skill itself, so the `skill` tool can load it.

OpenCode 1 cannot load this plugin. Its plugin API is different, and OpenCode 2 does not run OpenCode 1 plugins.

### Install

Clone the repo. One checkout serves every project:

```bash
git clone https://github.com/hayfever/succinct ~/.config/opencode/vendor/succinct
```

Add both entries to your global `~/.config/opencode/opencode.json`. The paths must be absolute, and a plugin path must point at a directory, not a file:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": ["/absolute/path/to/succinct/.opencode/plugins/succinct"],
  "skills": ["/absolute/path/to/succinct/skills"]
}
```

Or run OpenCode from the checkout. The root `opencode.json` already has both entries.

### Turn it on

```text
/succinct
/succinct on
/succinct off
```

- `/succinct` turns the mode on for this session.
- `/succinct on` turns it on now and creates the flag file `~/.config/opencode/.succinct-always`. Every new session starts on while the flag exists.
- `/succinct off` turns it off now and deletes the flag. Every new session starts off.
- `stop succinct mode` or `normal mode` turns the mode off for this session only. The flag stays.

With `XDG_CONFIG_HOME` set, the flag is `"$XDG_CONFIG_HOME/opencode/.succinct-always"`.

### Verify

Type `/` and confirm `succinct` appears in the command list. Ask the agent to list its skills and confirm `succinct` is there.

### Update

```bash
git -C ~/.config/opencode/vendor/succinct pull
opencode service restart
```

### Uninstall

Remove the `plugins` and `skills` entries from `opencode.json`, then delete the flag:

```bash
rm -f ~/.config/opencode/.succinct-always
```

</details>

<a id="pi"></a>
<details>
<summary><strong>Pi</strong></summary>

Pi discovers this repository as a native package: `extensions/` provides the session-persistent mode and `skills/` keeps the Agent Skills entry point available.

### Install

```bash
pi install https://github.com/hayfever/succinct
```

### Turn it on

```text
/succinct
/succinct on
/succinct off
```

- `/succinct` turns the mode on for this session.
- `/succinct on` turns it on now and creates the flag file `~/.pi/agent/.succinct-always`. Every new session starts on while the flag exists.
- `/succinct off` turns it off now and deletes the flag. Every new session starts off.
- `stop succinct mode` or `normal mode` turns the mode off for this session only. The flag stays.
- The footer shows `● SUCCINCT ON` while the mode is active.

If `PI_CODING_AGENT_DIR` is set, the flag lives in that directory.

The extension adds the ruleset to the conversation once instead of rewriting the system prompt on every request, and adds it again after compaction drops it. The existing Agent Skills command remains available as an alias:

```text
/skill:succinct
```

Start one Pi session with the mode on, without the flag:

```bash
pi --succinct
```

### Verify

```bash
pi list
```

Confirm the GitHub package is listed, then type `/succinct` and check that `● SUCCINCT ON` appears in the footer.

### Update

```bash
pi update https://github.com/hayfever/succinct
```

Or update every unpinned Pi package with `pi update --extensions`.

### Uninstall

```bash
pi remove https://github.com/hayfever/succinct
rm -f ~/.pi/agent/.succinct-always
```

### Status line placement

Plain Pi renders extension statuses on their own footer line below the stats row, and truncates with an ellipsis on overflow. There is no powerline `status` segment in Pi, so the separate line is the runtime's design; the same-line option below is OMP-only.

</details>

<a id="omp"></a>
<details>
<summary><strong>Oh My Pi (OMP)</strong></summary>

### Install

```bash
omp plugin marketplace add hayfever/succinct
omp plugin install --scope user succinct@succinct
```

### Turn it on

```text
/succinct
/succinct on
/succinct off
```

- `/succinct` turns the mode on for this session.
- `/succinct on` turns it on now and creates the flag file `~/.omp/agent/.succinct-always`. Every new session starts on while the flag exists.
- `/succinct off` turns it off now and deletes the flag. Every new session starts off.
- `stop succinct mode` or `normal mode` turns the mode off for this session only. The flag stays.
- The footer shows `● SUCCINCT ON` while the mode is active.

### Same-line status (optional)

By default OMP renders extension statuses on their own line below the powerline. To render `● SUCCINCT ON` inline with the other powerline modules, add the `status` segment to the status line and turn the below-line copy off in `~/.omp/agent/config.yml`:

```yaml
statusLine:
  preset: custom
  leftSegments: [pi, model, mode, path, git, status, context_pct, cost]
  rightSegments: [session_name]
  showHookStatus: false
```

Keep `showHookStatus: false` only when `status` is in a segment, or the status shows twice. The status line truncates on overflow rather than wrapping; a single `● SUCCINCT ON` always fits.

### Update

```bash
omp plugin marketplace update succinct
omp plugin upgrade --scope user succinct@succinct
```

### Uninstall

```bash
omp plugin uninstall --scope user succinct@succinct
omp plugin marketplace remove succinct
rm -f ~/.omp/agent/.succinct-always
```

</details>

<a id="agent-skills-harnesses"></a>
<details>
<summary><strong>Any skills CLI agent</strong></summary>

Works with any agent that reads agent skills. Swap `-a <agent>` for yours. These agents load the skill when you type `/succinct`; they have no `/succinct on` or `/succinct off`. To keep the rules on in every session, use the [always-on snippet](#other-agents).

### Install

```bash
npx skills add hayfever/succinct                  # this workspace
npx skills add hayfever/succinct -g               # all projects
npx skills add hayfever/succinct -a <agent> -y    # one agent only
```

New agent chat, type `/succinct`.

Without the CLI, copy the skill folder into whatever path your agent scans:

```bash
git clone https://github.com/hayfever/succinct
mkdir -p ~/.agents/skills     # or your agent's own skills path
cp -R succinct/skills/succinct ~/.agents/skills/
```

### Verify

```bash
npx skills list
npx skills ls -g    # if installed globally
```

### Update

```bash
npx skills update succinct
npx skills update -g    # if installed globally
```

### Uninstall

```bash
npx skills remove succinct
npx skills remove succinct -g    # if installed globally
```

</details>

## Other agents

Any other agent can keep the rules on in every session: paste the [always-on snippet](#always-on-snippet) into its persistent rules file. Examples: Cursor user rules, `AGENTS.md`, `GEMINI.md`, or `.github/copilot-instructions.md`. Delete the snippet to turn it off.

## Always-on snippet

Paste this into your agent's persistent rules file. It is a short form of the core rules.

```markdown
## Output style

The reader has ADHD. Shape every response so it can be acted on:

1. Lead with the answer: the result, or the command, path, or snippet that is the answer.
2. Number multi-step work; one bounded action per step.
3. End with one next action doable in under two minutes. It goes last.
4. Finish the current issue before raising a new one.
5. Restate progress each turn ("step 3 of 5 done").
6. Give time estimates in concrete units, never "a bit".
7. After a change, show what now works.
8. Errors: state location, cause, and fix. No drama.
9. Cap lists at 5 items.
10. No preamble, no recaps, no closers.

Write plain: active voice, imperative steps, steps of 20 words or fewer, no semicolons, one term per item, no contractions, no "e.g.", "i.e.", or "etc.". Sound human: no not-X-but-Y contrasts, one-line closers, forced triads, dashes, stock AI words, bold labels, or chatbot residue. Never invent a fact; quoted text, code, and paths stay exactly as they are.

Exceptions: explain fully when asked to explain. Confirm before destructive actions. After three failed fixes, stop and name the doubtful assumption. If the request is ambiguous, ask one short question.
```

## How activation works

1. **Installed, not invoked.** Nothing happens until you turn the mode on. Claude Code honors `disable-model-invocation: true` in `SKILL.md`, and Codex honors `policy.allow_implicit_invocation: false` in `skills/succinct/agents/openai.yaml`.
2. **`/succinct`** (`$succinct` in Codex) turns the mode on for the current session.
3. **`/succinct on`** creates the `.succinct-always` flag and **`/succinct off`** deletes it. Each harness keeps its own flag: `~/.claude/` (Claude Code), `~/.codex/` (Codex), `~/.config/opencode/` (OpenCode), `~/.pi/agent/` (Pi), and `~/.omp/agent/` (OMP). Every session starts from the flag: on while it exists, off when it does not.
4. **"stop succinct mode" or "normal mode"** turns the mode off for the current session only.
5. **Other agents** use the always-on snippet in their rules file.

## Troubleshooting

**`/succinct` not in autocomplete.** Restart the agent. The plugin index is read at startup.

**The flag has no effect.** Update the plugin and restart. Hooks are read at startup. In Codex, trust the hooks in `/hooks` first.

**`claude plugin marketplace add` fails.** Use the `owner/repo` form. A local path must point at the repo root, not `.claude-plugin/`.

**Installed but replies still preamble.** Open a new session. If it still drifts, tighten the wording in `skills/succinct/SKILL.md`.

**Want different rules.** Fork, edit `skills/succinct/SKILL.md`, then swap your copy in (see [README](README.md#tune-it)). Restart, then re-invoke `/succinct`.

**Skill missing after `npx skills add`.** Start a new agent chat. Skills are indexed at session start. Confirm the folder landed where your agent scans and that the frontmatter `name` matches the folder name.