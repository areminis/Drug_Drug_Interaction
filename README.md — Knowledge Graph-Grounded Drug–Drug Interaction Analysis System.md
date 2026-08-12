# Knowledge Graph-Grounded Drug–Drug Interaction Analysis System

An explainable **Drug–Drug Interaction (DDI) analysis system** that combines a **Neo4j Knowledge Graph, Large Language Models (LLMs), ingredient-level analysis, and knowledge-grounded verification** to identify potential medication interactions while reducing unsupported LLM-generated claims.

The project explores a central question:

> **How can a domain-specific Knowledge Graph be used as a grounding and verification layer to make LLM-generated healthcare information more reliable and explainable?**

---

## Project Overview

Large Language Models can generate useful natural-language explanations, but they may also produce information that is not supported by the underlying data.

This project addresses that problem by placing a **Knowledge Graph validation layer around the LLM workflow**.

Instead of allowing the LLM to act as the primary source of drug-interaction information, the system first retrieves structured evidence from a Neo4j Knowledge Graph.

The LLM is then used to generate a readable explanation from that evidence, and a separate verification component compares generated claims back against the Knowledge Graph.

The system also performs **ingredient-level interaction analysis** and produces a **Narrative Reasoning Trace** describing the major processing and verification stages.

---

# Core Architecture

```text
                    ┌──────────────────────┐
                    │      User Query      │
                    │ "Does Drug A interact│
                    │     with Drug B?"    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Query Processing   │
                    │ Drug Entity Mapping  │
                    └──────────┬───────────┘
                               │
                               ▼
              ┌────────────────────────────────┐
              │     Neo4j Knowledge Graph      │
              │                                │
              │ Drugs • Ingredients            │
              │ Interactions • Conditions      │
              │ Severity • Mechanisms          │
              └───────────────┬────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   KG Validation     │
                    │ Is evidence present?│
                    └─────────┬───────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
                   NO                   YES
                    │                    │
                    ▼                    ▼
          ┌──────────────────┐   ┌────────────────────┐
          │ Stop / Return    │   │ Retrieve Verified  │
          │ No KG Evidence   │   │ KG Evidence        │
          └──────────────────┘   └─────────┬──────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ Ingredient-Level     │
                               │ Interaction Analysis │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │     LLM Layer        │
                               │ Ollama / Groq        │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ Verification Agent   │
                               │ Compare LLM Claims   │
                               │ Against KG Evidence  │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │ Narrative Reasoning  │
                               │        Trace         │
                               └──────────┬───────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │   Streamlit Output   │
                               └──────────────────────┘
```

---

# Key Features

### Knowledge Graph-Grounded Interaction Detection

Drug-interaction information is stored and retrieved from **Neo4j** rather than relying solely on the pretrained knowledge of an LLM.

The graph contains structured information about:

- Drugs
- Ingredients
- Medical conditions
- Drug–drug interactions
- Ingredient–ingredient interactions
- Interaction severity
- Interaction mechanisms
- Drug indications

---

### Hallucination-Control Layer

The system uses the Knowledge Graph as a controlled evidence source.

Before generating an interaction explanation, the pipeline checks whether relevant information exists in the graph.

```text
User Query
    ↓
KG Lookup
    ↓
Evidence Available?
   /           \
 NO             YES
 ↓               ↓
Stop         Continue
 ↓               ↓
No verified   LLM receives
KG evidence   grounded evidence
```

This reduces the opportunity for the LLM to generate unsupported interaction information.

---

### Post-Generation Verification

Grounding is also performed after generation.

The **Verification Agent** evaluates generated claims against the Knowledge Graph.

Examples of claims that can be checked include:

- Drug pair
- Interaction severity
- Interaction mechanism
- Supporting KG evidence

This creates two layers of control:

```text
PRE-GENERATION
KG Grounding
      ↓
LLM Generation
      ↓
POST-GENERATION
KG Verification
```

---

### Ingredient-Level Interaction Analysis

The system goes beyond drug-level interactions by examining the ingredients associated with each medication.

For example:

```text
Drug A
  ↓
Ingredient A
  ↓
INTERACTS_WITH
  ↓
Ingredient B
  ↑
Drug B
```

The ingredient analyzer identifies relevant ingredient pairs and calculates their relative contribution to the interaction.

This allows the system to provide more detailed explanations of why two medications may interact.

---

### Narrative Reasoning Trace

