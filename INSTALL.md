# How to install

The canonical skill is `skills/succinct/SKILL.md`. Every agent that reads agent skills accepts it with no conversion; plugin manifests serve the marketplaces of Claude Code, Codex, Kimi, Antigravity, and OMP.

This repository lives at `https://github.com/hayfever/succinct`. If you forked it, swap `hayfever/succinct` for your own `owner/repo` in every command below. Local copies work everywhere: the "without the CLI" fallback in each section is a folder copy, and several marketplaces accept a local path (Claude Code: the path must point at the repo root).

## Always-on snippet

Reusable in every agent's persistent rules file. One copy; each agent section below points here.

```markdown
## Output style

The reader has ADHD. Shape every response so it can be acted on:

1. Lead with the answer or next action: command, path, or snippet first.
2. Number multi-step work; one bounded action per step.
3. End with one next action doable in under two minutes.
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

<details>
<summary><strong>Antigravity (<code>agy</code>)</strong></summary>

### Install

```bash
agy plugin install https://github.com/hayfever/succinct
```

### Verify

```bash
agy plugin list
```

### Update

```bash
agy plugin uninstall succinct
agy plugin install https://github.com/hayfever/succinct
```

### Uninstall

```bash
agy plugin uninstall succinct
```

Or keep it installed and turn it off: `agy plugin disable succinct`.

### Always-on (optional)

Add the [always-on snippet](#always-on-snippet) to `~/.gemini/GEMINI.md`.

</details>

<details>
<summary><strong>Claude Code</strong></summary>

### Install

```bash
claude plugin marketplace add hayfever/succinct
claude plugin install succinct@succinct
```

Type `/succinct`.

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
```

Or keep it installed and turn it off: `claude plugin disable succinct`.

### Always-on (optional)

A `SessionStart` hook loads the ruleset at the start of every session, no `/succinct` needed:

```bash
touch ~/.claude/.succinct-always
```

If you use a custom Claude configuration directory, create the flag there instead:

```bash
touch "$CLAUDE_CONFIG_DIR/.succinct-always"
```

Back to on-demand:

```bash
rm ~/.claude/.succinct-always
```

The hook only fires when the flag file exists, so installing the plugin changes nothing by itself. It tests for the flag, prints nothing, and exits 0 in about 30 ms. "stop succinct mode" still turns it off for the current session.

The hook needs no Node install. It runs `hooks/always-on.sh` with `sh` on macOS and Linux and in Git Bash on Windows. When Git Bash is missing, Claude Code passes the same command line to PowerShell, and `hooks/always-on.ps1` loads the ruleset instead.

Claude Code limits one hook's text to 10,000 characters. The ruleset is larger than that, so Claude receives a preview and the path of a saved copy. Shorten `skills/succinct/SKILL.md` below 10,000 characters if you need the whole text in context.

</details>

<details>
<summary><strong>Codex</strong></summary>

### Install

```bash
codex plugin marketplace add hayfever/succinct --ref main
codex plugin add succinct@succinct
```

Invoke the skill explicitly by typing `$succinct`. Codex will not activate it automatically.

The plugin ships a `SessionStart` hook. Codex asks you to review and trust plugin hooks before they run: type `/hooks`, read the hook, and trust it. Until you do, Codex skips the hook and prints a warning at startup.

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
```

### Always-on (optional)

The same `SessionStart` hook as Claude Code loads the ruleset at the start of every session. It reads one flag file for both agents:

```bash
mkdir -p ~/.claude
touch ~/.claude/.succinct-always
```

Back to on-demand:

```bash
rm ~/.claude/.succinct-always
```

Trust the hook in `/hooks` first. Without that trust, Codex skips it. When you use a custom Claude configuration directory, create the flag at `"$CLAUDE_CONFIG_DIR/.succinct-always"` instead.

Do not want Codex to run plugin hooks at all? Add the [always-on snippet](#always-on-snippet) to `~/.codex/AGENTS.md` instead.

</details>

<details>
<summary><strong>Gemini CLI</strong></summary>

Gemini CLI has no plugin marketplace, so there are two native routes: a **custom command** (opt-in, off until you invoke it) or an **extension** (always-on once installed). The command route matches this skill's default posture; pick it unless you want the rules on every session.

### Install (command, opt-in)

```bash
mkdir -p ~/.gemini/commands
curl -fsSL https://raw.githubusercontent.com/hayfever/succinct/main/skills/succinct/agents/gemini.toml \
  -o ~/.gemini/commands/succinct.toml
