---
name: topic-newsletter-compiler
description: Analyze a week of news research entries and compile them into a professional newsletter with key trends, top highlights, and actionable insights. Use when you need to synthesize multiple research topics into a cohesive narrative suitable for LinkedIn or email distribution.
---

# Topic Newsletter Compiler

## Overview

Transform a week's worth of research entries into a compelling newsletter that identifies trends, highlights key insights, and creates a narrative for professional audiences (LinkedIn, email, internal comms).

## Workflow

### 1. Analyze Input Data

- Review the provided list of research entries (topics, summaries, dates)
- Identify recurring themes, patterns, and connections across entries
- Note frequency of topics and sentiment (emerging trends vs. declining interest)
- Extract 3-5 key themes that represent the week's focus

### 2. Identify Top Highlights

- Extract the most impactful or novel findings from summaries
- Prioritize insights that would resonate with professional/technical audience
- Look for actionable intelligence, surprising discoveries, or significant announcements
- Select 3-5 highlights that represent the week's best insights

### 3. Synthesize Trends

- Connect individual research findings into broader narrative themes
- Identify emerging patterns (e.g., adoption trends, policy shifts, technology breakthroughs)
- Note intersections between different topics that create new insights
- Rate trend significance: high (major impact), medium (notable), low (minor signals)

### 4. Create Newsletter Structure

Format the newsletter with:
- **Opening Hook**: A compelling 1-2 sentence summary of the week's top story
- **Key Trends**: 3-5 identified trends with brief explanations
- **Top Highlights**: 3-5 standout findings with context
- **What It Means**: Implications and opportunities for the audience
- **Topics Covered**: List of all research topics from the period
- **Closing**: Call-to-action or reflection

### 5. Optimize for Platform

- Use professional but accessible language
- Include relevant emojis (if LinkedIn post)
- Keep paragraphs short and scannable
- Use bullet points and lists for readability
- Maintain consistent tone across sections

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

- [ ] Opening hook is compelling and accurate
- [ ] Key trends are backed by evidence from the entries
- [ ] Highlights are the week's most impactful findings
- [ ] Implications and "what it means" section adds interpretation
- [ ] All major topics are mentioned in the coverage summary
- [ ] Language is professional and accessible
- [ ] No claims without supporting evidence from the input entries
- [ ] Newsletter is suitable for LinkedIn post (if that's the target)

## Output Shape

Structured output should include:

```json
{
  "newsletter_title": "Title for the Week",
  "opening_hook": "Compelling opening statement",
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
      "description": "What happened and why it matters",
      "topics_involved": ["Topic 1", "Topic 2"]
    }
  ],
  "implications": "What this means for the audience",
  "topics_covered": ["Topic 1", "Topic 2", "..."],
  "newsletter_html": "Full formatted HTML newsletter for posting",
  "newsletter_markdown": "Full formatted Markdown newsletter"
}
```

## Example Triggers

- "Compile a LinkedIn newsletter from these 7 research entries"
- "Analyze last week's research and create trend highlights"
- "Synthesize these topics into a professional newsletter"
- "Create a newsletter narrative from the provided research summaries"
