# plusluo-site 博客内容管理规则

> 本规则在打开 plusluo-site 工作空间时自动加载，指导 AI 助手在添加、编辑博客文章时遵循统一规范。

---

## 一、文章 Front Matter 规范

每篇新文章的 front matter **必须**包含以下字段：

```yaml
---
# 作者: plusluo
title: "文章标题"
date: 2026-04-10T17:00:00+08:00
categories: ["分类名称"]
tags: ["标签1", "标签2", "标签3"]
author: "plusluo"
toc: true
icon: "fa-对应图标"
summary: "文章摘要，约100-200字"
---
```

### 字段格式要求

| 字段 | 格式 | 说明 |
|------|------|------|
| `# 作者: plusluo` | YAML 注释 | **第一行必须是此注释**，不可省略 |
| `title` | `"双引号字符串"` | 使用原始标题，不做英文转换 |
| `date` | `YYYY-MM-DDTHH:MM:SS+08:00` | ISO 8601 格式，**必须带东八区时区** |
| `categories` | `["分类"]` | 从下方 10 个分类中选择，可多选 |
| `tags` | `["标签1", "标签2"]` | 2-6 个标签，与内容相关 |
| `author` | `"plusluo"` | 固定值 |
| `toc` | `true` / `false` | article/code/gallery 用 `true`，status 用 `false` |
| `icon` | `"fa-xxx"` | 必须与 categories 主分类对应，见下方映射表 |
| `summary` | `"双引号字符串"` | 100-200 字摘要，用于首页卡片显示 |
| `draft` | 布尔值 | 已发布文章**不加此字段**；草稿才加 `draft: true` |

### 可选字段（导入文章时使用）

```yaml
zhihu_url: "https://zhuanlan.zhihu.com/p/xxx"    # 知乎原文链接
wechat_url: "https://mp.weixin.qq.com/s/xxx"     # 微信公众号原文链接
imageSlider: true                                  # gallery 类型专用
series: ["系列名称"]                                # 系列文章归组
```

---

## 二、分类与图标映射（10 个分类）

| 分类 | icon | 匹配关键词 |
|------|------|-----------|
| 投资理财 | `fa-chart-line` | 投资、理财、股票、基金、价值投资、红利、黄金 |
| 读书笔记 | `fa-book-open` | 读书、书评、阅读、读后感 |
| 心理学与认知 | `fa-brain` | 心理、认知、人性、社会学、决策、思维 |
| 物理学 | `fa-atom` | 物理、量子、相对论、力学 |
| 生物学 | `fa-dna` | 生物、基因、进化、细胞 |
| 汽车知识 | `fa-car` | 汽车、驾驶、新能源、电车 |
| 个人成长 | `fa-seedling` | 成长、自律、习惯、复盘 |
| 软件研发 | `fa-code` | 编程、开发、软件、代码、架构 |
| AI 技术 | `fa-robot` | AI、大模型、Agent、LLM |
| 碎碎念 | `fa-comment-dots` | 随想、感悟、日常、生活 |

一篇文章可属于多个分类，`icon` 取主分类对应的图标。

---

## 三、日期规则（重要）

| 来源 | date 取值 | 附加字段 |
|------|----------|---------|
| 微信公众号导入 | **公众号上的原始发布时间** | `wechat_url` |
| 知乎导入 | **知乎原始发布时间** | `zhihu_url` |
| 新写原创 | 当前时间 | 无 |

时区一律 `+08:00`。**绝不使用导入时间替代原始发布时间。**

---

## 四、目录结构（Page Bundle）

```
content/{type}/{slug}/
  ├── index.md          # 文章正文
  ├── image1.jpg        # 图片与 index.md 同目录
  └── ...
```

- slug 命名：中文用拼音/关键词缩写，英文用 kebab-case，用 `-` 连接
- 图片引用：**必须用相对路径** `![描述](filename.jpg)`

### 内容类型

| 类型 | 目录 | 用途 |
|------|------|------|
| article | `content/article/` | 标准文章（最常用） |
| gallery | `content/gallery/` | 多图文章（≥3 张图，加 `imageSlider: true`） |
| code | `content/code/` | 代码教程 |
| status | `content/status/` | 短动态/碎碎念 |
| page | `content/page/` | 导航页面 |

---

## 五、正文格式

1. **摘要分隔符**：正文前 2-3 段后**必须**插入 `<!--more-->`，其前内容为首页预览
2. **图片**：放在 Page Bundle 同目录，用相对路径引用
3. **所有新文档头部注明作者 plusluo**（即 YAML 注释 `# 作者: plusluo`）
4. **品牌名称「序员先生」**，在版权、关于等处使用
5. **不直接修改 `themes/` 下的文件**，通过 `layouts/` override

---

*规则文件由建站个性化要求汇总而成，仅保留动态内容管理所需规则。*
