"""
agents/pipeline.py

Main orchestration pipeline for the Oncology DDI Chatbot.
Coordinates slot extraction, knowledge graph queries, ingredient analysis, and clinical reasoning.
"""

import re
import asyncio
from agents.llm_agent_autogen import LLMAgentV04
from agents.kg_agent import KGClient, CY_DDI, CY_CONTRA, CY_DRUG_INDICATIONS, CY_DRUG_INGREDIENTS, CY_INGREDIENT_INTERACTIONS, CY_DRUG_EXISTS
from agents.evaluator_agent import (
    enforce_evidence, 
    format_drug_ingredients, 
    format_ingredient_interactions,
    format_complete_ingredient_analysis
)
from agents.ingredient_analyzer import IngredientAnalyzer
from agents.verification_agent import VerificationAgent  # NEW: Phase 3
from agents.hallucination_metric import hallucination_detector  # NEW: Phase 6
from agents.config import LLM_MODEL, OLLAMA_MODEL, GROQ_API_KEY, GROQ_MODEL
from agents.narrative_trace import generate_narrative_trace

# Autogen imports
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.ollama import OllamaChatCompletionClient


# -----------------------------
# Normalization helpers
# -----------------------------
def normalize_drug_name(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    known_drugs = ["warfarin", "fluconazole", "imatinib", "cisplatin", "paclitaxel", "doxorubicin", "erlotinib"]
    for drug in known_drugs:
        if drug in text:
            return drug.capitalize()
    return text.title()


def normalize_condition(text: str) -> str:
    if not text:
        return ""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    known_conditions = ["thrombosis", "leukemia", "fungal infection"]
    for cond in known_conditions:
        if cond in text:
            return cond.title()
    return text.title()


# -----------------------------
# ReasonerAgent (async-safe for Streamlit) - Supports Ollama and Groq
# -----------------------------
class ReasonerAgent:
    def __init__(self):
        """Initialize Reasoner with selected LLM provider."""
        try:
            if LLM_MODEL == "groq":
                # Use Groq API
                from groq import Groq
                if not GROQ_API_KEY:
                    raise ValueError("GROQ_API_KEY not found in environment")
                self.client = Groq(api_key=GROQ_API_KEY)
                self.model = GROQ_MODEL
                self.provider = "groq"
                self.agent = None  # Not used for Groq
                print(f"[Reasoner Agent] Using Groq provider with model: {self.model}")
            else:
                # Default to Ollama
                self.model_client = OllamaChatCompletionClient(model=OLLAMA_MODEL)
                self.agent = AssistantAgent(
                    name="ReasonerAgent",
                    model_client=self.model_client,
                    system_message=(
                        "You are a concise clinical pharmacology assistant. "
                        "Given KG evidence (including drug-drug and ingredient-ingredient interactions) and a user question, "
                        "explain in 2–4 sentences the pharmacological reasoning and one actionable clinical recommendation. "
                        "Be concise, factual, and medically sound. If ingredient-level interactions are provided, "
                        "explain how they contribute to the overall drug interaction."
                    ),
                )
                self.model = OLLAMA_MODEL
                self.provider = "ollama"
                print(f"[Reasoner Agent] Using Ollama provider with model: {self.model}")
        except Exception as e:
            print(f"[Reasoner Agent] Init error: {e}")
            self.agent = None
            self.provider = None
        self._loop = None  # persistent event loop for Ollama

    def reason(self, evidence_text: str, query: str) -> str:
        """Run reasoning safely across Streamlit reruns."""
        if self.provider == "groq":
            # Groq API call (synchronous)
            try:
                prompt = (
                    f"User question: {query}\n\n"
                    f"KG Evidence:\n{evidence_text}\n\n"
                    "Explain the pharmacological reasoning and one clinical recommendation."
                )
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a concise clinical pharmacology assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[Reasoner Agent] Groq error: {e}")
                return f"(⚠️ Reasoning failed: {e})"
        
        elif self.provider == "ollama":
            # Ollama (async with persistent loop)
            if not self.agent:
                return "(⚠️ Reasoner unavailable — KG evidence only.)"

            async def _run_async():
                prompt = (
                    f"User question: {query}\n\n"
                    f"KG Evidence:\n{evidence_text}\n\n"
                    "Explain the pharmacological reasoning and one clinical recommendation."
                )
                return await self.agent.run(task=prompt)

            try:
                import threading

                # Reuse or create event loop
                if not self._loop or self._loop.is_closed():
                    self._loop = asyncio.new_event_loop()
                    threading.Thread(target=self._loop.run_forever, daemon=True).start()

                future = asyncio.run_coroutine_threadsafe(_run_async(), self._loop)
                result = future.result(timeout=120)

                # Extract text content
                if hasattr(result, "messages"):
                    texts = [m.content for m in result.messages if isinstance(m, TextMessage)]
                    return texts[-1] if texts else str(result)
                return str(result)
            except Exception as e:
                print(f"[Reasoner Agent] Ollama error: {e}")
                return f"(⚠️ Reasoning failed: {e})"
        else:
            return "(⚠️ Reasoner unavailable — no valid provider configured.)"


# -----------------------------
# Main Pipeline
# -----------------------------
class Pipeline:
    def __init__(self):
        self.llm = LLMAgentV04()
        self.kg = KGClient()
        self.reasoner = ReasonerAgent()
        self.ingredient_analyzer = IngredientAnalyzer()  # Phase 2
        self.verifier = VerificationAgent()  # NEW: Phase 3

    def answer(self, question: str) -> str:
        # Step 1: Slot extraction
        slots = self.llm.extract_slots(question)
        slots["drug1"] = normalize_drug_name(slots.get("drug1", ""))
        slots["drug2"] = normalize_drug_name(slots.get("drug2", ""))
        if "condition" in slots:
            slots["condition"] = normalize_condition(slots.get("condition", ""))

        kind = slots.get("kind", "ddi")

        # -----------------------------
        # Intelligent KG Query Routing
        # -----------------------------
        rows = []
        ing_rows = []  # Initialize to avoid UnboundLocalError
        ing_int_rows = []  # Initialize to avoid UnboundLocalError
        evidence_text = ""
        ingredient_text = ""
        ingredient_interaction_text = ""
        _ingredient_analysis_for_trace = None  # captured once for Narrative Trace

        if kind == "contra" and slots.get("condition"):
            # Handle open-ended "what is X used for?" queries
            if slots.get("condition", "").lower() in ["indication", "indications", "used for"]:
                rows = self.kg.query(CY_DRUG_INDICATIONS, {"drug": slots.get("drug1", "")})
                if rows:
                    conditions = ", ".join([r.get("condition") for r in rows])
                    evidence_text = f"✅ Based on KG (indications): {slots.get('drug1')} is used to treat: {conditions}"
                else:
                    evidence_text = f"⚠️ No indications found in KG for {slots.get('drug1')}."
            else:
                # Specific drug-condition query
                rows = self.kg.query(CY_CONTRA, {"drug": slots.get("drug1", ""), "cond": slots.get("condition", "")})
                if rows:
                    evidence_text = enforce_evidence(rows, "contra")
                else:
                    evidence_text = f"{slots.get('drug1')} is used in {slots.get('condition')} (no contraindication flagged)."
        else:
            # Query drug-drug interactions
            rows = self.kg.query(CY_DDI, {"drug1": slots.get("drug1", ""), "drug2": slots.get("drug2", "")})

            # ✅ Exact-match filtering (avoid unrelated DDIs)
            drug1 = slots.get("drug1", "").lower()
            drug2 = slots.get("drug2", "").lower()
            filtered = [
                r for r in rows
                if {r.get('drug_a', '').lower(), r.get('drug_b', '').lower()} == {drug1, drug2}
            ]

            if filtered:
                rows = filtered
                evidence_text = enforce_evidence(rows, "ddi")
            else:
                # No interaction found - verify drugs exist (NEW - Phase 6)
                drug1_exists = self.kg.query(CY_DRUG_EXISTS, {"drug": slots.get("drug1", "")})
                drug2_exists = self.kg.query(CY_DRUG_EXISTS, {"drug": slots.get("drug2", "")})
                
                if drug1_exists and drug2_exists:
                    # Both drugs exist but no interaction documented
                    rows = []
                    evidence_text = (
                        f"✅ **No Interaction Found in Knowledge Graph**\n\n"
                        f"Both {slots.get('drug1')} and {slots.get('drug2')} are in our database, but "
                        f"no drug-drug interaction has been documented in our knowledge graph.\n\n"
                        f"**Important Notes:**\n"
                        f"- This does NOT mean the drugs are definitely safe together\n"
                        f"- This means we lack interaction data in our current dataset\n"
                        f"- Always consult a healthcare provider for clinical guidance\n"
                    )
                else:
                    # One or both drugs not found
                    missing = []
                    if not drug1_exists: missing.append(slots.get("drug1", ""))
                    if not drug2_exists: missing.append(slots.get("drug2", ""))
                    rows = []
                    evidence_text = f"⚠️ Drug(s) not found in knowledge graph: {', '.join(missing)}"

            # ✅ Enhanced Ingredient-Level Analysis with Quantitative Contributions
            if drug1 and drug2:
                # Run complete ingredient analysis (result also feeds Narrative Trace — no duplicate call needed)
                ingredient_analysis = self.ingredient_analyzer.analyze_drug_interaction(drug1, drug2)
                _ingredient_analysis_for_trace = ingredient_analysis  # ← captured once here

                # Format the beautiful output
                if ingredient_analysis.get('total_interactions', 0) > 0:
                    ingredient_text = format_complete_ingredient_analysis(
                        ingredient_analysis,
                        slots.get('drug1', drug1),
                        slots.get('drug2', drug2)
                    )
                else:
                    # Fallback to basic ingredient display if no interactions found
                    ing_rows = self.kg.query(CY_DRUG_INGREDIENTS, {"drug": drug1})
                    ing_rows += self.kg.query(CY_DRUG_INGREDIENTS, {"drug": drug2})

                    if ing_rows:
                        ingredient_text = "\n\n📋 **Drug Ingredients:**" + format_drug_ingredients(ing_rows)

        # -----------------------------
        # Step 2: Handle missing evidence gracefully
        # -----------------------------
        if not rows and not ing_rows:
            theory = self.reasoner.reason(
                f"No KG evidence found for {slots.get('drug1')} and {slots.get('drug2')}.",
                question,
            )
            return f"{evidence_text}\n\n🧠 Clinical Insight:\n{theory}"

        # -----------------------------
        # Step 3: Prepare concise KG evidence for reasoning
        # -----------------------------
        if kind == "contra":
            concise_evidence = "\n".join(f"{r.get('drug')} is used in {r.get('condition')}" for r in rows)
        else:
            concise_evidence = "\n".join(
                f"{r.get('drug_a')} ↔ {r.get('drug_b')} | Severity: {r.get('severity')} | Mechanism: {r.get('mechanism')}"
                for r in rows
            )
            
            # Add ingredient interaction evidence to reasoning context
            if kind == "ddi" and drug1 and drug2:
                ing_analysis = self.ingredient_analyzer.analyze_drug_interaction(drug1, drug2)
                if ing_analysis.get('total_interactions', 0) > 0:
                    # Add primary interactions to reasoning context
                    primary_ings = ing_analysis.get('contributions', {}).get('primary', [])
                    if primary_ings:
                        ing_evidence = "\n".join(
                            f"{i.get('ingredient_a')} ↔ {i.get('ingredient_b')} | {i.get('severity')} | {i.get('mechanism')} | Contribution: {pct:.1f}%"
                            for i, pct in primary_ings
                        )
                        concise_evidence += f"\n\nPrimary ingredient-level interactions:\n{ing_evidence}"

        # -----------------------------
        # Step 4: Generate Reasoning
        # -----------------------------
        theory = self.reasoner.reason(concise_evidence, question)
        
        # -----------------------------
        # Step 5: Verify LLM Output (Phase 3 MVP)
        # -----------------------------
        hallucination_result = None
        verification_status  = None

        if kind == "ddi" and rows:  # Only verify DDI queries with KG evidence
            # Run verification
            context = {
                'drug1': slots.get('drug1', ''),
                'drug2': slots.get('drug2', ''),
                'kg_rows': rows
            }
            claims       = self.verifier.extract_key_claims(theory, context)
            verification = self.verifier.verify_against_kg(claims, context)
            verification_status = verification.get('overall_status')
            theory = self.verifier.format_verified_output(theory, verification)

            # Calculate hallucination metric (Phase 6)
            hallucination_result = hallucination_detector.calculate_hallucination_score(
                theory,
                slots.get('drug1', ''),
                slots.get('drug2', ''),
                rows
            )
            
            # Build a prominent, clearly visible hallucination score block
            score      = hallucination_result['hallucination_score']
            total      = hallucination_result['total_claims']
            verified   = hallucination_result['verified_claims']
            unverified = hallucination_result['unverified_claims']
            
            # Determine score level, badge, progress bar, and advice
            if score == 0:
                badge        = "✅ FULLY VERIFIED"
                score_label  = "0%  — All claims are KG-grounded"
                progress     = "🟢🟢🟢🟢🟢🟢🟢🟢🟢🟢  0%"
                advice       = "The response is fully grounded in the Knowledge Graph. Safe to use."
                risk         = "✅ None"
            elif score <= 30:
                badge        = "⚠️ PARTIALLY VERIFIED"
                score_label  = f"{score}%  — Some claims may not be KG-grounded"
                dots         = int(score / 10)
                progress     = "🟡" * dots + "⬜" * (10 - dots) + f"  {score}%"
                advice       = "Minor risk. A few LLM claims could not be confirmed in the KG. Verify with a healthcare provider."
                risk         = "⚠️ Low"
            elif score <= 70:
                badge        = "⚠️ SIGNIFICANTLY HALLUCINATED"
                score_label  = f"{score}%  — Many claims are NOT in the KG"
                dots         = int(score / 10)
                progress     = "🟠" * dots + "⬜" * (10 - dots) + f"  {score}%"
                advice       = "High risk. Significant portion of the response was not verified against KG. Use with caution."
                risk         = "⚠️ High"
            else:
                badge        = "❌ HIGHLY HALLUCINATED"
                score_label  = f"{score}%  — Response largely fabricated"
                dots         = int(score / 10)
                progress     = "🔴" * dots + "⬜" * (10 - dots) + f"  {score}%"
                advice       = "Critical risk. Most of the response could not be verified. Do NOT use without expert review."
                risk         = "❌ Critical"

            metric_block = (
                f"\n\n---\n"
                f"## 📊 Hallucination Detection Report\n\n"
                f"| 🔍 Field            | 📋 Detail                                              |\n"
                f"|---------------------|--------------------------------------------------------|\n"
                f"| **Verdict**         | {badge}                                                |\n"
                f"| **Score**           | {score_label}                                          |\n"
                f"| **Risk Level**      | {risk}                                                 |\n"
                f"| **Progress Bar**    | {progress}                                             |\n"
                f"| **Total Claims**    | 🔢 {total} claim(s) identified in response            |\n"
                f"| **KG-Verified**     | ✅ {verified} claim(s) confirmed by Knowledge Graph   |\n"
                f"| **Unverified**      | ⚠️  {unverified} claim(s) not found in Knowledge Graph |\n"
                f"| **Formula**         | Score = ({unverified} ÷ {total}) × 100 = **{score}%** |\n\n"
                f"> 💡 **Interpretation:** {advice}\n\n"
                f"---\n"
            )
            theory += metric_block
            # _ingredient_analysis_for_trace already set earlier — no duplicate KG call needed

        # -----------------------------
        # Step 6: Generate Narrative Reasoning Trace
        # -----------------------------
        narrative = generate_narrative_trace(
            drug1=slots.get('drug1', ''),
            drug2=slots.get('drug2', ''),
            kg_rows=rows,
            ingredient_analysis=_ingredient_analysis_for_trace,
            hallucination_result=hallucination_result,
            verification_status=verification_status,
        )

        # Combine all evidence
        final_answer = evidence_text
        
        # Add ingredient analysis if available
        if ingredient_text:
            final_answer += ingredient_text
        
        # Add clinical reasoning (with verification + hallucination report if DDI)
        final_answer += f"\n\n{theory}"

        # Append Narrative Reasoning Trace
        final_answer += narrative
        
        return final_answer


# Singleton instance
PIPELINE = Pipeline()
