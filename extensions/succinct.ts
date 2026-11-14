import {
  existsSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  getAgentDir,
  type ExtensionAPI,
  type ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import {
  contextMessages,
  latestMarkerIsActive,
} from "./context-compat";

const EXTENSION_DIR = dirname(fileURLToPath(import.meta.url));
const SKILL_PATH = join(
  EXTENSION_DIR,
  "..",
  "skills",
  "succinct",
  "SKILL.md",
);
const CONFIG_FILE = "succinct.json";
const STATE_ENTRY_TYPE = "succinct-state";
const RULES_MESSAGE_TYPE = "succinct-rules";
const DISABLED_MESSAGE_TYPE = "succinct-disabled";
const STATUS_KEY = "succinct";
const DISABLE_CONFIRMATION = "Succinct mode disabled.";
const STOP_PHRASES: Record<string, true> = {
  "stop succinct mode": true,
  "normal mode": true,
};
const RULES_HEADER =
  'SUCCINCT MODE ACTIVE. The ruleset below applies to every response until turned off. "stop succinct mode" and "normal mode" turn it off for this session only. Run /succinct on or /succinct off to save the choice for future sessions.';
const DISABLED_NOTICE =
  "SUCCINCT MODE OFF. Ignore the succinct ruleset injected earlier in this conversation and return to your default response style.";

type SuccinctModeState = {
  enabled: boolean;
};

type SuccinctConfig = {
  alwaysOn?: boolean;
  hideStatus?: boolean;
  /**
   * Saved toggle state. Only an explicit /succinct on or /succinct off writes
   * it, so it carries to future sessions and outranks the legacy always-on
   * defaults. Session-only toggles never touch it.
   */
  enabled?: boolean;
};

type ConfigLoad =
  | { ok: true; config: SuccinctConfig }
  | { ok: false; config: SuccinctConfig; error: string };

type PersistResult = { saved: boolean; error?: string };

function configPath(): string {
  return join(getAgentDir(), CONFIG_FILE);
}

function reason(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Read the preference file. A missing file is not an error; an unreadable or
 * invalid file returns an error so the caller can warn instead of silently
 * dropping the other settings.
 */
function loadConfig(): ConfigLoad {
  const path = configPath();

  if (!existsSync(path)) {
    return { ok: true, config: {} };
  }

  let raw: string;
  try {
    raw = readFileSync(path, "utf8");
  } catch (error) {
    return {
      ok: false,
      config: {},
      error: `Cannot read ${path} (${reason(error)})`,
    };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    return {
      ok: false,
      config: {},
      error: `Cannot parse ${path} as JSON (${reason(error)})`,
    };
  }

  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    return {
      ok: false,
      config: {},
      error: `${path} must contain a JSON object`,
    };
  }

  return { ok: true, config: parsed as SuccinctConfig };
}

/**
 * Replace the preference file in one step: write a temporary file next to it
 * and rename it. A concurrent session sees either the old file or the new
 * one, never a partial write.
 */
function writeConfig(config: SuccinctConfig): void {
  const path = configPath();
  const tempPath = `${path}.${process.pid}.${Math.random().toString(36).slice(2)}.tmp`;

  writeFileSync(tempPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");

  try {
    renameSync(tempPath, path);
  } catch (error) {
    try {
      unlinkSync(tempPath);
    } catch {
      // Keep the original error: the rename failure is the useful one.
    }
    throw error;
  }
}

/**
 * Save the toggle choice. A file that cannot be read is never overwritten:
 * the user keeps their settings, and the toggle stays session-only.
 */
function persistEnabled(nextEnabled: boolean): PersistResult {
  const loaded = loadConfig();

  if (!loaded.ok) {
    return { saved: false, error: loaded.error };
  }

  try {
    writeConfig({ ...loaded.config, enabled: nextEnabled });
    return { saved: true };
  } catch (error) {
    return {
      saved: false,
      error: `Cannot write ${configPath()} (${reason(error)})`,
    };
  }
}

function stripFrontmatter(content: string): string {
  return content
    .replace(
      /^---[^\S\r\n]*\r?\n[\s\S]*?\r?\n---[^\S\r\n]*(?:\r?\n|$)/,
      "",
    )
    .trim();
}

function loadRules(): string {
  let content: string;

  try {
    content = readFileSync(SKILL_PATH, "utf8");
  } catch (error) {
    throw new Error(
      `Unable to load succinct rules from ${SKILL_PATH}: ${reason(error)}`,
    );
  }

  const rules = stripFrontmatter(content);
  if (!rules) {
    throw new Error(`The succinct rules file is empty: ${SKILL_PATH}`);
  }

  return rules;
}

function getSavedState(ctx: ExtensionContext): boolean | undefined {
  let savedState: boolean | undefined;

  for (const entry of ctx.sessionManager.getBranch()) {
    if (entry.type !== "custom" || entry.customType !== STATE_ENTRY_TYPE) {
      continue;
    }

    const data = entry.data as Partial<SuccinctModeState> | undefined;
    if (typeof data?.enabled === "boolean") {
      savedState = data.enabled;
    }
  }

  return savedState;
}

/**
 * Whether the rules are still live in the context the model actually receives.
 *
 * Only the newest marker counts: a later "disabled" notice cancels an earlier
 * ruleset, and compaction drops summarized entries so the ruleset has to be
 * injected again.
 */
function rulesAreInContext(ctx: ExtensionContext): boolean {
  return latestMarkerIsActive(
    contextMessages(ctx.sessionManager),
    RULES_MESSAGE_TYPE,
    DISABLED_MESSAGE_TYPE,
  );
}

export default function succinctExtension(pi: ExtensionAPI) {
  const rules = loadRules();
  const alwaysOnFlag = join(getAgentDir(), ".succinct-always");
  let enabled = false;
  let hideStatus = false;
  let configWarningShown = false;

  /** Read the config, warning once per session when the file is unusable. */
  const readConfig = (ctx: ExtensionContext): ConfigLoad => {
    const loaded = loadConfig();

    if (!loaded.ok && !configWarningShown) {
      configWarningShown = true;
      ctx.ui.notify(
        `${loaded.error}. Succinct uses defaults and leaves the file untouched.`,
        "warning",
      );
    }

    return loaded;
  };

  const updateStatus = (ctx: ExtensionContext): void => {
    if (!enabled || hideStatus) {
      ctx.ui.setStatus(STATUS_KEY, undefined);
      return;
    }

    const dot = ctx.ui.theme.fg("success", "●");
    const label = ctx.ui.theme.fg("accent", "SUCCINCT ON");
    ctx.ui.setStatus(STATUS_KEY, `${dot} ${label}`);
  };

  /**
   * Keep the conversation in sync with the current mode: inject the ruleset
   * once, never per request.
   */
  const syncContext = (ctx: ExtensionContext): void => {
    const injected = rulesAreInContext(ctx);

    if (enabled && !injected) {
      pi.sendMessage(
        {
          customType: RULES_MESSAGE_TYPE,
          content: `${RULES_HEADER}\n\n${rules}`,
          display: false,
        },
        { triggerTurn: false },
      );
      return;
    }

    if (!enabled && injected) {
      pi.sendMessage(
        {
          customType: DISABLED_MESSAGE_TYPE,
          content: DISABLED_NOTICE,
          display: false,
        },
        { triggerTurn: false },
      );
    }
  };

  const restoreState = (ctx: ExtensionContext): void => {
    const savedState = getSavedState(ctx);
    const cliFlag = pi.getFlag("succinct") === true;
    const { config } = readConfig(ctx);
    const persisted = config.enabled;
    const enabledByDefault = config.alwaysOn === true || existsSync(alwaysOnFlag);

    hideStatus = config.hideStatus === true;

    // A session's own history wins, then the persisted toggle, then the
    // launch-time defaults. --succinct keeps force-on semantics for that run.
    const defaultForSession = cliFlag
      ? true
      : typeof persisted === "boolean"
        ? persisted
        : enabledByDefault;
    enabled = savedState ?? defaultForSession;
    updateStatus(ctx);
    syncContext(ctx);
  };

  /**
   * Change the mode. Only an explicit /succinct on or /succinct off saves the
   * choice for future sessions; every other toggle lasts for this session.
   */
  const setEnabled = (
    nextEnabled: boolean,
    ctx: ExtensionContext,
    persist: boolean,
  ): void => {
    enabled = nextEnabled;
    pi.appendEntry(STATE_ENTRY_TYPE, { enabled } satisfies SuccinctModeState);

    let saved = false;
    if (persist) {
      const result = persistEnabled(nextEnabled);
      saved = result.saved;

      if (!result.saved) {
        ctx.ui.notify(
          `${result.error}. The choice applies to this session only.`,
          "warning",
        );
      }
    }

    updateStatus(ctx);
    syncContext(ctx);
    ctx.ui.notify(
      `Succinct mode ${enabled ? "enabled" : "disabled"} (${
        saved ? "saved for future sessions" : "this session only"
      })`,
      "info",
    );
  };

  pi.registerFlag("succinct", {
    description: "Start with succinct output enabled",
    type: "boolean",
    default: false,
  });

  pi.registerCommand("succinct", {
    description: "Toggle for this session; 'on' or 'off' saves the choice",
    handler: async (args, ctx) => {
      const argument = args.trim().toLowerCase();

      if (argument === "") {
        setEnabled(!enabled, ctx, false);
        return;
      }

      if (argument === "on") {
        setEnabled(true, ctx, true);
        return;
      }

      if (argument === "off") {
        setEnabled(false, ctx, true);
        return;
      }

      if (argument === "stop") {
        setEnabled(false, ctx, false);
        return;
      }

      ctx.ui.notify("Usage: /succinct [on|off]", "warning");
    },
  });

  pi.on("input", async (event, ctx) => {
    const input = event.text.trim().toLowerCase();

    // Keep the built-in skill command working as an alias without letting the
    // runtime expand a second copy of the same rules into the conversation.
    if (input === "/skill:succinct") {
      setEnabled(true, ctx, false);
      return { action: "handled" };
    }

    if (enabled && STOP_PHRASES[input]) {
      setEnabled(false, ctx, false);

      if (ctx.hasUI) {
        return { action: "handled" };
      }

      return {
        action: "transform",
        text: `Reply with exactly: ${DISABLE_CONFIRMATION}`,
      };
    }

    return { action: "continue" };
  });

  pi.on("session_start", async (_event, ctx) => restoreState(ctx));
  pi.on("session_tree", async (_event, ctx) => restoreState(ctx));
  pi.on("session_compact", async (_event, ctx) => syncContext(ctx));
}
