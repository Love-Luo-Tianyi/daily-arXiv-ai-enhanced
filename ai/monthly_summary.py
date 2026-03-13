#!/usr/bin/env python3
"""
每月综述生成脚本 (Trend Analysis)
Monthly Review Generation Script (Trend Analysis)

功能 / Features:
- 读取过去一个月的AI增强JSONL文件 / Read AI-enhanced JSONL files from the past month
- 统计论文总量及分类排序 / Count total papers and rank by category
- 生成词云图 / Generate word cloud image
- 分析每周热点演变 / Analyze weekly hotspot evolution
- 调用大模型撰写领域综述 / Use LLM to write comprehensive trend analysis
- 输出每月综述Markdown文件 / Output monthly review Markdown file to data/monthly/

用法 / Usage:
  python monthly_summary.py [--data_dir ../data] [--output_dir ../data/monthly]
                            [--asset_dir ../assets] [--month YYYY-MM]
"""

import os
import json
import sys
import re
import argparse
import calendar
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict, Tuple

import dotenv
from langchain_openai import ChatOpenAI

if os.path.exists('.env'):
    dotenv.load_dotenv()

# Optional: word cloud generation
try:
    from wordcloud import WordCloud
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False
    print("wordcloud/matplotlib not installed; skipping word cloud generation.", file=sys.stderr)

# Optional: jieba for Chinese word segmentation
try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


# ─────────────────────────── CLI args ───────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Generate monthly arXiv trend analysis")
    parser.add_argument("--data_dir", type=str, default="../data",
                        help="Directory containing daily JSONL files")
    parser.add_argument("--output_dir", type=str, default="../data/monthly",
                        help="Output directory for monthly reports")
    parser.add_argument("--asset_dir", type=str, default="../assets",
                        help="Directory to save generated images (word cloud)")
    parser.add_argument("--month", type=str, default=None,
                        help="Target month YYYY-MM (defaults to last month)")
    return parser.parse_args()


# ─────────────────────────── Date helpers ───────────────────────────

def get_month_dates(month_str: str = None) -> Tuple[List[str], int, int]:
    """Return (list_of_date_strings, year, month) for the target month."""
    if month_str:
        year, month = map(int, month_str.split("-"))
    else:
        today = datetime.utcnow()
        # Last month
        first_of_current = today.replace(day=1)
        last_month_end = first_of_current - timedelta(days=1)
        year, month = last_month_end.year, last_month_end.month

    _, days_in_month = calendar.monthrange(year, month)
    dates = [
        datetime(year, month, d).strftime("%Y-%m-%d")
        for d in range(1, days_in_month + 1)
    ]
    return dates, year, month


