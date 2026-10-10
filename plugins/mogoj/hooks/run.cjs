#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT || path.resolve(__dirname, "../../..");
const event = process.argv[2] || "";
const input = require("node:fs").readFileSync(0);
const isCli = event === "cli";
const script = path.join(pluginRoot, "tools", isCli ? "cli.py" : "auto_memory.py");
const scriptArgs = isCli ? process.argv.slice(3) : [event];

let result;
for (const executable of process.platform === "win32" ? ["python", "py"] : ["python3", "python"]) {
  const args = executable === "py" ? ["-3", script, ...scriptArgs] : [script, ...scriptArgs];
  result = spawnSync(executable, args, {
    input,
    encoding: "utf8",
    env: process.env,
    timeout: 19000,
    windowsHide: true,
  });
  if (!result.error || result.error.code !== "ENOENT") break;
}

if (!result || result.error) {
  process.stdout.write("{}\n");
  process.exit(isCli ? 4 : 0);
}
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
if (!isCli && !result.stdout.trim()) process.stdout.write("{}\n");
// Memory must never prevent Claude from working. Hook failures fail open and
// remain diagnosable through Claude Code's hook debug log.
process.exit(isCli ? (result.status || 0) : 0);
