# daily-arXiv-ai-enhanced

> [!CAUTION]
> **中文**：请确保你在所在法域合规使用学术数据与 AI 生成内容。  
> **English**: Ensure compliant use of academic data and AI-generated content in your jurisdiction.

一个基于 **GitHub Actions + GitHub Pages** 的 arXiv 自动追踪系统。  
An automated arXiv tracking system powered by **GitHub Actions + GitHub Pages**.

- 每日抓取指定分类论文并生成 AI 结构化摘要  
  Daily crawl for selected categories with AI-structured summaries
- 自动产出日报、周报、月报（含趋势与词云）  
  Auto-generated daily/weekly/monthly reports (with trend analysis and wordclouds)
- 前端纯静态部署，支持偏好高亮、日期范围筛选、可选访问密码  
  Static frontend with preference highlighting, date-range filtering, and optional password protection

---

## 功能概览 | Features

1. **Daily Pipeline（日更）**
   - 抓取 arXiv 新论文（分类可配置）  
     Crawl new arXiv papers (configurable categories)
   - 去重（对比最近 7 天）  
     Deduplicate against recent 7 days
   - LLM 结构化增强（TLDR / Motivation / Method / Result / Conclusion）  
     LLM enhancement with structured fields
   - 生成 Markdown 与 JSONL 数据并发布到 Pages  
     Generate Markdown + JSONL and publish via Pages

2. **Weekly Report（周报）**
   - MapReduce 思路提取主题、聚合热点并生成周度分析  
     MapReduce-style topic extraction and weekly trend summary

3. **Monthly Report（月报）**
   - 汇总月度数据，生成趋势综述与词云  
     Monthly trend review with wordcloud visualization

4. **Reading Experience（阅读体验）**
   - 本地存储关键词/作者偏好并高亮  
     Local keyword/author preferences with highlighting
   - 单日/区间日期浏览  
     Single-date and date-range browsing
   - 可选密码访问控制与邮件通知  
     Optional password protection and email notification

---

## 工作原理 | How It Works

### 1) 数据与处理流程 | Data & Processing Flow

`arXiv -> raw JSONL -> dedup -> AI enhancement -> Markdown/Reports -> Git commit -> GitHub Pages`

对应实现 / Implementation mapping:
- 抓取 / Crawl: `daily_arxiv/daily_arxiv/spiders/arxiv.py`
- 去重 / Dedup: `daily_arxiv/daily_arxiv/check_stats.py`
- AI 增强 / AI enhancement: `ai/enhance.py`
- 日报转换 / Daily markdown conversion: `to_md/convert.py`
- 周报 / Weekly summary: `ai/weekly_summary.py`
- 月报 / Monthly summary: `ai/monthly_summary.py`

### 2) 自动化工作流 | GitHub Actions Workflows

- `.github/workflows/run.yml`：每日主流程（抓取 -> 去重 -> AI -> 转换 -> 提交 -> 推送 -> 可选邮件）
- `.github/workflows/weekly.yml`：每周自动生成周报
- `.github/workflows/monthly.yml`：每月自动生成月报和词云
- `.github/workflows/test-email.yml`：手动测试邮件发送

### 3) 前端读取机制 | Frontend Delivery

- 页面从 `data/` 读取 JSONL/Markdown
- 从 `assets/file-list.txt` 与 `assets/reports-list.json` 获取可用日期与报告列表
- 在浏览器侧完成筛选、高亮、展示（无需后端）

---

## 快速开始 | Quick Start

1. **Fork 仓库** / Fork this repository
2. 在 `Settings -> Secrets and variables -> Actions` 配置 Secrets 与 Variables  
   Configure required Secrets and Variables
3. 在 Actions 中手动运行 `arXiv-daily-ai-enhanced` 验证流程  
   Run `arXiv-daily-ai-enhanced` manually once
4. 在 `Settings -> Pages` 启用 Pages（`main` / root）  
   Enable GitHub Pages (`main` / root)

---

## 必需配置 | Required Configuration

### Secrets

| Name | 说明 / Description |
|---|---|
| `OPENAI_API_KEY` | LLM API Key |
| `OPENAI_BASE_URL` | LLM Base URL |
| `ACCESS_PASSWORD` *(optional)* | 站点访问密码（可选）/ Optional site password |

### Variables

| Name | 说明 / Description |
|---|---|
| `CATEGORIES` | arXiv 分类，如 `cs.CL,cs.CV` |
| `LANGUAGE` | 输出语言，如 `Chinese` / `English` |
| `MODEL_NAME` | 模型名，如 `deepseek-chat` |
| `EMAIL` | Git 提交邮箱 |
| `NAME` | Git 提交用户名 |
| `GITHUB_PAGES_URL` *(optional)* | 邮件中使用的站点完整 URL（可选） |

---

## 邮件通知（可选）| Email Notification (Optional)

再配置以下 Secrets 可启用每日邮件推送：  
Add the following Secrets to enable daily email notifications:

- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- `EMAIL_SENDER`, `EMAIL_RECIPIENTS`

可选 Variable：`GITHUB_PAGES_URL`（邮件中展示的站点完整链接）  
Optional variable: `GITHUB_PAGES_URL` (full site URL used in email links)

---

## 自定义建议 | Customization

- 调整分类：改 `CATEGORIES`  
  Change categories via `CATEGORIES`
- 切换语言：改 `LANGUAGE`  
  Switch output language via `LANGUAGE`
- 更换模型：改 `MODEL_NAME`  
  Change model via `MODEL_NAME`
- 调整调度：编辑 `.github/workflows/*.yml` 中 cron  
  Adjust schedules by editing cron in `.github/workflows/*.yml`

---

## 许可 | License

Apache-2.0
