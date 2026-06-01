# 作者: plusluo
# 大模型评测页面 — 手动 / 定时巡检与版本更新规范

> 页面路径：`/Users/plusluo/Documents/code/plusluo-site/static/model-eval-ranking/`  
> 线上 URL：`https://plusluo.cn/model-eval-ranking/`  
> 当前版本：见 `version.json` 中 `currentVersion` 字段（首版 v1.0 / 2026-04-12）

## 一、触发方式

### 方式 A：手动触发（默认方式，当前阶段使用）

plusluo 在飞书 / 对话里只要说出以下任一意图即视为触发本任务：
- "更新一下大模型评测页面"
- "看下大模型评测有没有新数据"
- "model-eval-ranking 拉一下最新"
- "出一个 v1.x 新版本"
- 类似含义表述

### 方式 B：定时触发（接口恢复后再启用）

`automation_update` 工具可用时，一键创建：
- 任务名：`大模型评测页面新数据巡检`
- 频率：`FREQ=DAILY;BYHOUR=10;BYMINUTE=0`
- 工作目录：`/Users/plusluo/Documents/code/plusluo-site`
- Prompt：见本文件 §六

## 二、关注范围（硬约束）

### 关注厂家（共 9 家）

| 厂家 | 主要发布页 | 模型卡片 / 模型库 |
|------|-----------|-----------------|
| Anthropic (Claude) | https://www.anthropic.com/news | https://www.anthropic.com/claude |
| OpenAI (GPT) | https://openai.com/news/ | https://platform.openai.com/docs/models |
| Google (Gemini) | https://blog.google/technology/google-deepmind/ | https://deepmind.google/models/gemini/ |
| MiniMax | https://www.minimax.io/news | https://www.minimax.io/platform |
| DeepSeek | https://api-docs.deepseek.com/news/news | https://www.deepseek.com/ |
| Zhipu (GLM) | https://www.zhipuai.cn/news | https://open.bigmodel.cn/dev/api |
| Moonshot (Kimi) | https://platform.moonshot.cn/blog | https://platform.moonshot.cn/docs |
| Tencent (混元 / Hunyuan) | https://hunyuan.tencent.com/news | https://hunyuan.tencent.com/modelSquare |
| **Alibaba (Qwen / 通义千问)** | https://qwen.ai/home（英）/ https://qianwen.aliyun.com/（中） | https://github.com/QwenLM · https://huggingface.co/Qwen · https://modelscope.cn/organization/qwen |

> 完整 URL 也在 `static/model-eval-ranking/sources.json` 的 `vendorReleasePages` 字段里。

### 评测项（共 32 项）

来源全部记录在 `sources.json.benchmarks`，分两类：
- `verified: true`：有公开官方榜单 / 官方 Repo / 官方 Paper，可以直接拉。
- `vendorInternal: true`（即 `verified: false`）：厂家内部评测，只在厂家发布报告里出现，需要专门去厂家发布页找。

## 三、模型保留策略（硬约束）

| 厂家 | 保留几个版本 |
|------|------------|
| **Anthropic (Claude)** | **最近 2 个版本** |
| 其他所有厂家 | 仅保留当前最新版本 |

> 触发更新时，如果发现某厂家有更新版本，旧版本除非属于 Claude（且已是最近 2 个之一）否则一律剔除。

## 四、手动触发的标准工作流

收到触发指令后，按以下步骤逐步执行：

### Step 1 · 同步代码

```bash
cd /Users/plusluo/Documents/code/plusluo-site
git pull origin master
```

### Step 2 · 读当前快照

读取 `static/model-eval-ranking/version.json`：
- `currentVersion`：用于推算下一个版本号（v1.0 → v1.1 → v1.2 ...）
- `models`：当前已有的模型清单
- `vendorRetentionPolicy`：保留策略（Claude 2 个，其他 1 个）

### Step 3 · 巡检数据来源

按以下优先级抓取：

1. **9 家关注厂家**的 `releaseUrl`（看最近 2 周新闻 / 博客是否发了新模型）
2. **公开榜单**：
   - SWE-Bench：https://www.swebench.com/
   - Terminal-Bench：https://www.tbench.ai/
   - OSWorld-Verified：https://os-world.github.io/
   - MMMU-Pro：https://mmmu-benchmark.github.io/
   - VideoMME：https://video-mme.github.io/
   - SpreadsheetBench-v1：https://llm-stats.com/benchmarks/spreadsheetbench-v1
   - LiveSQLBench：https://github.com/bird-bench/livesqlbench
   - GPQA：https://github.com/idavidrein/gpqa
3. 各模型的 official model card 页面

### Step 4 · 比对差异

对照 `version.json.models` 与抓取结果，分两类问题：

- **新模型**：关注厂家发布了 `version.json.models` 里没有的新版本？
- **缺失分数**：现有模型在某个评测项上有新分数？（用于补全已有评测）

### Step 5 · 写入待处理文件（不直接改 v1.x 数据）

不论自动还是手动，**第一轮检查不直接修改 index.html / version.json / sources.json**。先写到：

