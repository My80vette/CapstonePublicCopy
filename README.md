# Ingenuity AI SME — Retrieval-Augmented Landing Decision Support for NASA JPL

**A production RAG system built for Jet Propulsion Laboratory operators in 2023 — before "RAG" was a word most engineers had heard.**

> Senior Capstone · Embry-Riddle Aeronautical University (Prescott, AZ)
> Sponsor: NASA Jet Propulsion Laboratory · Program: `CESE-NASA-JPL-IngenuityHelicopterLandingSystem-F2023`
> Team of 5 · August 2023 – May 2024 · Shipped through release `1.4`

---

## What this is

An AI subject-matter-expert assistant that answers Ingenuity Mars Helicopter operational questions — including **go / no-go landing decisions** — grounded strictly in JPL's own technical documentation, with mandatory source citation on every claim.

An operator asks a question in natural language ("The helicopter is reporting a navigation camera fault mid-flight at 8m altitude, what do we do?"). The system retrieves the most relevant excerpts from the indexed JPL documentation corpus, forces the model to reason only from those excerpts, and returns a recommendation with the specific documents it relied on named in full.

The measured result: **a 72% reduction in hallucinated content** versus querying the same base model directly.

---

## Why this was hard in 2023

This matters for reading the code, so it's worth stating plainly.

When this project started, the tooling that makes RAG a weekend project today either did not exist, was in preview, or was not trusted enough to build on for an aerospace sponsor. There was no drop-in RAG framework in this stack. **Every stage of the pipeline is hand-rolled**, and that was the only option:

- **No LangChain, no LlamaIndex, no vector-store abstraction.** The retrieval layer talks to Azure AI Search over **raw REST** (`requests.post` against `api-version=2023-11-01`), constructing the vector query payload by hand — `kind: vector`, `k: 7`, `exhaustive: True` — because the SDK surface for vector search wasn't there yet.
- **Azure AI Search had only just gained vector search**, and had literally just been renamed from Azure Cognitive Search. The Azure OpenAI calls run against `api-version=2023-07-01-preview`. We were building on preview APIs that changed underneath us mid-semester.
- **Embeddings were generated as a separate explicit step**, then hand-passed into the search payload. There was no "just point it at your documents" integrated pipeline.
- **Context assembly, citation handling, and conversation memory were all designed from scratch**, because there were no established patterns to copy. The prompt architecture below is the product of an entire semester of iteration against a domain expert's judgment, not a template.

The "obvious" RAG architecture in this repo looks obvious *now*. In 2023 it was arrived at by figuring out, from first principles, that grounding a generative model against a retrieved document set was the way to make an LLM trustworthy enough to advise on flight operations. GPT-3.5 was the frontier model available to us.

---

## Architecture

```
                          ┌──────────────────────────┐
   Operator query  ──────▶│  Streamlit multipage UI  │
                          │  Chat · History · Options│
                          └────────────┬─────────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │  1. EMBED                    │
                        │  Azure OpenAI                │
                        │  deployment: ingenuityEmbedder│
                        └──────────────┬───────────────┘
                                       │ float vector
                        ┌──────────────▼───────────────┐
                        │  2. RETRIEVE                 │
                        │  Azure AI Search (REST)      │
                        │  index: contextindexer       │
                        │  exhaustive KNN, k=7         │
                        └──────────────┬───────────────┘
                                       │ 7 × {title, chunk}
                        ┌──────────────▼───────────────┐
                        │  3. AUGMENT                  │
                        │  Layered system-message stack│
                        │  + operator-tunable prompt   │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │  4. GENERATE                 │
                        │  Azure OpenAI GPT-3.5        │
                        │  deployment: ingenuityGPT    │
                        │  temperature: operator-set   │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │  5. PERSIST                  │
                        │  Azure Blob Storage          │
                        │  chat-logs · error-logs ·    │
                        │  stored-options              │
                        └──────────────────────────────┘

   Deployment:  Docker (python:3.11) ──▶ GitHub Actions ──▶ Azure App Service
```

