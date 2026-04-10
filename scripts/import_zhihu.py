#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作者: plusluo

知乎文章导入脚本
从浏览器保存的知乎 HTML 文件中提取文章数据，转换为 Hugo 博客格式。

功能:
  - 解析 HTML 中的 js-initialData JSON 提取文章元数据
  - HTML 正文转 Markdown（保留格式、处理知乎特有元素）
  - 下载文章图片到本地 Page Bundle 目录
  - 自动分类、打标签、生成 Front Matter
  - 根据图片数量自动选择内容类型（article 或 gallery）
  - 创建 Hugo Page Bundle（content/{article|gallery}/{slug}/index.md）

依赖: Python 3 标准库（无额外依赖）
"""

import os
import re
import sys
import json
import logging
import unicodedata
import urllib.request
import urllib.error
import ssl
import html as html_module
from pathlib import Path
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser

# ============================================================
# 常量与日志配置
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONTENT_DIR_ARTICLE = PROJECT_ROOT / "content" / "article"
CONTENT_DIR_GALLERY = PROJECT_ROOT / "content" / "gallery"
CST = timezone(timedelta(hours=8))

# 图片尺寸阈值：小于此大小(字节)的图片视为 icon，不计入正式图片
IMG_SIZE_THRESHOLD = 5000  # 5KB

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("import_zhihu")

# ============================================================
# 分类与图标映射（与 migrate_config.yaml 保持一致）
# ============================================================
CATEGORY_ICON_MAPPING = {
    "投资理财": {
        "icon": "fa-chart-line",
        "keywords": ["投资", "理财", "股票", "基金", "价值投资", "市场", "交易",
                      "财务", "金融", "复利", "黄金", "红利", "低波", "利率",
                      "看盘", "亏损", "收益", "指数", "底仓", "银行"],
    },
    "读书笔记": {
        "icon": "fa-book-open",
        "keywords": ["读书", "书评", "阅读", "读后感", "书摘", "推荐书",
                      "书单", "纸质书", "电子书"],
    },
    "心理学与认知": {
        "icon": "fa-brain",
        "keywords": ["心理", "认知", "人性", "社会学", "行为", "情绪", "思维",
                      "偏见", "决策", "注意力", "记忆力", "碎片化"],
    },
    "汽车知识": {
        "icon": "fa-car",
        "keywords": ["汽车", "车", "驾驶", "发动机", "新能源", "电车",
                      "电动车", "增程", "内饰"],
    },
    "个人成长": {
        "icon": "fa-seedling",
        "keywords": ["成长", "自律", "习惯", "复盘", "反思", "目标", "规划",
                      "效率", "方法论", "面试"],
    },
    "软件研发": {
        "icon": "fa-code",
        "keywords": ["编程", "开发", "软件", "代码", "工程", "前端", "后端",
                      "微服务", "DevOps", "研发", "码农", "程序员", "团队"],
    },
    "AI 技术": {
        "icon": "fa-robot",
        "keywords": ["AI", "人工智能", "大模型", "Agent", "LLM", "GPT",
                      "机器学习", "深度学习", "RAG", "Prompt", "信息论",
                      "客户端", "APP", "取代"],
    },
    "碎碎念": {
        "icon": "fa-comment-dots",
        "keywords": ["随想", "感悟", "日常", "生活", "吐槽", "闲聊", "杂谈"],
    },
}


# ============================================================
# 工具函数（复用 migrate.py 的逻辑）
# ============================================================
def slugify(text: str, max_len: int = 60) -> str:
    """将中文/英文标题转换为 URL-friendly slug。"""
    text = re.sub(r"[#*_`\[\]()]", "", text).strip()
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text)
    text = re.sub(r"-+", "-", text).strip("-").lower()
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "untitled"


def infer_category_and_icon(title: str, content: str) -> tuple:
    """根据标题和正文推断分类和图标。"""
    check_text = (title + " " + content[:2000]).lower()

    best_cat = "碎碎念"
    best_score = 0
    best_icon = "fa-comment-dots"

    for cat_name, cat_info in CATEGORY_ICON_MAPPING.items():
        keywords = cat_info.get("keywords", [])
        score = 0
        for kw in keywords:
            if kw.lower() in check_text:
                score += 2
        if score > best_score:
            best_score = score
            best_cat = cat_name
            best_icon = cat_info.get("icon", "fa-pencil-alt")

    return best_cat, best_icon


def generate_tags(title: str, content: str, category: str, topics: list) -> list:
    """根据内容生成标签。"""
    tags = set()

    # 从知乎话题标签提取
    for topic in topics:
        name = topic.get("name", "")
        if name:
            tags.add(name)

    # 如果话题标签不足，从分类关键词中补充
    if len(tags) < 3:
        check_text = (title + " " + content[:2000]).lower()
        for cat_name, cat_info in CATEGORY_ICON_MAPPING.items():
            for kw in cat_info.get("keywords", []):
                if kw.lower() in check_text and len(tags) < 6:
                    tags.add(kw)

    # 确保至少有分类作为标签
    if not tags:
        tags.add(category)

    return sorted(list(tags))


# ============================================================
# HTML 转 Markdown 转换器
# ============================================================
class ZhihuHTMLToMarkdown(HTMLParser):
    """将知乎文章 HTML 转换为 Markdown 格式。"""

    def __init__(self):
        super().__init__()
        self.output = []
        self.current_text = []
        self.tag_stack = []
        self.list_stack = []  # ('ul' or 'ol', counter)
        self.in_code_block = False
        self.code_block_content = []
        self.in_blockquote = False
        self.blockquote_lines = []
        self.in_figure = False
        self.figure_img_src = ""
        self.figure_caption = ""
        self.in_figcaption = False
        self.skip_content = False
        self.link_href = ""
        self.in_link = False
        self.link_text = []
        self.images = []  # 收集所有图片 URL

    def _flush_text(self):
        text = "".join(self.current_text)
        self.current_text = []
        return text

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        tag_lower = tag.lower()

        if tag_lower in ('script', 'style', 'noscript'):
            self.skip_content = True
            return

        # 跳过知乎特有的 LinkCard 等
        cls = attrs_dict.get("class", "")
        if "LinkCard" in cls or "video-box" in cls:
            self.skip_content = True
            return

        self.tag_stack.append(tag_lower)

        if tag_lower == 'p':
            self._flush_text()

        elif tag_lower in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._flush_text()
            level = int(tag_lower[1])
            # 知乎文章的 h2 映射为 ##，h3 映射为 ### 等
            self.current_text.append("\n" + "#" * level + " ")

        elif tag_lower in ('strong', 'b'):
            self.current_text.append("**")

        elif tag_lower in ('em', 'i'):
            self.current_text.append("*")

        elif tag_lower == 'blockquote':
            self._flush_text()
            self.in_blockquote = True
            self.blockquote_lines = []

        elif tag_lower == 'ul':
            self._flush_text()
            self.list_stack.append(('ul', 0))

        elif tag_lower == 'ol':
            self._flush_text()
            self.list_stack.append(('ol', 0))

        elif tag_lower == 'li':
            self._flush_text()
            if self.list_stack:
                list_type, counter = self.list_stack[-1]
                indent = "  " * (len(self.list_stack) - 1)
                if list_type == 'ol':
                    counter += 1
                    self.list_stack[-1] = ('ol', counter)
                    self.current_text.append(f"{indent}{counter}. ")
                else:
                    self.current_text.append(f"{indent}- ")

        elif tag_lower == 'pre':
            self._flush_text()
            self.in_code_block = True
            self.code_block_content = []

        elif tag_lower == 'code' and not self.in_code_block:
            self.current_text.append("`")

        elif tag_lower == 'figure':
            self._flush_text()
            self.in_figure = True
            self.figure_img_src = ""
            self.figure_caption = ""

        elif tag_lower == 'figcaption':
            self.in_figcaption = True

        elif tag_lower == 'img':
            # 获取图片 URL（优先 data-original / data-actualsrc）
            src = (attrs_dict.get("data-original")
                   or attrs_dict.get("data-actualsrc")
                   or attrs_dict.get("src", ""))
            if src and 'zhimg.com' in src:
                self.images.append(src)
                if self.in_figure:
                    self.figure_img_src = src
                else:
                    # 独立的 img 标签
                    self.current_text.append(f"\n![](<<IMG:{src}>>)\n")

        elif tag_lower == 'a':
            href = attrs_dict.get("href", "")
            self.link_href = href
            self.in_link = True
            self.link_text = []

        elif tag_lower == 'br':
            self.current_text.append("\n")

        elif tag_lower == 'hr':
            self._flush_text()
            self.output.append("\n---\n")

        elif tag_lower == 'sup':
            self.current_text.append("<sup>")

        elif tag_lower == 'sub':
            self.current_text.append("<sub>")

    def handle_endtag(self, tag):
        tag_lower = tag.lower()

        if tag_lower in ('script', 'style', 'noscript'):
            self.skip_content = False
            return

        # 结束 LinkCard/video-box 跳过
        cls_tag = self.tag_stack[-1] if self.tag_stack else ""
        if self.skip_content and tag_lower in ('div', 'a', 'span'):
            # 简单处理：当关闭标签时检查是否需要恢复
            # 由于无法精确追踪嵌套层级，在发现非跳过标签时恢复
            pass

        if self.tag_stack and self.tag_stack[-1] == tag_lower:
            self.tag_stack.pop()

        if tag_lower == 'p':
            text = self._flush_text().strip()
            if text:
                if self.in_blockquote:
                    self.blockquote_lines.append(text)
                else:
                    self.output.append(text + "\n\n")

        elif tag_lower in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            text = self._flush_text().strip()
            if text:
                self.output.append(text + "\n\n")

        elif tag_lower in ('strong', 'b'):
            self.current_text.append("**")

        elif tag_lower in ('em', 'i'):
            self.current_text.append("*")

        elif tag_lower == 'blockquote':
            self.in_blockquote = False
            if self.blockquote_lines:
                quoted = "\n> ".join(self.blockquote_lines)
                self.output.append(f"> {quoted}\n\n")
            self.blockquote_lines = []

        elif tag_lower in ('ul', 'ol'):
            text = self._flush_text().strip()
            if text:
                self.output.append(text + "\n")
            if self.list_stack:
                self.list_stack.pop()
            if not self.list_stack:
                self.output.append("\n")

        elif tag_lower == 'li':
            text = self._flush_text().strip()
            if text:
                if self.in_blockquote:
                    self.blockquote_lines.append(text)
                else:
                    self.output.append(text + "\n")

        elif tag_lower == 'pre':
            self.in_code_block = False
            code = "".join(self.code_block_content)
            # 尝试检测代码语言
            self.output.append(f"\n```\n{code}\n```\n\n")
            self.code_block_content = []

        elif tag_lower == 'code' and not self.in_code_block:
            self.current_text.append("`")

        elif tag_lower == 'figcaption':
            self.in_figcaption = False
            self.figure_caption = self._flush_text().strip()

        elif tag_lower == 'figure':
            self.in_figure = False
            if self.figure_img_src:
                caption = self.figure_caption or ""
                self.output.append(
                    f"\n![{caption}](<<IMG:{self.figure_img_src}>>)\n\n"
                )
            self.figure_img_src = ""
            self.figure_caption = ""

        elif tag_lower == 'a':
            self.in_link = False
            link_text = "".join(self.link_text).strip()
            if link_text and self.link_href:
                href = self.link_href
                # 处理知乎站内链接
                if href.startswith("//link.zhihu.com"):
                    # 提取实际 URL
                    m = re.search(r'target=([^&]+)', href)
                    if m:
                        href = urllib.request.unquote(m.group(1))
                    else:
                        href = "https:" + href
                elif href.startswith("//"):
                    href = "https:" + href
                self.current_text.append(f"[{link_text}]({href})")
            elif link_text:
                self.current_text.append(link_text)
            self.link_text = []
            self.link_href = ""

        elif tag_lower == 'sup':
            self.current_text.append("</sup>")

        elif tag_lower == 'sub':
            self.current_text.append("</sub>")

    def handle_data(self, data):
        if self.skip_content:
            return

        if self.in_code_block:
            self.code_block_content.append(data)
            return

        if self.in_figcaption:
            self.current_text.append(data)
            return

        if self.in_link:
            self.link_text.append(data)
            return

        self.current_text.append(data)

    def handle_entityref(self, name):
        char = html_module.unescape(f"&{name};")
        if self.in_code_block:
            self.code_block_content.append(char)
        elif self.in_link:
            self.link_text.append(char)
        else:
            self.current_text.append(char)

    def handle_charref(self, name):
        char = html_module.unescape(f"&#{name};")
        if self.in_code_block:
            self.code_block_content.append(char)
        elif self.in_link:
            self.link_text.append(char)
        else:
            self.current_text.append(char)

    def get_markdown(self) -> str:
        """获取转换后的 Markdown 文本。"""
        # flush remaining text
        text = self._flush_text().strip()
        if text:
            self.output.append(text + "\n")

        result = "".join(self.output)
        # 清理多余空行
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip()


def html_to_markdown(html_content: str) -> tuple:
    """
    将知乎 HTML 正文转换为 Markdown。
    返回 (markdown_text, image_urls_list)
    """
    # 先解码 HTML 实体
    html_content = html_module.unescape(html_content)

    converter = ZhihuHTMLToMarkdown()
    try:
        converter.feed(html_content)
    except Exception as e:
        log.warning(f"HTML 解析警告: {e}")

    markdown = converter.get_markdown()
    images = converter.images

    return markdown, images


# ============================================================
# 图片下载
# ============================================================
def download_image(url: str, target_dir: Path, idx: int = 0) -> str:
    """
    下载图片到本地。
    返回本地文件名，失败返回 None。
    """
    # 提取文件名
    url_clean = url.split("?")[0]
    filename = url_clean.split("/")[-1]
    if not filename:
        filename = f"img_{idx}.jpg"

    # 确保文件扩展名
    if "." not in filename:
        filename += ".jpg"

    target_path = target_dir / filename
    # 避免重名
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        for i in range(1, 100):
            new_name = f"{stem}_{i}{suffix}"
            target_path = target_dir / new_name
            if not target_path.exists():
                filename = new_name
                break

    try:
        # 设置 SSL 上下文（忽略证书验证，防止 CDN 证书问题）
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
        req.add_header("Referer", "https://zhuanlan.zhihu.com/")

        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            data = resp.read()
            with open(target_path, "wb") as f:
                f.write(data)
            log.info(f"    ✅ 下载图片: {filename} ({len(data) // 1024}KB)")
            return filename

    except Exception as e:
        log.warning(f"    ⚠️ 下载图片失败: {url} → {e}")
        return None


# ============================================================
# HTML 文件解析
# ============================================================
def parse_zhihu_html(filepath: Path) -> dict:
    """
    解析知乎保存的 HTML 文件，提取文章数据。
    返回 {title, created, content_html, url, topics, excerpt} 或 None
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # 提取原始 URL
    url_match = re.search(r"saved from url=\(\d+\)(https?://[^\s)\"<>]+)", raw)
    original_url = url_match.group(1).rstrip(" ->") if url_match else ""

    # 提取 js-initialData JSON
    json_match = re.search(
        r'<script id="js-initialData" type="text/json">(.*?)</script>',
        raw, re.DOTALL
    )
    if not json_match:
        log.error(f"  ❌ 未找到 js-initialData: {filepath.name}")
        return None

    try:
        data = json.loads(json_match.group(1))
    except json.JSONDecodeError as e:
        log.error(f"  ❌ JSON 解析失败: {filepath.name} → {e}")
        return None

    # 从 entities.articles 中提取文章数据
    articles = data.get("initialState", {}).get("entities", {}).get("articles", {})
    if not articles:
        log.error(f"  ❌ 未找到文章数据: {filepath.name}")
        return None

    # 取第一篇（每个页面只有一篇文章）
    article_id, article = next(iter(articles.items()))

    title = article.get("title", "").strip()
    created = article.get("created", 0)
    content_html = article.get("content", "")
    excerpt = article.get("excerpt", "")
    topics = article.get("topics", [])

    if not title:
        # 回退：从 og:title 提取
        og_match = re.search(r'og:title"\s+content="([^"]+)"', raw)
        title = og_match.group(1) if og_match else filepath.stem

    return {
        "title": title,
        "created": created,
        "content_html": content_html,
        "url": original_url or f"https://zhuanlan.zhihu.com/p/{article_id}",
        "topics": topics,
        "excerpt": excerpt,
        "article_id": article_id,
    }


