#!/usr/bin/env python3
"""
每周摘要生成脚本 (Map-Reduce 策略)
Weekly Summary Generation Script (Map-Reduce Strategy)

功能 / Features:
- 读取过去一周的AI增强JSONL文件 / Read AI-enhanced JSONL files from the past week
- Map阶段：从每篇论文提取关键主题 / Map phase: extract key topics from each paper
- Reduce阶段：统计词频，聚类主题，找出研究热点 / Reduce phase: count term frequencies, cluster topics
- 输出每周摘要Markdown文件 / Output weekly summary Markdown file to data/weekly/

用法 / Usage:
  python weekly_summary.py [--data_dir ../data] [--output_dir ../data/weekly] [--week_start YYYY-MM-DD]
"""

import os
import json
import sys
import argparse
from datetime import datetime, timedelta
from collections import Counter
from typing import List, Dict, Tuple

import dotenv
from langchain_openai import ChatOpenAI

if os.path.exists('.env'):
    dotenv.load_dotenv()


# ─────────────────────────── CLI args ───────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Generate weekly arXiv summary")
    parser.add_argument("--data_dir", type=str, default="../data",
                        help="Directory containing daily JSONL files")
    parser.add_argument("--output_dir", type=str, default="../data/weekly",
                        help="Output directory for weekly summaries")
    parser.add_argument("--week_start", type=str, default=None,
                        help="Week start date YYYY-MM-DD (defaults to last Monday)")
    parser.add_argument("--batch_size", type=int, default=30,
                        help="Number of papers per LLM batch in Map phase")
    return parser.parse_args()


# ─────────────────────────── Date helpers ───────────────────────────

def get_week_dates(week_start_str: str = None) -> Tuple[List[str], datetime]:
    """Return list of date strings for the target week (Mon–Sun)."""
    if week_start_str:
        start = datetime.strptime(week_start_str, "%Y-%m-%d")
    else:
        today = datetime.utcnow()
        # Last completed Monday (go back to last week's Monday)
        days_since_monday = today.weekday()
        start = today - timedelta(days=days_since_monday + 7)
    dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    return dates, start


# ─────────────────────────── Data loading ───────────────────────────

