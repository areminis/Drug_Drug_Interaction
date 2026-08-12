"""
agents/narrative_trace.py

Generates a human-readable "Narrative Reasoning Trace" that describes, step by step,
exactly how the system produced its answer:
  1. How it queried the Knowledge Graph for the drug pair
  2. What ingredient records it retrieved and their weights
  3. How it compared those facts with the LLM's clinical recommendation
  4. What was confirmed and what (if anything) was unverified
"""

import itertools
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Helper – severity → plain English
# ---------------------------------------------------------------------------
_SEVERITY_DESC = {
    "Major":    "a high-risk, major",
    "Moderate": "a clinically significant, moderate",
    "Minor":    "a low-risk, minor",
}


def _severity_phrase(severity: str) -> str:
    return _SEVERITY_DESC.get(severity, f"a {severity.lower()}")


# ---------------------------------------------------------------------------
# Helper – format a small list nicely ("A, B and C")
# ---------------------------------------------------------------------------
def _join(items: List[str], limit: int = 4) -> str:
    if not items:
        return "none"
    items = [str(i) for i in items[:limit]]
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


# ---------------------------------------------------------------------------
# Core trace generator
# ---------------------------------------------------------------------------
def generate_narrative_trace(
    drug1: str,
    drug2: str,
    kg_rows: List[Dict],
    ingredient_analysis: Optional[Dict],
    hallucination_result: Optional[Dict],
    verification_status: Optional[str] = None,
) -> str:
    """
    Build a natural-language walkthrough of how the pipeline produced its answer.

    Args:
        drug1                : First drug name (display form)
        drug2                : Second drug name (display form)
        kg_rows              : Raw KG interaction rows returned for this drug pair
        ingredient_analysis  : Result dict from IngredientAnalyzer.analyze_drug_interaction()
        hallucination_result : Result dict from HallucinationMetric.calculate_hallucination_score()
        verification_status  : Overall status string from VerificationAgent ('verified', etc.)

    Returns:
        A formatted multi-line markdown string ready to be appended to the response.
    """
    lines: List[str] = []

    lines.append("\n\n---")
    lines.append("## 🔎 Narrative Reasoning Trace")
    lines.append(
        "*The following explains step-by-step how this answer was generated.*\n"
    )

    # ------------------------------------------------------------------
    # STEP 1 — Knowledge Graph search
    # ------------------------------------------------------------------
    lines.append("### Step 1 — Searching the Knowledge Graph")
    if kg_rows:
        severities = list({r.get("severity", "Unknown") for r in kg_rows})
        mechanisms = list({r.get("mechanism", "Unknown") for r in kg_rows})
        lines.append(
            f"The system queried the Neo4j Knowledge Graph for all documented interactions "
            f"between **{drug1}** and **{drug2}**. "
            f"**{len(kg_rows)}** interaction record(s) were found."
        )
        lines.append(
            f"- Severity level(s) on record: **{_join(severities)}**"
        )
        lines.append(
            f"- Mechanism(s) documented: *{_join(mechanisms)}*"
        )
    else:
        lines.append(
            f"The system queried the Neo4j Knowledge Graph for interactions between "
            f"**{drug1}** and **{drug2}**, but found **no direct interaction records** "
            f"for this drug pair in the current dataset."
        )

    # ------------------------------------------------------------------
    # STEP 2 — Ingredient retrieval & weight calculation
    # ------------------------------------------------------------------
    lines.append("\n### Step 2 — Retrieving Ingredient Records & Calculating Weights")
    if ingredient_analysis and ingredient_analysis.get("total_interactions", 0) > 0:
        d1_comp = ingredient_analysis.get("drug1_composition", [])
        d2_comp = ingredient_analysis.get("drug2_composition", [])
        total_int = ingredient_analysis.get("total_interactions", 0)
        contributions = ingredient_analysis.get("contributions", {})

        d1_names = [i.get("ingredient", "") for i in d1_comp if i.get("display_category") == "Active"]
        d2_names = [i.get("ingredient", "") for i in d2_comp if i.get("display_category") == "Active"]

        lines.append(
            f"The system fetched the active ingredient profiles of both drugs from the graph:"
        )
        lines.append(f"- **{drug1}** active ingredient(s): {_join(d1_names) if d1_names else 'not available'}")
        lines.append(f"- **{drug2}** active ingredient(s): {_join(d2_names) if d2_names else 'not available'}")
        lines.append(
            f"\nNext, it queried ingredient-level interaction edges and found "
            f"**{total_int}** ingredient-pair interaction(s). "
            "For each pair it calculated a **contribution weight** using the formula:"
        )
        lines.append(
            "> `Weight = (Quantity factor × 0.3) + (Severity factor × 0.5) + (Mechanism factor × 0.2)`"
        )
        lines.append(
            "Weights were then normalised to percentages so the relative importance "
            "of each ingredient pair is clear."
        )

        # Summarise primary contributors
        primary = contributions.get("primary", [])
        secondary = contributions.get("secondary", [])
        if primary:
            top_interaction, top_pct = primary[0]
            ing_a = top_interaction.get("ingredient_a", "?")
            ing_b = top_interaction.get("ingredient_b", "?")
            mech  = top_interaction.get("mechanism", "unknown mechanism")
            sev   = top_interaction.get("severity", "unknown severity")
            lines.append(
                f"\nThe **dominant contributor** ({top_pct:.1f}% of overall interaction weight) "
                f"is the **{ing_a} ↔ {ing_b}** pair, "
                f"acting via {mech} with {_severity_phrase(sev)} interaction."
            )
        if secondary:
            sec_pairs = [
                f"{i.get('ingredient_a')} ↔ {i.get('ingredient_b')} ({p:.1f}%)"
                for i, p in secondary
            ]
            lines.append(
                f"Additional secondary contributor(s): {_join(sec_pairs)}."
            )
    elif ingredient_analysis:
        # compositions exist but no ingredient-level interactions
        d1_comp = ingredient_analysis.get("drug1_composition", [])
        d2_comp = ingredient_analysis.get("drug2_composition", [])
        if d1_comp or d2_comp:
            lines.append(
                "The system retrieved ingredient composition records for both drugs, "
                "but the Knowledge Graph contains **no ingredient-level interaction edges** "
                "between their components. Weight calculation was therefore not performed."
            )
        else:
            lines.append(
                "No ingredient composition data was found in the Knowledge Graph "
                "for either drug, so ingredient-level weight analysis was skipped."
            )
    else:
        lines.append(
            "Ingredient-level analysis was not applicable for this query type "
            "(e.g. a drug-condition query rather than a drug-drug interaction)."
        )

    # ------------------------------------------------------------------
    # STEP 3 — Comparing KG evidence with the AI recommendation
    # ------------------------------------------------------------------
    lines.append("\n### Step 3 — Comparing KG Evidence with the AI Recommendation")
    if hallucination_result:
        total   = hallucination_result.get("total_claims", 0)
        verified = hallucination_result.get("verified_claims", 0)
        unverified = hallucination_result.get("unverified_claims", 0)
        score   = hallucination_result.get("hallucination_score", 0)

        lines.append(
            "The AI-generated clinical recommendation was broken down into "
            f"**{total}** verifiable claim(s) (severity levels and CYP enzyme mechanisms). "
            "Each claim was looked up directly in the Knowledge Graph:"
        )
        lines.append(f"- ✅ **{verified}** claim(s) confirmed by KG records")
        lines.append(f"- ⚠️  **{unverified}** claim(s) could not be matched to any KG record")

        if score == 0:
            lines.append(
                "\nSince every claim extracted from the AI response matched a record in the "
                "Knowledge Graph, the recommendation is **fully grounded** in verified data. "
                "No hallucinated content was detected."
            )
        elif score <= 30:
            lines.append(
                f"\nMost claims ({verified}/{total}) were verified. The small number of "
                "unmatched claims may represent valid clinical context not yet captured "
                "in the current KG dataset — but should be reviewed by a clinician."
            )
        elif score <= 70:
            lines.append(
                f"\nA significant portion ({unverified}/{total} claims) could not be "
                "confirmed by the Knowledge Graph. The AI may have introduced clinically "
                "plausible but unverified statements. Exercise caution and seek expert review."
            )
        else:
            lines.append(
                f"\nThe majority of the AI's claims ({unverified}/{total}) were **not found** "
                "in the Knowledge Graph. The response may contain substantially fabricated "
                "content. Do NOT rely on this output without independent expert verification."
            )
    else:
        lines.append(
            "Claim-level comparison against the Knowledge Graph was not performed "
            "for this query (this check only applies to drug-drug interaction results "
            "where KG evidence is present)."
        )

    # ------------------------------------------------------------------
    # STEP 4 — Final confirmation
    # ------------------------------------------------------------------
    lines.append("\n### Step 4 — Final Confirmation")
    if verification_status:
        status_map = {
            "verified":           "✅ **Fully Verified** — the drug pair, mechanism, and severity were all confirmed by the Knowledge Graph.",
            "mostly_verified":    "⚠️  **Mostly Verified** — the drug pair and at least one other claim were confirmed; minor aspects remain unverified.",
            "partially_verified": "⚠️  **Partially Verified** — the drug pair was found in the KG but mechanism or severity details differed.",
            "unverified":         "❌ **Unverified** — the drug pair was not found or no KG evidence could be matched to the AI's claims.",
        }
        verdict = status_map.get(verification_status, f"Status: {verification_status}")
        lines.append(
            "After completing the above steps, the VerificationAgent assigned the following verdict:"
        )
        lines.append(f"\n> {verdict}")
    else:
        lines.append(
            "The full end-to-end verification pipeline was not triggered for this query type. "
            "The answer is based solely on Knowledge Graph evidence."
        )

    lines.append(
        "\n> 📌 *This trace is generated automatically by the pipeline and reflects the "
        "actual data retrieved and calculations performed — not a post-hoc summary.*"
    )
    lines.append("---\n")

    return "\n".join(lines)
