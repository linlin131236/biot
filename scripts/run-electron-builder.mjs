import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const failurePattern = 'docs/failure-patterns/electron-builder-package-win-network-failure.md';
const idleTimeoutMs = timeout('BOLT_BUILDER_IDLE_TIMEOUT_MS', 60_000);
const totalTimeoutMs = timeout('BOLT_BUILDER_TOTAL_TIMEOUT_MS', 600_000);
const args = process.argv.slice(2);

if (args.length === 0) {
  console.error('Usage: node ../../scripts/run-electron-builder.mjs <electron-builder args>');
  process.exit(1);
}

const child = spawn(process.execPath, [builderCli(), ...args], { stdio: ['ignore', 'pipe', 'pipe'] });
let finished = false;
let idleTimer = resetIdleTimer();
let totalTimer = setTimeout(() => stop('total timeout'), totalTimeoutMs);

child.stdout.on('data', (chunk) => forward(process.stdout, chunk));
child.stderr.on('data', (chunk) => forward(process.stderr, chunk));
child.on('error', (error) => stop(`failed to start electron-builder: ${error.message}`));
child.on('exit', (code, signal) => finish(code ?? (signal ? 1 : 0)));

function forward(stream, chunk) {
  stream.write(chunk);
  clearTimeout(idleTimer);
  idleTimer = resetIdleTimer();
}

function resetIdleTimer() {
  return setTimeout(() => stop('no output timeout'), idleTimeoutMs);
}

function stop(reason) {
  if (finished) return;
  finished = true;
  clearTimeout(idleTimer);
  clearTimeout(totalTimer);
  console.error(`Electron Builder packaging stalled: ${reason}.`);
  console.error(`See ${failurePattern} for repair steps.`);
  child.kill('SIGTERM');
  setTimeout(() => child.kill('SIGKILL'), 2000).unref();
  process.exitCode = 1;
}

function finish(code) {
  if (finished) return;
  finished = true;
  clearTimeout(idleTimer);
  clearTimeout(totalTimer);
  process.exitCode = code;
}

function timeout(name, fallback) {
  const value = Number.parseInt(process.env[name] ?? '', 10);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function builderCli() {
  const localCli = join(process.cwd(), 'node_modules', 'electron-builder', 'cli.js');
  if (existsSync(localCli)) return localCli;
  console.error('Cannot find local electron-builder CLI at node_modules/electron-builder/cli.js.');
  process.exit(1);
}
