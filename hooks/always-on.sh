#!/usr/bin/env sh
# SessionStart hook: injects the succinct core ruleset when the flag file
# $CLAUDE_CONFIG_DIR/.succinct-always (default ~/.claude) exists. Codex passes
# --codex, which reads $CODEX_HOME/.succinct-always (default ~/.codex)
# instead. "/succinct on" creates the flag and "/succinct off" deletes it
# (toggle.sh). Never blocks session start: any failure exits 0.
#
# hooks/hooks.json runs this script first with sh, which is on every macOS and
# Linux system and in Git Bash on Windows. On Windows without Git Bash the
# shell is PowerShell, so the same command line runs always-on.ps1 next. That
# script exits early when sh is available, so only one of the two injects the
# ruleset. Plain-text stdout is what both Claude Code and Codex add to the
# context as developer instructions.
#
# The hook commands check that always-on.ps1 exists before they run it:
# Windows PowerShell prints its copyright banner when -File names a missing
# script, and a broken plugin install must still leave stdout empty.

if [ "${1:-}" = "--codex" ]; then
  flag_path="${CODEX_HOME:-$HOME/.codex}/.succinct-always"
  off_command='$succinct off'
else
  flag_path="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.succinct-always"
  off_command='/succinct off'
fi

# Only fire when the flag exists.
[ -f "$flag_path" ] || exit 0

# $0 is the path substituted into hooks.json by the harness, so resolve
# SKILL.md relative to it instead of trusting an exported environment variable.
script_dir=$(dirname -- "$0")
skill_path="$script_dir/../skills/succinct/SKILL.md"
[ -f "$skill_path" ] || exit 0

# Strip a leading YAML frontmatter block (--- ... --- at the very top of file).
# An unterminated fence is not frontmatter, so the whole file is kept unless the
# closing delimiter exists (two passes; matches the PowerShell hook).
body=$(awk '
  NR == FNR {
    if (NR == 1 && $0 ~ /^---[[:space:]]*$/) { in_fm = 1; next }
    if (in_fm && $0 ~ /^---[[:space:]]*$/)   { in_fm = 0; closed = 1 }
    next
  }
  FNR == 1 { strip = closed }
  strip && FNR == 1 && $0 ~ /^---[[:space:]]*$/ { skipping = 1; next }
  skipping && $0 ~ /^---[[:space:]]*$/          { skipping = 0; next }
  !skipping { print }
' "$skill_path" "$skill_path") || exit 0

printf 'SUCCINCT MODE ACTIVE (always-on). The ruleset below applies to every response. "stop succinct mode" turns it off for this session; "%s" turns it off for future sessions.\n\n%s\n' \
  "$off_command" "$body"