def load_week_papers(data_dir: str, dates: List[str], language: str) -> List[Dict]:
    """Load all papers from AI-enhanced JSONL files for the given dates."""
    papers = []
    for date in dates:
        ai_file = os.path.join(data_dir, f"{date}_AI_enhanced_{language}.jsonl")
        regular_file = os.path.join(data_dir, f"{date}.jsonl")
        target_file = (ai_file if os.path.exists(ai_file)
                       else regular_file if os.path.exists(regular_file)
                       else None)
        if target_file is None:
            print(f"No data file for {date}, skipping.", file=sys.stderr)
            continue
        with open(target_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    paper = json.loads(line)
                    paper['_date'] = date
                    papers.append(paper)
                except json.JSONDecodeError:
                    pass
    return papers


def extract_paper_info(paper: Dict) -> Dict:
    """Return a concise dict for downstream LLM processing."""
    ai = paper.get('AI', {}) or {}
    tldr = ai.get('tldr', '') or paper.get('summary', '')[:400]
    return {
        'id': paper.get('id', ''),
        'title': paper.get('title', ''),
        'categories': paper.get('categories', []),
        'date': paper.get('_date', ''),
        'tldr': tldr[:500],
    }


# ─────────────────────────── Map Phase ───────────────────────────

MAP_SYSTEM = (
    "You are an expert academic researcher specializing in AI and computer science. "
    "Your task is to extract concise key research topics from paper abstracts."
)

MAP_TEMPLATE = """\
For each paper below, extract 3–5 short key research topics or concepts (e.g., "diffusion models", "3D reconstruction", "RLHF").
Return ONLY valid JSON with this exact structure:
{{
  "papers": [
    {{"id": "<paper_id>", "topics": ["topic1", "topic2", "topic3"]}}
  ]
}}

Papers:
{papers_text}
"""


def map_papers_to_topics(papers: List[Dict], model_name: str,
                          batch_size: int = 30) -> Dict[str, List[str]]:
    """Map phase: for each paper extract key topics via LLM.

    Returns a dict mapping paper_id -> [topic, ...].
    """
    llm = ChatOpenAI(model=model_name)
    paper_topics: Dict[str, List[str]] = {}

    for start_idx in range(0, len(papers), batch_size):
        batch = papers[start_idx: start_idx + batch_size]
        papers_text = "\n\n".join(
            f"ID: {p['id']}\nTitle: {p['title']}\nTLDR: {p['tldr']}"
            for p in batch
        )
        try:
            response = llm.invoke([
                {"role": "system", "content": MAP_SYSTEM},
                {"role": "user", "content": MAP_TEMPLATE.format(papers_text=papers_text)},
            ])
            content = response.content.strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            result = json.loads(content)
            for entry in result.get("papers", []):
                pid = entry.get("id", "")
                topics = entry.get("topics", [])
                if pid:
                    paper_topics[pid] = [t.strip() for t in topics if t.strip()]
        except Exception as e:
            print(
                f"Map phase error at batch starting {start_idx}: {e}",
                file=sys.stderr,
            )
    return paper_topics


# ─────────────────────────── Reduce Phase ───────────────────────────

REDUCE_SYSTEM_TMPL = (
    "You are an expert academic researcher. "
    "Analyze the following weekly arXiv paper data and produce a structured "
    "weekly research hotspot report in {language}."
)

REDUCE_TEMPLATE = """\
You are given data about research papers published this week ({week_label}).

Total papers: {total}
Top research topics (topic: paper count):
{topic_list}

Category distribution:
{category_dist}

Write a well-structured weekly summary report in {language} that includes:
1. An executive summary (2–3 sentences) of the major trends this week.
2. A section listing the top research hotspots with brief explanations.
3. Notable observations (emerging topics, cross-domain connections, etc.).

Keep the total report under 600 words.
"""


def reduce_to_summary(topic_counter: Counter, category_counter: Counter,
                       total_papers: int, week_label: str,
                       model_name: str, language: str) -> str:
    """Reduce phase: call LLM to write the weekly summary narrative."""
    llm = ChatOpenAI(model=model_name)

    top_topics = topic_counter.most_common(30)
    topic_list = "\n".join(f"- {t}: {c}" for t, c in top_topics)

    top_cats = category_counter.most_common(15)
    category_dist = "\n".join(f"- {cat}: {cnt}" for cat, cnt in top_cats)

    try:
        response = llm.invoke([
            {"role": "system",
             "content": REDUCE_SYSTEM_TMPL.format(language=language)},
            {"role": "user", "content": REDUCE_TEMPLATE.format(
                week_label=week_label,
                total=total_papers,
                topic_list=topic_list,
                category_dist=category_dist,
                language=language,
            )},
        ])
        return response.content.strip()
    except Exception as e:
        print(f"Reduce phase error: {e}", file=sys.stderr)
        return "Summary generation failed."


# ─────────────────────────── Markdown output ───────────────────────────

def build_markdown(
    week_label: str,
    dates: List[str],
    total_papers: int,
    topic_counter: Counter,
    category_counter: Counter,
    paper_infos: List[Dict],
    narrative: str,
) -> str:
    """Assemble the weekly Markdown report."""
    top_topics = topic_counter.most_common(20)
    top_cats = category_counter.most_common()

    # Header
    lines = [
        f"# Weekly arXiv Summary — {week_label}",
        "",
        f"**Date range:** {dates[0]} to {dates[-1]}  ",
        f"**Total papers:** {total_papers}  ",
        "",
        "---",
        "",
        "## 📊 Research Hotspots (Top Terms)",
        "",
        "| Rank | Topic | Papers |",
        "| ---: | ----- | -----: |",
    ]
    for rank, (term, cnt) in enumerate(top_topics, 1):
        lines.append(f"| {rank} | {term} | {cnt} |")

    lines += [
        "",
        "---",
        "",
        "## 📂 Category Distribution",
        "",
        "| Category | Papers |",
        "| -------- | -----: |",
    ]
    for cat, cnt in top_cats:
        lines.append(f"| {cat} | {cnt} |")

    lines += [
        "",
        "---",
        "",
        "## 🤖 AI-Generated Weekly Analysis",
        "",
        narrative,
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

    dates, week_start_dt = get_week_dates(args.week_start)
    week_num = week_start_dt.isocalendar()[1]
    year = week_start_dt.year
    week_label = f"{year}-W{week_num:02d}"
    print(f"Generating weekly summary for {week_label} ({dates[0]} – {dates[-1]})", file=sys.stderr)

    # Load papers
    papers = load_week_papers(args.data_dir, dates, language)
    if not papers:
        print("No papers found for this week. Exiting.", file=sys.stderr)
        sys.exit(0)

    paper_infos = [extract_paper_info(p) for p in papers]
    total_papers = len(paper_infos)
    print(f"Loaded {total_papers} papers.", file=sys.stderr)

    # Category distribution
    category_counter: Counter = Counter()
    for info in paper_infos:
        cats = info.get('categories', [])
        if cats:
            category_counter[cats[0]] += 1

    # Map phase: extract topics
    print("Map phase: extracting topics from papers...", file=sys.stderr)
    paper_topics = map_papers_to_topics(paper_infos, model_name, args.batch_size)

    # Aggregate topic frequencies
    topic_counter: Counter = Counter()
    for topics in paper_topics.values():
        for topic in topics:
            topic_counter[topic.lower()] += 1

    # Reduce phase: generate narrative
    print("Reduce phase: generating summary narrative...", file=sys.stderr)
    narrative = reduce_to_summary(
        topic_counter, category_counter, total_papers,
        week_label, model_name, language
    )

    # Build and write Markdown
    markdown = build_markdown(
        week_label, dates, total_papers,
        topic_counter, category_counter,
        paper_infos, narrative,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, f"{week_label}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"Weekly summary written to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
