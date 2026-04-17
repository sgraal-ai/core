# Competitive Displacement Toolkit

## What this folder is

This folder contains migration guides for teams already using existing memory and agent frameworks (AutoGen, CrewAI, LangChain, LlamaIndex, LangMem, Mem0, OpenAI Agents SDK, Zep) who want to add Sgraal's governance layer on top. These are not "rip-and-replace" guides — they are **additive integration** playbooks.

## Core message

**You don't replace X with Sgraal. You add Sgraal before X.**

Sgraal is a preflight scoring engine that evaluates whether an AI agent's memory state is reliable enough to act on. It sits between your memory layer and your agent's decision logic. Your existing memory framework continues to do what it does well — storage, retrieval, summarization, graph extraction. Sgraal adds the governance decision: `USE_MEMORY`, `WARN`, `ASK_USER`, or `BLOCK`.

## Table of contents

| Guide | Framework | Core Role |
|-------|-----------|-----------|
| [from_autogen.md](./from_autogen.md) | AutoGen | Multi-agent conversation with teachable agents |
| [from_crewai.md](./from_crewai.md) | CrewAI | Role-based multi-agent task delegation |
| [from_langchain.md](./from_langchain.md) | LangChain | Orchestration + built-in memory abstractions |
| [from_llamaindex.md](./from_llamaindex.md) | LlamaIndex | Data framework with retrieval-augmented generation |
| [from_langmem.md](./from_langmem.md) | LangMem | Long-term semantic memory with hot/cold storage |
| [from_mem0.md](./from_mem0.md) | Mem0 | Persistent memory-as-a-service across sessions |
| [from_openai_agents.md](./from_openai_agents.md) | OpenAI Agents SDK | Official OpenAI agent framework with tool calling |
| [from_zep.md](./from_zep.md) | Zep | Knowledge-graph memory with fact extraction |

## When to use Sgraal with each tool

| Framework | What it does | What Sgraal adds |
|-----------|--------------|------------------|
| **AutoGen** | Multi-agent conversation, teachable agents, collaborative workflows | Governs whether accumulated agent context is safe to act on |
| **CrewAI** | Role-based task delegation across specialist agents | Preflight check on task context before crew execution |
| **LangChain** | Stores conversation/buffer memory, orchestrates agent steps | Governs whether stored memory is safe to READ before each step |
| **LlamaIndex** | Data ingestion, indexing, and retrieval-augmented generation | Preflight check on retrieved nodes before the LLM consumes them |
| **LangMem** | Long-term semantic search across hot/cold memory tiers | Preflight check on retrieved memories before the LLM consumes them |
| **Mem0** | Cross-session persistent memory as a managed service | Decides whether persisted memory is reliable for the current action |
| **OpenAI Agents SDK** | Tool calling, agent handoffs, structured outputs | Governs whether agent context is reliable before Runner execution |
| **Zep** | Extracts facts and builds knowledge graphs from conversation | Evaluates whether extracted facts are safe to act on in downstream decisions |

## The one-line positioning

> Your memory framework answers **"what do we remember?"** Sgraal answers **"should we act on it?"**
