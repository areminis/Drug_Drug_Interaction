"""
agents/config.py

Configuration loader for the Oncology DDI Chatbot.
Loads environment variables for Neo4j, Ollama, and Groq connections.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://localhost:7474")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# LLM Provider Selection (ollama or groq)
LLM_MODEL = os.getenv("LLM_MODEL", "ollama").lower()

# Ollama configuration (local LLM)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Groq configuration (API-based LLM)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