The application generates a human-readable trace describing what occurred during the processing pipeline.

The trace can include:

1. Knowledge Graph search
2. Interaction evidence retrieved
3. Ingredient records retrieved
4. Ingredient contribution analysis
5. Comparison of generated claims with KG evidence
6. Final verification result

This provides **application-level explainability** without exposing hidden LLM chain-of-thought.

---

### Dual LLM Support

The system supports two LLM execution options:

**Ollama**

- Local model execution
- Useful for local development and experimentation

**Groq**

- Cloud-based LLM inference
- Accessed through the Groq API
- Provides faster hosted inference

The LLM is used primarily for **natural-language explanation**, while Neo4j remains the structured evidence source.

---

# Technology Stack

| Technology | Purpose |
|---|---|
| **Python** | Core application and pipeline logic |
| **Neo4j** | Knowledge Graph database |
| **Cypher** | Querying graph relationships |
| **AutoGen AgentChat** | Agent-based pipeline components |
| **Ollama** | Local LLM inference |
| **Groq API** | Cloud-based LLM inference |
| **Streamlit** | Interactive web application |
| **CSV** | Source datasets |
| **python-dotenv** | Environment configuration |

---

# Knowledge Graph Dataset

The current prototype contains:

- **30 drugs**
- **30 ingredients**
- **10 medical conditions**
- **30 drug–ingredient mappings**
- **19 ingredient–ingredient interactions**
- **19 drug–drug interactions**
- **20 drug–condition relationships**
- **25+ predefined test questions**

The dataset is intentionally limited and designed for research/prototype evaluation rather than comprehensive clinical coverage.

---

# Example Query

```text
Does Fluconazole interact with Warfarin?
```

The system first queries Neo4j.

Example KG evidence:

```text
Fluconazole ↔ Warfarin

Severity: Major
Mechanism: CYP2C9 inhibition
```

The application then retrieves the corresponding ingredient information.

```text
Fluconazole
     ↓
Fluconazole

Warfarin
     ↓
Warfarin Sodium
```

Ingredient-level interaction relationships are analyzed before the evidence is passed to the LLM.

---

# Example Processing Flow

```text
"Does Fluconazole interact with Warfarin?"
                    ↓
          Identify Drug Entities
                    ↓
          Query Neo4j with Cypher
                    ↓
        Retrieve Interaction Evidence
                    ↓
        Retrieve Ingredient Records
                    ↓
       Analyze Ingredient Interaction
                    ↓
        Generate LLM Explanation
                    ↓
       Verification Agent Checks
          Claims Against Neo4j
                    ↓
       Generate Reasoning Trace
                    ↓
          Display Final Result
```

---

# Project Structure

```text
AutoGen_project/
│
├── ui_streamlit.py
│   └── Main Streamlit application
│
├── requirements.txt
├── .env
├── README.md
├── TESTING_QUESTIONS.md
│
├── agents/
│   │
│   ├── pipeline.py
│   │   └── Main pipeline orchestration
│   │
│   ├── kg_agent.py
│   │   └── Neo4j/Cypher interaction retrieval
│   │
│   ├── llm_agent_autogen.py
│   │   └── LLM interface
│   │
│   ├── ingredient_analyzer.py
│   │   └── Ingredient-level analysis
│   │
│   ├── verification_agent.py
│   │   └── KG-based LLM verification
│   │
│   └── evaluator_agent.py
│       └── Output evaluation/formatting
│
├── data/
│   │
│   ├── drugs.csv
│   ├── ingredients.csv
│   ├── interactions.csv
│   ├── ingredient_interactions.csv
│   ├── drug_ingredients.csv
│   ├── conditions.csv
│   └── indications.csv
│
└── kg/
    └── load_kg.py
        └── Loads structured data into Neo4j
```

---

# Installation

## 1. Clone the Repository

```bash
git clone <repository-url>
cd AutoGen_project
```

---

## 2. Create a Virtual Environment

```bash
python -m venv Autogen
```

### Windows PowerShell

```bash
.\Autogen\Scripts\Activate.ps1
```

### Windows Command Prompt

```bash
.\Autogen\Scripts\activate.bat
```

### macOS/Linux

```bash
source Autogen/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Neo4j Setup

The application requires a running Neo4j database.

You can use either:

- Neo4j Desktop
- Neo4j AuraDB

Typical local configuration:

```text
URI: bolt://localhost:7687
Username: neo4j
Password: <your-password>
```

---

# Environment Configuration

Create a `.env` file in the project root.

Example:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

LLM_MODEL=ollama

OLLAMA_MODEL=llama3.2
```

