import { createRequire } from 'node:module';
import { readFileSync, existsSync, writeFileSync, unlinkSync, appendFileSync } from 'node:fs';
import { parseArgs } from 'node:util';
import { tmpdir, homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import http from 'node:http';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = join(SCRIPT_DIR, '..');
const PLAYWRIGHT_CANDIDATES = [
  join(SKILL_ROOT, 'node_modules') + '/',
  join(homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/'),
];

function loadPlaywright() {
  let lastErr;
  for (const dir of PLAYWRIGHT_CANDIDATES) {
    try {
      return createRequire(dir)('playwright');
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr ?? new Error("Cannot find package 'playwright'");
}

const { chromium } = loadPlaywright();

const DEFAULT_PROFILE = join(homedir(), 'Documents', 'Codex', 'doubao-chrome-profile');
const CHAT_URL = 'https://www.doubao.com/chat/';
const STATE_FILE = join(tmpdir(), 'doubao-describe-server.json');
const SCRIPT_PATH = fileURLToPath(import.meta.url);
const IDLE_DEFAULT_MS = 15 * 60 * 1000;
const LOG_FILE = join(tmpdir(), 'doubao-describe-server.log');
const TASK_NAME = 'CodexDoubaoDescribe';
const execFileP = promisify(execFile);

function quoteIfNeeded(s) {
  return /\s/.test(s) ? `"${s}"` : s;
}

async function killDaemonProcess(pid) {
  if (!pid) return;
  try {
    await execFileP('taskkill', ['/PID', String(pid), '/F', '/T']);
  } catch {}
}

function log(msg) {
  try {
    appendFileSync(LOG_FILE, `[${new Date().toISOString()}] ${msg}\n`);
  } catch {}
}

const { values } = parseArgs({
  options: {
    image: { type: 'string' },
    prompt: { type: 'string', default: '' },
    profile: { type: 'string', default: DEFAULT_PROFILE },
    headed: { type: 'boolean', default: false },
    server: { type: 'boolean', default: false },
    stop: { type: 'boolean', default: false },
    status: { type: 'boolean', default: false },
    idleMs: { type: 'string', default: '' },
  },
});

function mimeFor(name) {
  const lower = name.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.gif')) return 'image/gif';
  if (lower.endsWith('.webp')) return 'image/webp';
  if (lower.endsWith('.bmp')) return 'image/bmp';
  return 'image/jpeg';
}

function readState() {
  try {
    return JSON.parse(readFileSync(STATE_FILE, 'utf8'));
  } catch {
    return null;
  }
}

function writeState(state) {
  try {
    writeFileSync(STATE_FILE, JSON.stringify(state));
  } catch {}
}

function clearState(pid) {
  const st = readState();
  if (st && (pid === undefined || st.pid === pid)) {
    try {
      unlinkSync(STATE_FILE);
    } catch {}
  }
}

function getJson(port, path) {
  return new Promise((resolve) => {
    const req = http.request(
      { host: '127.0.0.1', port, path, method: 'GET', agent: false },
      (res) => {
        let chunks = '';
        res.setEncoding('utf8');
        res.on('data', (c) => (chunks += c));
        res.on('end', () => {
          try {
            resolve({ ok: true, status: res.statusCode, body: JSON.parse(chunks) });
          } catch {
            resolve({ ok: true, status: res.statusCode, body: null });
          }
        });
      }
    );
    req.on('error', () => resolve({ ok: false }));
    req.setTimeout(10000, () => {
      req.destroy();
      resolve({ ok: false });
    });
    req.end();
  });
}

function postJson(port, path, body) {
  return new Promise((resolve) => {
    const data = JSON.stringify(body || {});
    const req = http.request(
      {
        host: '127.0.0.1',
        port,
        path,
        method: 'POST',
        agent: false,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(data),
        },
      },
      (res) => {
        let chunks = '';
        res.setEncoding('utf8');
        res.on('data', (c) => (chunks += c));
        res.on('end', () => {
          try {
            resolve({ ok: true, status: res.statusCode, body: JSON.parse(chunks) });
          } catch {
            resolve({ ok: true, status: res.statusCode, body: null });
          }
        });
      }
    );
    req.on('error', () => resolve({ ok: false }));
    req.setTimeout(300000, () => {
      req.destroy();
      resolve({ ok: false });
    });
    req.end(data);
  });
}

async function launchAndOpen(profile, headed) {
  const ctx = await chromium.launchPersistentContext(profile, {
    channel: 'chrome',
    headless: !headed,
    viewport: { width: 1280, height: 800 },
    userAgent:
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    args: ['--disable-blink-features=AutomationControlled'],
  });
  const page = ctx.pages()[0] ?? (await ctx.newPage());
  await page.goto(CHAT_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  return { ctx, page };
}

// Optimized login detection: logged-in state is detected by the chat input
// being visible, instead of polling the sidebar for conversation anchors.
async function checkLogin(page, timeoutMs = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const hasInput = await page
      .locator('textarea')
      .first()
      .isVisible()
      .catch(() => false);
    if (hasInput) return 'logged-in';
    const loginVisible = await page
      .getByText('登录', { exact: true })
      .first()
      .isVisible()
      .catch(() => false);
    if (loginVisible) return 'login-required';
    await page.waitForTimeout(500);
  }
  const loginVisible = await page
    .getByText('登录', { exact: true })
    .first()
    .isVisible()
    .catch(() => false);
  return loginVisible ? 'login-required' : 'logged-in';
}

async function showLoginQR(page) {
  const loginBtn = page.getByText('登录', { exact: true }).first();
  try {
    await loginBtn.click();
  } catch {}
  await page.waitForTimeout(3000);
  const qrPath = join(tmpdir(), 'doubao-login-qr.png');
  await page.screenshot({ path: qrPath });
  return qrPath;
}

async function dismissPromoDialog(page) {
  try {
    const dialog = page.locator('[data-slot="dialog-content"][data-state="open"]').first();
    if (!(await dialog.count())) return;
    if (!(await dialog.isVisible().catch(() => false))) return;
    const closeBtn = dialog.locator('button[aria-label="关闭"]').first();
    if (await closeBtn.count()) {
      await closeBtn.click();
      await page.waitForTimeout(800);
      log('promo dialog dismissed');
    }
  } catch {}
}

async function newChatIfNeeded(page) {
  await dismissPromoDialog(page);
  const newChat = page.getByText('新对话', { exact: true }).first();
  if (await newChat.isVisible().catch(() => false)) {
    await newChat.click();
  }
  await page
    .locator('textarea')
    .first()
    .waitFor({ state: 'visible', timeout: 15000 })
    .catch(() => {});
}

async function attachImage(page, imagePath) {
  const fileName = imagePath.split(/[\\/]/).pop() || 'image.png';
  const b64 = readFileSync(imagePath).toString('base64');
  const pasteImage = async () => {
    const dt = await page.evaluateHandle(
      async ({ b64data, name, type }) => {
        const bin = atob(b64data);
        const bytes = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
        const file = new File([bytes], name, { type });
        const d = new DataTransfer();
        d.items.add(file);
        return d;
      },
      { b64data: b64, name: fileName, type: mimeFor(fileName) }
    );
    await page.evaluate((d) => {
      const el = document.querySelector('textarea');
      el.dispatchEvent(
        new ClipboardEvent('paste', { clipboardData: d, bubbles: true, cancelable: true })
      );
    }, dt);
  };

  const hasAttachment = () =>
    page.evaluate(() => {
      const el = document.querySelector('textarea');
      const tr = el ? el.getBoundingClientRect() : null;
      return [...document.querySelectorAll('img')].some((i) => {
        const r = i.getBoundingClientRect();
        return r.width >= 30 && tr && i.y > tr.y - 500 && (i.src || '').startsWith('blob:');
      });
    });

  const waitAttachment = async (ms) => {
    const start = Date.now();
    while (Date.now() - start < ms) {
      if (await hasAttachment()) return true;
      await page.waitForTimeout(500);
    }
    return false;
  };

  const ta = page.locator('textarea').first();
  await ta.click();
  await pasteImage();
  if (await waitAttachment(8000)) return true;
  await pasteImage();
  return waitAttachment(8000);
}

async function sendPromptAndWait(page, prompt) {
  if (prompt) {
    await page.locator('textarea').first().fill(prompt);
  }
  const sendBtn = page.locator('#flow-end-msg-send');
  try {
    await sendBtn.waitFor({ state: 'visible', timeout: 10000 });
    await sendBtn.click({ timeout: 10000 });
  } catch {
    const clicked = await page.evaluate(() => {
      const btn = document.querySelector('#flow-end-msg-send');
      if (btn) {
        btn.click();
        return true;
      }
      return false;
    });
    if (!clicked) return { error: 'send-button-not-found' };
  }

  await page.waitForTimeout(1000);
  const readText = () =>
    page.evaluate(() => {
      const list = document.querySelector('div[class*="message-list-"]');
      return list ? list.innerText : (document.querySelector('main')?.innerText || '');
    });

  let lastText = await readText();
  let stable = 0;
  let sawChange = false;
  let finalText = lastText;
  const start = Date.now();
  while (Date.now() - start < 240000) {
    await page.waitForTimeout(1000);
    const txt = await readText();
    if (txt !== lastText) {
      sawChange = true;
      lastText = txt;
      stable = 0;
    } else {
      stable++;
    }
    finalText = txt;
    // Only accept a stable text once the assistant actually started replying;
    // 3 consecutive identical polls (~3s) means the stream has finished.
    if (sawChange && stable >= 3) break;
  }
  return { reply: finalText.trim() };
}

async function deleteConversation(page) {
  await dismissPromoDialog(page);
  const convId = (page.url().match(/\/chat\/(\d+)/) || [])[1];
  const item = convId
    ? page.locator(`a#conversation_${convId}`).first()
    : page.locator('a[id^="conversation_"]').first();
  try {
    await item.waitFor({ state: 'visible', timeout: 8000 });
    const box = await item.boundingBox();
    if (!box) return false;
    await page.mouse.move(box.x + box.width - 10, box.y + box.height / 2);
    const trigger = item.locator('button[data-slot="dropdown-menu-trigger"], button[aria-haspopup="menu"]').first();
    await trigger.waitFor({ state: 'visible', timeout: 3000 });
    await trigger.click();
    const delItem = page.getByText('删除', { exact: true }).last();
    await delItem.waitFor({ state: 'visible', timeout: 3000 });
    await delItem.click();
    const confirmBtn = page.locator('[role="alertdialog"] button, [role="dialog"] button', { hasText: '删除' }).last();
    await confirmBtn.waitFor({ state: 'visible', timeout: 3000 }).catch(() => {});
    if (await confirmBtn.isVisible().catch(() => false)) {
      await confirmBtn.click();
    }
    await page.waitForTimeout(800);
    await item.waitFor({ state: 'detached', timeout: 5000 }).catch(() => {});
    return (await item.count()) === 0;
  } catch (e) {
    log('delete fail: ' + (e && e.message));
    return false;
  }
}

async function describeFlow(page, imagePath, prompt) {
  if (!existsSync(imagePath)) return { error: 'image-not-found' };
  const t0 = Date.now();
  await newChatIfNeeded(page);
  log(`phase new_chat ${Date.now() - t0}ms`);
  const t1 = Date.now();
  const attached = await attachImage(page, imagePath);
  log(`phase attach ${Date.now() - t1}ms ok=${attached}`);
  if (!attached) return { error: 'image-attachment-failed' };
  const t2 = Date.now();
  const res = await sendPromptAndWait(page, prompt);
  log(`phase reply ${Date.now() - t2}ms`);
  if (res.error) return { error: res.error };
  const t3 = Date.now();
  const deleted = await deleteConversation(page);
  log(`phase delete ${Date.now() - t3}ms deleted=${deleted}`);
  return { reply: res.reply, deleted };
}

async function runServer() {
  const idleMs = values.idleMs ? parseInt(values.idleMs, 10) : IDLE_DEFAULT_MS;
  const { ctx, page } = await launchAndOpen(values.profile, values.headed);
  log('browser launched');
  let loginState = await checkLogin(page);
  log(`login=${loginState}`);
  let lastActivity = Date.now();

  const server = http.createServer((req, res) => {
    const send = (code, obj) => {
      res.writeHead(code, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(obj));
    };

    if (req.method === 'GET' && req.url === '/health') {
      lastActivity = Date.now();
      log('health hit');
      return send(200, { ok: true, login: loginState });
    }
    if (req.method === 'POST' && req.url === '/shutdown') {
      lastActivity = Date.now();
      log('shutdown requested');
      send(200, { ok: true });
      setTimeout(() => shutdown(0), 50);
      return;
    }
    if (req.method === 'POST' && req.url === '/describe') {
      lastActivity = Date.now();
      log('describe start');
      let body = '';
      req.on('data', (c) => (body += c));
      req.on('end', async () => {
        try {
          const { image, prompt } = JSON.parse(body);
          loginState = await checkLogin(page, 5000);
          if (loginState === 'login-required') {
            const qrPath = await showLoginQR(page);
            return send(409, {
              ok: false,
              code: 'LOGIN_REQUIRED',
              qrPath,
            });
          }
          const result = await describeFlow(page, image, prompt || '');
          if (result.error === 'image-not-found') {
            return send(400, { ok: false, code: 'IMAGE_NOT_FOUND' });
          }
          if (result.error === 'image-attachment-failed') {
            return send(500, { ok: false, code: 'ATTACH_FAILED' });
          }
          if (result.error) {
            return send(500, { ok: false, code: 'SEND_FAILED' });
          }
          send(200, { ok: true, reply: result.reply, deleted: result.deleted });
        } catch (e) {
          send(500, { ok: false, code: 'INTERNAL', message: String((e && e.message) || e) });
        }
      });
      return;
    }
    send(404, { ok: false });
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const port = server.address().port;
  writeState({ port, pid: process.pid, startedAt: Date.now() });
  log(`server ready port=${port} pid=${process.pid}`);

  let shuttingDown = false;
  const shutdown = async (code) => {
    if (shuttingDown) return;
    shuttingDown = true;
    log(`shutdown(${code})`);
    clearInterval(idleTimer);
    clearState(process.pid);
    try {
      await execFileP('schtasks', ['/delete', '/tn', TASK_NAME, '/f']);
    } catch {}
    try {
      server.close();
    } catch {}
    try {
      await ctx.close();
    } catch {}
    process.exit(code);
  };

  const idleTimer = setInterval(() => {
    if (Date.now() - lastActivity > idleMs) {
      console.error('IDLE_TIMEOUT: shutting down');
      shutdown(0);
    }
  }, 30000);
  idleTimer.unref();

  process.on('SIGINT', () => shutdown(0));
  process.on('SIGTERM', () => shutdown(0));
  process.on('exit', () => clearState(process.pid));

  console.log(`DOUBAO_SERVER_READY port=${port} pid=${process.pid}`);
}

async function requestDescribe(port, image) {
  const res = await postJson(port, '/describe', { image, prompt: values.prompt });
  if (!res.ok) {
    console.error('ERROR: cannot reach the doubao background server');
    process.exitCode = 7;
    return;
  }
  const b = res.body || {};
  if (b.code === 'LOGIN_REQUIRED') {
    console.log(
      `LOGIN_REQUIRED: screenshot saved to ${b.qrPath}. Show it to the user to scan with the Doubao app, then re-run this script.`
    );
    process.exitCode = 3;
    return;
  }
  if (b.code === 'IMAGE_NOT_FOUND') {
    console.error('ERROR: image file not found');
    process.exitCode = 2;
    return;
  }
  if (b.code === 'ATTACH_FAILED') {
    console.error('ERROR: image attachment failed');
    process.exitCode = 5;
    return;
  }
  if (!b.ok) {
    console.error('ERROR:', b.message || b.code || 'unknown server error');
    process.exitCode = 8;
    return;
  }
  console.log('===DOUBAO_REPLY===');
  console.log(b.reply);
  console.log('===END===');
  console.log(
    b.deleted
      ? 'DELETED: conversation removed from Doubao'
      : 'WARN_DELETE_FAILED: conversation may still exist in Doubao'
  );
  console.log('DONE');
  process.exitCode = 0;
}

async function runClient() {
  const image = values.image;
  if (!image || !existsSync(image)) {
    console.error('ERROR: --image <path> is required and the file must exist');
    process.exitCode = 2;
    return;
  }

  const st = readState();
  if (st && st.port) {
    const health = await getJson(st.port, '/health');
    if (health.ok && health.body && health.body.ok) {
      return requestDescribe(st.port, image);
    }
    // stale daemon: kill it so its Chrome profile lock is released
    await killDaemonProcess(st.pid);
    clearState(st.pid);
  }

  console.error('starting background doubao server...');
  const serverArgs = ['--server'];
  if (values.profile !== DEFAULT_PROFILE) serverArgs.push('--profile', values.profile);
  if (values.headed) serverArgs.push('--headed');
  if (values.idleMs) serverArgs.push('--idle-ms', values.idleMs);
  // Launch through a hidden VBS wrapper: the scheduled task runs wscript.exe
  // (a windowless GUI app), which starts node.exe with window style 0 (hidden),
  // so no console window ever appears.
  const vbsPath = join(tmpdir(), 'doubao-server-launch.vbs');
  const innerCmd = [quoteIfNeeded(process.execPath), quoteIfNeeded(SCRIPT_PATH), ...serverArgs].join(' ');
  const vbs =
    'CreateObject("WScript.Shell").Run "' + innerCmd.replace(/"/g, '""') + '", 0, False';
  writeFileSync(vbsPath, vbs);
  const tr = [
    quoteIfNeeded('C:\\Windows\\System32\\wscript.exe'),
    quoteIfNeeded(vbsPath),
  ].join(' ');
  try {
    await execFileP('schtasks', [
      '/create',
      '/tn',
      TASK_NAME,
      '/tr',
      tr,
      '/sc',
      'once',
      '/st',
      '00:00',
      '/f',
    ]);
    try {
      await execFileP('schtasks', ['/run', '/tn', TASK_NAME]);
    } catch {
      await new Promise((r) => setTimeout(r, 1000));
      await execFileP('schtasks', ['/run', '/tn', TASK_NAME]);
    }
  } catch (e) {
    console.error(
      'ERROR: failed to start the background server via Task Scheduler:',
      e.message
    );
    process.exitCode = 6;
    return;
  }

  const deadline = Date.now() + 90000;
  let port = null;
  while (Date.now() < deadline) {
    const s = readState();
    if (s && s.port) {
      const health = await getJson(s.port, '/health');
      if (health.ok && health.body && health.body.ok) {
        port = s.port;
        break;
      }
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  if (!port) {
    try {
      await execFileP('schtasks', ['/end', '/tn', TASK_NAME]);
    } catch {}
    try {
      await execFileP('schtasks', ['/delete', '/tn', TASK_NAME, '/f']);
    } catch {}
    const s = readState();
    if (s && s.pid) await killDaemonProcess(s.pid);
    clearState();
    console.error(
      'ERROR: background server did not become ready in time (run with --server in a terminal to see logs)'
    );
    process.exitCode = 6;
    return;
  }
  return requestDescribe(port, image);
}

async function stopServer() {
  const st = readState();
  if (st && st.port) {
    const res = await postJson(st.port, '/shutdown', {});
    console.log(res.ok ? 'DOUBAO_SERVER_STOPPED' : 'DOUBAO_SERVER_NOT_RESPONDING');
  } else {
    console.log('DOUBAO_SERVER_NOT_RUNNING');
  }
  try {
    await execFileP('schtasks', ['/end', '/tn', TASK_NAME]);
  } catch {}
  try {
    await execFileP('schtasks', ['/delete', '/tn', TASK_NAME, '/f']);
  } catch {}
  clearState();
  process.exitCode = 0;
}

async function showStatus() {
  const st = readState();
  if (st && st.port) {
    const health = await getJson(st.port, '/health');
    if (health.ok && health.body && health.body.ok) {
      console.log(
        `DOUBAO_SERVER_RUNNING port=${st.port} pid=${st.pid} login=${health.body.login}`
      );
      process.exitCode = 0;
      return;
    }
    console.log('DOUBAO_SERVER_STALE');
    await killDaemonProcess(st.pid);
    clearState(st.pid);
    process.exitCode = 0;
    return;
  }
  console.log('DOUBAO_SERVER_NOT_RUNNING');
  process.exitCode = 0;
}

if (values.server) {
  await runServer();
} else if (values.stop) {
  await stopServer();
} else if (values.status) {
  await showStatus();
} else {
  await runClient();
}
