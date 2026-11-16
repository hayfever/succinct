#!/usr/bin/env sh
# Prompt hook: "/succinct on" creates the .succinct-always flag file and
# "/succinct off" deletes it ("$succinct on" and "$succinct off" in Codex).
# The flag is the whole saved state: always-on.sh reads it at every session
# start. A bare /succinct and the stop phrases change only the current
# session, so this hook ignores them. Never blocks the prompt: any failure
# exits 0.
#
# Claude Code runs this from a UserPromptExpansion hook that matches only the
# succinct command (hooks/hooks.json), with the flag in $CLAUDE_CONFIG_DIR
# (default ~/.claude). Codex has no per-command event, so it runs this from
# UserPromptSubmit with --codex (hooks/codex-hooks.json), with the flag in
# $CODEX_HOME (default ~/.codex), and the script returns at once for every
# other prompt. Plain-text stdout is what both agents add to the context next
# to the prompt.

if [ "${1:-}" = "--codex" ]; then
  flag_dir="${CODEX_HOME:-$HOME/.codex}"
  command_name='$succinct'
else
  flag_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  command_name='/succinct'
fi
flag_path="$flag_dir/.succinct-always"

input=$(cat 2>/dev/null) || exit 0

# Pull the "prompt" string out of the hook's JSON input without jq. JSON
# escapes for whitespace (\n, \r, \t) count as spaces; any other escape means
# the prompt is not a bare on/off command.
choice=$(printf '%s' "$input" | tr '\r\n' '  ' | sed -E -n \
  's/.*"prompt"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)".*/\1/p' |
  sed -E 's/\\[nrt]/ /g' | tr '[:upper:]' '[:lower:]' | sed -E -n \
  's/^[[:space:]]*[/$]succinct(:succinct)?[[:space:]]+(on|off)[[:space:]]*$/\2/p')

case "$choice" in
  on)
    mkdir -p "$flag_dir" 2>/dev/null && : > "$flag_path" 2>/dev/null
    saved=$?
    action=create
    ;;
  off)
    rm -f "$flag_path" 2>/dev/null && [ ! -e "$flag_path" ]
    saved=$?
    action=delete
    ;;
  *) exit 0 ;;
esac

if [ "$saved" -ne 0 ]; then
  printf 'The user ran %s %s, but succinct could not %s %s. Tell the user in one line that the choice applies to this session only.\n' \
    "$command_name" "$choice" "$action" "$flag_path"
  exit 0
fi

if [ "$choice" = on ]; then
  printf 'The user ran %s on. Succinct mode is on for this session, and future sessions start on while %s exists. Confirm in one line.\n' \
    "$command_name" "$flag_path"
else
  printf 'The user ran %s off. Succinct mode is off for this session and future sessions, and %s is deleted. Stop applying the succinct ruleset, confirm in one line, and return to your default style.\n' \
    "$command_name" "$flag_path"
fi
exit 0