For Groq:

```env
LLM_MODEL=groq
GROQ_API_KEY=your_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

> Never commit `.env` or API credentials to a public repository.

---

# Load the Knowledge Graph

After configuring Neo4j, load the project data:

```bash
python kg/load_kg.py
```

Expected dataset:

```text
30 drugs
30 ingredients
10 conditions
30 drug-ingredient mappings
19 ingredient interactions
19 drug-drug interactions
20 drug-condition relationships
```

---

# Run the Application

Start the Streamlit application:

```bash
streamlit run ui_streamlit.py
```

Then open the local Streamlit address displayed in the terminal.

---

# Example Questions

### Drug Interactions

```text
Does Fluconazole interact with Warfarin?

What happens if I take Warfarin with Ibuprofen?

Is Cisplatin safe with Gentamicin?

Can I combine Prednisone and Aspirin?
```

### Drug Indications

```text
What is Paclitaxel used for?

Is Warfarin used for Thrombosis?

What does Imatinib treat?
```

Additional validated queries are available in:

```text
TESTING_QUESTIONS.md
```

---

# Main Pipeline Components

## KG Agent

`agents/kg_agent.py`

Responsible for retrieving structured evidence from Neo4j using Cypher queries.

---

## Ingredient Analyzer

`agents/ingredient_analyzer.py`

Retrieves drug ingredients, identifies ingredient-level interactions, and calculates their relative contribution to an interaction.

---

## LLM Agent

`agents/llm_agent_autogen.py`

Interfaces with the configured LLM provider.

Supported options:

```text
Ollama → Local inference

Groq → Cloud/API inference
```

---

## Verification Agent

`agents/verification_agent.py`

Compares generated claims with evidence retrieved from the Knowledge Graph.

Its purpose is to identify whether generated information is supported by the controlled knowledge source.

---

## Evaluator Agent

`agents/evaluator_agent.py`

Supports evaluation and formatting of the final output.

---

## Pipeline

`agents/pipeline.py`

Coordinates the major components:

```text
Query
  ↓
KG Retrieval
  ↓
Ingredient Analysis
  ↓
LLM
  ↓
Verification
  ↓
Evaluation
  ↓
Final Response
```

---

# Why This Is Different From a Standard LLM Chatbot

A conventional chatbot can generate an answer directly from an LLM:

```text
Question → LLM → Answer
```

This project introduces a structured evidence layer:

```text
Question
   ↓
Knowledge Graph
   ↓
Evidence Retrieval
   ↓
LLM Explanation
   ↓
KG Verification
   ↓
Final Answer
```

The distinction is that the **LLM is not treated as the primary source of factual drug-interaction knowledge**.

Neo4j provides the controlled evidence, while the LLM is primarily responsible for generating a readable explanation from that evidence.

---

# Limitations

The current system is a research prototype.

Important limitations include:

- Limited number of drugs and interactions
- Knowledge Graph coverage determines what can be verified
- Missing KG evidence does not necessarily mean a real-world interaction does not exist
- The prototype has not been clinically validated
- Results should not be interpreted as medical advice
- The system is not intended to replace pharmacists, physicians, or validated clinical decision-support systems

---

# Future Work

Potential extensions include:

- Expand the Knowledge Graph with larger validated pharmaceutical datasets
- Improve drug-name normalization and entity mapping
- Add additional interaction mechanisms and evidence sources
- Improve quantitative hallucination evaluation
- Evaluate the system on larger test sets
- Add automated KG update pipelines
- Improve evidence provenance and citation tracking
- Containerize the application with Docker
- Deploy the application to a managed cloud environment
- Evaluate scalability with larger Neo4j datasets
- Conduct expert evaluation with healthcare professionals

---

# Research Focus

The broader research direction of this project is:

> **Using domain-specific Knowledge Graphs as grounding and verification layers to reduce unsupported generation in Large Language Model applications.**

The drug–drug interaction domain serves as the experimental application for evaluating this architecture.

---

# Disclaimer

This project is intended for **research and educational purposes only**.

It is not a clinically validated drug-interaction system and should not be used to make medical decisions. Always consult qualified healthcare professionals and validated clinical resources for medication-related decisions.