```
model-eval-ranking-pending/<YYYY-MM-DD>.md
```

文件结构建议：

```markdown
# 作者: plusluo
# 大模型评测页面巡检 - <日期>

## 总结
- 是否建议发起新版本：<是 / 否>
- 建议下一个版本号：v1.x

## 新模型发现
- <厂家> · <模型名称>
  - 发布日期：
  - 发布链接：
  - 已抓到的评测分数：…

## 现有评测的新分数
- <评测项> · <模型名称>：分数 / 来源 URL

## 抓取失败
- <URL> — <失败原因>

## 旧版本剔除建议
- 按保留策略：…
```

写完后向用户简明汇报"今天发现 X 个新模型 / Y 项分数补全 / 是否建议发起 v1.x"。

### Step 6 · 等用户确认后再发版

确认要发起新版本时：

1. **更新 version.json**
   - `currentVersion` → 下一个小版本号（v1.0 → v1.1）
   - `lastUpdated` → 今天日期
   - `models` 数组按保留策略重排（Claude 保留 2 个、其他厂家替换为最新）
   - `history` 数组追加一条
2. **更新 CHANGELOG.md**：在文件顶部新增一节
3. **更新 index.html**
   - 顶部徽章：`版本 vX.Y` / `模型快照 <date>` / `最后更新 <date>`
   - hero stats 数字
   - "本版本模型清单"中的 `vendor-tag` 列表
   - footer 文案中的版本号
   - JS 数据数组：`benchmarks` 和 `modelColors` 中的模型替换 / 新增
4. **本地构建验证**：`hugo --gc --minify`
5. **提交推送**：
   ```bash
   git add static/model-eval-ranking/
   git commit -m "feat: 大模型评测页面更新到 vX.Y"
   git push origin master
   ```
6. **清理 pending**：将本次使用的 `model-eval-ranking-pending/<date>.md` 移到 `model-eval-ranking-pending/archived/` 或直接删掉

### Step 7 · 没有新数据的情况

仅在 `static/model-eval-ranking/check-log.txt` 末尾追加一行：

```
2026-06-01 - no new models from focused vendors
```

不要做其他改动，不要 commit。

## 五、严格约束

- ⛔ 不要修改 `themes/`
- ⛔ 不要在第一轮检查就改 v1.x 现有数据；先写到 pending 文件
- ⛔ 不要 push 没有确认的版本
- ⛔ 检查范围限定在 9 家关注厂家
- ⛔ 输出语言：中文
- ⛔ 禁止删除 v1.0 的快照（保留版本历史可审计）

## 六、定时任务 Prompt（备忘）

接口恢复后再次创建定时任务时，把以下整段作为 prompt：

```
你的任务是为 plusluo 维护 plusluo-site 仓库中的 `static/model-eval-ranking/` 页面，每天检查关注厂家是否发布了当前页面尚未包含的新模型数据。

【固定上下文】
- 工作仓库：/Users/plusluo/Documents/code/plusluo-site（master 分支）
- 关注厂家：Claude / Gemini / GPT / MiniMax / Kimi / 混元(Tencent Hunyuan) / DeepSeek / GLM / Qwen(阿里通义千问)
- 模型保留策略：Claude 保留最近 2 个版本，其他厂家仅保留当前最新模型
- 当前版本：读取 `static/model-eval-ranking/version.json` 中 currentVersion 与 models 字段
- 评测官方来源：读取 `static/model-eval-ranking/sources.json`

【每日工作流程】
1. git pull origin master
2. 读取 version.json
3. 按 sources.json.vendorReleasePages 检查 8 家厂家最近一周新闻
4. 检查公开榜单：SWE-Bench / Terminal-Bench / OSWorld-Verified / MMMU-Pro / VideoMME / SpreadsheetBench-v1 / LiveSQLBench
5. 比对差异：是否出现新模型 / 现有模型新分数
6. 如果发现新数据：写到 `model-eval-ranking-pending/<日期>.md`，文件顶部加一句通知告诉 plusluo 是否建议发起新版本
7. 如果没有新数据：仅追加一行到 `static/model-eval-ranking/check-log.txt`

【严格约束】
- 不要修改 themes 目录
- 不要 push 到远程；所有发现都先以本地 pending 文件呈现
- 检查范围限定在 9 家关注厂家
- 输出语言：中文
- 完成后简洁汇报：今日检查结果 + 是否需要发起新版本
```

## 七、配套文件清单

| 文件 | 用途 |
|------|------|
| `index.html` | 页面本体 |
| `version.json` | 版本元数据 + 关注厂家 + 保留策略 + 历史快照 |
| `sources.json` | 32 个评测项的官方来源 + 8 家厂家发布页 |
| `CHANGELOG.md` | 版本变更日志（每次发版必更新） |
| `AUTOMATION.md` | 本文件（操作规范） |
| `check-log.txt` | 巡检无新数据的轻日志（巡检每天追加一行） |
| `model-eval-ranking-pending/` | 巡检发现的待处理新数据（仓库根目录，发版后清理） |
