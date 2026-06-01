# 作者: plusluo
# 大模型能力评测分数排名可视化 — 版本日志

> 版本号规则：每次内容更新（新增模型 / 新增评测项 / 数据修订）都递增一个小版本号（v1.0 → v1.1 → v1.2 ...）。  
> 模型保留策略：**Claude 保留最近 2 个版本**，其他厂家只保留当前能拿到的最新模型版本。

## v1.0 — 2026-04-12

首次发布。基于 MiniMax-M3 发布技术报告 + 各评测公开榜单整理。

**模型清单（9 个）**
- Anthropic：Claude Opus 4.7、Claude Sonnet 4.5
- OpenAI：GPT-5.5
- Google：Gemini 3.0 Pro
- MiniMax：MiniMax-M3、MiniMax-M2.7（待下次精简）
- DeepSeek：DeepSeek V4 Pro
- Zhipu：GLM Thinking
- Moonshot：Kimi K2.6 Thinking

**评测项数量**：32

**能力分类**：Coding、Computer Agent、GUI、Multimodal、Reasoning

**已知缺口**
- 暂无腾讯混元数据；下次更新时若官方榜单出现混元成绩需补齐
- `MiniMax-M2.7` 未来可去除（已被 `MiniMax-M3` 取代）；保留至下次内容更新时一并精简
- 部分厂家内部评测（MCP-Atlas、Apex-Agents、YC-Bench、LOCA-Bench、CUA-Eval、PostTrainBench、SWE-Calibr-QA、NL2Repo、SWE-Atlas-Test Writing、CI-Bench、BrowseToolBench、OfficeQA Pro）暂无公开榜单链接，状态见 `sources.json`

---

<!-- 后续版本在上方追加，保留时间倒序 -->
