import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# LLM Provider Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
# Ollama Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama:13b-instruct")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# GitHub Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "")

# Project Paths
BASE_DIR = Path(r"C:\Users\balas\Documents\Projects")
OUTPUT_DIR = BASE_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Agent Configuration
AGENT_VERBOSE = True
MAX_ITERATIONS = 15

# File Extensions for Different Project Types
PROJECT_EXTENSIONS = {
    "python": [".py", ".txt", ".md", ".yml", ".yaml", ".json"],
    "javascript": [".js", ".jsx", ".json", ".md", ".html", ".css"],
    "web": [".html", ".css", ".js", ".json", ".md"],
    "ml": [".py", ".ipynb", ".txt", ".md", ".pkl", ".h5"],
}

# Testing Configuration
TEST_TIMEOUT = 300
RUN_TESTS = True