**Stack:** Python 3.11 · Streamlit · Azure OpenAI (GPT-3.5 + embeddings) · Azure AI Search · Azure Blob Storage · Azure App Service · Docker · GitHub Actions · Loguru

---

## The engineering that isn't obvious from the diagram

### Grounding through a layered system-message stack

Rather than string-concatenating documents into one prompt, each turn builds a structured five-message stack that separates *instructions*, *evidence*, and *question* into distinct roles:

1. The operator-tunable system prompt (behavioral contract)
2. An explicit instruction on how to use and cite the supplied excerpts
3. The retrieved document excerpts, each labeled `Title:` / `Excerpt:`
4. A delimiter message announcing the user's question
5. The user's actual query

Keeping evidence in its own message — rather than blended into the instruction text — measurably reduced the model's tendency to blur retrieved fact with parametric recall. This separation is standard practice today; in 2023 we arrived at it empirically.

### Ephemeral evidence, persistent conversation

The most deliberate design decision in the codebase. After each response, the four injected system messages are deleted from the chat memory, and only the user turn and the assistant turn are retained:

```python
del st.session_state["chatMemory"][-5]
del st.session_state["chatMemory"][-4]
del st.session_state["chatMemory"][-3]
del st.session_state["chatMemory"][-2]
st.session_state["chatMemory"].append({"role": "assistant", "content": ...})
```

The effect: **document context is scoped to the turn that retrieved it, while conversational continuity survives.** This solves two problems at once — context windows stay bounded across a long operator session (a hard constraint on 2023-era models), and stale excerpts from three questions ago can't contaminate the current answer. Retrieval runs fresh against every query.

### Safety-oriented prompt engineering

The system prompt is the heart of the hallucination reduction, and every clause in it exists because of an observed failure during testing:

- **Bias toward decisive action** — if the query describes danger, the model must state that Ingenuity must land *now*, with the reason. Hedging is a failure mode when someone is making a real-time flight call.
- **Explicitly ignore documents describing past hardware failures** — the model was anchoring on historical incidents and pattern-matching them onto unrelated scenarios instead of reasoning from technical specifications. This clause forces judgment from criteria, not from precedent.
- **Numerical vigilance** — mandatory specific numbers, units, and ranges; explicit instruction to attend to any number in the query. Aerospace tolerances don't survive paraphrase.
- **Strict citation discipline** — full document names never abbreviated, no duplicate citations, citations only at the very end with no trailing text. An operator needs to verify a recommendation against the source in seconds.
- **Conditional scoping** — cite nothing when the query isn't Ingenuity-related, preventing spurious authority on out-of-domain questions.
- **Low default temperature (0.20)**, with the operator-facing range constrained after testing showed higher values degraded citation fidelity.

### Operator-tunable at runtime, no redeploy

The Options page lets JPL operators adjust the temperature and **edit the entire system prompt live**, persisted as JSON to blob storage and reloaded on session start. Domain experts could tune model behavior against their own judgment without a developer in the loop or a deployment cycle — which is how the prompt above got as sharp as it did.

### Three-tier error handling with operator-visible status

Built for a control-room context where silent failure is unacceptable:

- Embedding-generation failures, `RateLimitError` during generation, and a page-level catch-all are each handled separately with distinct, actionable operator messaging.
- A **sidebar status indicator** reports system state at a glance — 🟩 all systems functional, 🟨 rate limit exceeded, 🟥 backend failure.
- Every error is written to Azure Blob Storage with a timestamped, collision-resistant filename, and is browsable in-app through a debug-log modal.

### Auditable session history

Every conversation is persisted to blob storage, **auto-titled by a second LLM call** (four words, fifteen characters max per word) so operators can find a prior session by subject rather than by timestamp, and browsable through a dedicated Chat History page. Timestamps are Pacific-time normalized to match JPL operations.

---

## Repository layout

