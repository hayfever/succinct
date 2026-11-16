#!/usr/bin/env sh
# Prompt hook: saves the choice when the user types "/succinct on" or
# "/succinct off" ("$succinct on" or "$succinct off" in Codex). The saved
# choice lives in succinct.json and outranks the .succinct-always flag at the
# next session start (see always-on.sh). A bare /succinct and the stop phrases
# change only the current session, so this hook ignores them.
# Never blocks the prompt: any failure exits 0.
#
# Claude Code runs this from a UserPromptExpansion hook that matches only the
# succinct command (hooks/hooks.json). Codex has no per-command event, so it
# runs this from UserPromptSubmit with --codex (hooks/codex-hooks.json), and
# the script returns at once for every other prompt. Plain-text stdout is what
# both agents add to the context next to the prompt.

if [ "${1:-}" = "--codex" ]; then
  state_dir="${CODEX_HOME:-$HOME/.codex}"
  command_name='$succinct'
else
  state_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
  command_name='/succinct'
fi
state_path="$state_dir/succinct.json"

input=$(cat 2>/dev/null) || exit 0

# Pull the "prompt" string out of the hook's JSON input without jq. JSON
# escapes for whitespace (\n, \r, \t) count as spaces; any other escape means
# the prompt is not a bare on/off command.
choice=$(printf '%s' "$input" | tr '\r\n' '  ' | sed -E -n \
  's/.*"prompt"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)".*/\1/p' |
  sed -E 's/\\[nrt]/ /g' | tr '[:upper:]' '[:lower:]' | sed -E -n \
  's/^[[:space:]]*[/$]succinct(:succinct)?[[:space:]]+(on|off)[[:space:]]*$/\2/p')

case "$choice" in
  on) enabled=true ;;
  off) enabled=false ;;
  *) exit 0 ;;
esac

saved=0
if mkdir -p "$state_dir" 2>/dev/null; then
  tmp_path="$state_path.$$.tmp"
  if printf '{\n  "enabled": %s\n}\n' "$enabled" > "$tmp_path" 2>/dev/null &&
    mv -f "$tmp_path" "$state_path" 2>/dev/null; then
    saved=1
  else
    rm -f "$tmp_path" 2>/dev/null
  fi
fi

if [ "$saved" -ne 1 ]; then
  printf 'The user ran %s %s, but succinct could not save the choice to %s. Tell the user in one line that the choice applies to this session only.\n' \
    "$command_name" "$choice" "$state_path"
  exit 0
fi

if [ "$enabled" = true ]; then
  printf 'The user ran %s on. Succinct mode is on for this session, and the on choice is saved in %s for future sessions. Confirm in one line.\n' \
    "$command_name" "$state_path"
else
  printf 'The user ran %s off. Succinct mode is off for this session, and the off choice is saved in %s for future sessions. Stop applying the succinct ruleset, confirm in one line, and return to your default style.\n' \
    "$command_name" "$state_path"
fi
exit 0
