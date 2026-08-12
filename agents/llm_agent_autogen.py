import asyncio
import json
import re
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.ollama import OllamaChatCompletionClient
from agents.config import LLM_MODEL, OLLAMA_MODEL, GROQ_API_KEY, GROQ_MODEL


# ---------------------------------------------------------------------------
# ✅ Async helper — runs safely under both normal Python and Streamlit threads
# ---------------------------------------------------------------------------
# def _def(coro):
#     try:
#         loop = asyncio.get_running_loop()
#     except RuntimeError:
#         loop = None

#     if loop and loop.is_running():
#         # If Streamlit already has a running event loop
#         return asyncio.run_coroutine_threadsafe(coro, loop).result()
#     else:
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         result = loop.run_until_complete(coro)
#         loop.close()
#         return result

# def _def(coro):
#     try:
#         loop = asyncio.get_running_loop()
#     except RuntimeError:
#         loop = None

#     if loop and loop.is_running():
#         # Streamlit thread already has an active loop
#         return asyncio.run_coroutine_threadsafe(coro, loop).result()
#     else:
#         # Always create a fresh loop for new reruns
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         try:
#             result = loop.run_until_complete(coro)
#         finally:
#             loop.close()
#         return result

def _def(coro):
    """
    Runs async coroutines safely under Streamlit's rerun environment.
    Recreates event loops if closed or missing.
    """
    try:
        loop = asyncio.get_running_loop()
        if loop.is_closed():
            raise RuntimeError("Loop closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 🔍 Debug line: shows loop status every time
    print(f"[DEBUG] Loop alive: {loop.is_running()}, closed: {loop.is_closed()}")

    try:
        if loop.is_running():
            # If Streamlit already has a loop, run safely in thread
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
        else:
            return loop.run_until_complete(coro)
    finally:
        # Do NOT close the loop — keep it persistent across Streamlit reruns
        pass

# ---------------------------------------------------------------------------
# Prompt template (few-shot guidance)
# ---------------------------------------------------------------------------
SLOT_PROMPT = (
    "Extract interaction query slots and return STRICT JSON.\n"
    "Keys: kind in ['ddi','contra'], drug1, drug2 (optional), condition (optional).\n"
    "Q: Does Fluconazole interact with Warfarin?\n"
    "A: {\"kind\":\"ddi\",\"drug1\":\"Fluconazole\",\"drug2\":\"Warfarin\"}\n\n"
    "Q: Is Warfarin contraindicated for Thrombosis?\n"
    "A: {\"kind\":\"contra\",\"drug1\":\"Warfarin\",\"condition\":\"Thrombosis\"}"
)


# ---------------------------------------------------------------------------
# LLMAgentV04 — handles slot extraction using Ollama or Groq
# ---------------------------------------------------------------------------
class LLMAgentV04:
    def __init__(self):
        """Initialize LLM provider based on LLM_MODEL configuration."""
        if LLM_MODEL == "groq":
            # Use Groq API
            try:
                from groq import Groq
            except ImportError:
                raise ImportError("groq package not installed. Run: pip install groq")
            
            if not GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not found in environment. Please set it in .env file.")
            
            self.client = Groq(api_key=GROQ_API_KEY)
            self.model = GROQ_MODEL
            self.provider = "groq"
            print(f"[LLM Agent] Using Groq provider with model: {self.model}")
        else:
            # Default to Ollama (local)
            self.model_client = OllamaChatCompletionClient(model=OLLAMA_MODEL)
            self.agent = AssistantAgent(
                name="LLMAgent",
                model_client=self.model_client,
                system_message="You convert medical questions into structured KG query slots; respond only with JSON."
            )
            self.model = OLLAMA_MODEL
            self.provider = "ollama"
            print(f"[LLM Agent] Using Ollama provider with model: {self.model}")

    async def _extract_slots_async(self, user_text: str):
        """
        Use the LLM to extract query type and entities.
        Output must be a JSON dict with fields:
        - kind: 'ddi' or 'contra'
        - drug1: str
        - drug2 or condition: str
        """

        prompt = f"""
You are an intelligent slot extractor for an oncology drug–drug/condition interaction chatbot.

Given the user question below, identify:
1. Whether it is about a drug–drug interaction ('ddi')
2. Or about a drug–condition usage/contraindication ('contra')
3. Extract relevant entities.

IMPORTANT: Questions about "what is X used for" or "what does X treat" are 'contra' type queries about drug indications.

Respond ONLY in JSON like:
{{"kind": "ddi", "drug1": "Fluconazole", "drug2": "Warfarin"}}
or
{{"kind": "contra", "drug1": "Warfarin", "condition": "Thrombosis"}}

Examples:
- "Does Fluconazole interact with Warfarin?" → {{"kind": "ddi", "drug1": "Fluconazole", "drug2": "Warfarin"}}
- "Is Warfarin contraindicated for Thrombosis?" → {{"kind": "contra", "drug1": "Warfarin", "condition": "Thrombosis"}}
- "What is Paclitaxel used for?" → {{"kind": "contra", "drug1": "Paclitaxel", "condition": "indication"}}
- "Can Cisplatin treat Ovarian Cancer?" → {{"kind": "contra", "drug1": "Cisplatin", "condition": "Ovarian Cancer"}}

User question: "{user_text}"
"""

        try:
            if self.provider == "groq":
                # Groq API call
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You convert medical questions into structured KG query slots; respond only with JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=200
                )
                result = response.choices[0].message.content
            else:
                # Ollama (existing AutoGen code)
                result = await self.agent.run(task=prompt)
                
                # Extract raw text if result is a message object
                if hasattr(result, "messages"):
                    texts = [m.content for m in result.messages if isinstance(m, TextMessage)]
                    if texts:
                        result = texts[-1]

            # Parse JSON from result (same for both providers)
            json_text = re.search(r"\{.*\}", str(result), re.DOTALL)
            if json_text:
                return json.loads(json_text.group())
            else:
                return {"kind": "unknown"}
        except Exception as e:
            print(f"[LLM Agent] Slot extraction error ({self.provider}):", e)
            return {"kind": "unknown"}

    def extract_slots(self, user_text: str) -> dict:
        """Public method (sync-safe wrapper)."""
        return _def(self._extract_slots_async(user_text))