```

Start a new session, type `/succinct`. It stays on for that session.

### Install (extension, always-on)

```bash
gemini extensions install https://github.com/hayfever/succinct
```

The extension loads `GEMINI.md`, which imports the full skill, so the rules apply from message one. `git` must be installed.

### Verify

```bash
gemini extensions list          # extension route
ls ~/.gemini/commands           # command route: succinct.toml present
```

Or type `/` in a session and confirm `succinct` is listed.

### Update

```bash
gemini extensions update succinct    # extension route
# command route: re-run the curl above
```

### Uninstall

```bash
gemini extensions uninstall succinct    # extension route
rm ~/.gemini/commands/succinct.toml     # command route
```

</details>

<details>
<summary><strong>GitHub Copilot (VS Code and Copilot CLI)</strong></summary>

Copilot reads Agent Skills natively: the same `SKILL.md`, no conversion. It scans `.github/skills/`, `.claude/skills/`, and `.agents/skills/` in the project, and `~/.copilot/skills/`, `~/.claude/skills/`, and `~/.agents/skills/` globally.

### Install

```bash
npx skills add hayfever/succinct -a github-copilot        # this project
npx skills add hayfever/succinct -a github-copilot -g     # all projects
```

Without the CLI, copy the skill folder into any directory Copilot scans:

```bash
git clone https://github.com/hayfever/succinct
mkdir -p ~/.copilot/skills
cp -R succinct/skills/succinct ~/.copilot/skills/
```

### Verify

Type `/` in the chat input and confirm `succinct` appears. Or:

```bash
npx skills list
npx skills ls -g    # if installed globally
```

### Update

```bash
npx skills update succinct
```

Or re-copy the folder after `git pull`.

### Uninstall

```bash
npx skills remove succinct
```

Or delete the `succinct` folder from the skills directory it landed in.

### Activation note

Copilot respects `disable-model-invocation`: nothing applies until you invoke the skill, same as Claude Code.

### Always-on (optional)

Add the [always-on snippet](#always-on-snippet) to `.github/copilot-instructions.md` in the project.

</details>

<details>
<summary><strong>Hermes</strong></summary>

### Install

```bash
hermes skills install hayfever/succinct/skills/succinct
```

Type `/succinct`. The skill installs into `~/.hermes/skills/` and is exposed as a slash command at the next session start.

Prefer to browse first? Add this repo as a skill source (a "tap"), then search and install:

```bash
hermes skills tap add hayfever/succinct
hermes skills search succinct
hermes skills install hayfever/succinct/skills/succinct
```

### Verify

```bash
hermes skills list
```

### Update

```bash
hermes skills update succinct
```

### Uninstall

```bash
hermes skills uninstall succinct
```

Or remove the tap too: `hermes skills tap remove hayfever/succinct`.

### Always-on (optional)

Add the [always-on snippet](#always-on-snippet) to the `AGENTS.md` in your working directory, or to your persona `SOUL.md` for every session.

</details>

<details>
<summary><strong>Kimi Code CLI</strong></summary>

### Install

Start a Kimi Code session, then:

1. Run `/plugins`.
2. Choose **Custom**.
3. Paste `https://github.com/hayfever/succinct` and press `Enter`.
4. Choose **Trust and install**.

Use slash command `/skill:succinct` to invoke the skill explicitly.

### Update

`/plugins` in a Kimi Code session, cursor to **Succinct**, press `R`.

### Uninstall

`/plugins` in a Kimi Code session, cursor to **Succinct**, press `D`.

</details>

<details>
<summary><strong>OpenCode</strong></summary>

OpenCode 2 loads this repository as a local plugin. The plugin in `.opencode/plugins/succinct/` registers the `/succinct` command and appends the ruleset to the system prompt when always-on is on. The `skills` entry adds the skill itself, so the `skill` tool can load it.

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

### Use

