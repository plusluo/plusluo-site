# 作者: plusluo
# 大模型评测页面 — 每日数据巡检自动化

## 任务名称
大模型评测页面新数据巡检

## 调度
- 频率：每天 10:00
- RRULE：`FREQ=DAILY;BYHOUR=10;BYMINUTE=0`
- 工作目录：`/Users/plusluo/Documents/code/plusluo-site`

## Prompt（提交给 Agent 的完整指令）

```
你的任务是为 plusluo 维护 plusluo-site 仓库中的 `static/model-eval-ranking/` 页面，每天检查关注厂家是否发布了当前页面尚未包含的新模型数据。

【固定上下文】
- 工作仓库：/Users/plusluo/Documents/code/plusluo-site（master 分支）
- 关注厂家：Claude / Gemini / GPT / MiniMax / Kimi / 混元(Tencent Hunyuan) / DeepSeek / GLM
- 模型保留策略：Claude 保留最近 2 个版本，其他厂家仅保留当前最新模型
- 当前版本：读取 `static/model-eval-ranking/version.json` 中 currentVersion 与 models 字段
- 评测官方来源：读取 `static/model-eval-ranking/sources.json`
- 历史快照：`static/model-eval-ranking/CHANGELOG.md`

【每日工作流程】
1. 先 `git pull origin master` 同步最新代码
2. 读取 version.json 拿到当前的模型清单和版本号
3. 对照 sources.json，按以下优先级检查关注厂家是否发布了新模型并附带评测分数：
   a. 厂家 releaseUrl（vendorReleasePages 列表）— 检查最近一周新闻
   b. 知名公开榜单：SWE-Bench、Terminal-Bench、OSWorld-Verified、MMMU-Pro、VideoMME、SpreadsheetBench-v1、LiveSQLBench
   c. 各模型的 official model card 页面
4. 比对差异：
   - 是否出现关注厂家的、当前 models 列表里没有的新模型版本？
   - 是否出现现有评测项的、当前数据里缺失的某模型新分数？
5. 如果发现新数据：
   a. 在仓库根目录新建 `model-eval-ranking-pending/<日期>.md` 文件，结构化列出：新模型名称 / 新数据点 / 来源 URL / 抓取摘要
   b. 同步更新一个简短的通知文本，写到该文件顶部，告诉 plusluo 是否需要发起新版本（v1.0 → v1.1）
   c. 不要直接修改 version.json / index.html / sources.json；保持当前版本不变，等用户确认后再动
   d. 不要 git commit，只把待处理材料留在工作区
6. 如果没有发现新数据：
   a. 仅追加一行到 `static/model-eval-ranking/check-log.txt`：日期 + "no new models from focused vendors"
   b. 不要做任何其他改动

【严格约束】
- 不要修改 `themes/` 目录
- 不要 push 到远程仓库；所有发现都先以本地待处理文件形式呈现
- 检查范围限定在 8 家关注厂家
- 输出语言：中文
- 完成后简洁汇报：今日检查结果 + 是否需要发起新版本

【失败兜底】
- 如果某个 URL 抓取失败，记录到 pending 文件的 "fetch failures" 段，继续其他来源
- 如果 git pull 冲突，停止并报告，不做任何改动
```

## 回退方案

### 方案 A：通过 CodeBuddy automation 创建（推荐，接口恢复后可一键创建）

让我重新调用 `automation_update` 工具创建即可，参数已固化在本文件。

### 方案 B：macOS launchd 调度（独立于 IDE 的本机定时任务）

如果希望系统级稳定运行，可以用 launchd：

```bash
# 创建脚本
mkdir -p ~/bin
cat > ~/bin/model-eval-ranking-check.sh <<'SH'
#!/bin/bash
cd /Users/plusluo/Documents/code/plusluo-site || exit 1
git pull --quiet origin master
# 这里放你想执行的检查逻辑（最简单：调起 codebuddy CLI 或写 Python）
SH
chmod +x ~/bin/model-eval-ranking-check.sh

# 创建 launchd plist
cat > ~/Library/LaunchAgents/site.plusluo.model-eval-check.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>site.plusluo.model-eval-check</string>
  <key>ProgramArguments</key><array><string>/Users/plusluo/bin/model-eval-ranking-check.sh</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/model-eval-check.log</string>
  <key>StandardErrorPath</key><string>/tmp/model-eval-check.err</string>
</dict>
</plist>
PLIST

launchctl load ~/Library/LaunchAgents/site.plusluo.model-eval-check.plist
```

### 当前状态
- 2026-06-01：CodeBuddy automation 桥接接口暂时不可用（`Agent Manager automation bridge is unavailable`）
- 接口恢复后让我重新创建即可
