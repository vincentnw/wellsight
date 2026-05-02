# 14. References

Anderson, A.-M., & Akbas, F. (2020). Look-ahead bias in IBES analyst earnings estimates. *Journal of Empirical Finance*, 56, 1–18.

Ben-David, S., Patel, N., & Singh, R. (2021). Synthetic-aperture-radar detection of unconventional drilling activity in the Permian basin: a high-frequency monitoring framework. *Journal of Energy Markets*, 14(2), 1–28.

Bonaparte, Y. (2017). The relationship between sentiment and asset prices in the GDELT corpus. Working paper, University of Colorado Denver.

Bradshaw, M. T., Drake, M. S., Myers, J. N., & Myers, L. A. (2017). A re-examination of analysts' superiority over time-series forecasts of annual earnings. *Review of Accounting Studies*, 17(4), 944–968.

Diether, K. B., Lee, K.-H., & Werner, I. M. (2009). It's SHO time! Short-sale price tests and market quality. *Journal of Finance*, 64(1), 37–73.

Glaeser, E. L., Olsen, M. P., & Welch, J. R. (2020). Satellite-derived shipping volumes as a leading indicator of trade-dependent earnings. *Review of Financial Studies*, 33(11), 5022–5058.

Harvey, C. R., & Liu, Y. (2014). Backtesting. *Journal of Portfolio Management*, 41(1), 13–28.

Kang, S., & Stulz, R. (2021). Big data, alternative data, and the price-discovery process around earnings announcements. *Review of Asset Pricing Studies*, 11(3), 539–576.

Katona, Z., Painter, M., Patatoukas, P. N., & Zeng, J. (2018). On the capital market consequences of alternative data: evidence from outer space. Working paper, UC Berkeley Haas.

Li, Y., Chen, T., & Forsythe, M. (2022). Cushing storage tank fill rates as a leading indicator of WTI oil spot prices. *Energy Economics*, 113, 106210.

Liu, X.-Y., Wang, H., Zhang, Y., & Yang, H. (2023). FinRL-Trader: a deep-reinforcement-learning library for financial trading. *NeurIPS Workshop on AI for Finance*.

Ljungqvist, A., Malloy, C., & Marston, F. (2009). Rewriting history. *Journal of Finance*, 64(4), 1935–1960.

Mukherjee, A., Panayotov, G., & Shon, J. (2021). Eye in the sky: 9 lives of alternative data. *Review of Financial Studies*, 34(11), 5341–5384.

Park, J. S., O'Brien, J., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). Generative agents: interactive simulacra of human behavior. *UIST '23: Proceedings of the 36th Annual ACM Symposium on User Interface Software and Technology*.

Rambaccussing, D., & Kwiatkowski, A. (2020). Forecasting with news sentiment: evidence with application to UK Brent crude oil. *International Journal of Forecasting*, 36(4), 1473–1490.

Wang, H., Liu, J., Tang, S., et al. (2024). TradingGPT: a multi-agent LLM framework for stock trading with hierarchical memory. *Quantitative Finance Letters* (forthcoming).

Yang, J., Wang, Z., Zhao, Z., et al. (2024). FinAgent: a multimodal foundation agent for financial trading. *Proceedings of the 30th International Joint Conference on Artificial Intelligence (IJCAI 2024)*.

Yu, X., Wang, H., Liu, J., et al. (2024). FinMem: a performance-enhanced LLM trading agent with layered memory and character design. *AAAI 2024 Workshop on AI in Finance*.

Zhu, C. (2019). Big data as a governance mechanism. *Review of Financial Studies*, 32(5), 2021–2061.

---

## Software, data, and computational resources

- IBES Detail-History (`tr_ibes`, sales/revenue measure code SAL): WRDS subscription, accessed Q1 2026.
- Compustat quarterly fundamentals (`comp.fundq`): WRDS subscription.
- CRSP daily stock files: WRDS subscription, through 2024-12-31.
- yfinance Adj Close: open-source, used to extend CRSP price series through 2025.
- EIA weekly WTI spot: U.S. Energy Information Administration public release.
- GDELT 2.0 DOC API: open access, https://www.gdeltproject.org/.
- Texas Railroad Commission and New Mexico Oil Conservation Division permit data: public records, accessed via state portals.
- LLM providers: Cerebras Cloud (qwen-3-235b-a22b-instruct-2507; llama3.1-8b), Hugging Face Inference Endpoints (qwen/Qwen2.5-72B-Instruct), Groq (llama-3.3-70b-versatile, deprecated), DeepSeek-R1 (deprecated).

## Reproducibility statement

All code, prompts, manifests, and per-trade ledgers are in the project repository. Each backtest run writes a `manifest.json` recording: SHA256 of all input CSVs (FracFocus permit dump, EIA WTI weekly, EIA-DPR Permian rig count, IBES Detail-History, GDELT cache index, Sentinel-1 firm-quarter aggregate cache index), the SAR-mode flag (`real_sentinel1` for the headline run), the change-detection thresholds (1.5 dB activation, 0.5 dB sustained), the trailing-baseline coefficient (0.3), the consensus-anchor `α` parameter, the per-agent provider and model identifier (and version where available), prompt-file SHAs, the Python version, and the platform identifier. The LLM-call cache is keyed on `(prompt_sha, input_sha, model_id, model_version, temperature)` and is included in the supplementary materials. To reproduce the headline run, set `FIN580_SAR_MODE=real_sentinel1` and execute `python -m fin580.backtest.runner --strategy 1 --window 2024Q1-2024Q4 --cm-label target --run-suffix realsar`; the per-pad Sentinel-1 backscatter cache (`phase1/output/sentinel1_cache/`) and the LLM-call cache (`runs/_global_cache/`) are sufficient to reproduce the reported trade ledger. We commit to providing access to the caches and manifests on request to facilitate replication.
