# daily-arXiv-ai-enhanced

> 一个基于 **GitHub Actions + GitHub Pages + LLM** 的 arXiv 自动追踪与智能解读系统。  
> 每日自动抓取、去重、AI 增强、生成日报/周报/月报，并以纯静态站点发布。


---

## 1. 这是什么？解决了什么问题？

这个项目把“**追论文**”拆成一条自动化流水线：

- 自动抓取你关心的 arXiv 分类（如 `cs.CL, cs.CV`）
- 自动去重（避免重复读相同论文）
- 自动生成结构化 AI 摘要（TL;DR / Motivation / Method / Result / Conclusion）
- 自动生成：
  - 每日论文看板（按类别浏览）
  - 每周热点报告（Map-Reduce 风格）
  - 每月趋势综述 + 词云
- 自动发布到 GitHub Pages（无需后端）

---

## 2. 页面效果（图文）

### 论文看板（按分类浏览，支持关键词/作者高亮过滤）

![论文看板](images/ss_papers_keywords.png)

### 论文详情弹窗（含结构化 AI 摘要：TL;DR / Motivation / Method / Result / Conclusion）

![详情弹窗](images/ss_modal_detail.png)

### 日期选择器（支持单日 / 区间模式）

![日期选择器](images/ss_datepicker.png)

### 偏好设置（关键词 + 作者，持久化到 localStorage）

![偏好设置](images/ss_settings.png)

### 周报 / 月报浏览器

![报告浏览](images/ss_reports.png)

---

## 3. 技术原理：功能是如何实现的？

## 3.1 日报主流程（Daily Pipeline）

核心链路：

```text
arXiv 分类页
  -> Scrapy 抓取论文ID
  -> data/YYYY-MM-DD.jsonl
  -> 近7天去重
  -> LLM结构化增强
  -> data/YYYY-MM-DD_AI_enhanced_{LANGUAGE}.jsonl
  -> Markdown日报
  -> 更新索引文件
  -> GitHub Pages 展示
```

对应实现：

- 抓取：`daily_arxiv/daily_arxiv/spiders/arxiv.py`
  - 读取环境变量 `CATEGORIES`
  - 从 `https://arxiv.org/list/<category>/new` 抓取新论文 ID
  - 仅保留目标分类匹配论文
- 去重：`daily_arxiv/daily_arxiv/check_stats.py`
  - 当日数据对比历史 7 天 `id`
  - 删除重复项；若全重复则删除当日文件并停止后续流程
- AI 增强：`ai/enhance.py`
  - 使用 `ChatOpenAI(...).with_structured_output(Structure)`
  - 生成 `tldr/motivation/method/result/conclusion`
  - 包含异常兜底与字段补全，保证输出结构完整
- 日报生成：`to_md/convert.py`
  - 按分类聚合论文
  - 将 AI 字段渲染到 Markdown 模板

---

## 3.2 周报原理（Map-Reduce 思路）

实现文件：`ai/weekly_summary.py`

- **Map 阶段**：分批读取一周论文，提取每篇论文 3~5 个主题词
- **Reduce 阶段**：统计主题词频、统计分类分布
- **总结阶段**：让 LLM 生成周度趋势综述
- 输出：`data/weekly/YYYY-Wxx.md`

这让周报不仅是“论文列表汇总”，而是“**热点主题抽取 + 趋势解释**”。

---

## 3.3 月报原理（趋势分析 + 词云）

实现文件：`ai/monthly_summary.py`

- 汇总目标月份全部论文（自动去除跨日重复 id）
- 计算分类占比、周级演化
- 词云生成：
  - 标题 + TLDR 分词（中文优先 `jieba`）
  - 停用词过滤 + LLM 二次过滤无意义词
  - 输出 `assets/wordcloud-YYYY-MM.png`
- 让 LLM 根据“分类排名 + 每周热点”写月度综述
- 输出：`data/monthly/YYYY-MM.md`

示例词云：

![月度词云示例](assets/wordcloud-2026-03.png)

---

## 3.4 前端展示原理（纯静态，无后端）

核心 JS：

- `js/app.js`：日报主页面（日期选择、分类过滤、关键词/作者高亮、检索）
- `js/statistic.js`：统计页（关键词云、趋势曲线、区间分析）
- `js/settings.js`：偏好设置页（关键词/作者写入 localStorage）
- `js/reports.js`：周报/月报浏览器（读取 Markdown 并渲染）

数据来源：

- 原始/增强数据：`data/*.jsonl`
- 日期索引：`assets/file-list.txt`
- 报告索引：`assets/reports-list.json`

特点：

- 浏览器本地存储偏好（`localStorage`）
- 无数据库、无后端服务，部署成本低

---

## 3.5 自动化工作流（GitHub Actions）

- `.github/workflows/run.yml`：每日主流程（抓取 -> 去重 -> AI -> Markdown -> 更新索引 -> 提交）
- `.github/workflows/weekly.yml`：每周生成周报
- `.github/workflows/monthly.yml`：每月生成月报与词云
- `.github/workflows/test-email.yml`：邮件功能联调

> 调度默认使用 UTC，可按需修改 cron。

---

## 4. 快速开始

1. Fork 本仓库
2. 在 `Settings -> Secrets and variables -> Actions` 配置参数（见下方）
3. 手动运行 `arXiv-daily-ai-enhanced` 工作流，确认生成 `data/*.jsonl` 与日报
4. 在 `Settings -> Pages` 启用 Pages（`main` / root）

---

## 5. 配置说明

### 5.1 必需 Secrets

| Name | 用途 |
|---|---|
| `OPENAI_API_KEY` | LLM API Key |
| `OPENAI_BASE_URL` | LLM Base URL |
| `ACCESS_PASSWORD` *(可选)* | 站点访问密码（配置后启用密码保护） |

### 5.2 必需 Variables

| Name | 用途 |
|---|---|
| `CATEGORIES` | arXiv 分类，如 `cs.CL,cs.CV` |
| `LANGUAGE` | 输出语言，如 `Chinese` / `English` |
| `MODEL_NAME` | 模型名，如 `deepseek-chat` |
| `EMAIL` | Git 提交邮箱 |
| `NAME` | Git 提交用户名 |
| `GITHUB_PAGES_URL` *(可选)* | 邮件内站点 URL |

### 5.3 邮件通知（可选）

如需每日邮件推送，再配置以下 Secrets：

- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- `EMAIL_SENDER`, `EMAIL_RECIPIENTS`

---

## 6. 常见自定义

- 改抓取方向：修改 `CATEGORIES`
- 改摘要语言：修改 `LANGUAGE`
- 改模型：修改 `MODEL_NAME`
- 改执行时间：修改 `.github/workflows/*.yml` 的 `cron`

---

## 7. 仓库结构速览

```text
daily_arxiv/         # 爬虫与去重
ai/                  # AI增强、周报、月报
to_md/               # JSONL -> Markdown
data/                # 每日数据、周报、月报
assets/              # logo、词云、索引文件
images/              # README 页面截图
js/                  # 前端逻辑
.github/workflows/   # 自动化调度
```

---

## 8. 合规与免责声明

请确保你在所在法域内合规使用：

- arXiv 数据
- 第三方 LLM 服务
- AI 生成内容（尤其是公开传播或商用场景）

---

## 9. License

Apache-2.0
