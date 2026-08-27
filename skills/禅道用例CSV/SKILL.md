---
name: 禅道用例CSV
description: 独立禅道CSV：把清单或现有 JSON 转成团队 12 列可导入 CSV；完整测试四件套走测试规则统一生成器。
---

# 禅道测试用例 CSV 生成

本 skill 只处理独立 CSV 交付。任务属于完整测试用例设计、同步或归档时，改 `source/manifest.json`，运行 `%USERPROFILE%\.codex\测试规则\scripts\generate_test_package.py`，本 skill 到此完成。

## 工作流

1. **收集输入**：从用户给的清单、图片或文档中提取每条用例的名称、模块、前置条件、步骤和预期。用户未指定输出目录时先询问；已指定则直接使用。完成：用例内容和输出路径齐全。
2. **读取格式**：完整阅读 [references/format.md](references/format.md)，它是 12 列、编码、标点和导入格式的唯一真相。完成：每条用例已按该格式整理，步骤与预期一一对应。
3. **准备 JSON**：按下方 schema 写入 `cases.json`。完成：字段齐全，`steps` 与 `expects` 等长。
4. **生成 CSV**：目录不存在时自动创建，运行：

   ```powershell
   node scripts/generate_zentao_csv.mjs <cases.json> <output.csv>
   ```

   完成：脚本成功输出 CSV。
5. **校验**：解析 CSV，并逐项执行 `format.md` 的文件、列数、编号和对应关系检查。完成：全部校验通过。
6. **交付**：只交付 CSV；回复给出完整路径和 `format.md` 中的禅道导入路径。完成：用户可直接找到并导入文件。

## cases.json 输入格式

```json
[
  {
    "module": "商品营销",
    "keyword": "预售活动",
    "priority": 1,
    "name": "预售活动标签展示与购买",
    "precondition": "已登录商户端，商品已发布并配置预售活动。",
    "steps": ["在商户端配置预售活动及开始/结束时间。", "用户端打开商品详情页。"],
    "expects": ["配置保存成功。", "展示“预售”标识及活动时间。"]
  }
]
```

`module` 同时用于 所属模块、用例编号（TC_模块_001）和关键词（模块_关键词）。`steps` 与 `expects` 长度必须相等，脚本会校验。
