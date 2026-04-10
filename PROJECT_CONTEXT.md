# plusluo-site 项目上下文（AI 记忆文档）

> 作者：plusluo
> 创建时间：2026-04-10
> 最后更新：2026-04-10
> 用途：本文档供 AI 助手在切换工作区后快速恢复上下文，避免记忆丢失。

---

## 一、项目概述

**项目名称**：plusluo-site
**品牌名称**：序员先生
**项目路径**：`/Users/plusluo/Documents/code/plusluo-site`
**项目性质**：基于 Hugo 静态站点生成器的**个人博客网站**
**站点地址**：`https://plusluo.site/`
**GitHub 仓库**：`git@github.com:plusluo/plusluo-site.git`
**Hugo 主题**：[Bilberry Hugo Theme v4](https://github.com/Lednerb/bilberry-hugo-theme)（通过 git submodule 引入）

### 站点信息

- **站点标题**: 序员先生
- **副标题**: 探索 AI · 记录技术 · 分享生活
- **头像**: `/static/images/avatar.jpg`（卡通头像，主题自动圆形蒙版）
- **作者**: plusluo
- **邮箱**: plusluo@gmail.com

### 联系方式与社交链接

| 平台 | 链接 | 图标 |
|------|------|------|
| GitHub | https://github.com/plusluo | `fab fa-github` |
| 邮箱 | plusluo@gmail.com | `fas fa-envelope` |
| 知乎 | https://www.zhihu.com/people/plusluo | `fab fa-zhihu` |
| 微信公众号 | 序员先生 | `fab fa-weixin` |

---

## 二、规划目标

### 阶段一：工程规范化与云端同步 ✅ 已完成
1. ✅ `.gitignore` 配置完成（排除 public/、resources/、.hugo_build.lock）
2. ✅ GitHub 远程仓库已配置（SSH: `git@github.com:plusluo/plusluo-site.git`）
3. ✅ 站点标题改为"序员先生"
4. ✅ 头像图片已配置（customImage）
5. ✅ 社交链接已添加（GitHub、邮箱、知乎、微信公众号）
6. ✅ 关于页面已更新（含微信公众号二维码）
7. ✅ Archetype 模板已扩展（含 author、tags、categories、icon 等字段）

### 阶段二：首页性能优化 ✅ 已完成
1. ✅ 图片懒加载（`layouts/partials/featured-image.html` → `loading="lazy"`）
2. ✅ JS 异步加载（`layouts/partials/js.html` → `defer`）
3. ✅ 关闭 Moment.js（`enableMomentJs = false`，减少约 262KB JS）
4. ✅ 关键资源预加载（`layouts/partials/hooks/head-end.html`）

### 阶段三：GitHub Actions 自动化部署 ✅ 已完成
1. ✅ `.github/workflows/deploy.yml` 工作流配置
2. ✅ `static/CNAME` 自定义域名配置（plusluo.site）
3. 🔲 待操作：在 GitHub 创建仓库后首次 push
4. 🔲 待操作：GitHub 仓库设置中配置 Custom Domain 和 HTTPS

### 阶段四：OpenClaw 自动化内容搬运 ✅ 已完成
1. ✅ `scripts/migrate.py` 核心搬运脚本
2. ✅ `scripts/migrate_config.yaml` 搬运配置文件
3. ✅ `scripts/openclaw_task.md` OpenClaw 任务说明文档
4. ✅ `.migration-log.json` 搬运状态记录
5. 🔲 待操作：在云端服务器部署搬运脚本和 cron 定时任务

---

## 三、与 plusluo_doc 项目的关系

### plusluo_doc（知识库 / 素材仓库）
- **路径**：`/Users/plusluo/Documents/code/plusluo_doc`
- **性质**：个人技术调研文档和知识库，非公开发布

### 自动化搬运机制

```
plusluo_doc/my-kb/
  ├── articles/      → article/code 类型
  ├── knowledge/     → 拆分为 status/article
  ├── work/          → code/article 类型
  ├── diary/         → ❌ 排除（私人日记）
  └── excerpts/      → 待未来纳入

  ──migrate.py──→  plusluo-site/content/
                     ├── article/   文章类
                     ├── code/      技术类
                     └── status/    短笔记
```

### 搬运脚本使用

```bash
# 正常搬运
python3 scripts/migrate.py --source /path/to/my-kb --target .

# 试运行
python3 scripts/migrate.py --source /path/to/my-kb --target . --dry-run
```

---

## 四、内容分类与图标映射

OpenClaw 搬运文章时根据内容自动选择分类和图标：

| 分类 | 图标（FA 6） | 匹配关键词 |
|------|-------------|-----------|
| 投资理财 | `fa-chart-line` | 投资、理财、股票、基金、价值投资 |
| 读书笔记 | `fa-book-open` | 读书、书评、阅读、读后感 |
| 心理学与认知 | `fa-brain` | 心理、认知、人性、社会学 |
| 物理学 | `fa-atom` | 物理、量子、相对论、力学 |
| 生物学 | `fa-dna` | 生物、基因、进化、细胞 |
| 汽车知识 | `fa-car` | 汽车、驾驶、新能源、电车 |
| 个人成长 | `fa-seedling` | 成长、自律、习惯、复盘 |
| 软件研发 | `fa-code` | 编程、开发、软件、代码 |
| AI 技术 | `fa-robot` | AI、大模型、Agent、LLM |
| 碎碎念 | `fa-comment-dots` | 随想、感悟、日常、生活 |

---

## 五、当前站点技术架构

### 主题：Bilberry Hugo Theme v4
- 安装方式：`git submodule`
- 子模块路径：`themes/bilberry-hugo-theme`
- 主题入口：`bilberry-hugo-theme/v4`

### Layouts Override（性能优化）

| 覆盖文件 | 优化内容 |
|---------|---------|
| `layouts/partials/featured-image.html` | 图片 `loading="lazy"` |
| `layouts/partials/js.html` | Script `defer` |
| `layouts/partials/hooks/head-end.html` | 字体 preload、DNS prefetch |

### 支持的 10 种内容类型

| # | 类型 | 目录 | 默认图标 | 卡片特点 |
|---|------|------|---------|---------|
| 1 | **article** | `content/article/` | fa-pencil-alt | 标准文章 |
| 2 | **code** | `content/code/` | fa-code | 代码教程 |
| 3 | **audio** | `content/audio/` | fa-music | 音频嵌入 |
| 4 | **video** | `content/video/` | fa-video | 视频嵌入 |
| 5 | **gallery** | `content/gallery/` | fa-camera | 图片轮播 |
| 6 | **picture** | `content/picture/` | fa-camera | 单张图片 |
| 7 | **link** | `content/link/` | fa-link | 外部链接 |
| 8 | **quote** | `content/quote/` | fa-quote-right | 名言引用 |
| 9 | **status** | `content/status/` | fa-comment | 短动态 |
| 10 | **page** | `content/page/` | fa-file | 导航页面 |

### 系列文章支持
- 使用 Hugo 内置 `series` taxonomy（已配置）
- 文章 front matter 中 `series: ["系列名称"]` 即可归入系列
- `/series/` 页面显示所有系列列表

---

## 六、目录结构

```
plusluo-site/
├── .gitignore                          ← Git 忽略规则
├── .gitmodules                         ← Git Submodule 配置
├── .migration-log.json                 ← 搬运状态记录
├── .github/workflows/deploy.yml        ← GitHub Actions 部署工作流
├── hugo.toml                           ← Hugo 主配置文件
├── archetypes/default.md               ← 内容模板（含图标映射注释）
├── layouts/                            ← Layouts Override（性能优化）
│   └── partials/
│       ├── featured-image.html         ← 图片懒加载
│       ├── js.html                     ← JS defer
│       └── hooks/head-end.html         ← 资源预加载
├── content/                            ← 博客内容
│   ├── article/ code/ audio/ video/
│   ├── gallery/ picture/ link/ quote/
│   ├── status/ page/
│   └── archive.md
├── static/
│   ├── images/avatar.jpg               ← 站点头像
│   └── CNAME                           ← GitHub Pages 域名
├── scripts/
│   ├── migrate.py                      ← 内容搬运脚本
│   ├── migrate_config.yaml             ← 搬运配置
│   └── openclaw_task.md                ← OpenClaw 任务说明
├── themes/bilberry-hugo-theme/         ← 主题（Git Submodule）
├── public/                             ← Hugo 构建输出（已 gitignore）
└── resources/                          ← Hugo 资源缓存（已 gitignore）
```

---

## 七、常用操作命令

```bash
# 进入项目目录
cd /Users/plusluo/Documents/code/plusluo-site

# 本地预览（带热重载）
hugo server --disableFastRender -p 1313

# 构建生产版本
hugo --minify

# 新建文章
hugo new article/my-new-post/index.md
hugo new code/my-tutorial/index.md
hugo new status/my-thought.md

# 运行搬运脚本（试运行）
python3 scripts/migrate.py --source ../plusluo_doc/my-kb --target . --dry-run

# 运行搬运脚本（正式搬运）
python3 scripts/migrate.py --source ../plusluo_doc/my-kb --target .

# 更新主题
cd themes/bilberry-hugo-theme && git pull origin master && cd ../..
```

---

## 八、CI/CD 配置

### GitHub Actions 工作流

- **文件**: `.github/workflows/deploy.yml`
- **触发条件**: push 到 `master` 分支 或 手动触发
- **Hugo 版本**: v0.160.1（extended）
- **流程**: Checkout(含submodule) → Install Hugo → Build(--gc --minify) → Deploy to GitHub Pages
- **部署目标**: GitHub Pages + 自定义域名 `plusluo.site`

### 首次部署待操作
1. 在 GitHub 创建 `plusluo-site` 仓库
2. 首次 `git push -u origin master`
3. GitHub 仓库 Settings → Pages → Source 选 "GitHub Actions"
4. GitHub 仓库 Settings → Pages → Custom domain 填 `plusluo.site`
5. DNS 配置：`plusluo.site` CNAME 指向 `plusluo.github.io`

---

## 九、AI 工作注意事项

1. **所有新建文档默认在头部注明作者 plusluo**
2. **新 git 仓库默认本地根目录为** `/Users/plusluo/Documents/code`
3. **品牌名称为「序员先生」**，站点标题和版权信息已统一
4. **plusluo_doc** 是私有知识库，**plusluo-site** 是公开博客
5. 主题为 **Bilberry Hugo Theme v4**（git submodule 方式），不要回退
6. 所有定制通过 **layouts override** 机制，不直接修改 `themes/` 下的文件
7. Hugo 配置文件为 `hugo.toml`（非 config.toml）
8. 文章 front matter 中 `icon` 字段可自定义气泡图标（参考分类图标映射表）
9. 当前站点内容均为**示例文章**，后续通过搬运脚本替换为真实内容
10. **用户的 TAPD 项目地址**：https://tapd.woa.com/tapd_fe/10121621/story/list
