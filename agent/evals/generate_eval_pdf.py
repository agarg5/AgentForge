#!/usr/bin/env python3
"""Generate a human-readable PDF of all AgentForge eval cases."""

import json
from pathlib import Path

import yaml
from fpdf import FPDF

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
OUTPUT_PATH = Path(__file__).resolve().parent / "AgentForge_Eval_Cases.pdf"


class EvalPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "AgentForge - Eval Test Cases", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, "150 cases across 4 datasets", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    @staticmethod
    def _sanitize(text):
        return text.replace("\u2014", "-").replace("\u2013", "-").replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_fill_color(40, 60, 100)
        self.set_text_color(255, 255, 255)
        self.cell(0, 9, f"  {self._sanitize(title)}", new_x="LMARGIN", new_y="NEXT", fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def category_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(220, 230, 240)
        self.cell(0, 7, f"  {title}", new_x="LMARGIN", new_y="NEXT", fill=True)
        self.ln(2)

    def case_entry(self, num, query, description, expected_tools, extra=None):
        # Case number + description
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 5, f"{num}. {description}", new_x="LMARGIN", new_y="NEXT")

        # Query
        self.set_font("Helvetica", "", 9)
        self.set_x(15)
        self.set_text_color(50, 50, 50)
        # Sanitize for latin-1
        safe_query = query.replace("\u2014", "-").replace("\u2013", "-").replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"').encode("latin-1", errors="replace").decode("latin-1")
        self.multi_cell(0, 4.5, f'Query: "{safe_query}"')
        self.set_text_color(0, 0, 0)

        # Expected tools
        if expected_tools:
            self.set_x(15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(0, 100, 0)
            self.cell(0, 4.5, f"Expected tools: {', '.join(expected_tools)}", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)
        else:
            self.set_x(15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(180, 0, 0)
            self.cell(0, 4.5, "Expected: No tools (should decline/redirect)", new_x="LMARGIN", new_y="NEXT")
            self.set_text_color(0, 0, 0)

        # Extra info (must_contain, must_not_contain, expected_behavior)
        if extra:
            for key, val in extra.items():
                if val:
                    self.set_x(15)
                    self.set_font("Helvetica", "", 7.5)
                    self.set_text_color(100, 100, 100)
                    if isinstance(val, list):
                        val_str = ", ".join(str(v) for v in val)
                    else:
                        val_str = str(val).strip()
                        val_str = self._sanitize(val_str).encode("latin-1", errors="replace").decode("latin-1")
                    label = key.replace("_", " ").title()
                    self.multi_cell(0, 4, f"{label}: {val_str}")
                    self.set_text_color(0, 0, 0)

        self.ln(2)


def load_cases_json():
    cases_by_cat = {}
    for path in sorted(DATASETS_DIR.glob("*.json")):
        if path.stem == "preference_cases":
            continue  # handled separately
        with open(path) as f:
            data = json.load(f)
        items = data if isinstance(data, list) else [data]
        for item in items:
            cat = item.get("category", "unknown")
            cases_by_cat.setdefault(cat, []).append(item)
    return cases_by_cat


def load_golden():
    golden_path = DATASETS_DIR / "golden_set.yaml"
    if not golden_path.exists():
        return {}
    with open(golden_path) as f:
        items = yaml.safe_load(f) or []
    cases_by_cat = {}
    for item in items:
        cat = item.get("category", "unknown")
        cases_by_cat.setdefault(cat, []).append(item)
    return cases_by_cat


def load_preference_cases():
    pref_path = DATASETS_DIR / "preference_cases.json"
    if not pref_path.exists():
        return {}
    with open(pref_path) as f:
        data = json.load(f)
    items = data if isinstance(data, list) else [data]
    cases_by_cat = {}
    for item in items:
        cat = item.get("category", "unknown")
        cases_by_cat.setdefault(cat, []).append(item)
    return cases_by_cat


CATEGORY_LABELS = {
    "portfolio_analysis": "Portfolio Analysis",
    "transaction_history": "Transaction History",
    "market_data": "Market Data",
    "risk_assessment": "Risk Assessment",
    "benchmark_comparison": "Benchmark Comparison",
    "dividend_analysis": "Dividend Analysis",
    "account_summary": "Account Summary",
    "multi_tool": "Multi-Tool Reasoning",
    "market_news": "Market News",
    "guardrails": "Guardrails & Safety",
    "hallucination": "Hallucination Prevention",
    "verification": "Verification",
    "format": "Response Format",
    "edge_cases": "Edge Cases",
    "preferences": "User Preferences",
    "preferences_influence": "Preferences Influence on Responses",
}


def main():
    pdf = EvalPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # --- Dataset 1: cases.json + guardrails_cases.json ---
    pdf.add_page()
    pdf.section_title("Functional & Guardrail Cases (82 cases)")
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4, "Source: cases.json + guardrails_cases.json")
    pdf.ln(3)

    cases_by_cat = load_cases_json()
    num = 0
    cat_order = [
        "portfolio_analysis", "transaction_history", "market_data",
        "risk_assessment", "benchmark_comparison", "dividend_analysis",
        "account_summary", "multi_tool", "market_news", "guardrails",
        "hallucination", "verification", "format", "edge_cases",
    ]
    for cat in cat_order:
        items = cases_by_cat.get(cat, [])
        if not items:
            continue
        label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        pdf.category_title(f"{label} ({len(items)} cases)")
        for item in items:
            num += 1
            pdf.case_entry(
                num=num,
                query=item.get("input", ""),
                description=item.get("description", ""),
                expected_tools=item.get("expected_tools", []),
            )

    # --- Dataset 2: golden_set.yaml ---
    pdf.add_page()
    pdf.section_title("Golden Set - Curated Rubric Cases (26 cases)")
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4, "Source: golden_set.yaml - Each case has must_contain/must_not_contain phrases and expected behavior rubrics for LLM-as-judge scoring.")
    pdf.ln(3)

    golden_by_cat = load_golden()
    num = 0
    golden_order = [
        "portfolio_analysis", "transaction_history", "market_data",
        "risk_assessment", "benchmark_comparison", "dividend_analysis",
        "account_summary", "multi_tool", "preferences", "preferences_influence",
        "guardrails",
    ]
    for cat in golden_order:
        items = golden_by_cat.get(cat, [])
        if not items:
            continue
        label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        pdf.category_title(f"{label} ({len(items)} cases)")
        for item in items:
            num += 1
            extra = {}
            if item.get("must_contain"):
                extra["must_contain"] = item["must_contain"]
            if item.get("must_not_contain"):
                extra["must_not_contain"] = item["must_not_contain"]
            if item.get("expected_behavior"):
                extra["expected_behavior"] = item["expected_behavior"]
            pdf.case_entry(
                num=num,
                query=item.get("query", ""),
                description=item.get("id", ""),
                expected_tools=item.get("expected_tools", []),
                extra=extra,
            )

    # --- Dataset 3: preference_cases.json ---
    pdf.add_page()
    pdf.section_title("Preference Memory Cases (22 cases)")
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4, "Source: preference_cases.json - Tests the agent's ability to save, retrieve, delete, and apply user preferences.")
    pdf.ln(3)

    pref_by_cat = load_preference_cases()
    num = 0
    pref_order = ["preferences", "preferences_influence"]
    for cat in pref_order:
        items = pref_by_cat.get(cat, [])
        if not items:
            continue
        label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        pdf.category_title(f"{label} ({len(items)} cases)")
        for item in items:
            num += 1
            pdf.case_entry(
                num=num,
                query=item.get("input", ""),
                description=item.get("description", ""),
                expected_tools=item.get("expected_tools", []),
            )

    # --- Summary page ---
    pdf.add_page()
    pdf.section_title("Summary")
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 10)

    summary = [
        ("Total eval cases", "150"),
        ("Functional cases (cases.json)", "62"),
        ("Guardrail/adversarial cases", "20"),
        ("Golden set rubric cases", "26"),
        ("Preference memory cases", "22"),
        ("", ""),
        ("Scorers Used", ""),
        ("  ToolsMatch", "Did the agent call the expected tool(s)?"),
        ("  ScopeDeclined", "Did the agent refuse off-topic/adversarial queries?"),
        ("  MustContain", "Does the response include required phrases?"),
        ("  MustNotContain", "Does the response avoid banned phrases?"),
        ("  NoHallucination", "Is the response grounded in tool data?"),
        ("  Factuality (LLM judge)", "Does the response match expected behavior?"),
        ("", ""),
        ("Performance Targets", ""),
        ("  Tool success rate", ">95%"),
        ("  Eval pass rate", ">80%"),
        ("  Hallucination rate", "<5%"),
        ("  Single-tool latency", "<5s"),
        ("  Multi-step latency", "<15s"),
    ]

    for label, value in summary:
        if not label and not value:
            pdf.ln(3)
            continue
        pdf.set_font("Helvetica", "B" if not label.startswith("  ") else "", 9)
        if value and label:
            pdf.cell(100, 5, label)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 5, value, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.cell(0, 5, label or value, new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(OUTPUT_PATH))
    print(f"PDF generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
