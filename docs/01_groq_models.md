# Groq Models

Groq serves open-weight models through an OpenAI-compatible API, and is known
for very low inference latency because it runs models on custom LPU (Language
Processing Unit) hardware instead of GPUs.

As of September 2026, the models confirmed live on the Groq API (via the
`/openai/v1/models` endpoint) include:

- `openai/gpt-oss-120b` — OpenAI's larger open-weight model. Best general
  quality, higher latency than the 20b variant.
- `openai/gpt-oss-20b` — smaller sibling of gpt-oss-120b. Faster and cheaper,
  slightly lower quality on complex reasoning tasks.
- `openai/gpt-oss-safeguard-20b` — a safety/moderation-tuned variant.
- `qwen/qwen3.8-27b` — Alibaba's Qwen model family, a different architecture
  from the GPT-OSS models, useful as a quality/style comparison point.
- `groq/compound` and `groq/compound-mini` — Groq's own agentic system with
  built-in web search and code execution tools.
- `whisper-large-v3` and `whisper-large-v3-turbo` — speech-to-text models,
  not for chat.

Groq deprecated `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` in June
2026. Older tutorials that reference those model names will fail — always
check the live `/models` endpoint before trusting a model name from a guide.

Because Groq does not offer an embeddings endpoint, RAG pipelines that use
Groq for generation still need a separate embedding provider (for example, a
local model via FastEmbed) to turn text into vectors for retrieval.
