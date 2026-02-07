import { spawn, ChildProcess } from "child_process";
import path from "path";

let botProcess: ChildProcess | null = null;

export async function setupBot() {
  if (botProcess) {
    botProcess.kill();
    botProcess = null;
  }

  const botScript = path.resolve("server/bot.py");

  botProcess = spawn("python", [botScript], {
    env: { ...process.env },
    stdio: ["pipe", "pipe", "pipe"],
  });

  botProcess.stdout?.on("data", (data: Buffer) => {
    const lines = data.toString().trim().split("\n");
    for (const line of lines) {
      console.log(`[bot] ${line}`);
    }
  });

  botProcess.stderr?.on("data", (data: Buffer) => {
    const lines = data.toString().trim().split("\n");
    for (const line of lines) {
      console.log(`[bot] ${line}`);
    }
  });

  botProcess.on("exit", (code: number | null) => {
    console.log(`[bot] Process exited with code ${code}`);
    botProcess = null;
  });

  console.log("[bot] Python bot process started");
}

export function isBotRunning(): boolean {
  return botProcess !== null && !botProcess.killed;
}
