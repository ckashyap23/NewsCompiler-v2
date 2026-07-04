---
name: topic-newsletter-compiler
description: Analyze a week of news research entries and compile them into a professional newsletter with key trends, top highlights, and actionable insights. Use when you need to synthesize multiple research topics into a cohesive, human-sounding narrative suitable for LinkedIn or email distribution.
---

# Topic Newsletter Compiler

## Overview

Transform a week's worth of research entries into a newsletter that reads like it was written by a sharp, opinionated industry analyst who happens to have read everything this week — not like a summarization pipeline. The test for every draft: if you covered the headline with your hand, could someone tell this was written by a person with a take, or does it sound like it could've been generated from a template? If the latter, it needs another pass.

## Workflow

### 1. Analyze Input Data

- Review the provided list of research entries (topics, summaries, dates)
- Identify recurring themes, patterns, and connections across entries
- Note frequency of topics and sentiment (emerging trends vs. declining interest)
- Extract 3-5 key themes — but more importantly, figure out **how they relate to each other**. Real analysis finds tension or cause-and-effect between stories, not just a shared keyword. Ask: does Story A explain why Story B is happening? Does Story C contradict the narrative in Story A? That relationship is the actual insight — lead with it.

### 2. Identify Top Highlights

- Extract the most impactful or novel findings — favor specific numbers, named companies, and concrete claims over vague characterizations
- Prioritize insights that would make a smart reader stop scrolling: something surprising, a number bigger than expected, a move that contradicts what the market assumed
- Select 3-4 highlights. Fewer, better-argued highlights beat five thin ones.

### 3. Synthesize Trends

- Don't just list trends — build a **through-line**. A newsletter is not five unrelated bullet points; it's one argument about the week, told through several examples.
- Pick ONE central thesis for the week (e.g., "everyone's trying to monetize compute scarcity before it becomes compute abundance"). Every trend and highlight should either support or complicate that thesis.
- It's fine — good, even — to flag where the evidence is mixed or where you're speculating. Certainty about everything is itself a tell of AI-generated writing.

### 4. Create Newsletter Structure — prose first, structure second

Structure should serve the argument, not replace it. Default shape:

- **Opening Hook**: Lead with the single most consequential or surprising fact from the week — a specific number, a name, a contradiction — not a summary sentence about "the landscape." Two sentences max. No throat-clearing.
- **The Thread**: 2-4 short paragraphs of actual prose connecting the week's stories into one narrative. This replaces a flat list of "Key Trends." Vary paragraph length — one paragraph can be two sentences, another can be five. Use transitions ("But here's the twist," "Meanwhile," "That's not the whole story") instead of restarting with a fresh header each time.
- **Worth Your Attention**: 3-4 highlights, each framed as *why it matters* rather than *what happened*. Skip repeating a "Topics:" tag line under each one — that's database metadata, not something a reader wants to see.
- **My Read** (or "What It Means"): A genuine, slightly opinionated take. Take a side on something. Flag a prediction. This is the section most likely to feel human because it's the one place the writer is allowed to be wrong.
- **Closing**: End on a question, a prediction, or a one-line provocation — not "stay tuned for more insights" or similar filler.