# ============================================================
# 文章导入主函数
# ============================================================
def import_article(filepath: Path, dry_run: bool = False) -> bool:
    """
    导入单篇知乎文章。
    返回是否成功。
    """
    log.info(f"📄 处理: {filepath.name}")

    # 1. 解析 HTML
    article = parse_zhihu_html(filepath)
    if not article:
        return False

    title = article["title"]
    created_ts = article["created"]
    content_html = article["content_html"]
    topics = article["topics"]

    # 2. 转换时间戳
    if created_ts:
        dt = datetime.fromtimestamp(created_ts, tz=CST)
    else:
        dt = datetime.now(tz=CST)
    date_str = dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")

    log.info(f"  标题: {title}")
    log.info(f"  发布时间: {dt.strftime('%Y-%m-%d %H:%M')}")

    # 3. HTML 转 Markdown
    markdown, image_urls = html_to_markdown(content_html)

    # 4. 推断分类和图标
    category, icon = infer_category_and_icon(title, markdown)

    # 5. 生成标签
    tags = generate_tags(title, markdown, category, topics)

    # 6. 生成 slug
    slug = slugify(title)

    log.info(f"  分类: {category} | 图标: {icon}")
    log.info(f"  标签: {tags}")
    log.info(f"  slug: {slug}")
    log.info(f"  图片数: {len(image_urls)}")

    if dry_run:
        content_type = "gallery" if len(image_urls) >= 2 else "article"
        log.info(f"  [DRY RUN] 将写入 content/{content_type}/{slug}/")
        return True

    # 7. 下载图片到临时列表，统计正式图片数量
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    img_map = {}  # original_url -> local_filename
    img_sizes = {}  # local_filename -> file_size
    for idx, img_url in enumerate(image_urls):
        if img_url in img_map:
            continue
        local_name = download_image(img_url, temp_dir, idx)
        if local_name:
            img_map[img_url] = local_name
            img_sizes[local_name] = (temp_dir / local_name).stat().st_size
        else:
            img_map[img_url] = None

    # 统计正式图片数（排除小于阈值的 icon 类图片）
    real_img_count = sum(
        1 for name, size in img_sizes.items()
        if name and size >= IMG_SIZE_THRESHOLD
    )
    first_real_img = None
    for name, size in img_sizes.items():
        if name and size >= IMG_SIZE_THRESHOLD:
            first_real_img = name
            break

    # 8. 根据图片数量选择内容类型
    if real_img_count >= 2:
        content_type = "gallery"
        content_dir = CONTENT_DIR_GALLERY
    else:
        content_type = "article"
        content_dir = CONTENT_DIR_ARTICLE

    log.info(f"  内容类型: {content_type} (正式图片: {real_img_count})")

    # 9. 创建 Page Bundle 目录并移动图片
    bundle_dir = content_dir / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)

    import shutil
    for orig_url, local_name in img_map.items():
        if local_name:
            src = temp_dir / local_name
            dst = bundle_dir / local_name
            shutil.move(str(src), str(dst))

    # 清理临时目录
    shutil.rmtree(str(temp_dir), ignore_errors=True)

    # 10. 为单图 article 创建 featuredImage 封面
    if content_type == "article" and first_real_img:
        src_img = bundle_dir / first_real_img
        feat_img = bundle_dir / f"featuredImage{Path(first_real_img).suffix}"
        if src_img.exists():
            shutil.copy2(str(src_img), str(feat_img))
            log.info(f"    📷 封面图: {feat_img.name}")

    # 替换 Markdown 中的图片占位符
    for orig_url, local_name in img_map.items():
        placeholder = f"<<IMG:{orig_url}>>"
        if local_name:
            markdown = markdown.replace(placeholder, local_name)
        else:
            markdown = markdown.replace(placeholder, orig_url)

    # 11. 插入 <!--more--> 分隔符
    markdown = insert_more_separator(markdown)

    # 12. 生成摘要（在图片替换之后，确保摘要中没有占位符）
    plain_text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", markdown)  # 去掉图片语法
    plain_text = re.sub(r"[#*`\[\]()!>-]", "", plain_text)
    plain_text = re.sub(r"\s+", " ", plain_text).strip()
    summary = plain_text[:150].strip()
    if len(plain_text) > 150:
        summary += "..."

    # 13. 生成 Front Matter
    tags_str = ", ".join('"' + t + '"' for t in tags)
    safe_summary = summary.replace('"', '\\"')
    safe_title = title.replace('"', '\\"')
    fm_lines = [
        "---",
        "# 作者: plusluo",
        f'title: "{safe_title}"',
        f"date: {date_str}",
        f'categories: ["{category}"]',
        f"tags: [{tags_str}]",
        'author: "plusluo"',
        "toc: true",
        f'icon: "{icon}"',
        f'summary: "{safe_summary}"',
        f'zhihu_url: "{article["url"]}"',
    ]
    # gallery 类型添加 imageSlider 参数
    if content_type == "gallery":
        fm_lines.append("imageSlider: true")
    fm_lines.append("---")
    frontmatter = "\n".join(fm_lines)

    # 14. 写入 index.md
    index_path = bundle_dir / "index.md"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"{frontmatter}\n\n{markdown}\n")

    log.info(f"  ✅ 导入完成 → content/{content_type}/{slug}/")
    return True


