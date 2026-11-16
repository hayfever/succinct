// Test driver for the OpenCode plugin (V2 plugin API).
//
// Imports the plugin at argv[2], calls its `setup` with a context that exposes
// only the V2 domains the plugin may use, then prints one JSON report:
//
//   { "id", "commands": [{ "name", "description" }], "system": [text…],
//     "prompts": [prompt input…] }
//
// `system` holds the system parts after the `context` hook runs, so tests can
// assert on the always-on injection. `prompts` holds what the `/succinct`
// command submitted.
//
// Anything outside the V2 surface throws, so a V1 hook or a stray API call
// fails the test instead of passing silently.
import { pathToFileURL } from "node:url";

const pluginPath = process.argv[2];
// Optional argument text for the `/succinct` command, such as "on" or "off".
const commandArgs = process.argv[3] ?? "";
const { default: plugin } = await import(pathToFileURL(pluginPath).href);

const commands = [];
const hooks = {};
const prompts = [];

const registration = { dispose: async () => {} };

function only(name, allowed) {
  if (!allowed.includes(name)) {
    throw new Error(`unexpected ${name}: ${allowed.join(", ")}`);
  }
}

const ctx = {
  command: {
    async transform(callback) {
      callback({ add: (definition) => commands.push(definition) });
      return registration;
    },
  },
  session: {
    async hook(name, callback) {
      only(name, ["context"]);
      hooks[name] = callback;
      return registration;
    },
    async prompt(input) {
      prompts.push(input);
    },
  },
};

await plugin.setup(ctx);

if (hooks.context === undefined) {
  throw new Error("the plugin must register a session `context` hook");
}

for (const command of commands) {
  await command.execute({
    sessionID: "ses_test",
    prompt: { text: commandArgs },
    delivery: "steer",
  });
}

// The context hook runs after the command, so `system` shows what the next
// model request receives.
const system = [];
await hooks.context({ system });

process.stdout.write(
  JSON.stringify({
    id: plugin.id,
    commands: commands.map(({ name, description }) => ({ name, description })),
    system,
    prompts,
  }),
);
