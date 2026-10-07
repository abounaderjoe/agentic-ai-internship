# Recording Script: Testing Each Agent

One screen recording per agent. Each clip shows the agent working in the chat app, then the
matching trace in LangSmith.

## Before you start recording

1. **Postgres must be running.** It already runs locally on port 5432 on this PC.
2. **Start the app.** In a terminal inside this folder:
   ```powershell
   .venv\Scripts\activate
   streamlit run capstone_app.py
   ```
   It opens at http://localhost:8501. The first start can take a minute.
3. **Open LangSmith** in a second browser tab: https://smith.langchain.com, then go to
   **Tracing Projects → `agentic-ai-internship`**.
4. **Start recording:** press **Win + Shift + R** (Snipping Tool), drag over the whole screen,
   then click **Start**. Click **Stop** when the clip is done and save it.

## Rules while recording

- **Start a new chat for every clip** (the **+ New chat** button in the sidebar). This keeps each
  LangSmith trace clean.
- **Wait about 1 minute between prompts.** The free Groq plan only allows 8,000 tokens per
  minute. If you send prompts too fast, the app shows a `RateLimitError`. If that happens, wait a
  minute and send the prompt again.
- **Don't test before recording.** The free plan also caps usage at 200,000 tokens per day, and
  every test run uses part of the same budget you need for the clips. If the error says
  `tokens per day (TPD)`, stop and continue later. The budget refills at about 8,000 tokens per
hour. All six clips together use about 35,000 tokens (each prompt is about 3,000–7,500).
- After the answer appears, switch to the LangSmith tab, refresh, and click the **newest trace**
  at the top.

## What to show in LangSmith (every clip)

1. The trace list in `agentic-ai-internship`, with the newest run at the top.
2. Click it to open the **trace tree** on the left. Point out:
   - **`supervisor`**: the routing step. Click its LLM call to show the `next` agent it chose and
     the `instructions` it passed on.
   - **The specialist node**, for example `sql_query_agent`, and what it returned.
   - The **supervisor running again** at the end, then finishing.
3. The **latency** and **token count** at the top of the trace.

---

## Clip 1: Supervisor + `conversation_agent`

**Type:**
> Hi! What kinds of things can you help me with?

**Expected:** A friendly reply.

**In LangSmith:** `supervisor` → `conversation_agent` → `supervisor` (finish).

---

## Clip 2: `rag_agent` (answers from the internal docs)

**Type:**
> According to the internal docs, how do run names and tags work in LangSmith tracing?

**Expected:** An explanation of `run_name` and `tags` passed through `config` in `.invoke()`,
with a code example.

**In LangSmith:** `supervisor` → `rag_agent`. Open `rag_agent` and show the **retriever** step:
the doc chunks it found (from `03_langsmith_tracing.md`) that were passed to the LLM.

---

## Clip 3: `sql_query_agent` (sales database)

**Type:**
> Who are the top 3 customers by total amount spent on completed orders?

**Expected:** Marcus Webb ($698.00), Daniel Kim ($563.00), Priya Nair ($311.94), plus the SQL
that was used.

**In LangSmith:** `supervisor` → `sql_query_agent`. Open it and show the **two LLM calls**: the
first writes the SQL query, the second explains the results in plain English.

---

## Clip 4: `visualization_agent` (charts)

Two prompts, so the clip shows both ways this agent is used. Wait 1 minute between them.

**Prompt A (data given directly):**
> Make a bar chart of this data: Monday 12, Tuesday 18, Wednesday 9, Thursday 15

**Expected:** A bar chart appears, plus one sentence describing it.

**In LangSmith:** `supervisor` → `visualization_agent` only. Show the LLM call that produced the
chart JSON (`type`, `labels`, `data`).

**Prompt B (Supervisor chains two agents):**
> Show me a pie chart of total revenue by product category

**Expected:** A pie chart of Furniture / Electronics / Stationery revenue.

**In LangSmith:** `supervisor` → `sql_query_agent` → `supervisor` → `visualization_agent`. This
is the best clip for showing the Supervisor **coordinating several agents**: the chart agent
can't fetch data, so the Supervisor gets the numbers from SQL first.

---

## Clip 5: `web_research_team` (live web search sub-team)

**Type:**
> What are the latest discoveries from the James Webb Space Telescope?

Avoid topics like LangGraph or LangChain for this clip. The Supervisor may also send those to
`rag_agent`, whose "I don't know" can replace the web report.

**Expected:** A short report with clickable source links. Takes 30–60 seconds.

**In LangSmith:** `supervisor` → `web_research_team`. Expand it to show the **nested sub-graph**:
`sub_supervisor` → `researcher` (the DuckDuckGo search results) → `sub_supervisor` → `writer`
(the final report). This shows the team has its own internal supervisor.

---

## Clip 6: `remember_fact` (memory across chats)

**In a new chat, type:**
> Please remember that my favourite chart type is a pie chart

**Expected:** A short confirmation, such as "Sure thing, I'll keep in mind that your favourite
chart type is a pie chart!"

**Then click + New chat, wait 1 minute, and type:**
> What's my favourite chart type?

**Expected:** "Your favourite chart type is a pie chart." This is a brand-new chat, so it proves
the memory is saved in the database, not just kept inside one conversation.

**In LangSmith:**
- **First trace:** `supervisor` → `remember_fact`, which saves the fact to Postgres. Then
  `conversation_agent` writes the friendly confirmation.
- **Second trace:** open the first `supervisor` LLM call and look at its input messages. There is a
  system message saying "Known facts about the user from past conversations: …". That is the
  saved memory being loaded into the new chat.