def get_week_label(date_str: str) -> str:
    """Return ISO week label for a given date string."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


# ─────────────────────────── Data loading ───────────────────────────

def load_month_papers(data_dir: str, dates: List[str], language: str) -> List[Dict]:
    """Load all papers from AI-enhanced JSONL files for the given month dates."""
    papers = []
    seen_ids: set = set()
    for date in dates:
        ai_file = os.path.join(data_dir, f"{date}_AI_enhanced_{language}.jsonl")
        regular_file = os.path.join(data_dir, f"{date}.jsonl")
        target_file = (ai_file if os.path.exists(ai_file)
                       else regular_file if os.path.exists(regular_file)
                       else None)
        if target_file is None:
            continue
        with open(target_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    paper = json.loads(line)
                    pid = paper.get('id', '')
                    if pid and pid in seen_ids:
                        continue
                    seen_ids.add(pid)
                    paper['_date'] = date
                    papers.append(paper)
                except json.JSONDecodeError:
                    pass
    return papers


# ─────────────────────────── Statistics ───────────────────────────

def compute_statistics(papers: List[Dict]) -> Dict:
    """Compute paper counts, category distribution, and weekly breakdowns."""
    category_counter: Counter = Counter()
    weekly_papers: Dict[str, List[Dict]] = {}
    all_titles: List[str] = []
    all_tldrs: List[str] = []

    for paper in papers:
        cats = paper.get('categories', [])
        if cats:
            category_counter[cats[0]] += 1

        date = paper.get('_date', '')
        week = get_week_label(date) if date else 'unknown'
        if week not in weekly_papers:
            weekly_papers[week] = []
        weekly_papers[week].append(paper)

        title = paper.get('title', '')
        if title:
            all_titles.append(title)

        ai = paper.get('AI', {}) or {}
        tldr = ai.get('tldr', '') or paper.get('summary', '')[:300]
        if tldr:
            all_tldrs.append(tldr)

    return {
        'total': len(papers),
        'category_counter': category_counter,
        'weekly_papers': weekly_papers,
        'all_titles': all_titles,
        'all_tldrs': all_tldrs,
    }


# ─────────────────────────── Word Cloud ───────────────────────────

_STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
    'we', 'our', 'us', 'it', 'its', 'as', 'such', 'also', 'which', 'not',
    'paper', 'model', 'method', 'approach', 'show', 'propose', 'present',
    'based', 'using', 'used', 'new', 'than', 'more', 'both', 'each',
    'their', 'them', 'they', 'while', 'when', 'how', 'what', 'here',
    'well', 'i.e', 'e.g', 'via', 'two', 'three', 'one', 'first', 'second',
    '的', '了', '在', '是', '和', '与', '等', '该', '其', '为', '对', '中',
    '进行', '通过', '以', '并', '能够', '提出', '方法', '模型', '论文',
}


def _tokenize(text: str, language: str) -> str:
    """Tokenize text for word cloud generation."""
    # Remove LaTeX/special chars
    text = re.sub(r'\$[^$]*\$', ' ', text)
    text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
    text = text.lower()

    if language.lower() in ('chinese', 'zh') and JIEBA_AVAILABLE:
        words = jieba.cut(text, cut_all=False)
        words = [w for w in words if w.strip() and w not in _STOP_WORDS and len(w) > 1]
        return ' '.join(words)
    else:
        words = text.split()
        words = [w for w in words if w not in _STOP_WORDS and len(w) > 2]
        return ' '.join(words)


def generate_wordcloud(texts: List[str], output_path: str, language: str) -> bool:
    """Generate a word cloud image and save it. Returns True on success."""
    if not WORDCLOUD_AVAILABLE:
        return False
    combined = ' '.join(texts)
    tokenized = _tokenize(combined, language)
    if not tokenized.strip():
        return False
    try:
        wc = WordCloud(
            width=1200,
            height=600,
            background_color='white',
            max_words=150,
            colormap='viridis',
            prefer_horizontal=0.85,
            collocations=False,
        )
        wc.generate(tokenized)
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')
        plt.tight_layout(pad=0)
        plt.savefig(output_path, dpi=120, bbox_inches='tight')
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Word cloud generation error: {e}", file=sys.stderr)
        return False


# ─────────────────────────── Weekly topic extraction ───────────────────────────

WEEKLY_MAP_SYSTEM = (
    "You are an expert academic researcher. "
    "Extract concise key research topics from the following paper summaries."
)

WEEKLY_MAP_TEMPLATE = """\
Given these paper TL;DRs from {week_label}, list the top 10 most prominent research topics as short phrases.
Return ONLY valid JSON: {{"topics": ["topic1", "topic2", ...]}}

