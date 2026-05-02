# Agent 4 (News Verification) — Scope Narrowing

## Purpose

Narrow the documented claim of Agent 4 from "checks whether the market already knows our information" to "checks whether the satellite finding has been disclosed in GDELT-visible public news prior to T-14." This is a paper-text and prompt-text change only; no data-pipeline change. The narrower claim is what the system actually tests; the original claim overstated the scope.

This spec resolves Pre-Code Action Item 15 and supports DL #41.

## Where the Claim Appears (and Must Change)

1. `project_overview.md` — Multi-Agent Architecture section, Agent 4 description.
2. Final paper — Methodology section, Agent 4 subsection.
3. Final paper — Limitations section.
4. The agent's prompt template (system instructions and task framing).
5. Any slide deck or demo description.

## Replacement Language

### For paper Methodology (Agent 4 subsection)

> **Agent 4: News Verification Agent.** For each company flagged by Agent 3, this agent retrieves GDELT articles published between the most recent earnings date and T-14 (the trade-entry anchor) that mention the company name or ticker. It applies an LLM-based classifier (Llama 70B via Groq) to determine whether any retrieved article describes a publicly disclosed change in drilling activity, production guidance, or operational pace consistent with the satellite-detected pattern. If such disclosure exists in the GDELT corpus, the company's signal is downgraded by one conviction tier on the basis that the information is already publicly visible. The agent's claim scope is limited to GDELT-indexed news; sell-side research notes, investor decks, conference call transcripts, state regulatory filings, and other private or non-indexed channels are out of scope. The agent therefore tests whether the signal is GDELT-visible, not whether it is fully embedded in market prices.

### For paper Limitations section (new paragraph)

> **News-verification scope limitation.** The News Verification Agent uses GDELT as its sole news source. GDELT indexes a broad cross-section of online news but does not capture sell-side analyst notes, investor presentations and decks, earnings-call transcripts and prepared remarks, state-level regulatory filings (such as Texas Railroad Commission permit announcements outside news coverage), industry trade publications behind paywalls, or social-media commentary. As a result, the agent's downgrade rule operationalizes "already in GDELT-indexed news" rather than "already known to the market." A company's drilling activity may be priced in via channels outside GDELT, in which case our system would assign full conviction to a signal that the market has already absorbed. We treat this as a known scope limitation rather than a leakage problem, because our temporal-discipline rule (T-14 cutoff on GDELT timestamps) prevents future news from entering the agent regardless of channel coverage.

### For Agent 4 prompt template (system instruction)

```
You are the News Verification Agent in a multi-agent satellite-based trading system.

Your job is narrow and specific: determine whether the satellite-detected drilling pattern for {company} has already been disclosed in GDELT-indexed news articles published before {decision_date_T_minus_14}.

You are NOT being asked whether the market already knows the information. You are NOT analyzing sell-side notes, investor decks, earnings transcripts, or state filings — you do not have access to those sources. You are checking only GDELT-indexed news.

Inputs you will receive:
- The satellite-detected pattern for {company} (e.g., "newly active drilling at 12 sites in Q3 2024").
- A list of GDELT articles mentioning {company} between {previous_earnings_date} and {decision_date_T_minus_14}, with publication timestamps, titles, and excerpts.

Output a JSON object with these fields:
- "gdelt_disclosed": true | false  (does the GDELT corpus contain any article that publicly describes a drilling-activity change consistent with the satellite-detected pattern?)
- "matching_article_ids": [list of GDELT article IDs that triggered the True classification, empty list if False]
- "confidence": "high" | "medium" | "low"  (your confidence in the gdelt_disclosed determination)
- "reasoning": "<one short paragraph explaining the decision>"

Do not speculate about coverage outside GDELT. If gdelt_disclosed is False, state explicitly that this is a determination about GDELT-indexed news only, not about full market awareness.
```

### For project_overview.md Agent 4 description (replacement)

The current description (line 22 of project_overview.md) reads:

> Agent 4: News Verification Agent. For each flagged company, reads recent news from GDELT to check whether the market already knows what we detected. Hard-coded to use only GDELT data up to T-14 days (the position open date); no data after that point enters the agent. If a company already announced a drilling expansion publicly, our signal has no information edge and the flag is downgraded. LLM: Llama 70B via Groq (reads news and determines whether our satellite finding is already public knowledge).

Replace with:

> Agent 4: News Verification Agent. For each flagged company, reads recent news from GDELT to check whether the satellite-detected drilling pattern has been disclosed in GDELT-indexed public news prior to T-14. Hard-coded to use only GDELT data up to T-14 days (the position open date); no data after that point enters the agent. If GDELT contains an article describing a consistent drilling-activity change before T-14, the signal is downgraded by one conviction tier. The agent's scope is limited to GDELT-indexed news; sell-side research, investor decks, transcripts, and state filings are out of scope and listed as a Limitations item in the paper. LLM: Llama 70B via Groq (classifies GDELT articles for consistency with the satellite-detected pattern, not "full market knowledge").

## Implementation Note

The narrowing is purely linguistic — the agent's data inputs, retrieval window, classification logic, and output schema are unchanged from the prior design. Only the documented claim shrinks to match what the agent actually does. This is the cheapest fix in the entire pre-code list and must be reflected consistently across the paper, the overview document, the prompt, and any presentation materials.

## Sign-off Gate

The replacement language is committed to project_overview.md before Phase 2 begins, and the prompt template is locked alongside the rest of the LLM determinism manifest (Pre-Code Action Item 6).
