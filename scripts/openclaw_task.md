# OpenClaw 自动化内容搬运任务说明

> 作者: plusluo
> 最后更新: 2026-04-10

## 任务概述

本任务由 OpenClaw AI Agent 在云端定时执行，自动将 `plusluo_doc` 知识库中成熟的文章内容搬运到 `plusluo-site` Hugo 博客，并触发自动部署。

## 环境要求

- **Python**: 3.8+（标准库即可，无需额外依赖）
- **Git**: 已配置 SSH key，可访问 GitHub 上的两个仓库
- **仓库**:
  - `plusluo_doc`: `git@github.com:plusluo/plusluo_doc.git`
  - `plusluo-site`: `git@github.com:plusluo/plusluo-site.git`

## 定时调度

| 参数 | 值 |
|------|------|
| 执行频率 | 每天 1 次 |
| 执行时间 | 北京时间 02:00（避开工作时间） |
| Cron 表达式 | `0 2 * * *` |

## 执行步骤

### 1. 准备环境

```bash
# 进入工作目录
cd /opt/openclaw/workspace

# 克隆或更新两个仓库
if [ ! -d "plusluo_doc" ]; then
  git clone git@github.com:plusluo/plusluo_doc.git
fi
if [ ! -d "plusluo-site" ]; then
  git clone git@github.com:plusluo/plusluo-site.git
fi

# 更新到最新
cd plusluo_doc && git pull --rebase && cd ..
cd plusluo-site && git pull --rebase && cd ..
```

### 2. 执行搬运

```bash
cd plusluo-site

# 正常搬运模式
python3 scripts/migrate.py \
  --source ../plusluo_doc/my-kb \
  --target . \
  --config scripts/migrate_config.yaml

# 试运行模式（仅查看计划搬运的文件，不实际写入）
python3 scripts/migrate.py \
  --source ../plusluo_doc/my-kb \
  --target . \
  --dry-run
```

### 3. 自动部署

搬运脚本会自动执行 `git add + commit + push`，GitHub Actions 会自动触发构建和部署。

## 扫描规则

### 扫描范围

- `plusluo_doc/my-kb/` 下所有 `.md` 文件

### 排除规则

| 排除项 | 原因 |
|--------|------|
| `diary/` 整个目录 | 私人日记，不公开 |
| `_draft_` 前缀文件 | 草稿，未完成 |
| `INDEX.md`、`work-kb-index.md` | 纯导航索引文件 |
| `专题导航-*.md`、`专题总入口-*.md` | 纯导航文件 |
| `文档目录概要.md` | 纯导航文件 |
| 文件 < 200 字节 | 空文件 |
| 正文 < 300 字 | 内容不够完善 |

### 内容类型判定

| 类型 | 条件 | Hugo 目录 | 图标 |
|------|------|-----------|------|
| `code` | 代码块占比 > 20% 或技术关键词命中 ≥ 3 | `content/code/` | 根据分类选择 |
| `article` | 长文 ≥ 800 字，非代码密集型 | `content/article/` | 根据分类选择 |
| `status` | 短笔记 < 500 字 | `content/status/` | 根据分类选择 |
| `page` | 来自 articles/首页、联系我、Github | `content/page/` | - |

### 分类与图标对照

| 分类 | 图标 | 匹配关键词 |
|------|------|-----------|
| 投资理财 | `fa-chart-line` | 投资、理财、股票、基金、价值投资 |
| 读书笔记 | `fa-book-open` | 读书、书评、阅读、读后感 |
| 心理学与认知 | `fa-brain` | 心理、认知、人性、社会学、行为 |
| 物理学 | `fa-atom` | 物理、量子、相对论、力学 |
| 生物学 | `fa-dna` | 生物、基因、进化、细胞 |
| 汽车知识 | `fa-car` | 汽车、车、驾驶、新能源 |
| 个人成长 | `fa-seedling` | 成长、自律、习惯、复盘 |
| 软件研发 | `fa-code` | 编程、开发、软件、代码 |
| AI 技术 | `fa-robot` | AI、大模型、Agent、LLM、GPT |
| 碎碎念 | `fa-comment-dots` | 随想、感悟、日常、生活 |

## 异常处理

### 常见异常及处理方式

| 异常 | 处理方式 |
|------|---------|
| Git pull 冲突 | 记录日志，跳过本次执行，通知 plusluo |
| 源文件编码错误 | 跳过该文件，记录 warning 日志 |
| 图片复制失败 | 保留原路径引用，记录 warning，继续处理其余内容 |
| Git push 失败 | 保留本地 commit，下次执行时会自动重试 push |
| 搬运记录损坏 | 重建 `.migration-log.json`，可能导致重复搬运（通过 slug 检查可避免覆盖） |

### 监控与通知

- 每次执行后输出搬运统计（搬运数量、跳过数量、错误数量）
- 如果连续 7 天无新内容搬运，不需要告警（正常情况）
- 如果出现 git 操作失败，发送通知提醒

## 手动操作指南

### 查看搬运记录

```bash
cat plusluo-site/.migration-log.json | python3 -m json.tool
```

### 强制重新搬运某篇文章

从 `.migration-log.json` 中删除对应记录，然后重新运行脚本。

### 只搬运特定目录

```bash
# 只处理 articles/ 目录
python3 scripts/migrate.py \
  --source ../plusluo_doc/my-kb/articles \
  --target .
```

## 版本日志

| 日期 | 变更 |
|------|------|
| 2026-04-10 | 初始版本，支持全量扫描和三种内容类型 |