Start a new session and turn on succinct output:

```text
/succinct
```

The rules stay on until `stop succinct mode` or `normal mode`.

### Verify

Type `/` and confirm `succinct` appears in the command list. Ask the agent to list its skills and confirm `succinct` is there.

### Update

```bash
git -C ~/.config/opencode/vendor/succinct pull
opencode service restart
```

### Uninstall

Remove the `plugins` and `skills` entries from `opencode.json`.

### Always-on (optional)

```bash
touch ~/.config/opencode/.succinct-always
```

While the flag exists, the plugin appends the full ruleset to the system prompt of every model request. `stop succinct mode` or `normal mode` disables it for the current session; delete the flag to turn always-on off for good:

```bash
rm ~/.config/opencode/.succinct-always
```

</details>

<details>
<summary><strong>Pi</strong></summary>

Pi discovers this repository as a native package: `extensions/` provides the session-persistent mode and `skills/` keeps the Agent Skills entry point available.

### Install

```bash
pi install https://github.com/hayfever/succinct
```

Start a new Pi session. Toggle succinct output for the current session:

```text
/succinct
```

The footer shows `● SUCCINCT ON` while the mode is active. Run the command again to turn it off, or be explicit:

```text
/succinct on
/succinct off
stop succinct mode
```

The extension adds the ruleset to the conversation once instead of rewriting the system prompt on every request, and adds it again after compaction drops it. The existing Agent Skills command remains available as an alias:

```text
/skill:succinct
```

Start a new Pi session with the mode enabled by default:

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
```

### Always-on (optional)

Create a flag in Pi's agent configuration directory:

```bash
touch ~/.pi/agent/.succinct-always
```

The extension checks the flag at every new, resumed, forked, or reloaded session. A saved choice for the current session wins over this default, so `stop succinct mode` keeps that session disabled.

Back to on-demand:

```bash
rm ~/.pi/agent/.succinct-always
```

### Config file (optional)

Create `~/.pi/agent/succinct.json` in Pi's agent configuration directory:

```json
{
  "alwaysOn": true,
  "hideStatus": true
}
```

- `alwaysOn`: start every session with the rules active, same as the `.succinct-always` flag file, which still works
- `hideStatus`: keep the `● SUCCINCT ON` status-bar entry hidden; the rules and the `/succinct` command still work

Read once at extension startup, so restart Pi after changing it. If `PI_CODING_AGENT_DIR` is set, put `.succinct-always` in that directory instead. Run `/reload` or start a new session after changing the flag.

### Status line placement

Plain Pi renders extension statuses on their own footer line below the stats row, and truncates with an ellipsis on overflow. There is no powerline `status` segment in Pi, so the separate line is the runtime's design; the same-line option above is OMP-only.

<details>
<summary><strong>Oh My Pi (OMP)</strong></summary>

### Install

```bash
omp plugin marketplace add hayfever/succinct
omp plugin install --scope user succinct@succinct
```

Start a new OMP session and run `/succinct` to toggle the mode. The footer shows `● SUCCINCT ON` while the mode is active.

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
```

### Always-on (optional)

Create a flag in OMP's agent configuration directory:

```bash
touch ~/.omp/agent/.succinct-always
```

Or set `"alwaysOn": true` in `~/.omp/agent/succinct.json`. A saved choice for the current session wins over the default, so `stop succinct mode` keeps that session disabled. Run `/reload` or start a new session after changing the flag.

</details>

<details>
<summary><strong>Qwen Code</strong></summary>

### Install

```bash
qwen extensions install hayfever/succinct
```

Qwen Code supports the GitHub shorthand and installs the repository as a native extension. The extension discovers the skill under `skills/`.

Type `/succinct` to invoke the skill explicitly. Installing the extension does not change output until the skill is invoked.

### Verify

```bash
qwen extensions list
```

Then start a new Qwen Code session and run `/skills`. Confirm that `succinct` appears in the list.

### Update

```bash
qwen extensions update succinct
```

### Uninstall

```bash
qwen extensions uninstall succinct
```

</details>

<details>
<summary><strong>Zed</strong></summary>

Zed's Agent reads Agent Skills natively: the same `SKILL.md`, no conversion.