Do NOT create a separate numbered header (### 1, ### 2...) for every single trend and every single highlight — that's what produces the database-readout feeling. Headers are fine for major sections; individual items within a section should flow as prose or a lightly-formatted list, not as repeated mini-templates.

### 5. Voice and Language Guardrails

**Avoid these phrases/patterns — they are the most common AI-newsletter tells:**
- "pivotal moment," "landscape," "underscores," "highlights the need for," "navigate," "in today's rapidly evolving," "it's important to note," "signals a shift toward," "poised to," "plays a crucial role," "a testament to"
- Starting every sentence with "This week..." or "As [X] continues to..."
- Ending a paragraph by restating what it just said in slightly more abstract language
- Assigning "Significance: High/Medium/Low" tags in the reader-facing text (fine to reason about internally, not fine to print — it reads like a spreadsheet, not a newsletter)

**Do this instead:**
- Use contractions ("it's," "here's," "doesn't")
- Vary sentence length aggressively — short punchy sentences next to longer explanatory ones
- Use specific numbers and names instead of abstractions ("NVIDIA's new revenue-share deal" beats "evolution of AI business models")
- Let two stories argue with each other in the same paragraph instead of describing them in separate, parallel paragraphs
- Write like you'd explain it to a smart colleague over coffee, not like you're presenting to a board

### 6. Optimize for Platform

Two distinct outputs are needed, and they should NOT look alike. A newsletter-markdown version (for email/blog) and a LinkedIn version are formatted differently — don't just reuse one for the other.

**For `newsletter_markdown` (email/blog):**
- Prose paragraphs as described in Section 4, 2-5 sentences each
- Headers for major sections only (Hook, The Thread, Worth Your Attention, My Read, Closing)
- No emoji required; if used, sparing (1-3 total)

**For the LinkedIn version specifically:**
- **One sentence per line, or close to it.** LinkedIn is read on mobile in a narrow column — dense paragraphs get collapsed under "see more" and lose readers. Break almost every sentence onto its own line, with a blank line between them. This looks sparse in a markdown editor; that's correct, not a bug.
- **No headers.** LinkedIn posts don't use "###" section titles. Section transitions are signaled with a short standalone line instead (e.g., "Here's the thread connecting this week's stories 🧵" or "Here's my read 👇").
- **Arrow bullets (→) or short dashes** for highlight lists instead of markdown headers per item.
- **Emoji as section punctuation, not decoration** — one emoji marking a transition (🧵 for "here's the thread," 👇 for "here's my take," 💬 for inviting comments) reads as intentional; scattering emoji through every sentence reads as noise. Cap at 3-5 for the whole post.
- **Bold sparingly**, if the platform preview supports it — LinkedIn strips most markdown formatting, so don't rely on bold/italics to carry structure. Line breaks and standalone short lines do that work instead.
- **Hashtags**: 3-5 relevant ones, placed at the very end, never inline.
- **Closing line**: a direct question inviting engagement works especially well on LinkedIn specifically (comments drive distribution) — more so than on email, where a reflective closer is fine.
- **Length**: LinkedIn rewards posts that fit mostly above the "see more" fold with a hook strong enough to justify the click to expand. Front-load the most surprising fact in the first two lines.

## Input Format

Provide a JSON array of research entries with structure:

```json
[
  {
    "id": 1,
    "datetime": "2026-06-01T09:00:00",
    "topic": "AI Enterprise Adoption 2026",
    "content": "Research summary about AI adoption..."
  },
  {
    "id": 2,
    "datetime": "2026-06-02T09:00:00",
    "topic": "Quantum Computing Breakthroughs",
    "content": "Latest developments in quantum computing..."
  }
]
```

## Output Checklist

- [ ] Opening hook leads with a specific fact, not a summary of "the landscape"
- [ ] The body reads as connected prose with a through-line, not siloed bullet write-ups
- [ ] At least one place takes a real, slightly risky point of view
- [ ] No banned phrases from Section 5 appear in the reader-facing text
- [ ] Sentence lengths vary noticeably within paragraphs
- [ ] Highlights are framed as "why it matters," not restated headlines
- [ ] Closing ends on a question, prediction, or provocation — not generic sign-off language
- [ ] No claims without supporting evidence from the input entries
- [ ] "Significance" ratings, if used, stay in structured data and never appear in newsletter prose

## Output Shape

Structured output should include:

```json
{
  "newsletter_title": "Title for the Week",
  "opening_hook": "Compelling opening statement",
  "thesis": "The one-sentence argument tying the week together",
  "key_trends": [
    {
      "trend": "Trend name",
      "description": "What's happening",
      "significance": "high|medium|low"
    }
  ],
  "top_highlights": [
    {
      "highlight": "Insight title",
      "description": "Why it matters, not just what happened",
      "topics_involved": ["Topic 1", "Topic 2"]
    }
  ],
  "my_read": "A genuine, opinionated take — not neutral implications",
  "topics_covered": ["Topic 1", "Topic 2", "..."],
  "newsletter_html": "Full formatted HTML newsletter for posting",
  "newsletter_markdown": "Full formatted Markdown newsletter (prose, headers for major sections)",
  "linkedin_post": "Separate LinkedIn-native version: one-sentence-per-line, no headers, arrow bullets, sparing emoji as transition markers, hashtags at the end — per Section 6"
}
```

Note: `key_trends` and `top_highlights` remain structured here for programmatic use (e.g., feeding a dashboard), but the `newsletter_markdown`/`newsletter_html`/`linkedin_post` fields should read as prose per Section 4-5 — NOT as a rendering of this JSON into headers and bullets. `linkedin_post` must be formatted per the LinkedIn-specific rules in Section 6, not simply copied from `newsletter_markdown`.

## Example Triggers

- "Compile a LinkedIn newsletter from these 7 research entries"
- "Analyze last week's research and create trend highlights"
- "Synthesize these topics into a professional newsletter"
- "Create a newsletter narrative from the provided research summaries"
