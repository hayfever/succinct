import { afterEach, beforeEach, describe, expect, mock, test } from "bun:test";
import {
  existsSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

// The real extension imports getAgentDir from the Pi SDK. Point it at the
// per-test directory so the tests exercise the same code path as a runtime.
mock.module("@earendil-works/pi-coding-agent", () => ({
  getAgentDir: () =>
    process.env.PI_CODING_AGENT_DIR ?? join(tmpdir(), "succinct-no-agent-dir"),
}));

// The SDK is not installed outside a runtime, and bun resolves static imports
// before mock.module runs, so the extension must be loaded after the mock.
const { default: succinctExtension } = await import("../extensions/succinct");

type CustomEntry = {
  type: "custom";
  customType: string;
  data?: unknown;
};

type ContextMessage = {
  role: "custom";
  customType: string;
  content: string;
};

type SentMessage = {
  customType: string;
  content: string;
  display?: boolean;
};

type CommandSpec = {
  description: string;
  handler: (args: string, ctx: FakeContext) => Promise<void>;
};

type FakeContext = {
  hasUI: boolean;
  ui: {
    theme: { fg: (color: string, text: string) => string };
    setStatus: (key: string, text?: string) => void;
    notify: (text: string, type?: string) => void;
  };
  sessionManager: {
    getBranch: () => CustomEntry[];
    buildSessionContext: () => { messages: ContextMessage[] };
  };
};

type InputResult =
  | { action: "continue" }
  | { action: "handled" }
  | { action: "transform"; text: string };

type Handler = (event: unknown, ctx: FakeContext) => Promise<unknown>;

type FakePi = {
  getFlag: (name: string) => boolean | undefined;
  registerFlag: (name: string, options: unknown) => void;
  registerCommand: (name: string, spec: CommandSpec) => void;
  on: (event: string, handler: Handler) => void;
  appendEntry: (customType: string, data: unknown) => void;
  sendMessage: (message: SentMessage) => void;
};

type FakeAgent = {
  pi: FakePi;
  ctx: FakeContext;
  entries: CustomEntry[];
  messages: ContextMessage[];
  notifications: Array<{ text: string; type?: string }>;
  sent: SentMessage[];
  statuses: Array<string | undefined>;
  commands: Map<string, CommandSpec>;
  listeners: Map<string, Handler[]>;
  fire: (event: string, payload?: unknown) => Promise<unknown[]>;
  fireInput: (text: string) => Promise<InputResult>;
  runCommand: (args: string) => Promise<void>;
};

function createAgent(
  options: { flag?: boolean; hasUI?: boolean } = {},
): FakeAgent {
  const entries: CustomEntry[] = [];
  const messages: ContextMessage[] = [];
  const statuses: Array<string | undefined> = [];
  const notifications: Array<{ text: string; type?: string }> = [];
  const sent: SentMessage[] = [];
  const commands = new Map<string, CommandSpec>();
  const listeners = new Map<string, Handler[]>();

  const ctx: FakeContext = {
    hasUI: options.hasUI ?? true,
    ui: {
      theme: { fg: (_color, text) => text },
      setStatus: (_key, text) => {
        statuses.push(text);
      },
      notify: (text, type) => {
        notifications.push({ text, type });
      },
    },
    sessionManager: {
      getBranch: () => entries,
      buildSessionContext: () => ({ messages }),
    },
  };

  const pi: FakePi = {
    getFlag: (name: string) => (name === "succinct" ? options.flag : undefined),
    registerFlag: () => {},
    registerCommand: (name: string, spec: CommandSpec) => {
      commands.set(name, spec);
    },
    on: (event: string, handler: Handler) => {
      const handlers = listeners.get(event) ?? [];
      handlers.push(handler);
      listeners.set(event, handlers);
    },
    appendEntry: (customType: string, data: unknown) => {
      entries.push({ type: "custom", customType, data });
    },
    sendMessage: (message: SentMessage) => {
      sent.push(message);
      messages.push({
        role: "custom",
        customType: message.customType,
        content: message.content,
      });
    },
  };

  const fire = async (event: string, payload: unknown = {}) => {
    const results: unknown[] = [];
    for (const handler of listeners.get(event) ?? []) {
      results.push(await handler(payload, ctx));
    }
    return results;
  };

  const fireInput = async (text: string): Promise<InputResult> => {
    const [result] = await fire("input", { text });
    return result as InputResult;
  };

  const runCommand = async (args: string) => {
    const command = commands.get("succinct");
    if (!command) {
      throw new Error("The succinct command was not registered");
    }
    await command.handler(args, ctx);
  };

  return {
    pi,
    ctx,
    entries,
    messages,
    notifications,
    sent,
    statuses,
    commands,
    listeners,
    fire,
    fireInput,
    runCommand,
  };
}


let agentDir: string;

beforeEach(() => {
  agentDir = mkdtempSync(join(tmpdir(), "succinct-test-"));
  process.env.PI_CODING_AGENT_DIR = agentDir;
});

afterEach(() => {
  rmSync(agentDir, { recursive: true, force: true });
  delete process.env.PI_CODING_AGENT_DIR;
});

async function startAgent(
  options: { flag?: boolean; hasUI?: boolean } = {},
): Promise<FakeAgent> {
  const agent = createAgent(options);
  succinctExtension(agent.pi as never);
  await agent.fire("session_start");
  return agent;
}

function writeConfig(config: unknown): void {
  writeFileSync(join(agentDir, "succinct.json"), JSON.stringify(config), "utf8");
}

function readConfigFile(): Record<string, unknown> {
  return JSON.parse(
    readFileSync(join(agentDir, "succinct.json"), "utf8"),
  ) as Record<string, unknown>;
}

function rulesCount(agent: FakeAgent): number {
  return agent.messages.filter(
    (message) => message.customType === "succinct-rules",
  ).length;
}

function disabledCount(agent: FakeAgent): number {
  return agent.messages.filter(
    (message) => message.customType === "succinct-disabled",
  ).length;
}

function statusOn(agent: FakeAgent): boolean {
  return (agent.statuses.at(-1) ?? "").includes("SUCCINCT ON");
}

describe("startup", () => {
  test("starts off on demand", async () => {
    const agent = await startAgent();

    expect(rulesCount(agent)).toBe(0);
    expect(disabledCount(agent)).toBe(0);
    expect(statusOn(agent)).toBe(false);
    expect(existsSync(join(agentDir, "succinct.json"))).toBe(false);
  });

  test("--succinct starts enabled without saving a preference", async () => {
    const agent = await startAgent({ flag: true });

    expect(rulesCount(agent)).toBe(1);
    expect(statusOn(agent)).toBe(true);
    expect(existsSync(join(agentDir, "succinct.json"))).toBe(false);
  });

  test("alwaysOn starts enabled and hideStatus hides the status", async () => {
    writeConfig({ alwaysOn: true, hideStatus: true });

    const agent = await startAgent();

    expect(rulesCount(agent)).toBe(1);
    expect(statusOn(agent)).toBe(false);
  });

  test(".succinct-always starts enabled", async () => {
    writeFileSync(join(agentDir, ".succinct-always"), "", "utf8");

    const agent = await startAgent();

    expect(rulesCount(agent)).toBe(1);
    expect(statusOn(agent)).toBe(true);
  });

  test("a saved off choice outranks alwaysOn and the flag file", async () => {
    writeConfig({ enabled: false, alwaysOn: true });
    writeFileSync(join(agentDir, ".succinct-always"), "", "utf8");

    const agent = await startAgent();

    expect(rulesCount(agent)).toBe(0);
    expect(statusOn(agent)).toBe(false);
  });

  test("--succinct outranks a saved off choice for that run", async () => {
    writeConfig({ enabled: false });

    const agent = await startAgent({ flag: true });

    expect(rulesCount(agent)).toBe(1);
    expect(readConfigFile()).toEqual({ enabled: false });
  });
});

describe("toggles", () => {
  test("bare /succinct toggles this session only", async () => {
    const agent = await startAgent();

    await agent.runCommand("");

    expect(rulesCount(agent)).toBe(1);
    expect(statusOn(agent)).toBe(true);
    expect(existsSync(join(agentDir, "succinct.json"))).toBe(false);
    expect(agent.notifications.at(-1)?.text).toContain("this session only");

    await agent.runCommand("");

    expect(disabledCount(agent)).toBe(1);
    expect(statusOn(agent)).toBe(false);
    expect(existsSync(join(agentDir, "succinct.json"))).toBe(false);
  });

  test("/succinct off saves the choice and keeps other settings", async () => {
    writeConfig({ hideStatus: true, alwaysOn: false });

    const agent = await startAgent();
    await agent.runCommand("off");

    expect(readConfigFile()).toEqual({
      hideStatus: true,
      alwaysOn: false,
      enabled: false,
    });
    expect(agent.notifications.at(-1)?.text).toContain(
      "saved for future sessions",
    );

    const nextSession = await startAgent();
    expect(rulesCount(nextSession)).toBe(0);
  });

  test("/succinct on saves the choice for the next session", async () => {
    writeConfig({ enabled: false });

    const agent = await startAgent();
    expect(rulesCount(agent)).toBe(0);

    await agent.runCommand("on");

    expect(readConfigFile()).toEqual({ enabled: true });
    expect(rulesCount(agent)).toBe(1);

    const nextSession = await startAgent();
    expect(rulesCount(nextSession)).toBe(1);
    expect(statusOn(nextSession)).toBe(true);
  });

  test("/succinct stop ends this session without saving", async () => {
    const agent = await startAgent({ flag: true });

    await agent.runCommand("stop");

    expect(statusOn(agent)).toBe(false);
    expect(disabledCount(agent)).toBe(1);
    expect(existsSync(join(agentDir, "succinct.json"))).toBe(false);
  });

  test("/succinct with an unknown argument shows usage", async () => {
    const agent = await startAgent();

    await agent.runCommand("sideways");

    expect(agent.notifications.at(-1)).toEqual({
      text: "Usage: /succinct [on|off]",
      type: "warning",
    });
    expect(agent.entries).toHaveLength(0);
  });

  test("the save leaves no temporary file behind", async () => {
    const agent = await startAgent();

    await agent.runCommand("on");

    expect(readdirSync(agentDir)).toEqual(["succinct.json"]);
  });
});

describe("stop phrases", () => {
  for (const phrase of ["stop succinct mode", "normal mode"]) {
    test(`"${phrase}" ends the session only`, async () => {
      const agent = await startAgent({ flag: true });

      const result = await agent.fireInput(phrase);

      expect(result).toEqual({ action: "handled" });
      expect(statusOn(agent)).toBe(false);
      expect(disabledCount(agent)).toBe(1);
      expect(existsSync(join(agentDir, "succinct.json"))).toBe(false);

      const nextSession = await startAgent({ flag: true });
      expect(rulesCount(nextSession)).toBe(1);
    });
  }

  test("a stop phrase passes through while the mode is off", async () => {
    const agent = await startAgent();

    expect(await agent.fireInput("normal mode")).toEqual({ action: "continue" });
    expect(agent.entries).toHaveLength(0);
  });

  test("a stop phrase without a UI asks for the confirmation text", async () => {
    const agent = await startAgent({ flag: true, hasUI: false });

    expect(await agent.fireInput("stop succinct mode")).toEqual({
      action: "transform",
      text: "Reply with exactly: Succinct mode disabled.",
    });
  });

  test("/skill:succinct enables this session without saving", async () => {
    const agent = await startAgent();

    expect(await agent.fireInput("/skill:succinct")).toEqual({
      action: "handled",
    });
    expect(rulesCount(agent)).toBe(1);
    expect(statusOn(agent)).toBe(true);
    expect(existsSync(join(agentDir, "succinct.json"))).toBe(false);
  });
});

describe("session state and compaction", () => {
  test("reload keeps the session toggle and does not duplicate the rules", async () => {
    const agent = await startAgent({ flag: true });
    expect(rulesCount(agent)).toBe(1);

    await agent.runCommand("");
    await agent.fire("session_start");

    expect(rulesCount(agent)).toBe(1);
    expect(disabledCount(agent)).toBe(1);
    expect(statusOn(agent)).toBe(false);
  });

  test("compaction re-injects the rules after they drop out", async () => {
    const agent = await startAgent({ flag: true });
    expect(rulesCount(agent)).toBe(1);

    agent.messages.length = 0;
    await agent.fire("session_compact");

    expect(rulesCount(agent)).toBe(1);

    await agent.fire("session_compact");
    expect(rulesCount(agent)).toBe(1);
  });

  test("compaction while off injects nothing", async () => {
    const agent = await startAgent();

    agent.messages.length = 0;
    await agent.fire("session_compact");

    expect(rulesCount(agent)).toBe(0);
    expect(disabledCount(agent)).toBe(0);
  });

  test("rules and disabled notices stay in sync across toggles", async () => {
    const agent = await startAgent();

    await agent.runCommand("on");
    await agent.runCommand("off");
    await agent.runCommand("on");

    expect(rulesCount(agent)).toBe(2);
    expect(disabledCount(agent)).toBe(1);
  });
});

describe("unusable config", () => {
  test("warns once, uses defaults, and leaves the file untouched", async () => {
    const corrupt = "{ this is not json";
    writeFileSync(join(agentDir, "succinct.json"), corrupt, "utf8");

    const agent = await startAgent();

    expect(rulesCount(agent)).toBe(0);
    expect(agent.notifications).toHaveLength(1);
    expect(agent.notifications[0]?.type).toBe("warning");
    expect(agent.notifications[0]?.text).toContain("Cannot parse");

    await agent.fire("session_tree");
    expect(agent.notifications).toHaveLength(1);

    await agent.runCommand("off");
    expect(
      readFileSync(join(agentDir, "succinct.json"), "utf8"),
    ).toBe(corrupt);
    expect(agent.notifications.at(-1)?.text).toContain(
      "this session only",
    );
    expect(statusOn(agent)).toBe(false);
  });

  test("a JSON array is not a valid config", async () => {
    writeConfig([1, 2, 3]);

    const agent = await startAgent();

    expect(agent.notifications).toHaveLength(1);
    expect(agent.notifications[0]?.text).toContain("JSON object");
    expect(rulesCount(agent)).toBe(0);
  });
});