### Install

In the Agent Panel, open the Skills manager and choose **Create skill from URL** (also in the command palette as `agent: create skill from url`), then paste:

```
https://github.com/hayfever/succinct/blob/main/skills/succinct/SKILL.md
```

Save it in **User** scope for every project, or **Project** scope for one. Then type `/succinct` in the Agent Panel.

Prefer the filesystem? Clone the repo and drop the skill folder into your user skills directory:

```bash
git clone https://github.com/hayfever/succinct
cp -R succinct/skills/succinct ~/.config/zed/skills/
```

### Verify

Open the Skills manager in the Agent Panel and confirm `succinct` is listed. Or type `/` and confirm it appears.

### Update

Re-import from the same URL (overwrites), or re-copy the folder after `git pull`.

### Uninstall

Remove `succinct` from the Skills manager, or delete `~/.config/zed/skills/succinct`.

### Always-on (optional)

Add the [always-on snippet](#always-on-snippet) to your personal `~/.config/zed/AGENTS.md`.

</details>

<details>
<summary><strong>Cursor, Amp, and any other agent-skills harness</strong></summary>

Works with any harness that reads agent skills. Swap `-a <agent>` for yours.

### Install

```bash
npx skills add hayfever/succinct                  # this workspace
npx skills add hayfever/succinct -g               # all projects
npx skills add hayfever/succinct -a cursor -y     # one agent only
npx skills add hayfever/succinct -a opencode -y
```

New agent chat, type `/succinct`.

Without the CLI, copy the skill folder into whatever path your agent scans:

```bash
git clone https://github.com/hayfever/succinct
mkdir -p ~/.cursor/skills     # Cursor. Use .agents/skills for OpenCode, or your agent's own path
cp -R succinct/skills/succinct ~/.cursor/skills/
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

### Always-on (optional)

Paste the [always-on snippet](#always-on-snippet) into your agent's persistent rules file. Cursor: **Settings, Rules, User Rules**, or a project rule under `.cursor/rules/` with `alwaysApply: true`. OpenCode: `~/.config/opencode/AGENTS.md`.

</details>

## How activation works

1. **Installed, not invoked.** In Claude Code, Qwen Code, and Codex, nothing happens until you invoke the skill explicitly. Claude Code and Qwen Code honor `disable-model-invocation: true` in `SKILL.md`; Codex honors `policy.allow_implicit_invocation: false` in `skills/succinct/agents/openai.yaml`. Other harnesses may load every skill's description at startup and activate the skill themselves.
2. **You invoke it explicitly.** Type `/succinct` in Claude Code or Qwen Code, or `$succinct` in Codex. Rules stay on for that session. "stop succinct mode" or "normal mode" turns them off.
3. **You touch `~/.claude/.succinct-always`** (Claude Code, Codex) or `~/.config/opencode/.succinct-always` (OpenCode) or `~/.pi/agent/.succinct-always` (Pi, OMP). A hook or extension loads the full ruleset from message one, every session.
4. **You add the always-on snippet** (other harnesses). Keeps the core rules in your agent's persistent context.

In Claude Code, Qwen Code, and Codex, no middle ground: if you did not turn it on, it is off.

## Troubleshooting

**`/succinct` not in autocomplete.** Restart the agent. The plugin index is read at startup.

**Always-on flag has no effect.** Update the plugin (`claude plugin marketplace update succinct`) and restart. Hooks are read at startup, and the flag needs the plugin version that ships `hooks/hooks.json`.

**`claude plugin marketplace add` fails.** Use the `owner/repo` form. A local path must point at the repo root, not `.claude-plugin/`.

**Installed but replies still preamble.** Open a new session. If it still drifts, tighten the wording in `skills/succinct/SKILL.md`.

**Want different rules.** Fork, edit `skills/succinct/SKILL.md`, then swap your copy in (see [README](README.md#tune-it)). Restart, then re-invoke `/succinct`.

**Skill missing after `npx skills add`.** Start a new agent chat. Skills are indexed at session start. Confirm the folder landed where your agent scans (`~/.cursor/skills/` for Cursor, `.agents/skills/` for OpenCode) and that the frontmatter `name` matches the folder name.