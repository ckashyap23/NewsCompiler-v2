---
name: topic-research-summarizer
description: Research a user-supplied topic by planning related web searches, screening results for relevance and credibility, comparing sources, and producing a concise sourced summary. Use when Codex needs to investigate a topic, gather current information from the web, identify which results matter, discard weak or duplicate results, and synthesize findings into a brief, explainer, comparison, or answer with links and caveats.
---

# Topic Research Summarizer

## Overview

Research a topic with a repeatable search-screen-summarize workflow. Expand the topic into focused queries, review results for authority, relevance, and recency, then return a concise summary grounded in the strongest available sources.

## Workflow

### 1. Define the research target

- Identify whether the user wants an explainer, latest update, comparison, source list, or decision brief.
- Infer a reasonable scope when the request is slightly underspecified.
- Do not ask clarifying questions in one-shot research runs. Make the best reasonable assumptions, state them briefly, and continue.
- When a request is ambiguous, prefer a broad-but-useful answer over a follow-up question.
- If source selection is unclear, prioritize primary sources first and add high-quality secondary coverage only for corroboration or important context.
- If a time window is relative, resolve it using the date supplied in the user request or runtime prompt; otherwise use the current date and state the assumed window briefly.
- Treat freshness as important whenever the topic could have changed recently.

### 2. Plan the search set

- Start with 2-4 complementary searches that cover:
  - the exact topic
  - alternate phrasing or synonyms
  - primary-source or official-site variants
  - recent-news variants when freshness matters
- Prefer primary sources first: official documentation, original announcements, papers, government sources, company pages, or direct datasets.
- Use secondary sources to add context, triangulate, or compare interpretations.

### 3. Screen the results

- Keep sources that are directly relevant, specific, and credible.
- Drop results that are duplicative, off-topic, SEO-heavy, thin on evidence, or obviously derivative.
- Note why each retained source matters before moving on.
- When multiple sources say the same thing, keep the best representative source instead of repeating weak duplicates.

### 4. Extract and compare

- Pull only the facts needed to answer the request.
- Capture dates and source ownership when those details affect trust or timeliness.
- Separate sourced facts from your own inference.
- Preserve meaningful disagreement between sources instead of flattening it away.

### 5. Summarize the selected content

- Lead with the direct answer or top takeaway.
- Follow with the key supporting points in a compact structure that matches the request.
- Include source links in the final answer.
- Never return only a question or request for clarification when a best-effort summary can be produced.
- Call out uncertainty, incomplete evidence, or unresolved conflicts when present.
- Keep quotations short and use paraphrase by default.

## Output Checklist

- Answer the user's actual question, not just the search topic.
- Show the strongest sources, not the largest number of sources.
- Include dates when the topic is time-sensitive.
- Make it explicit when a point is an inference.
- Say when the evidence is insufficient.

## Example Triggers

- "Research the latest changes to India's semiconductor policy and summarize them."
- "Find credible sources about vector databases for RAG and give me a short comparison."
- "Look up recent coverage of a company's earnings and tell me what changed."
- "Search this topic, keep only the most relevant results, and create a sourced summary."
