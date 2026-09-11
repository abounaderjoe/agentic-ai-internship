# Agentic AI Internship — Environment Setup

This folder is scaffolded for Step 1 of the onboarding roadmap. Python 3.12 is
already on this machine (confirmed from your other PyCharm project), so you
just need a fresh virtual environment for this project.

## 1. Open a terminal in this folder

In PyCharm: right-click the project root -> **Open in Terminal**.
Or open Windows Terminal / PowerShell and `cd` into this folder.

## 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

(If PyCharm opens this folder as a project, it will usually offer to create
the venv for you automatically and you can skip this step.)

## 3. Install the packages

```powershell
pip install -r requirements.txt
```

## 4. Set up your API keys

1. Create a free account at https://console.groq.com/home, go to **API Keys**,
   and generate a key.
2. Create a free account at https://smith.langchain.com/ for tracing.
3. Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```
4. Open `.env` and paste your real Groq and LangSmith keys in
   (never commit `.env` — it's already in `.gitignore`).

## 5. Test it

```powershell
python exercise1_simple_chain.py
```

You should see a French translation printed. That's Exercise 1 (Step 4) done —
it's already the "simple chain with ChatGroq" exercise from the roadmap.

## Next up
- Step 3: work through the LangGraph learning path (see roadmap.md in your
  Claude project "ai interniship").
- Exercise 2: RAG implementation.
- Exercise 3: Multi-node LangGraph.
- Exercise 4: Agent with tools.
- Project 1: Multi-agent system with a Supervisor.
