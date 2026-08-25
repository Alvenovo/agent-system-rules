# PowerShell 7 一次性安装（系统级参考）

> 触发：仅当 `%USERPROFILE%\.codex\pwsh7.ok` **不存在**时读取并执行。标记已存在则禁止读取本文件、禁止检测版本。

目的：让 Cursor / Codex Agent 的 Shell 用 PowerShell 7，避免 5.1 不认 `&&` 等语法导致失败重试。

## 判定

1. 只看 **当前 Agent Shell**（本对话里跑命令的那个），不要拿用户自己开的终端当证据。
2. 合格：`$PSVersionTable.PSVersion.Major -ge 7` **且** 进程路径为 `C:\Program Files\PowerShell\7\pwsh.exe`。
3. 不合格：5.x，或路径在 `WindowsApps` / `%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe`（商店/MSIX 空壳别名）。Agent 扫 PATH 认不出这种别名，会继续用 5.1。

已合格 → 写入标记文件，结束。不要再改配置。

## 安装（不合格时）

1. 下载 MSI（不要再用 winget 的 msix）：  
   `https://github.com/PowerShell/PowerShell/releases/download/v7.6.5/PowerShell-7.6.5-win-x64.msi`
2. 管理员安装（当前进程非管理员时用 `-Verb RunAs`，让用户点 UAC 是）：  
   `msiexec /package <msi> /quiet ADD_PATH=1 REGISTER_MANIFEST=1 ENABLE_PSREMOTING=0`
3. 确认存在 `C:\Program Files\PowerShell\7\pwsh.exe`。
4. 写入 Cursor `settings.json`：
   - `terminal.integrated.defaultProfile.windows` = `pwsh`
   - profiles / `automationProfile` / `agentHostProfile` 的 path 都指向 `C:\Program Files\PowerShell\7\pwsh.exe`
   - `cursor.useLegacyTerminalTool` = true
5. 请用户 **完全退出 Cursor**（托盘也退）再重开，新对话里再验 Agent 版本。旧对话会一直挂 5.1。
6. 新对话确认 Agent 已是 7 且路径为 Program Files 后，写入标记。

## 标记

路径：`%USERPROFILE%\.codex\pwsh7.ok`  
内容示例：

```
ok
version=7.6.5
path=C:\Program Files\PowerShell\7\pwsh.exe
date=YYYY-MM-DD
```

写入后本机永远跳过本流程。换电脑或用户明确要求重装时，先删该文件。
