// succinct — OpenCode plugin, V2 plugin API.
//
// The skill in `skills/succinct/SKILL.md` is the single source of truth for the
// ruleset. The plugin adds the parts OpenCode cannot derive from a checkout:
//
//   • the `/succinct` command, so the ruleset applies for the rest of the
//     session from any project that loads this plugin. `/succinct on` creates
//     the flag file below and `/succinct off` deletes it;
//   • always-on, which appends the ruleset to the system prompt of every model
//     request while the flag file exists (the OpenCode equivalent of the
//     SessionStart hook in hooks/always-on.sh).
//
// The skill itself is registered through the `skills` array in `opencode.json`.
// The stop phrases ("stop succinct mode", "normal mode") are part of the
// ruleset, so both delivery paths honour them.
//
// Turn on for future sessions:   /succinct on   (creates ~/.config/opencode/.succinct-always)
// Turn off for future sessions:  /succinct off  (deletes it)

import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const skillFile = join(repoRoot, "skills", "succinct", "SKILL.md");
const commandFile = join(repoRoot, ".opencode", "command", "succinct.md");

// The flag file is the whole saved state, under OpenCode's config directory so
// the other harnesses stay independent.
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

// Create or delete the flag file. Returns an error message on failure.
function saveFlag(on) {
  try {
    if (on) {
      mkdirSync(dirname(flagFile), { recursive: true });
      writeFileSync(flagFile, "", "utf8");
    } else {
      rmSync(flagFile, { force: true });
    }
    return undefined;
  } catch (error) {
    return error instanceof Error ? error.message : String(error);
  }
}

// What the model reads after /succinct on or /succinct off.
function savedText(on, error) {
  const name = on ? "on" : "off";
  if (error !== undefined) {
    return (
      `The user ran /succinct ${name}, but succinct could not ` +
      `${on ? "create" : "delete"} ${flagFile} (${error}). ` +
      "Tell the user in one line that the choice applies to this session only."
    );
  }
  if (on) {
    return (
      "The user ran /succinct on. Succinct mode is on for this session, and " +
      `future sessions start on while ${flagFile} exists. Confirm in one line.`
    );
  }
  return (
    "The user ran /succinct off. Succinct mode is off for this session and " +
    `future sessions, and ${flagFile} is deleted. Stop applying the succinct ` +
    "ruleset, confirm in one line, and return to your default style."
  );
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
            const argument = (prompt?.text ?? "").trim().toLowerCase();
            let text = template;
            if (argument === "on" || argument === "off") {
              const on = argument === "on";
              text = savedText(on, saveFlag(on));
            }
            await ctx.session.prompt({
              ...prompt,
              sessionID,
              text,
              delivery,
            });
          },
        });
      });
    }

    // Always-on: append the ruleset to the system prompt of every model
    // request while the flag file exists. "stop succinct mode" turns it off
    // for the session (the ruleset's own Persistence rules); /succinct off
    // deletes the flag for future sessions.
    await ctx.session.hook("context", (event) => {
      if (!existsSync(flagFile)) return;

      const ruleset = rulesetBody();
      if (ruleset === undefined) return;

      const header =
        "SUCCINCT MODE ACTIVE (always-on). The ruleset below applies to every " +
        'response. "stop succinct mode" or "normal mode" turns it off for this ' +
        'session; "/succinct off" turns it off for future sessions.';

      event.system.push({ type: "text", text: header + "\n\n" + ruleset });
    });
  },
};
