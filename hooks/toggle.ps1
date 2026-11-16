# Prompt hook fallback for Windows PowerShell. "/succinct on" creates the
# .succinct-always flag file and "/succinct off" deletes it ("$succinct on"
# and "$succinct off" in Codex). The flag is the whole saved state:
# always-on.ps1 reads it at every session start. A bare /succinct and the stop
# phrases change only the current session, so this hook ignores them. Never
# blocks the prompt: any failure exits 0.
#
# hooks/hooks.json runs toggle.sh first. Claude Code passes the command line
# to PowerShell only when Git Bash is not installed, so this script skips when
# a POSIX shell is on PATH: toggle.sh already handled the prompt. Codex runs
# this script directly from hooks/codex-hooks.json with -SkipShellCheck and
# -Codex, which moves the flag to CODEX_HOME.

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
    $flagDir = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $userProfile ".codex" }
    $commandName = '$succinct'
  } else {
    $flagDir = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $userProfile ".claude" }
    $commandName = '/succinct'
  }
  $flagPath = Join-Path $flagDir ".succinct-always"

  $prompt = ([Console]::In.ReadToEnd() | ConvertFrom-Json).prompt
  if (-not ($prompt -is [string])) {
    exit 0
  }
  if ($prompt -notmatch '(?i)^\s*[/$]succinct(:succinct)?\s+(on|off)\s*$') {
    exit 0
  }
  $choice = $Matches[2].ToLowerInvariant()
  $action = if ($choice -eq "on") { "create" } else { "delete" }

  $saved = $false
  try {
    if ($choice -eq "on") {
      [void][System.IO.Directory]::CreateDirectory($flagDir)
      [System.IO.File]::WriteAllText($flagPath, "")
    } elseif (Test-Path -LiteralPath $flagPath) {
      Remove-Item -LiteralPath $flagPath -Force -ErrorAction Stop
    }
    $saved = $true
  } catch {
    $saved = $false
  }

  if (-not $saved) {
    Write-Utf8 ("The user ran $commandName $choice, but succinct could not $action $flagPath. " +
      "Tell the user in one line that the choice applies to this session only.`n")
  } elseif ($choice -eq "on") {
    Write-Utf8 ("The user ran $commandName on. Succinct mode is on for this session, and future sessions start on " +
      "while $flagPath exists. Confirm in one line.`n")
  } else {
    Write-Utf8 ("The user ran $commandName off. Succinct mode is off for this session and future sessions, and " +
      "$flagPath is deleted. Stop applying the succinct ruleset, confirm in one line, and return to your default style.`n")
  }
} catch {
  # Never block the prompt.
  exit 0
}
