#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作者: plusluo

plusluo-site 内容搬运脚本
从 plusluo_doc 知识库自动扫描、转换、搬运内容到 plusluo-site Hugo 博客

功能:
  - 扫描 my-kb/ 全目录（排除 diary/）
  - 自动判定内容类型（code / article / status）
  - 解析并转换 front matter
  - 拆分 knowledge/ 聚合笔记为独立条目
  - 创建 Hugo Page Bundle 并处理图片路径
  - 记录搬运状态，防止重复搬运
  - 自动 git commit + push

依赖: Python 3 标准库（无额外依赖）
"""

import os
import re
import sys
import json
import shutil
import hashlib
import logging
import subprocess
import unicodedata
from pathlib import Path
from datetime import datetime, timezone, timedelta

try:
    import yaml
except ImportError:
    yaml = None

# ============================================================
# 常量与日志配置
# ============================================================
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "migrate_config.yaml"
CST = timezone(timedelta(hours=8))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("migrate")


# ============================================================
# 配置加载（支持 YAML 或内嵌默认值）
# ============================================================
# 内嵌默认配置（当 PyYAML 不可用时使用）
DEFAULT_CONFIG = {
    "paths": {
        "source_root": "../plusluo_doc/my-kb",
        "target_root": "..",
        "migration_log": ".migration-log.json",
    },
    "exclude": {
        "directories": ["diary"],
        "file_patterns": [
            "_draft_*",
            "INDEX.md",
            "work-kb-index.md",
            "文档目录概要.md",
        ],
        "min_file_size": 200,
        "min_content_chars": 300,
    },
    "type_rules": {
        "code_block_ratio_threshold": 0.20,
        "status_max_chars": 500,
        "article_min_chars": 800,
        "tech_keywords": [
            "架构", "方案", "技术", "CLI", "API", "MCP", "Setup",
            "研究", "部署", "配置", "源码", "框架", "引擎", "算法",
            "SDK", "协议", "调试", "性能",
        ],
        "directory_type_mapping": {
            "articles/文章": "article",
            "articles/AI生成文章": "article",
            "articles/首页": "page",
            "articles/联系我": "page",
            "articles/Github": "page",
            "knowledge/AI编码/OpenClaw全流程分析": "code",
            "work": "code",
        },
    },
    "knowledge_split": {
        "separator_pattern": r"(?:^|\n)---\s*\n###\s+",
        "date_pattern": r">\s*记录于\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)",
        "wikilink_pattern": r"\[\[([^\]]+)\]\]",
    },
    "category_icon_mapping": {
        "投资理财": {"icon": "fa-chart-line"},
        "读书笔记": {"icon": "fa-book-open"},
        "心理学与认知": {"icon": "fa-brain"},
        "物理学": {"icon": "fa-atom"},
        "生物学": {"icon": "fa-dna"},
        "汽车知识": {"icon": "fa-car"},
        "个人成长": {"icon": "fa-seedling"},
        "软件研发": {"icon": "fa-code"},
        "AI 技术": {"icon": "fa-robot"},
        "碎碎念": {"icon": "fa-comment-dots"},
    },
    "frontmatter": {
        "default_author": "plusluo",
        "timezone": "+08:00",
        "strip_fields": ["source", "url", "weight", "bookCollapseSection",
                         "bookFlatSection", "bookToc"],
        "toc_for_article": True,
        "toc_for_code": True,
        "toc_for_status": False,
    },
    "git": {
        "auto_commit": True,
        "commit_message_template": "content: migrate {count} articles from plusluo_doc ({date})",
        "auto_pull": True,
    },
}


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """加载配置文件，如果 YAML 不可用则使用内嵌默认配置。"""
    if yaml and config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
            log.info(f"已加载配置: {config_path}")
            return cfg
    log.info("使用内嵌默认配置")
    return DEFAULT_CONFIG


# ============================================================
# 工具函数
# ============================================================
def slugify(text: str, max_len: int = 60) -> str:
    """将中文/英文标题转换为 URL-friendly slug。"""
    # 去除 Markdown 格式标记
    text = re.sub(r"[#*_`\[\]()]", "", text).strip()
    # 规范化 unicode
    text = unicodedata.normalize("NFKD", text)
    # 替换空格和特殊字符为连字符
    text = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text)
    text = re.sub(r"-+", "-", text).strip("-").lower()
    # 截断
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "untitled"


def file_hash(filepath: Path) -> str:
    """计算文件的 SHA256 hash。"""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()[:16]}"


def content_hash(text: str) -> str:
    """计算文本内容的 SHA256 hash。"""
    h = hashlib.sha256(text.encode("utf-8"))
    return f"sha256:{h.hexdigest()[:16]}"


def count_chars(text: str) -> int:
    """统计正文字符数（排除空白和 Markdown 标记）。"""
    # 去除代码块
    clean = re.sub(r"```[\s\S]*?```", "", text)
    # 去除 front matter
    clean = re.sub(r"^---[\s\S]*?---\s*", "", clean)
    # 去除 HTML 标签
    clean = re.sub(r"<[^>]+>", "", clean)
    # 去除 Markdown 图片和链接语法
    clean = re.sub(r"!\[.*?\]\(.*?\)", "", clean)
    clean = re.sub(r"\[.*?\]\(.*?\)", "", clean)
    # 去除空白
    clean = re.sub(r"\s+", "", clean)
    return len(clean)


def code_block_ratio(text: str) -> float:
    """计算代码块占比（代码行数 / 总行数）。"""
    lines = text.split("\n")
    total = len(lines)
    if total == 0:
        return 0.0
    in_code = False
    code_lines = 0
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            code_lines += 1
    return code_lines / total


# ============================================================
# Front Matter 解析与生成
# ============================================================
def parse_frontmatter(content: str) -> tuple:
    """
    解析 Markdown 文件的 front matter。
    返回 (metadata_dict, body_text)。
    """
    # YAML front matter: ---\n...\n---
    yaml_match = re.match(r"^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)", content)
    if yaml_match:
        meta_str = yaml_match.group(1)
        body = yaml_match.group(2)
        meta = _parse_yaml_simple(meta_str)
        return meta, body

    # TOML front matter: +++\n...\n+++
    toml_match = re.match(r"^\+\+\+\s*\n([\s\S]*?)\n\+\+\+\s*\n?([\s\S]*)", content)
    if toml_match:
        meta_str = toml_match.group(1)
        body = toml_match.group(2)
        meta = _parse_toml_simple(meta_str)
        return meta, body

    return {}, content


def _parse_yaml_simple(text: str) -> dict:
    """简单的 YAML 解析（不依赖 PyYAML 库）。"""
    if yaml:
        try:
            return yaml.safe_load(text) or {}
        except Exception:
            pass

    result = {}
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # 去除引号
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            # 简单列表解析 [a, b, c]
            if val.startswith("[") and val.endswith("]"):
                items = val[1:-1].split(",")
                val = [i.strip().strip("\"'") for i in items if i.strip()]
            # 布尔值
            elif val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            result[key] = val
    return result


def _parse_toml_simple(text: str) -> dict:
    """简单的 TOML 解析。"""
    result = {}
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            elif val.lower() == "true":
                val = True
            elif val.lower() == "false":
                val = False
            result[key] = val
    return result


def generate_frontmatter(meta: dict, content_type: str, config: dict) -> str:
    """生成符合 Bilberry 主题的 Hugo front matter（YAML 格式）。"""
    fm_cfg = config.get("frontmatter", {})
    strip_fields = fm_cfg.get("strip_fields", [])

    # 清理不需要的字段
    for field in strip_fields:
        meta.pop(field, None)

    # 确保必填字段
    if "author" not in meta:
        meta["author"] = fm_cfg.get("default_author", "plusluo")

    # 确保 date 带时区
    if "date" in meta:
        date_str = str(meta["date"])
        if "T" not in date_str:
            date_str = f"{date_str}T00:00:00{fm_cfg.get('timezone', '+08:00')}"
        elif "+" not in date_str and "Z" not in date_str:
            date_str = f"{date_str}{fm_cfg.get('timezone', '+08:00')}"
        meta["date"] = date_str

    # TOC 设置
    if content_type == "article":
        meta.setdefault("toc", fm_cfg.get("toc_for_article", True))
    elif content_type == "code":
        meta.setdefault("toc", fm_cfg.get("toc_for_code", True))
    elif content_type == "status":
        meta.pop("toc", None)

    # 确保 draft 为 false
    meta["draft"] = False

    # 排序输出
    lines = ["---"]
    # 优先字段
    priority = ["title", "date", "author", "categories", "tags", "icon",
                "series", "summary", "toc", "draft"]
    for key in priority:
        if key in meta:
            lines.append(_yaml_line(key, meta[key]))
    # 其余字段
    for key, val in meta.items():
        if key not in priority:
            lines.append(_yaml_line(key, val))
    lines.append("---")
    return "\n".join(lines)


def _yaml_line(key: str, val) -> str:
    """将 key-value 转为 YAML 行。"""
    if isinstance(val, bool):
        return f"{key}: {'true' if val else 'false'}"
    elif isinstance(val, list):
        items = ", ".join(f'"{v}"' for v in val)
        return f"{key}: [{items}]"
    elif isinstance(val, str):
        # 含特殊字符时加引号
        if any(c in val for c in ":{}[]&*?|>!%@`#,"):
            return f'{key}: "{val}"'
        return f"{key}: {val}"
    else:
        return f"{key}: {val}"


# ============================================================
# 内容类型判定
# ============================================================
def determine_content_type(
    source_path: Path,
    source_root: Path,
    content: str,
    title: str,
    config: dict,
) -> str:
    """
    根据内容特征判定 Hugo 内容类型。
    返回 "code" / "article" / "status" / "page"
    """
    rules = config.get("type_rules", {})
    rel_path = str(source_path.relative_to(source_root))

    # 优先检查目录映射
    dir_mapping = rules.get("directory_type_mapping", {})
    for dir_prefix, mapped_type in sorted(dir_mapping.items(), key=lambda x: -len(x[0])):
        if rel_path.startswith(dir_prefix):
            default_type = mapped_type
            break
    else:
        default_type = "article"

    # page 类型直接返回
    if default_type == "page":
        return "page"

    # 代码块占比检查
    ratio = code_block_ratio(content)
    threshold = rules.get("code_block_ratio_threshold", 0.20)
    if ratio > threshold:
        return "code"

    # 技术关键词检查
    tech_kw = rules.get("tech_keywords", [])
    check_text = (title + " " + content[:500]).lower()
    tech_hits = sum(1 for kw in tech_kw if kw.lower() in check_text)
    if tech_hits >= 3 and default_type == "code":
        return "code"

    # 字数判定（仅当默认不是 code 时）
    char_count = count_chars(content)
    status_max = rules.get("status_max_chars", 500)
    article_min = rules.get("article_min_chars", 800)

    if char_count < status_max:
        return "status"
    elif char_count >= article_min:
        return default_type  # 保持目录映射的类型
    else:
        return default_type

    return default_type


# ============================================================
# 分类与图标推断
# ============================================================
def infer_category_and_icon(
    title: str,
    content: str,
    source_path: Path,
    config: dict,
) -> tuple:
    """
    根据内容推断最佳分类和对应图标。
    返回 (category_name, icon_class)
    """
    mapping = config.get("category_icon_mapping", {})
    check_text = (title + " " + content[:1000]).lower()

    best_cat = "碎碎念"
    best_score = 0
    best_icon = "fa-comment-dots"

    # 源目录名也纳入匹配
    dir_name = source_path.parent.name.lower()

    for cat_name, cat_info in mapping.items():
        keywords = cat_info.get("keywords", [])
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in check_text:
                score += 2
            if kw_lower in dir_name:
                score += 3  # 目录名匹配权重更高
        if score > best_score:
            best_score = score
            best_cat = cat_name
            best_icon = cat_info.get("icon", "fa-pencil-alt")

    return best_cat, best_icon


# ============================================================
# 图片路径处理
# ============================================================
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def process_images(
    content: str,
    source_file: Path,
    target_dir: Path,
) -> tuple:
    """
    处理 Markdown 中的图片引用。
    - 复制图片到 Page Bundle 目录
    - 修正路径为相对引用
    - 返回 (modified_content, first_image_name_or_None)
    """
    first_image = None
    source_dir = source_file.parent

    def replace_image(match):
        nonlocal first_image
        alt = match.group(1)
        img_path_str = match.group(2)

        # 跳过外部 URL
        if img_path_str.startswith(("http://", "https://", "//")):
            return match.group(0)

        # 解析图片绝对路径
        if img_path_str.startswith("/"):
            # 绝对路径（相对于 source_root）
            img_abs = Path(img_path_str)
        else:
            # 相对路径
            img_abs = (source_dir / img_path_str).resolve()

        if not img_abs.exists():
            log.warning(f"  图片不存在，跳过: {img_abs}")
            return match.group(0)

        # 复制图片到目标目录
        img_name = img_abs.name
        target_img = target_dir / img_name
        try:
            shutil.copy2(img_abs, target_img)
            log.info(f"  复制图片: {img_name}")
        except Exception as e:
            log.error(f"  复制图片失败: {e}")
            return match.group(0)

        # 记录第一张图片
        if first_image is None:
            first_image = img_name

        return f"![{alt}]({img_name})"

    modified = IMAGE_PATTERN.sub(replace_image, content)
    return modified, first_image


# ============================================================
# knowledge/ 聚合笔记拆分
# ============================================================
def split_knowledge_file(
    filepath: Path,
    content: str,
    config: dict,
) -> list:
    """
    拆分 knowledge/ 下的聚合笔记文件为独立条目。
    返回 [{title, body, date, source_key}, ...]
    """
    ks_cfg = config.get("knowledge_split", {})
    sep_pattern = ks_cfg.get("separator_pattern", r"(?:^|\n)---\s*\n###\s+")
    date_pattern = ks_cfg.get("date_pattern", r">\s*记录于\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?)")
    wikilink_pattern = ks_cfg.get("wikilink_pattern", r"\[\[([^\]]+)\]\]")

    entries = []

    # 先尝试按 ### 分割
    parts = re.split(r"\n(?=###\s+)", content)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 提取标题
        title_match = re.match(r"###\s+(.+?)(?:\n|$)", part)
        if title_match:
            title = title_match.group(1).strip()
            body = part[title_match.end():].strip()
        else:
            # 没有 ### 标题，跳过（可能是文件头部描述）
            continue

        # 去除分隔线
        body = re.sub(r"^---\s*$", "", body, flags=re.MULTILINE).strip()

        # 提取日期
        date_match = re.search(date_pattern, body)
        entry_date = None
        if date_match:
            date_str = date_match.group(1).strip()
            entry_date = date_str
            # 从正文中移除日期行
            body = body[:date_match.start()] + body[date_match.end():]
            body = body.strip()

        # 替换 [[双链]] 语法
        body = re.sub(wikilink_pattern, r"\1", body)

        # 跳过空内容
        if count_chars(body) < 50:
            continue

        source_key = f"{filepath}#{title}"
        entries.append({
            "title": title[:50],  # 截断到 50 字
            "body": body,
            "date": entry_date,
            "source_key": source_key,
        })

    return entries


# ============================================================
# 搬运记录管理
# ============================================================
class MigrationLog:
    """管理 .migration-log.json 搬运状态记录。"""

    def __init__(self, log_path: Path):
        self.path = log_path
        self.data = {"migrated": []}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except json.JSONDecodeError:
                log.warning("搬运记录文件损坏，将重新创建")
                self.data = {"migrated": []}

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def is_migrated(self, source_key: str) -> bool:
        """检查是否已搬运。"""
        return any(m["source"] == source_key for m in self.data["migrated"])

    def record(self, source: str, target: str, content_type: str, hash_val: str):
        """记录搬运。"""
        self.data["migrated"].append({
            "source": source,
            "target": target,
            "type": content_type,
            "hash": hash_val,
            "date": datetime.now(CST).strftime("%Y-%m-%d"),
        })


# ============================================================
# 核心搬运逻辑
# ============================================================
def create_page_bundle(
    target_root: Path,
    content_type: str,
    slug: str,
    frontmatter_str: str,
    body: str,
    source_file: Path = None,
    has_images: bool = False,
) -> Path:
    """
    创建 Hugo Page Bundle。
    返回创建的 index.md 路径。
    """
    bundle_dir = target_root / "content" / content_type / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)

    index_path = bundle_dir / "index.md"
    full_content = f"{frontmatter_str}\n\n{body}\n"

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(full_content)

    log.info(f"  创建 Page Bundle: content/{content_type}/{slug}/")
    return bundle_dir


def migrate_single_file(
    source_file: Path,
    source_root: Path,
    target_root: Path,
    config: dict,
    migration_log: MigrationLog,
) -> bool:
    """
    搬运单个 Markdown 文件。
    返回是否成功搬运。
    """
    rel_path = str(source_file.relative_to(source_root))
    log.info(f"处理: {rel_path}")

    # 检查是否已搬运
    if migration_log.is_migrated(rel_path):
        log.info(f"  已搬运，跳过")
        return False

    # 读取文件
    try:
        content = source_file.read_text(encoding="utf-8")
    except Exception as e:
        log.error(f"  读取失败: {e}")
        return False

    # 检查文件大小
    min_size = config.get("exclude", {}).get("min_file_size", 200)
    if source_file.stat().st_size < min_size:
        log.info(f"  文件太小（{source_file.stat().st_size}B），跳过")
        return False

    # 解析 front matter
    meta, body = parse_frontmatter(content)

    # 检查正文长度
    min_chars = config.get("exclude", {}).get("min_content_chars", 300)
    char_count = count_chars(body)
    if char_count < min_chars:
        log.info(f"  正文太短（{char_count}字），跳过")
        return False

    # 提取标题
    title = meta.get("title", "")
    if not title:
        # 从 H1 标题提取
        h1_match = re.match(r"^#\s+(.+)", body, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()
            # 从正文中移除 H1（避免重复）
            body = body[h1_match.end():].strip()
        else:
            title = source_file.stem

    # 判定内容类型
    content_type = determine_content_type(
        source_file, source_root, body, title, config
    )

    # 推断分类和图标
    category, icon = infer_category_and_icon(title, body, source_file, config)

    # 构建 front matter
    meta["title"] = title
    if "date" not in meta:
        # 使用文件修改时间
        mtime = source_file.stat().st_mtime
        meta["date"] = datetime.fromtimestamp(mtime, tz=CST).strftime(
            "%Y-%m-%dT%H:%M:%S+08:00"
        )
    if "categories" not in meta or not meta["categories"]:
        meta["categories"] = [category]
    if "tags" not in meta or not meta["tags"]:
        # 从分类推导一些基础标签
        meta["tags"] = [category]
    meta["icon"] = icon

    # 生成 slug
    slug = slugify(title)

    # 创建 Page Bundle 目录
    bundle_dir = target_root / "content" / content_type / slug
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # 处理图片
    body, first_image = process_images(body, source_file, bundle_dir)

    # 如果有图片，复制第一张作为 featuredImage
    if first_image:
        src_img = bundle_dir / first_image
        feat_ext = Path(first_image).suffix
        feat_img = bundle_dir / f"featuredImage{feat_ext}"
        if src_img.exists() and not feat_img.exists():
            shutil.copy2(src_img, feat_img)
            log.info(f"  设置封面图: featuredImage{feat_ext}")

    # 替换 [[双链]] 语法
    wl_pattern = config.get("knowledge_split", {}).get(
        "wikilink_pattern", r"\[\[([^\]]+)\]\]"
    )
    body = re.sub(wl_pattern, r"\1", body)

    # 生成 front matter 字符串
    fm_str = generate_frontmatter(meta, content_type, config)

    # 写入 index.md
    index_path = bundle_dir / "index.md"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"{fm_str}\n\n{body}\n")

    # 记录搬运
    migration_log.record(
        source=rel_path,
        target=f"content/{content_type}/{slug}/",
        content_type=content_type,
        hash_val=file_hash(source_file),
    )

    log.info(f"  ✅ 搬运完成 → {content_type}/{slug}/ ({char_count}字)")
    return True


def migrate_knowledge_file(
    source_file: Path,
    source_root: Path,
    target_root: Path,
    config: dict,
    migration_log: MigrationLog,
) -> int:
    """
    拆分并搬运 knowledge/ 下的聚合笔记文件。
    返回成功搬运的条目数。
    """
    rel_path = str(source_file.relative_to(source_root))
    log.info(f"拆分笔记: {rel_path}")

    content = source_file.read_text(encoding="utf-8")
    entries = split_knowledge_file(source_file, content, config)

    if not entries:
        log.info(f"  无可拆分条目，跳过")
        return 0

    migrated_count = 0
    for entry in entries:
        source_key = entry["source_key"]

        if migration_log.is_migrated(source_key):
            continue

        title = entry["title"]
        body = entry["body"]
        char_count = count_chars(body)

        # 判定类型
        status_max = config.get("type_rules", {}).get("status_max_chars", 500)
        article_min = config.get("type_rules", {}).get("article_min_chars", 800)

        if char_count < status_max:
            content_type = "status"
        elif char_count >= article_min:
            content_type = "article"
        else:
            # 中间地带，默认 status
            content_type = "status"

        # 推断分类和图标
        category, icon = infer_category_and_icon(
            title, body, source_file, config
        )

        # 构建 slug（加日期避免冲突）
        date_suffix = entry.get("date", "")
        if date_suffix:
            date_suffix = date_suffix[:10].replace("-", "")
        slug = slugify(f"{title}-{date_suffix}" if date_suffix else title)

        # 构建 front matter
        meta = {
            "title": title,
            "author": config.get("frontmatter", {}).get("default_author", "plusluo"),
            "categories": [category],
            "tags": [category],
            "icon": icon,
            "draft": False,
        }
        if entry.get("date"):
            date_str = entry["date"]
            if len(date_str) == 10:
                date_str = f"{date_str}T00:00:00+08:00"
            else:
                date_str = f"{date_str.replace(' ', 'T')}:00+08:00"
            meta["date"] = date_str
        else:
            meta["date"] = datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00")

        fm_str = generate_frontmatter(meta, content_type, config)

        # 创建 Page Bundle
        bundle_dir = target_root / "content" / content_type / slug
        bundle_dir.mkdir(parents=True, exist_ok=True)

        index_path = bundle_dir / "index.md"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(f"{fm_str}\n\n{body}\n")

        # 记录搬运
        migration_log.record(
            source=source_key,
            target=f"content/{content_type}/{slug}/",
            content_type=content_type,
            hash_val=content_hash(body),
        )

        log.info(f"  ✅ 笔记条目 → {content_type}/{slug}/ ({char_count}字)")
        migrated_count += 1

    return migrated_count


# ============================================================
# 扫描与主流程
# ============================================================
def should_exclude(filepath: Path, source_root: Path, config: dict) -> bool:
    """检查文件是否应被排除。"""
    excl = config.get("exclude", {})

    # 目录排除
    rel = filepath.relative_to(source_root)
    for excl_dir in excl.get("directories", []):
        if str(rel).startswith(excl_dir):
            return True

    # 文件名模式排除
    from fnmatch import fnmatch
    for pattern in excl.get("file_patterns", []):
        if fnmatch(filepath.name, pattern):
            return True

    return False


def is_knowledge_aggregate(filepath: Path, source_root: Path) -> bool:
    """判断文件是否为 knowledge/ 下的聚合笔记。"""
    rel = str(filepath.relative_to(source_root))
    # knowledge/ 下非 AI编码 子目录的文件
    if rel.startswith("knowledge/") and "/AI编码/" not in rel:
        return True
    return False


def scan_and_migrate(
    source_root: Path,
    target_root: Path,
    config: dict,
    dry_run: bool = False,
) -> int:
    """
    扫描源目录并执行搬运。
    返回成功搬运的总数。
    """
    log_path = target_root / config.get("paths", {}).get(
        "migration_log", ".migration-log.json"
    )
    migration_log = MigrationLog(log_path)

    total_migrated = 0

    # 遍历所有 .md 文件
    for md_file in sorted(source_root.rglob("*.md")):
        if should_exclude(md_file, source_root, config):
            continue

        if dry_run:
            rel = str(md_file.relative_to(source_root))
            log.info(f"[DRY RUN] 发现: {rel}")
            total_migrated += 1
            continue

        # knowledge/ 聚合文件需要拆分处理
        if is_knowledge_aggregate(md_file, source_root):
            count = migrate_knowledge_file(
                md_file, source_root, target_root, config, migration_log
            )
            total_migrated += count
        else:
            if migrate_single_file(
                md_file, source_root, target_root, config, migration_log
            ):
                total_migrated += 1

    # 保存搬运记录
    migration_log.save()
    log.info(f"\n📊 搬运完成: 共处理 {total_migrated} 篇内容")

    return total_migrated


def git_operations(target_root: Path, count: int, config: dict):
    """执行 git 操作（add, commit, push）。"""
    git_cfg = config.get("git", {})
    if not git_cfg.get("auto_commit", True):
        return

    if count == 0:
        log.info("无新内容，跳过 git 操作")
        return

    try:
        os.chdir(target_root)

        # git add
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)

        # git commit
        msg_template = git_cfg.get(
            "commit_message_template",
            "content: migrate {count} articles from plusluo_doc ({date})",
        )
        msg = msg_template.format(
            count=count,
            date=datetime.now(CST).strftime("%Y-%m-%d"),
        )
        subprocess.run(
            ["git", "commit", "-m", msg],
            check=True,
            capture_output=True,
        )
        log.info(f"📝 Git commit: {msg}")

        # git push
        result = subprocess.run(
            ["git", "push"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log.info("🚀 Git push 成功")
        else:
            log.warning(f"⚠️ Git push 失败: {result.stderr}")

    except subprocess.CalledProcessError as e:
        log.error(f"Git 操作失败: {e}")
    except Exception as e:
        log.error(f"Git 异常: {e}")


# ============================================================
# CLI 入口
# ============================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="plusluo-site 内容搬运脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 正常搬运
  python migrate.py --source /path/to/plusluo_doc/my-kb --target /path/to/plusluo-site

  # 试运行（不实际写入文件）
  python migrate.py --source /path/to/plusluo_doc/my-kb --target /path/to/plusluo-site --dry-run

  # 使用自定义配置
  python migrate.py --config ./my_config.yaml
        """,
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="知识库源目录路径（覆盖配置文件中的 paths.source_root）",
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="博客目标目录路径（覆盖配置文件中的 paths.target_root）",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG_PATH),
        help="配置文件路径",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="试运行模式，仅输出计划搬运的文件列表",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="跳过 git 操作",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志输出",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 加载配置
    config = load_config(Path(args.config))

    # 确定源和目标路径
    source_root = Path(args.source) if args.source else Path(
        config.get("paths", {}).get("source_root", "../plusluo_doc/my-kb")
    )
    target_root = Path(args.target) if args.target else Path(
        config.get("paths", {}).get("target_root", "..")
    )

    source_root = source_root.resolve()
    target_root = target_root.resolve()

    log.info(f"📂 源目录: {source_root}")
    log.info(f"📂 目标目录: {target_root}")

    # 验证路径
    if not source_root.exists():
        log.error(f"源目录不存在: {source_root}")
        sys.exit(1)
    if not target_root.exists():
        log.error(f"目标目录不存在: {target_root}")
        sys.exit(1)

    # 如果需要，先 git pull
    if config.get("git", {}).get("auto_pull", True) and not args.dry_run:
        try:
            for repo_dir in [source_root, target_root]:
                if (repo_dir / ".git").exists():
                    subprocess.run(
                        ["git", "pull", "--rebase"],
                        cwd=repo_dir,
                        capture_output=True,
                        timeout=30,
                    )
                    log.info(f"📥 Git pull: {repo_dir.name}")
        except Exception as e:
            log.warning(f"Git pull 失败（继续执行）: {e}")

    # 执行搬运
    count = scan_and_migrate(source_root, target_root, config, dry_run=args.dry_run)

    # Git 操作
    if not args.dry_run and not args.no_git:
        git_operations(target_root, count, config)

    log.info("✨ 全部完成")


if __name__ == "__main__":
    main()
