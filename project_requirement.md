Final Project Announcement Multi-Agent Trading and Investment Systems in the Age of AI
Multi-Agent Trading and Investment Systems in the Age of AI
With a Sponsored Project Track by Menos AI
Hi All,

The final project for this course is designed to push you beyond a traditional single-factor or single-model trading strategy and into the frontier of multi-agent trading and investment systems.

Your task is to design, implement, and rigorously evaluate an AI-enabled investment framework in which multiple specialized agents collaborate, debate, or coordinate to produce trading and portfolio decisions. The strongest projects will not merely generate signals; they will demonstrate how agent specialization, alternative data, narrative reasoning, and disciplined portfolio design can work together in a coherent investment process.

This year’s project also includes a special sponsored track by Menos AI, focused on textual-narrative and event-driven trading, in which teams assess whether LLM-based systems can reason about economic events, policy changes, and market narratives and translate that reasoning into systematic portfolio positioning. The Menos AI proposal specifically frames the project around trading signals derived from raw textual narratives across assets such as the S&P 500, Nasdaq 100, U.S. yields, gold, oil, DXY, VIX, MSCI EM, and Bitcoin.

Why This Project Matters
Recent finance and AI research suggests that this is a highly promising but still underdeveloped area.

Alternative-data research has expanded quickly across text, consumer behavior, transactions, ESG events, and sensor-based information, yet researchers still note major open challenges in merging heterogeneous data types, avoiding overfitting, and extracting durable investment value from these signals. At the same time, the newer literature on financial multi-agent systems argues that the field still lacks a strong framework for testing whether performance improvements come from better models or from better coordination mechanisms, task decomposition, and workflow design.

Accordingly, this final project is intentionally structured around several live research gaps:

Multimodal integration gap: finance research has many papers on alternative data and many recent papers on multi-agent LLM trading systems, but much less work combining both in a rigorous and investable way.
Coordination and attribution gap: recent work suggests that coordination design and fine-grained task decomposition may matter substantially, yet these systems are rarely evaluated against clean single-agent or no-communication baselines.
Temporal-integrity and leakage gap: recent studies emphasize that financial agent systems can appear strong in backtests while suffering from look-ahead bias, weak timestamp discipline, or knowledge contamination.
Reproducibility gap: proprietary data, unstable prompts, missing environment controls, and incomplete documentation make many AI-finance projects difficult to reproduce credibly.
Your project should engage with at least one of these gaps explicitly.

Project Objective
Your team will design a multi-agent trading and investment system that operates over a clearly defined investment universe and demonstrates how multiple agents can contribute meaningfully to:

information gathering,
interpretation,
signal generation,
risk management,
portfolio construction,
and final trading decisions.
A successful project should show not just that an AI system can produce trades, but that a well-designed division of labor across agents improves the quality, clarity, robustness, or economic usefulness of the investment process.

Acceptable Project Directions
You may choose one of the following main directions.

1. Multi-Agent Alternative-Data Alpha System
Design a multi-agent system that constructs and tests at least one alternative-data-driven investment signal and evaluates whether it adds value beyond traditional signals or factors.

Possible alternative-data inputs include:

news-derived event signals,
social-media sentiment,
search-interest data,
ESG controversy or sustainability event data,
web-scraped consumer or product-review data,
transaction-style demand proxies,
satellite or geospatial indicators,
blockchain / on-chain indicators.
This direction should directly address the current research gap that, while alternative data are increasingly important in finance, researchers still struggle with heterogeneous data integration, signal validation, and proving incremental value after controlling for standard baselines.

A strong version of this project would test:

whether the alternative-data factor improves performance beyond momentum, value, quality, carry, or simple sentiment baselines,
whether a multi-agent design improves the handling of noisy or multimodal data,
whether the factor survives delays, costs, and robustness checks.
2. Narrative-to-Portfolio Multi-Agent Trading System
Menos AI Sponsored Track

In this track, your system derives trading signals primarily from textual narratives rather than from purely historical price correlations.

