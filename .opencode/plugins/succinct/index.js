// succinct — OpenCode plugin, V2 plugin API.
//
// The skill in `skills/succinct/SKILL.md` is the single source of truth for the
// ruleset. The plugin adds the parts OpenCode cannot derive from a checkout:
//
//   • the `/succinct` command, so the ruleset applies for the rest of the
//     session from any project that loads this plugin;
//   • always-on, which appends the ruleset to the system prompt of every model
//     request while the opt-in flag file exists (the OpenCode equivalent of the
//     SessionStart hook in hooks/always-on.sh).
//
// The skill itself is registered through the `skills` array in `opencode.json`.
// The stop phrases ("stop succinct mode", "normal mode") are part of the
// ruleset, so both delivery paths honour them.
//
// Opt in to always-on:   touch ~/.config/opencode/.succinct-always
// Opt back out:          rm ~/.config/opencode/.succinct-always

import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const skillFile = join(repoRoot, "skills", "succinct", "SKILL.md");
const commandFile = join(repoRoot, ".opencode", "command", "succinct.md");

// Always-on opt-in flag, under OpenCode's config directory so the other
// harnesses stay independent.
const flagFile = join(
  process.env.XDG_CONFIG_HOME || join(homedir(), ".config"),
  "opencode",
  ".succinct-always",
);

const FRONTMATTER = /^---[^\S\r\n]*\r?\n([\s\S]*?)\r?\n---[^\S\r\n]*(?:\r?\n|$)/;

// Body of a Markdown file, without its leading YAML frontmatter. The
// frontmatter pattern mirrors the stripping in hooks/always-on.sh, so every
// harness drops the same block.
function body(text) {
  return text.replace(FRONTMATTER, "").trim();
}

function describe(text) {
  const frontmatter = FRONTMATTER.exec(text);
  const line = frontmatter && /^description:[^\S\r\n]*(.+)$/m.exec(frontmatter[1]);
  return line ? line[1].trim() : undefined;
}

function read(file) {
  try {
    return readFileSync(file, "utf8");
  } catch {
    return undefined;
  }
}

function rulesetBody() {
  const text = read(skillFile);
  return text === undefined ? undefined : body(text);
}

export default {
  id: "succinct",

  async setup(ctx) {
    const command = read(commandFile);

    if (command !== undefined) {
      const template = body(command);
      const description = describe(command);

      await ctx.command.transform((editor) => {
        editor.add({
          name: "succinct",
          ...(description === undefined ? {} : { description }),
          async execute({ sessionID, prompt, delivery }) {
            await ctx.session.prompt({
              ...prompt,
              sessionID,
              text: template,
              delivery,
            });
          },
        });
      });
    }

    // Always-on: append the ruleset to the system prompt of every model
    // request while the flag file exists. "stop succinct mode" turns it off
    // for the session (the ruleset's own Persistence rules); deleting the flag
    // turns always-on off for good.
    await ctx.session.hook("context", (event) => {
      if (!existsSync(flagFile)) return;

      const ruleset = rulesetBody();
      if (ruleset === undefined) return;

      const header =
        "SUCCINCT MODE ACTIVE (always-on). The ruleset below applies to every " +
        'response. "stop succinct mode" or "normal mode" turns it off for this ' +
        "session; delete " + flagFile + " to turn always-on off for good.";

      event.system.push({ type: "text", text: header + "\n\n" + ruleset });
    });
  },
};
