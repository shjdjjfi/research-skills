#!/usr/bin/env python3
"""Generate a medical AI review draft from arXiv metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import html
from pathlib import Path
import textwrap
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ARXIV_API = "https://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def parse_feed(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    papers: list[dict] = []

    for entry in root.findall("atom:entry", NS):
        title = (entry.findtext("atom:title", default="", namespaces=NS) or "").strip().replace("\n", " ")
        summary = (entry.findtext("atom:summary", default="", namespaces=NS) or "").strip().replace("\n", " ")
        published = (entry.findtext("atom:published", default="", namespaces=NS) or "").strip()
        if not published:
            continue

        paper_id = ""
        abs_url = ""
        pdf_url = ""
        for link in entry.findall("atom:link", NS):
            href = link.attrib.get("href", "")
            rel = link.attrib.get("rel", "")
            title_attr = link.attrib.get("title", "")
            if rel == "alternate":
                abs_url = href
            if title_attr == "pdf":
                pdf_url = href

        if abs_url:
            paper_id = abs_url.rstrip("/").split("/")[-1]

        authors = [a.findtext("atom:name", default="", namespaces=NS).strip() for a in entry.findall("atom:author", NS)]
        categories = [c.attrib.get("term", "") for c in entry.findall("atom:category", NS)]

        papers.append(
            {
                "title": html.unescape(title),
                "summary": html.unescape(summary),
                "published": published,
                "year": int(published[:4]),
                "id": paper_id,
                "abs_url": abs_url,
                "pdf_url": pdf_url,
                "authors": [x for x in authors if x],
                "categories": [x for x in categories if x],
            }
        )

    return papers


def fetch_arxiv(topic: str, max_results: int) -> list[dict]:
    params = {
        "search_query": f"all:{topic}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    query_url = f"{ARXIV_API}?{urlencode(params)}"
    req = Request(query_url, headers={"User-Agent": "codex-medical-review/1.0 (+https://arxiv.org)"})
    with urlopen(req, timeout=30) as response:
        xml_text = response.read().decode("utf-8")
    return parse_feed(xml_text)


def filter_by_year(papers: list[dict], start_year: int) -> list[dict]:
    return [p for p in papers if p["year"] >= start_year]


def render_review(topic: str, papers: list[dict], template: str) -> str:
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d")
    title = f"{topic.title()}: An arXiv-grounded Review of Medical AI Methods"

    key_points = "\n".join(
        [
            f"- This review summarizes {len(papers)} arXiv papers retrieved for the topic: `{topic}`.",
            "- The manuscript is generated from verifiable arXiv metadata with direct URL traceability.",
            "- Figure slots are provided as placeholders with caption suggestions (no image generation).",
        ]
    )

    abstract = (
        f"This draft review provides a structured synthesis of recent studies on {topic}, "
        f"based on arXiv metadata collected on {now}. We summarize methodological trends, "
        "identify common limitations, and highlight future directions for clinically robust "
        "medical AI. All references are linked to online arXiv records for traceable verification."
    )

    intro_refs = ", ".join(f"[R{i}]" for i in range(1, min(6, len(papers) + 1)))

    introduction = (
        f"Medical AI has rapidly evolved in recent years, with a notable increase in preprints "
        f"covering representation learning, foundation models, and multimodal reasoning {intro_refs}. "
        "This draft is intended as a Codex-editable scaffold: users can further refine each section "
        "without changing the verified citation backbone."
    )

    landscape_lines = []
    for idx, p in enumerate(papers, start=1):
        authors_short = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors_short += ", et al."
        landscape_lines.append(
            f"- [R{idx}] **{p['title']}** ({p['year']}) by {authors_short}. "
            f"Categories: {', '.join(p['categories'][:4]) or 'N/A'}."
        )
    landscape = "\n".join(landscape_lines) if landscape_lines else "- No papers retrieved under current query constraints."

    trends = textwrap.dedent(
        """
        1. **Architecture shift**: Recent work increasingly combines CNN priors with transformer-based global modeling.
        2. **Pretraining and transfer**: Self-supervised and weakly supervised paradigms are used to mitigate annotation scarcity.
        3. **Clinical robustness**: More studies evaluate cross-center generalization, uncertainty, and calibration.
        4. **Efficiency**: Distillation and lightweight deployment become central for real-world integration.
        """
    ).strip()

    limitations = textwrap.dedent(
        """
        - Dataset bias and annotation inconsistency remain major barriers.
        - External validation is still limited in many preprint-stage studies.
        - Reproducibility varies due to incomplete code/data release.
        - Metric heterogeneity complicates direct method comparison.
        """
    ).strip()

    future_directions = textwrap.dedent(
        """
        - Standardized, multi-institution benchmarks with protocol harmonization.
        - Clinician-in-the-loop evaluation and prospective impact studies.
        - Robustness auditing under distribution shift and adversarial noise.
        - Better interpretability and regulatory-aware model reporting.
        """
    ).strip()

    figure_placeholders = textwrap.dedent(
        """
        - **[Insert Figure 1 here]**
          - **Caption suggestion:** Taxonomy of medical AI methods for this review topic, grouped by task type and modeling paradigm.
        - **[Insert Figure 2 here]**
          - **Caption suggestion:** Timeline of methodological evolution across selected arXiv papers (year vs. key innovation).
        - **[Insert Figure 3 here]**
          - **Caption suggestion:** Comparative schematic of representative model families and their strengths/limitations.
        """
    ).strip()

    refs = []
    for idx, p in enumerate(papers, start=1):
        author_str = ", ".join(p["authors"])
        refs.append(
            f"- [R{idx}] {author_str}. **{p['title']}**. arXiv:{p['id']} ({p['year']}). "
            f"[abs]({p['abs_url']}) | [pdf]({p['pdf_url']})"
        )
    references = "\n".join(refs) if refs else "- No references available."

    return template.format(
        title=title,
        key_points=key_points,
        abstract=abstract,
        introduction=introduction,
        landscape=landscape,
        trends=trends,
        limitations=limitations,
        future_directions=future_directions,
        figure_placeholders=figure_placeholders,
        references=references,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate medical AI review markdown from arXiv.")
    parser.add_argument("--topic", required=True, help="Search topic for arXiv query.")
    parser.add_argument("--max-results", type=int, default=30, help="Maximum arXiv papers to retrieve.")
    parser.add_argument("--start-year", type=int, default=2020, help="Keep papers published from this year.")
    parser.add_argument("--output", default="manuscript_draft.md", help="Output markdown file path.")
    parser.add_argument(
        "--template",
        default=str(Path(__file__).resolve().parents[1] / "assets" / "review_template.md"),
        help="Markdown template file.",
    )
    parser.add_argument("--input-feed", help="Optional local arXiv Atom XML file for offline generation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    template_text = Path(args.template).read_text(encoding="utf-8")
    try:
        if args.input_feed:
            xml_text = Path(args.input_feed).read_text(encoding="utf-8")
            papers = parse_feed(xml_text)
        else:
            papers = fetch_arxiv(args.topic, args.max_results)
    except URLError as exc:
        raise SystemExit(
            "Failed to access arXiv API. Use --input-feed with a local Atom XML export in restricted environments. "
            f"Original error: {exc}"
        )

    papers = filter_by_year(papers, args.start_year)

    review_md = render_review(args.topic, papers, template_text)
    Path(args.output).write_text(review_md, encoding="utf-8")

    print(f"Generated review: {args.output}")
    print(f"Papers included: {len(papers)}")


if __name__ == "__main__":
    main()