The Menos AI project proposal frames the challenge as assessing whether LLMs can interpret real-world events and economic narratives and convert them into coherent, tradable portfolio decisions. Example inputs include news articles, central-bank statements, earnings transcripts, macroeconomic releases, and other text sources. The proposal emphasizes understanding events, regimes, and causal chains, rather than merely forecasting returns from historical patterns.

A strong multi-agent design for this track may include roles such as:

Narrative/Event Agent – identifies the key event or story,
Macro Transmission Agent – reasons about implications for growth, inflation, rates, or policy,
Asset Mapping Agent – translates narratives into asset-level exposures,
Risk Manager Agent – constrains drawdown, turnover, and concentration,
Portfolio Manager Agent – aggregates views and produces final positions.
This track is especially suitable for students interested in macro, cross-asset trading, event-driven strategies, and LLM reasoning systems.

3. Hybrid Quantamental Multi-Agent Investment System
Design a system that combines structured finance signals with unstructured alternative data.

For example:

a value agent,
a momentum agent,
a narrative or macro-text agent,
an alternative-data verification agent,
a risk-allocation agent.
This direction is attractive because it engages an important research question: whether alternative data are most useful as standalone alpha signals, or whether they add more value as contextual or verification layers inside a broader investment process.

4. Coordination and Attribution Research Project
This direction is for teams who want to focus explicitly on the multi-agent systems research question itself.

Your central question may be:

Does a communicating multi-agent system outperform a single-agent system?
Does fine-grained task decomposition outperform coarse “analyst-manager” role design?
Does debate, voting, hierarchy, or gated approval produce better outcomes?
Which agent actually adds value?
This project direction is strongly motivated by recent literature arguing that coordination design may be one of the most important but least rigorously tested dimensions of financial multi-agent systems.

Investment Universe Requirement
Your project must define a clear investment universe.

Acceptable universes include:

Equities
S&P 500
Nasdaq 100
Russell 1000
Russell 2000
sector or industry portfolios
selected international equity universes, if well justified
Macro / Cross-Asset Universes
U.S. 10Y Yield
U.S. 2Y Yield
Gold
Oil (WTI)
DXY
VIX
MSCI Emerging Markets
Digital Assets
Bitcoin
Ethereum
other major crypto assets or DeFi-linked assets, if justified
For the Menos AI sponsored track, the suggested tradable asset set includes S&P 500, Nasdaq 100, Russell 2000, U.S. 10Y Yield, U.S. 2Y Yield, Gold, Oil (WTI), DXY, VIX, MSCI EM, and Bitcoin.

Core Requirement: Multi-Agent Architecture
Every project must include a meaningful multi-agent design.

At minimum, your system must include:

at least 3 distinct agents with clearly different functions,
an explicit method for aggregation, coordination, or interaction,
and a documented process that translates agent outputs into final portfolio actions.
Possible coordination mechanisms include:

ensemble voting,
hierarchical decision-making,
debate and synthesis,
planner-executor structures,
regime-based switching,
gated approval by a risk or portfolio agent.
Your paper must justify why the multi-agent design is appropriate and explain why a simpler architecture would be less effective.

Required Research Framing
Your paper must explicitly identify one or more research gaps that your project addresses.

Examples:

alternative data are promising, but integration across modalities remains underdeveloped,
multi-agent systems are increasingly popular, but attribution of value added by coordination remains unclear,
narrative-based trading systems often lack strict timestamp discipline and leakage control,
proprietary-data projects often underperform on reproducibility and auditability.
At least one section of your paper should clearly state:

the research gap,
your hypothesis,
and how your design addresses it.
Deliverables
1. Academic Paper
Submit a PDF paper of no more than 7,000 words, written at a Master’s level and formatted in a professional academic style.

Recommended structure:

Title Page
Abstract
Introduction
Literature Review
Research Gap and Hypotheses
Data and Investment Universe
Multi-Agent Architecture
Methodology
Portfolio Construction and Risk Management
Backtesting and Evaluation Design
Results
Attribution and Ablation Analysis
Robustness Checks
Discussion and Limitations
Conclusion
References
Appendix (optional)
2. Reproducible Code Repository
Submit a public GitHub repository containing:

