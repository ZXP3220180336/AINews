# AI News Aggregator

每日AI新闻聚合器，自动爬取前一天AI领域的重要新闻（新模型发布、智能体进展、技术突破等），处理后生成静态网站。

## 功能特性

- **多源爬取**: 支持RSS feeds、API接口、网页抓取
- **智能处理**: 去重、分类、摘要生成（OpenAI GPT）
- **静态网站**: 响应式设计，支持分类、归档、RSS订阅
- **完全自动化**: GitHub Actions每日自动运行并部署到GitHub Pages
- **多语言支持**: 中英文新闻源混合处理

## 数据来源

### 国际来源

- arXiv AI (RSS)
- Google AI Blog (RSS)
- OpenAI Blog (RSS)
- Anthropic Blog (RSS)
- TechCrunch AI (RSS)
- VentureBeat AI (RSS)
- MIT Technology Review AI (RSS)
- Reddit r/MachineLearning (RSS)
- AI Alignment Forum (RSS)

### 中国来源

- 机器之心 (RSS)
- 雷锋网 AI (RSS)
- 知乎 AI 话题 (RSS)
- 开源中国 AI 资讯 (RSS)
- 百度 AI 开发者社区 (RSS)

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据采集       │    │   数据处理       │    │   网站生成       │
│  - RSS爬虫      │───▶│  - 去重         │───▶│  - Jinja2模板   │
│  - API接口      │    │  - 分类         │    │  - 静态文件     │
│  - 网页抓取      │    │  - 摘要生成     │    │  - RSS生成      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
                                                      ▼
                                            ┌─────────────────┐
                                            │   GitHub Pages   │
                                            │  自动部署        │
                                            └─────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -e .
```

### 2. 配置设置

编辑 `src/ainews/config/sources.yaml` 调整数据源：

```yaml
settings:
  max_age_days: 1
  enable_summarization: false  # 设为true以启用OpenAI摘要
  output_dir: "./data/output"
```

### 3. 运行测试

```bash
# 测试模块导入
python test_imports.py

# 运行端到端测试
python test_e2e.py
```

### 4. 手动运行管道

```bash
# 爬取昨天的新闻
python scripts/run_pipeline.py

# 生成网站
python scripts/generate_site.py

# 查看生成的文件
ls -la data/output/
```

## 自动化部署

### GitHub Actions配置

系统已配置每日自动运行的工作流（`.github/workflows/daily-crawl.yml`）：

- **触发时间**: 每天UTC时间8:00
- **执行操作**:
  1. 爬取前一天的AI新闻
  2. 处理文章（去重、分类）
  3. 生成静态网站
  4. 部署到GitHub Pages

### 设置GitHub Pages

1. 推送代码到GitHub仓库
2. 进入仓库 Settings → Pages
3. 设置 Source 为 "GitHub Actions"
4. 工作流将自动部署到 `gh-pages` 分支

### 环境变量（可选）

如需OpenAI摘要功能，在仓库Settings → Secrets → Actions中添加：

- `OPENAI_API_KEY`: 你的OpenAI API密钥

## 输出示例

生成的网站包含：

```
data/output/
├── index.html              # 今日新闻首页
├── about.html              # 关于页面
├── rss.xml                 # RSS订阅
├── archive/                # 历史归档
│   ├── index.html
│   └── 2024-01-15.html
├── categories/             # 分类页面
│   ├── models.html
│   ├── research.html
│   └── index.html
└── static/                 # 静态资源
    ├── css/style.css
    └── js/main.js
```

## 项目结构

```
ainews/
├── src/ainews/
│   ├── crawler/           # 爬虫模块
│   │   ├── base.py        # 基础爬虫类
│   │   └── rss_crawler.py # RSS爬虫
│   ├── processor/         # 处理模块
│   │   ├── deduplicator.py # 去重
│   │   ├── categorizer.py # 分类
│   │   └── summarizer.py  # OpenAI摘要
│   ├── generator/         # 网站生成
│   │   ├── site_generator.py
│   │   ├── templates/     # Jinja2模板
│   │   └── static/        # 静态文件
│   ├── storage/           # 数据存储
│   │   └── database.py    # JSON文件存储
│   ├── models.py          # 数据模型
│   └── config/            # 配置
│       ├── __init__.py
│       └── sources.yaml   # 源配置
├── scripts/               # 可执行脚本
│   ├── run_pipeline.py   # 主管道
│   └── generate_site.py  # 网站生成
├── .github/workflows/     # GitHub Actions
│   └── daily-crawl.yml   # 每日自动运行
└── pyproject.toml        # 项目依赖
```

## 自定义配置

### 添加新数据源

编辑 `src/ainews/config/sources.yaml`，添加新源：

```yaml
- name: "Your Source Name"
  url: "https://example.com/feed.xml"
  type: "rss"  # 或 "api"、"web"
  enabled: true
  priority: 3  # 1-5，越高越重要
  category: "research"  # models, agents, research, business, tools, ethics, policy, other
```

### 修改网站样式

编辑模板文件：
- `src/ainews/generator/templates/base.html` - 基础布局
- `src/ainews/generator/templates/index.html` - 首页模板
- `src/ainews/generator/static/css/style.css` - 自定义样式

### 调整处理逻辑

- **去重阈值**: 修改 `src/ainews/processor/deduplicator.py`
- **分类规则**: 修改 `src/ainews/processor/categorizer.py`
- **摘要提示**: 修改 `src/ainews/processor/summarizer.py`

## 故障排除

### 常见问题

1. **模块导入失败**
   ```
   pip install -e .
   ```

2. **OpenAI API错误**
   - 确保API密钥正确
   - 或在配置中禁用摘要生成

3. **GitHub Pages未更新**
   - 检查Actions运行状态
   - 确认仓库Settings中Pages已启用

4. **RSS源无法解析**
   - 检查源URL是否有效
   - 查看日志中的解析错误

### 日志查看

所有模块使用loguru记录日志：

```python
from loguru import logger
logger.info("Processing started")
```

## 成本估算

- **OpenAI API**: 每日约$0.05-$0.20（10篇文章，GPT-3.5-Turbo）
- **GitHub Actions**: 免费额度内完全免费
- **GitHub Pages**: 完全免费

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

1. Fork仓库
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 致谢

- 所有新闻来源提供者
- OpenAI GPT API
- Jinja2模板引擎
- Tailwind CSS
- GitHub Actions & Pages