import { existsSync, readFileSync, writeFileSync } from "node:fs";
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
  'SUCCINCT MODE ACTIVE. The ruleset below applies to every response until turned off. "stop succinct mode" or "normal mode" turns it off for this session and future sessions. Run /succinct to switch it back on.';
const DISABLED_NOTICE =
  "SUCCINCT MODE OFF. Ignore the succinct ruleset injected earlier in this conversation and return to your default response style.";

type SuccinctModeState = {
  enabled: boolean;
};

type SuccinctConfig = {
  alwaysOn?: boolean;
  hideStatus?: boolean;
  /**
   * Persisted toggle state. /succinct and the stop phrases write it so the
   * choice carries to future sessions; it outranks the legacy always-on
   * defaults but not a session's own saved state.
   */
  enabled?: boolean;
};

function loadConfig(): SuccinctConfig {
  try {
    return JSON.parse(readFileSync(join(getAgentDir(), "succinct.json"), "utf8"));
  } catch {
    return {};
  }
}

/**
 * Write the toggle choice so future sessions start in the same mode.
 * Returns false when the preference file cannot be written.
 */
function persistState(nextEnabled: boolean): boolean {
  const merged: SuccinctConfig = { ...loadConfig(), enabled: nextEnabled };
  try {
    writeFileSync(
      join(getAgentDir(), "succinct.json"),
      `${JSON.stringify(merged, null, 2)}\n`,
      "utf8",
    );
    return true;
  } catch {
    return false;
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
    const reason = error instanceof Error ? error.message : String(error);
    throw new Error(
      `Unable to load succinct rules from ${SKILL_PATH}: ${reason}`,
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
  const config = loadConfig();
  let enabled = false;

  const updateStatus = (ctx: ExtensionContext): void => {
    if (!enabled || config.hideStatus) {
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
    const persisted = loadConfig().enabled;
    const enabledByDefault = config.alwaysOn === true || existsSync(alwaysOnFlag);

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

  const setEnabled = (nextEnabled: boolean, ctx: ExtensionContext): void => {
    enabled = nextEnabled;
    pi.appendEntry(STATE_ENTRY_TYPE, { enabled } satisfies SuccinctModeState);

    if (!persistState(nextEnabled)) {
      ctx.ui.notify(
        "Could not save the succinct preference; this toggle is session-only.",
        "warning",
      );
    }

    updateStatus(ctx);
    syncContext(ctx);
    ctx.ui.notify(
      `Succinct mode ${enabled ? "enabled" : "disabled"} (saved for future sessions)`,
      "info",
    );
  };

  pi.registerFlag("succinct", {
    description: "Start with succinct output enabled",
    type: "boolean",
    default: false,
  });

  pi.registerCommand("succinct", {
    description: "Toggle succinct output (persists across sessions)",
    handler: async (args, ctx) => {
      const argument = args.trim().toLowerCase();

      if (argument === "") {
        setEnabled(!enabled, ctx);
        return;
      }

      if (argument === "on") {
        setEnabled(true, ctx);
        return;
      }

      if (argument === "off" || argument === "stop") {
        setEnabled(false, ctx);
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
      setEnabled(true, ctx);
      return { action: "handled" };
    }

    if (enabled && STOP_PHRASES[input]) {
      setEnabled(false, ctx);

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