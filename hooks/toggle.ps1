# Prompt hook fallback for Windows PowerShell. Saves the choice when the user
# types "/succinct on" or "/succinct off" ("$succinct on" or "$succinct off"
# in Codex). The saved choice lives in succinct.json and outranks the
# .succinct-always flag at the next session start (see always-on.ps1). A bare
# /succinct and the stop phrases change only the current session, so this
# hook ignores them. Never blocks the prompt: any failure exits 0.
#
# hooks/hooks.json runs toggle.sh first. Claude Code passes the command line
# to PowerShell only when Git Bash is not installed, so this script skips when
# a POSIX shell is on PATH: toggle.sh already handled the prompt. Codex runs
# this script directly from hooks/codex-hooks.json with -SkipShellCheck and
# -Codex, which also moves the saved choice to CODEX_HOME.

param(
  [switch]$SkipShellCheck,
  [switch]$Codex
)

function Write-Utf8([string]$Text) {
  # Write UTF-8 bytes to the raw stdout stream so a redirected pipe keeps the
  # text intact instead of re-encoding it through the console code page.
  $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
  $stdout = [System.Console]::OpenStandardOutput()
  $stdout.Write($bytes, 0, $bytes.Length)
  $stdout.Flush()
}

try {
  if (-not $SkipShellCheck -and (Get-Command sh -CommandType Application -ErrorAction SilentlyContinue)) {
    exit 0
  }

  $userProfile = [Environment]::GetFolderPath("UserProfile")
  if ($Codex) {
    $stateDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $userProfile ".codex" }
    $commandName = '$succinct'
  } else {
    $stateDir = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $userProfile ".claude" }
    $commandName = '/succinct'
  }
  $statePath = Join-Path $stateDir "succinct.json"

  $prompt = ([Console]::In.ReadToEnd() | ConvertFrom-Json).prompt
  if (-not ($prompt -is [string])) {
    exit 0
  }
  if ($prompt -notmatch '(?i)^\s*[/$]succinct(:succinct)?\s+(on|off)\s*$') {
    exit 0
  }
  $choice = $Matches[2].ToLowerInvariant()
  $enabled = if ($choice -eq "on") { "true" } else { "false" }

  $saved = $false
  try {
    [void][System.IO.Directory]::CreateDirectory($stateDir)
    $tmpPath = "$statePath.$PID.tmp"
    [System.IO.File]::WriteAllText($tmpPath, "{`n  `"enabled`": $enabled`n}`n", [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $tmpPath -Destination $statePath -Force
    $saved = $true
  } catch {
    if ($tmpPath) { Remove-Item -LiteralPath $tmpPath -Force -ErrorAction SilentlyContinue }
  }

  if (-not $saved) {
    Write-Utf8 ("The user ran $commandName $choice, but succinct could not save the choice to $statePath. " +
      "Tell the user in one line that the choice applies to this session only.`n")
  } elseif ($enabled -eq "true") {
    Write-Utf8 ("The user ran $commandName on. Succinct mode is on for this session, and the on choice is saved in " +
      "$statePath for future sessions. Confirm in one line.`n")
  } else {
    Write-Utf8 ("The user ran $commandName off. Succinct mode is off for this session, and the off choice is saved in " +
      "$statePath for future sessions. Stop applying the succinct ruleset, confirm in one line, and return to your default style.`n")
  }
} catch {
  # Never block the prompt.
  exit 0
}