Papers (TL;DRs):
{tldrs}
"""


def extract_weekly_topics(weekly_papers: Dict[str, List[Dict]],
                           model_name: str) -> Dict[str, List[str]]:
    """For each week, extract top research topics via LLM."""
    llm = ChatOpenAI(model=model_name)
    weekly_topics: Dict[str, List[str]] = {}

    for week_label in sorted(weekly_papers.keys()):
        papers = weekly_papers[week_label]
        tldrs_sample = []
        for p in papers[:60]:  # Limit to first 60 papers per week
            ai = p.get('AI', {}) or {}
            tldr = ai.get('tldr', '') or p.get('summary', '')[:200]
            if tldr:
                tldrs_sample.append(f"- {tldr[:200]}")
        if not tldrs_sample:
            weekly_topics[week_label] = []
            continue
        try:
            response = llm.invoke([
                {"role": "system", "content": WEEKLY_MAP_SYSTEM},
                {"role": "user", "content": WEEKLY_MAP_TEMPLATE.format(
                    week_label=week_label,
                    tldrs="\n".join(tldrs_sample[:40]),
                )},
            ])
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)
            weekly_topics[week_label] = result.get("topics", [])
        except Exception as e:
            print(f"Weekly topic extraction error for {week_label}: {e}", file=sys.stderr)
            weekly_topics[week_label] = []

    return weekly_topics


# ─────────────────────────── LLM Trend Analysis ───────────────────────────

TREND_SYSTEM_TMPL = (
    "You are an expert academic researcher writing a monthly review of arXiv papers. "
    "Write a comprehensive, insightful trend analysis in {language}."
)

TREND_TEMPLATE = """\
Monthly arXiv Paper Review — {month_label}

Total papers this month: {total}

Top categories by paper count:
{category_table}

Weekly research hotspot evolution:
{weekly_evolution}

Write a comprehensive monthly trend analysis in {language} including:
1. Overall research landscape this month (key numbers, dominant fields).
2. Analysis of major research trends and hotspots.
3. How research topics evolved across weeks (evolution narrative).
4. Emerging or noteworthy directions.
5. Brief conclusions and outlook.

