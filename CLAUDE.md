# AI News Aggregator - Project Documentation

## Overview

这是一个基于Python的AI新闻聚合器，每日自动爬取AI领域（机器学习、人工智能）的最新新闻，处理后生成静态网站并部署到GitHub Pages。

**核心价值**：自动化AI新闻收集、处理和展示，提供每日AI领域动态摘要。

## 主要功能

1. **多源新闻爬取** - 从15+个国际和中文RSS源收集AI新闻
   - 国际源：arXiv AI, Google AI Blog, OpenAI Blog, Anthropic Blog, TechCrunch AI等
   - 中文源：机器之心、雷锋网、知乎AI话题、开源中国等
2. **智能处理流水线**：
   - 去重：基于文本相似度识别重复文章
   - 分类：自动分类为models, agents, research, business, tools, ethics, policy, other
   - 摘要生成：可选OpenAI GPT模型自动生成文章摘要
3. **静态网站生成**：
   - 响应式设计，支持移动端
   - 包含首页、分类页面、归档、RSS订阅
   - 使用Jinja2模板引擎
4. **完全自动化**：
   - GitHub Actions每日UTC 8:00自动运行
   - 自动部署到GitHub Pages
   - 失败通知机制

## 技术栈

- **语言**: Python 3.14+
- **核心依赖**:
  - 爬虫: httpx, beautifulsoup4, feedparser, lxml
  - 处理: pandas, scikit-learn, sentence-transformers
  - AI: openai (可选，用于摘要生成)
  - 网站: jinja2, markdown
  - 工具: python-dateutil, loguru, pyyaml
- **部署**: GitHub Actions, GitHub Pages

## 项目结构

```
ainews/
├── src/ainews/                    # 主代码目录
│   ├── config/                    # 配置文件
│   │   ├── __init__.py
│   │   └── sources.yaml          # 新闻源配置（关键文件）
│   ├── crawler/                  # 爬虫模块
│   │   ├── base.py              # 基础爬虫类
│   │   └── rss_crawler.py       # RSS爬虫实现
│   ├── processor/                # 处理模块
│   │   ├── deduplicator.py      # 去重逻辑
│   │   ├── categorizer.py       # 分类逻辑
│   │   └── summarizer.py        # OpenAI摘要生成
│   ├── generator/                # 网站生成
│   │   ├── site_generator.py    # 网站生成器
│   │   ├── templates/           # Jinja2模板
│   │   └── static/              # CSS/JS静态文件
│   ├── storage/                  # 数据存储
│   │   └── database.py          # JSON文件存储
│   ├── models.py                # 数据模型定义（Article, CrawlSource等）
│   └── __init__.py
├── scripts/                      # 可执行脚本
│   ├── run_pipeline.py          # 主处理流水线
│   └── generate_site.py         # 网站生成脚本
├── .github/workflows/           # CI/CD配置
│   └── daily-crawl.yml          # 每日自动运行工作流（关键）
├── pyproject.toml              # 项目依赖和配置
├── README.md                   # 用户文档
└── CLAUDE.md                  # 本项目文档
```

## 关键文件

1. **[src/ainews/config/sources.yaml](src/ainews/config/sources.yaml)** - 新闻源配置，可添加/禁用来源
2. **[pyproject.toml](pyproject.toml)** - 项目依赖和Python配置
3. **[.github/workflows/daily-crawl.yml](.github/workflows/daily-crawl.yml)** - 自动化工作流配置
4. **[scripts/run_pipeline.py](scripts/run_pipeline.py)** - 主处理流水线
5. **[scripts/generate_site.py](scripts/generate_site.py)** - 网站生成脚本

## 数据流

```
RSS源 → 爬取 → Article对象 → 去重 → 分类 → (可选)摘要生成 → 存储为JSON → 网站生成 → 静态HTML → GitHub Pages
```

## 开发指南

### 运行环境

```bash
# 创建虚拟环境
python -m venv .venv

# Windows激活
.venv\Scripts\activate

# 安装依赖
pip install -e .
```

### 测试

```bash
# 测试导入
python test_imports.py

# 端到端测试（不依赖网络）
python test_e2e.py
```

### 手动运行

```bash
# 爬取昨天新闻
python scripts/run_pipeline.py

# 生成网站
python scripts/generate_site.py

# 查看输出
ls -la data/output/
```

### 添加新数据源

编辑 [src/ainews/config/sources.yaml](src/ainews/config/sources.yaml):

```yaml
- name: "New Source"
  url: "https://example.com/feed.xml"
  type: "rss"  # 或 "api"、"web"
  enabled: true
  priority: 3  # 1-5，越高越重要
  category: "research"
```

### 配置选项

- `enable_summarization`: 是否使用OpenAI生成摘要（需要API密钥）
- `max_age_days`: 爬取文章的最大天数（默认1天）
- `output_dir`: 输出目录

## 部署配置

### GitHub Pages设置

1. 仓库Settings → Pages → Source选择"GitHub Actions"
2. 工作流自动部署到`gh-pages`分支

### 环境变量（可选）

如需OpenAI摘要功能，在仓库Settings → Secrets → Actions中添加：

- `OPENAI_API_KEY`: OpenAI API密钥

### 定时任务

- 每日UTC 8:00自动运行
- 可通过`workflow_dispatch`手动触发

## 维护要点

### 常见问题

1. **模块导入失败**：运行`pip install -e .`
2. **GitHub Pages未更新**：检查Actions运行状态，确认Pages已启用
3. **RSS源失效**：检查[sources.yaml](src/ainews/config/sources.yaml)中的URL

### 日志查看

所有模块使用loguru记录日志，可在控制台查看处理进度。

### 成本估算

- OpenAI API：每日约$0.05-$0.20（10篇文章，GPT-3.5-Turbo）
- GitHub Actions：免费额度内完全免费
- GitHub Pages：完全免费

## 扩展建议

### 待实现功能

1. **API爬虫**：支持Hacker News API（目前配置中已定义但未实现）
2. **网页抓取**：对于无RSS的网站实现动态爬取
3. **多语言处理**：更好的中英文混合处理
4. **个性化推荐**：基于用户兴趣的文章推荐
5. **邮件订阅**：每日新闻摘要邮件推送

### 性能优化

- 增量爬取：只爬取新文章
- 缓存机制：减少重复网络请求
- 并行处理：多源并发爬取

## 项目状态

- ✅ 基础架构完成
- ✅ RSS爬虫实现
- ✅ 处理流水线
- ✅ 静态网站生成
- ✅ GitHub Actions自动化
- ⚠️ OpenAI摘要功能（可选，需要API密钥）
- ⚠️ API爬虫（待实现）

## 相关链接

- [README.md](README.md) - 用户使用文档
- [test_e2e.py](test_e2e.py) - 端到端测试
- [test_imports.py](test_imports.py) - 导入测试

---
*最后更新：2026-04-19*
*维护者：AI News Aggregator项目*