```
.github/workflows/
  rel-1.0_ingenuitygpt.yml        CI/CD → Azure App Service
  dev-cap-51_ingenuitygpt.yml     Per-ticket deployment pipeline
app/
  Chat.py                         Main RAG pipeline + chat interface
  log_setup.py                    Error logging → Azure Blob
  Dockerfile                      python:3.11 + Streamlit healthcheck
  requirements.txt
  pages/
    Options.py                    Runtime prompt/temperature/theme control
    Chat History.py               Persisted session browser
```

---

## Team process

This ran as a real software project, not a coursework submission. I directed a five-person team through:

- **Ticket-driven development** — Jira-style branches (`dev/CAP-51`, `dev/CAP-73`, `dev/CAP-82` …) mapped one-to-one to tracked work items
- **Pull-request review** — 27 merged PRs; no direct pushes to release branches
- **Release-train branching** — `dev/*` → `test/*` → `rel/1.0` … `rel/1.4`, with a dedicated test stage before each release
- **Continuous deployment** — GitHub Actions building and deploying to Azure App Service on merge to a release branch, using publish-profile secrets

The commit history reflects the real shape of the work: an initial functional push, then a long tail of prompt refinement (`fixed unnecessary citations, only citations, wordy resps, mis-ordered resps`), state-management bugs, and UI polish through April 2024. Roughly the final two months were spent almost entirely on **response quality**, not features — which is the correct allocation for a system whose value is being trusted.

---

## Known limitations

Stated plainly, because a portfolio README that only lists strengths isn't worth reading.

- **Credentials were hardcoded.** Azure storage, OpenAI, and AI Search keys were committed in plaintext rather than sourced from environment variables or Azure Key Vault. This was wrong at the time and remains the single worst practice in the codebase. The associated resources have been decommissioned; the correct pattern is `DefaultAzureCredential` (already imported, never wired up) plus managed identity.
- **No automated tests.** The CI workflow carries the literal comment `# Optional: Add step to run tests here` — the placeholder was never filled. For a system making flight-safety recommendations, a regression suite over a fixed set of query/expected-citation pairs should have been mandatory. This is the gap I'd close first.
- **`requirements.txt` lists standard-library modules** (`os`, `json`, `datetime`, `logger`) as pip dependencies — harmless but sloppy, and evidence the dependency file was assembled from import statements rather than maintained.
- **`css_fix()` is duplicated verbatim across all three pages** rather than living in a shared module.
- **Retrieval is fixed at `k=7` with exhaustive KNN** — no reranking, no relevance thresholding, no adaptive retrieval depth. Exhaustive search was acceptable at our corpus size and would not scale.
- **Blob-per-session chat storage** has no indexing or pagination; the History page downloads every blob to render the list.
- **A stray `Dockerfile.txt`** duplicates the real Dockerfile.

## What I'd build differently today

The 2023 constraints that shaped this system are gone. A current rebuild would use managed identity end to end, a maintained retrieval framework instead of hand-rolled REST, hybrid search with semantic reranking rather than pure vector KNN, structured outputs to make citation extraction deterministic instead of prompt-enforced, and an evaluation harness (RAGAS-style faithfulness and answer-relevance scoring) so the 72% hallucination reduction is a continuously measured regression metric rather than a point-in-time result.

**None of which changes the part that mattered:** the core insight — that you make a generative model trustworthy for high-stakes operational use by forcing it to reason only over retrieved, cited, domain-authoritative evidence — was correct then and is correct now. We just had to derive it, and build every layer of it, before there was a name for it.

---

## Notes on this copy

This is a public mirror of the original private capstone repository under the `ERAU-PRCOE-Capstones` organization. The default branch is `rel/1.4`, the final delivered release. The JPL documentation corpus that populated the search index is not included and was never part of this repository.

**Nicholas Capriotti** · [github.com/My80vette](https://github.com/My80vette) · [LinkedIn](https://www.linkedin.com/in/nicholas-capriotti-5775031b9/)
