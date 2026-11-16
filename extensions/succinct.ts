import {
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
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
const FLAG_FILE = ".succinct-always";
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
  'SUCCINCT MODE ACTIVE. The ruleset below applies to every response until turned off. "stop succinct mode" and "normal mode" turn it off for this session only. /succinct off turns it off for future sessions.';
const DISABLED_NOTICE =
  "SUCCINCT MODE OFF. Ignore the succinct ruleset injected earlier in this conversation and return to your default response style.";

type SuccinctModeState = {
  enabled: boolean;
};

/**
 * The flag file is the whole saved state: it exists while the mode is on for
 * future sessions. /succinct on creates it and /succinct off deletes it.
 */
function flagPath(): string {
  return join(getAgentDir(), FLAG_FILE);
}

function reason(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Create or delete the flag file. Returns an error message on failure. */
function saveFlag(on: boolean): string | undefined {
  const path = flagPath();

  try {
    if (on) {
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, "", "utf8");
    } else {
      rmSync(path, { force: true });
    }
    return undefined;
  } catch (error) {
    return `Cannot ${on ? "create" : "delete"} ${path} (${reason(error)})`;
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

function getSessionState(ctx: ExtensionContext): boolean | undefined {
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
  let enabled = false;

  const updateStatus = (ctx: ExtensionContext): void => {
    if (!enabled) {
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
    // A session's own history wins, so a reload or resume keeps its state.
    // A new session starts from the flag file; --succinct forces it on for
    // that run.
    const startOn = pi.getFlag("succinct") === true || existsSync(flagPath());
    enabled = getSessionState(ctx) ?? startOn;
    updateStatus(ctx);
    syncContext(ctx);
  };

  /**
   * Change the mode. With save set, also create or delete the flag file so
   * future sessions start the same way.
   */
  const setEnabled = (
    nextEnabled: boolean,
    ctx: ExtensionContext,
    save: boolean,
  ): void => {
    enabled = nextEnabled;
    pi.appendEntry(STATE_ENTRY_TYPE, { enabled } satisfies SuccinctModeState);

    let saved = false;
    if (save) {
      const error = saveFlag(nextEnabled);
      saved = error === undefined;

      if (error !== undefined) {
        ctx.ui.notify(`${error}. The choice applies to this session only.`, "warning");
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
    description: "Turn on for this session; 'on' or 'off' also sets future sessions",
    handler: async (args, ctx) => {
      const argument = args.trim().toLowerCase();

      if (argument === "") {
        setEnabled(true, ctx, false);
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
