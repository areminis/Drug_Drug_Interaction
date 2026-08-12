# 🧬 Oncology DDI Chatbot — AutoGen v0.4 + Neo4j + Ollama

A local Conversational AI system integrating an open-source LLM (via Ollama) with a Knowledge Graph of oncology drug-drug interactions.

---

## 🧰 Requirements
- Windows 10 / 11
- Python 3.11+
- Neo4j Desktop (port 7687)
- Ollama installed (`ollama pull llama3.2`)

---

## ⚙️ Setup
```powershell
python -m venv Autogen
Autogen\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
