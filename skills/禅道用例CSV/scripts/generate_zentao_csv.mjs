import fs from "node:fs/promises";

const [casesPath, outPath] = process.argv.slice(2);
if (!casesPath || !outPath) {
  console.error("用法: node generate_zentao_csv.mjs <cases.json> <output.csv>");
  process.exit(1);
}

const cases = JSON.parse(await fs.readFile(casesPath, "utf8"));
if (!Array.isArray(cases) || cases.length === 0) {
  console.error("cases.json 必须是非空数组");
  process.exit(1);
}

const pad = (n) => String(n).padStart(3, "0");
const counters = {};
const rows = [];

for (const c of cases) {
  const module = String(c.module ?? "").trim();
  if (!module) throw new Error("每条用例必须有 module");
  const steps = Array.isArray(c.steps) ? c.steps.map((s) => String(s).trim()) : [];
  const expects = Array.isArray(c.expects) ? c.expects.map((s) => String(s).trim()) : [];
  if (steps.length === 0) throw new Error(`用例「${c.name}」缺少步骤`);
  if (steps.length !== expects.length) {
    throw new Error(`用例「${c.name}」步骤(${steps.length})与预期(${expects.length})数量不一致`);
  }
  counters[module] = (counters[module] ?? 0) + 1;
  const no = counters[module];
  const stepsCell = steps.map((s, i) => `${i + 1}. ${s}`).join("\r\n");
  const expectsCell = expects.map((s, i) => `${i + 1}. ${s}`).join("\r\n");
  rows.push([
    module,
    `TC_${module}_${pad(no)}`,
    `${module}_${String(c.keyword ?? "").trim()}`,
    Number(c.priority) || 2,
    String(c.name ?? "").trim(),
    String(c.precondition ?? "").trim(),
    stepsCell,
    expectsCell,
    "",
    "",
    "功能测试",
    "功能测试阶段",
  ]);
}

const HEADERS = ["所属模块", "用例编号", "关键词", "优先级", "用例名称", "前置条件", "步骤", "预期", "测试结果（留空）", "用例备注", "用例类型", "适用阶段"];

const csvField = (v) => {
  const s = String(v ?? "");
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

const lines = [HEADERS.map(csvField).join(",")];
for (const r of rows) lines.push(r.map(csvField).join(","));
const csv = "\uFEFF" + lines.join("\r\n");

const dir = outPath.slice(0, Math.max(outPath.lastIndexOf("/"), outPath.lastIndexOf("\\")));
if (dir) await fs.mkdir(dir, { recursive: true });
await fs.writeFile(outPath, csv, "utf8");
console.log(`OK: ${rows.length} 条用例已写入 ${outPath}`);
