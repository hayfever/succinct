# SessionStart hook fallback for Windows PowerShell. Injects the succinct
# core ruleset when the user has opted in by creating
# $CLAUDE_CONFIG_DIR/.succinct-always (default ~/.claude). A choice saved with
# "/succinct on" or "/succinct off" (toggle.ps1) outranks the flag: it lives
# in succinct.json in the same directory, or in $CODEX_HOME (default
# ~/.codex) when Codex passes -Codex.
# Never blocks session start: any failure exits 0.
#
# hooks/hooks.json runs always-on.sh first. Claude Code passes the command line
# to PowerShell only when Git Bash is not installed, so this script skips when a
# POSIX shell is on PATH: always-on.sh already handled that session, and the
# ruleset must not be injected twice. Codex runs this script directly from
# hooks/codex-hooks.json, where no sh branch ran, so it passes -SkipShellCheck.

param(
  [switch]$SkipShellCheck,
  [switch]$Codex
)

try {
  if (-not $SkipShellCheck -and (Get-Command sh -CommandType Application -ErrorAction SilentlyContinue)) {
    exit 0
  }

  $claudeDir = if ($env:CLAUDE_CONFIG_DIR) {
    $env:CLAUDE_CONFIG_DIR
  } else {
    Join-Path ([Environment]::GetFolderPath("UserProfile")) ".claude"
  }
  $flagPath = Join-Path $claudeDir ".succinct-always"
  if ($Codex) {
    $codexDir = if ($env:CODEX_HOME) {
      $env:CODEX_HOME
    } else {
      Join-Path ([Environment]::GetFolderPath("UserProfile")) ".codex"
    }
    $statePath = Join-Path $codexDir "succinct.json"
    $offCommand = '$succinct off'
  } else {
    $statePath = Join-Path $claudeDir "succinct.json"
    $offCommand = '/succinct off'
  }

  # The saved choice wins. Without one, fire only when the user has opted in
  # with the flag.
  $saved = ""
  if (Test-Path -LiteralPath $statePath -PathType Leaf) {
    $compact = [System.IO.File]::ReadAllText($statePath) -replace '\s', ''
    if ($compact -match '"enabled":(true|false)') {
      $saved = $Matches[1]
    }
  }
  if ($saved -eq "false") {
    exit 0
  }
  if ($saved -ne "true" -and -not (Test-Path -LiteralPath $flagPath -PathType Leaf)) {
    exit 0
  }

  $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
  $skillPath = Join-Path $scriptDir "../skills/succinct/SKILL.md"
  if (-not (Test-Path -LiteralPath $skillPath -PathType Leaf)) {
    exit 0
  }

  $lines = [System.IO.File]::ReadAllLines($skillPath)
  $bodyStart = 0

  if ($lines.Length -gt 0 -and $lines[0] -match '^---\s*$') {
    # Only treat the block as frontmatter when the closing delimiter exists;
    # an unterminated fence is not frontmatter, so keep the whole file.
    for ($i = 1; $i -lt $lines.Length; $i++) {
      if ($lines[$i] -match '^---\s*$') {
        $bodyStart = $i + 1
        break
      }
    }
  }

  $body = if ($bodyStart -lt $lines.Length) {
    [string]::Join([Environment]::NewLine, $lines[$bodyStart..($lines.Length - 1)])
  } else {
    ""
  }

  $banner = 'SUCCINCT MODE ACTIVE (always-on). The ruleset below applies to every response. ' +
    '"stop succinct mode" turns it off for this session; "'
  $text = $banner + $offCommand + '" turns it off for future sessions.' + "`n`n" + $body + "`n"

  # Write UTF-8 bytes to the raw stdout stream so a redirected pipe keeps the
  # text intact instead of re-encoding it through the console code page.
  $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($text)
  $stdout = [System.Console]::OpenStandardOutput()
  $stdout.Write($bytes, 0, $bytes.Length)
  $stdout.Flush()
} catch {
  # Never block session start.
  exit 0
}