def insert_more_separator(markdown: str) -> str:
    """在正文适当位置插入 <!--more--> 分隔符。"""
    lines = markdown.split("\n")
    # 找到第 2-3 个非空段落后的位置
    paragraph_count = 0
    insert_pos = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            if paragraph_count >= 2:
                insert_pos = i
                break
        elif not stripped.startswith("#") and not stripped.startswith("!"):
            paragraph_count += 1

    if insert_pos > 0:
        lines.insert(insert_pos, "\n<!--more-->\n")
        return "\n".join(lines)

    return markdown


# ============================================================
# 主流程
# ============================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="知乎文章导入脚本 — 将浏览器保存的知乎 HTML 文件转换为 Hugo 博客文章",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际写入文件",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 扫描知乎 HTML 文件
    html_files = sorted(SCRIPT_DIR.glob("*知乎.html"))

    if not html_files:
        log.error("❌ 未找到知乎 HTML 文件（scripts/*知乎.html）")
        sys.exit(1)

    log.info(f"📦 找到 {len(html_files)} 个知乎 HTML 文件")
    log.info(f"📂 文章目录: {CONTENT_DIR_ARTICLE}")
    log.info(f"📂 图库目录: {CONTENT_DIR_GALLERY}")

    if args.dry_run:
        log.info("🔍 预览模式 — 不写入文件\n")

    success = 0
    failed = 0

    for html_file in html_files:
        try:
            if import_article(html_file, dry_run=args.dry_run):
                success += 1
            else:
                failed += 1
        except Exception as e:
            log.error(f"  ❌ 处理失败: {html_file.name} → {e}")
            failed += 1
        print()  # 空行分隔

    log.info("=" * 50)
    log.info(f"📊 导入完成: 成功 {success} 篇, 失败 {failed} 篇")
    if not args.dry_run:
        log.info(f"📂 文章目录: {CONTENT_DIR_ARTICLE}")
        log.info(f"📂 图库目录: {CONTENT_DIR_GALLERY}")
    log.info("✨ 全部完成")


if __name__ == "__main__":
    main()