Keep it under 800 words, well-structured with clear headings.
"""


def generate_trend_analysis(stats: Dict, weekly_topics: Dict[str, List[str]],
                              month_label: str, model_name: str, language: str) -> str:
    """Call LLM to generate the monthly trend analysis narrative."""
    llm = ChatOpenAI(model=model_name)

    top_cats = stats['category_counter'].most_common(15)
    category_table = "\n".join(f"  {i+1}. {cat}: {cnt} papers"
                                for i, (cat, cnt) in enumerate(top_cats))

    weekly_evo_lines = []
    for week in sorted(weekly_topics.keys()):
        topics = weekly_topics[week]
        count = len(stats['weekly_papers'].get(week, []))
        topics_str = ", ".join(topics[:6]) if topics else "N/A"
        weekly_evo_lines.append(f"  {week} ({count} papers): {topics_str}")
    weekly_evolution = "\n".join(weekly_evo_lines) if weekly_evo_lines else "N/A"

    try:
        response = llm.invoke([
            {"role": "system",
             "content": TREND_SYSTEM_TMPL.format(language=language)},
            {"role": "user", "content": TREND_TEMPLATE.format(
                month_label=month_label,
                total=stats['total'],
                category_table=category_table,
                weekly_evolution=weekly_evolution,
                language=language,
            )},
        ])
        return response.content.strip()
    except Exception as e:
        print(f"Trend analysis LLM error: {e}", file=sys.stderr)
        return "Trend analysis generation failed."


# ─────────────────────────── Markdown output ───────────────────────────

def build_markdown(
    month_label: str,
    year: int,
    month: int,
    stats: Dict,
    weekly_topics: Dict[str, List[str]],
    trend_narrative: str,
    wordcloud_rel_path: str,
) -> str:
    """Assemble the monthly Markdown report."""
    month_name = datetime(year, month, 1).strftime("%B %Y")
    top_cats = stats['category_counter'].most_common()
    sorted_weeks = sorted(weekly_topics.keys())

    lines = [
        f"# Monthly arXiv Review — {month_name}",
        "",
        f"**Period:** {year}-{month:02d}-01 to {year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}  ",
        f"**Total papers:** {stats['total']}  ",
        f"**Active weeks:** {len(sorted_weeks)}  ",
        "",
        "---",
        "",
        "## 📈 Paper Volume Ranking by Category",
        "",
        "| Rank | Category | Papers | Share |",
        "| ---: | -------- | -----: | ----: |",
    ]
    total = stats['total'] if stats['total'] > 0 else 1
    for rank, (cat, cnt) in enumerate(top_cats, 1):
        share = f"{cnt / total * 100:.1f}%"
        lines.append(f"| {rank} | {cat} | {cnt} | {share} |")

    # Word cloud section
    lines += ["", "---", "", "## ☁️ Research Hotspot Word Cloud", ""]
    if wordcloud_rel_path:
        lines.append(f"![Word Cloud]({wordcloud_rel_path})")
        lines.append("")
        lines.append(
            "*The word cloud above visualizes the most frequently appearing research topics "
            "and concepts across all papers this month.*"
        )
    else:
        lines.append("*Word cloud generation requires `wordcloud` and `matplotlib` packages.*")

    # Weekly evolution table
    lines += ["", "---", "", "## 📅 Weekly Hotspot Evolution", ""]
    if sorted_weeks:
        lines += [
            "| Week | Papers | Top Research Topics |",
            "| ---- | -----: | ------------------- |",
        ]
        for week in sorted_weeks:
            count = len(stats['weekly_papers'].get(week, []))
            topics = weekly_topics.get(week, [])
            topics_str = " · ".join(topics[:5]) if topics else "—"
            lines.append(f"| {week} | {count} | {topics_str} |")
    else:
        lines.append("*No weekly data available.*")

    # AI narrative
    lines += [
        "",
        "---",
        "",
        "## 🤖 AI-Generated Monthly Trend Analysis",
        "",
        trend_narrative,
        "",
        "---",
        "",
        f"*Generated automatically on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*",
    ]
    return "\n".join(lines)


# ─────────────────────────── Main ───────────────────────────

def main():
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", "deepseek-chat")
    language = os.environ.get("LANGUAGE", "Chinese")

    dates, year, month = get_month_dates(args.month)
    month_label = f"{year}-{month:02d}"
    print(f"Generating monthly summary for {month_label}", file=sys.stderr)

    # Load papers
    papers = load_month_papers(args.data_dir, dates, language)
    if not papers:
        print("No papers found for this month. Exiting.", file=sys.stderr)
        sys.exit(0)
    print(f"Loaded {len(papers)} papers.", file=sys.stderr)

    # Compute statistics
    stats = compute_statistics(papers)

    # Generate word cloud
    os.makedirs(args.asset_dir, exist_ok=True)
    wc_filename = f"wordcloud-{month_label}.png"
    wc_abs_path = os.path.join(args.asset_dir, wc_filename)
    texts_for_wc = stats['all_titles'] + stats['all_tldrs']
    wc_ok = generate_wordcloud(texts_for_wc, wc_abs_path, language)
    wordcloud_rel_path = ""
    if wc_ok:
        print(f"Word cloud saved to {wc_abs_path}", file=sys.stderr)
        # Relative path from data/monthly/ to assets/
        wordcloud_rel_path = f"../../assets/{wc_filename}"

    # Extract weekly topics via LLM
    print("Extracting weekly topics via LLM...", file=sys.stderr)
    weekly_topics = extract_weekly_topics(stats['weekly_papers'], model_name)

    # Generate trend analysis narrative
    print("Generating trend analysis...", file=sys.stderr)
    trend_narrative = generate_trend_analysis(
        stats, weekly_topics, month_label, model_name, language
    )

    # Build and write Markdown
    markdown = build_markdown(
        month_label, year, month,
        stats, weekly_topics,
        trend_narrative, wordcloud_rel_path,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"{month_label}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"Monthly review written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
