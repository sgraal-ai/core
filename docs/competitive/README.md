# Competitive Displacement Toolkit

## What this folder is

This folder contains migration guides for teams already using existing memory frameworks (LangChain, LangMem, Mem0, Zep) who want to add Sgraal's governance layer on top. These are not "rip-and-replace" guides — they are **additive integration** playbooks.

## Core message

**You don't replace X with Sgraal. You add Sgraal before X.**

Sgraal is a preflight scoring engine that evaluates whether an AI agent's memory state is reliable enough to act on. It sits between your memory layer and your agent's decision logic. Your existing memory framework continues to do what it does well — storage, retrieval, summarization, graph extraction. Sgraal adds the governance decision: `USE_MEMORY`, `WARN`, `ASK_USER`, or `BLOCK`.

## Table of contents

| Guide | Framework | Core Role |
|-------|-----------|-----------|
| [from_langchain.md](./from_langchain.md) | LangChain | Orchestration + built-in memory abstractions |
| [from_langmem.md](./from_langmem.md) | LangMem | Long-term semantic memory with hot/cold storage |
| [from_mem0.md](./from_mem0.md) | Mem0 | Persistent memory-as-a-service across sessions |
| [from_zep.md](./from_zep.md) | Zep | Knowledge-graph memory with fact extraction |

## When to use Sgraal with each tool

| Framework | What it does | What Sgraal adds |
|-----------|--------------|------------------|
| **LangChain** | Stores conversation/buffer memory, orchestrates agent steps | Governs whether stored memory is safe to READ before each step |
| **LangMem** | Long-term semantic search across hot/cold memory tiers | Preflight check on retrieved memories before the LLM consumes them |
| **Mem0** | Cross-session persistent memory as a managed service | Decides whether persisted memory is reliable for the current action |
| **Zep** | Extracts facts and builds knowledge graphs from conversation | Evaluates whether extracted facts are safe to act on in downstream decisions |

## The one-line positioning

> Your memory framework answers **"what do we remember?"** Sgraal answers **"should we act on it?"**