data-processing code,
agent logic and workflow code,
backtesting scripts,
evaluation scripts,
configuration files / prompt templates where relevant,
and a clear README.md.
Your repository should make it possible for another researcher to understand and reproduce your workflow as closely as possible.

3. Presentation
Prepare a presentation of no more than 12 slides.

Your presentation should cover:

research question,
investment universe,
multi-agent architecture,
data sources,
methodology,
main findings,
limitations,
and practical implications.
4. Demo / Walkthrough
Submit a 10-minute demo or recorded walkthrough if your project has a live system, pipeline, or interactive interface.

Methodological Expectations
Your project should go beyond simple backtesting.

At minimum, teams should consider:

transaction costs,
rolling or out-of-sample evaluation,
benchmark comparisons,
ablation tests,
regime or subperiod analysis,
risk-adjusted metrics,
and limitations of the data and design.
For the Menos AI track, the proposal specifies a benchmark setup of $1,000,000 initial capital, 30 bps round-trip transaction cost, and a suggested medium-term holding horizon from several days to several weeks, depending on information timeliness. Longer backtests are preferred when feasible.

Special Evaluation Expectations for This Course
Because this project is tied to live academic gaps, all teams must include:

1. Baseline Comparison
Compare your system to at least one simpler baseline, such as:

a single-agent system,
a no-communication ensemble,
a traditional factor benchmark,
or a simpler text/sentiment baseline.
2. Attribution or Ablation
Show which agents, signals, or data sources actually matter.

Examples:

remove one agent and re-test,
remove one data stream and re-test,
compare hierarchical vs flat coordination,
compare text-only vs text-plus-alt-data.
3. Temporal Discipline
Clearly document when your data became available and how your backtest avoids look-ahead bias.

4. Reproducibility
Document your prompts, configurations, assumptions, and environment as clearly as possible.

Submission Instructions
Please submit all materials to Canvas:

Final Paper PDF
GitHub URL
Slides
Demo / Video, if applicable
Timeline
Project Release: [Insert date]
Due Date: [Insert date]
Weight: 30% of final grade
Evaluation Criteria
Criterion	Weight
Research framing and literature grounding	15%
Multi-agent architecture and system design	20%
Alternative data / narrative methodology	15%
Empirical rigor and backtesting quality	20%
Attribution, robustness, and gap-addressing value	15%
Code quality and reproducibility	10%
Presentation quality and professionalism	5%
Competition and Awards
The final competition will be judged by a panel of faculty and industry professionals. The detailed judge list will be announced separately.

Based on presentation quality, empirical rigor, and overall project strength, the top three teams will receive:

Top 1: $1,000 Award
Top 2: $300 Award
Top 3: $200 Award
All top three teams will also receive an award certificate.

Recommended Readings
You are encouraged to review recent work on:

alternative data in finance,
financial multi-agent systems,
leakage-aware evaluation,
and agent coordination design.
A few especially relevant recent references include a 2024 review of alternative data in finance, a 2026 evaluation paper on financial multi-agent systems and coordination, and a 2026 paper on fine-grained task decomposition in multi-agent trading. These works help motivate why this project should emphasize not only returns, but also architecture quality, attribution, and credible evaluation.

Final Note
This project is meant to be ambitious, research-oriented, and professionally relevant.
The final result of the system does not have to be fully correct. It just needs to show
a new innovative way and going in the right direction (have a right way of thinking).

The best projects will show that you can think like both a researcher and an investment-system designer:

identifying a genuine literature gap,
designing a disciplined multi-agent framework,
working with alternative or narrative data responsibly,
and evaluating the system with intellectual honesty.
We are not only looking for a profitable backtest. We are looking for a project that demonstrates clear thinking, rigorous experimentation, and a compelling view of how AI may reshape trading and investment management.

We look forward to your final presentations.