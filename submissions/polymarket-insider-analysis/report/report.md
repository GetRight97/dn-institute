# Polymarket Potentially Informed Trading Analysis

## 1. Objective

The objective of this analysis is to identify Polymarket wallets whose public trading behavior is unusually consistent with patterns that may warrant further investigation for potentially informed trading.

The study covers trades from **November 1, 2025 to May 1, 2026**.

The analysis is heuristic and behavioral. A high score does **not** prove that a wallet possessed material non-public information and should not be interpreted as an accusation of insider trading, market manipulation, or other misconduct.

The project is designed as a reproducible screening framework that prioritizes wallets, markets, and trades for closer investigation.

---

## 2. Dataset Scope

The final analysis uses a deliberately scoped market universe.

The selection procedure chooses the **20 highest-volume closed Polymarket markets** returned under the selected date filters while rejecting markets with missing or inverted date ranges.

A market is accepted only when:

```text
start_date is present
end_date is present
start_date < end_date
2025-11-01 <= end_date < 2026-05-01
```

The fixed universe is persisted in:

```text
data/raw/market_dates.csv
```

### Final dataset

The final rerun produced:

- **20 selected markets**
- **18 markets with trades inside the analysis window**
- **20 / 20 markets successfully retrieved during outcome enrichment**
- **20 / 20 markets with an identified final winning outcome**
- **1,562,144 trades returned by the Polymarket Data API**
- **1,253,275 trades inside the analysis period**
- **826,178 raw BUY trades in the enriched dataset**
- **22 total trades after recorded `closed_time`**
- **11 post-close BUY trades excluded from predictive metrics**
- **826,167 predictive BUY trades**
- **490,382 predictive BUY trades on the eventual winning outcome**
- **214,824 unique predictive BUY wallets**

The resulting global predictive BUY hit-rate baseline is:

```text
490,382 / 826,167 = 59.36%
```

This is a trade-weighted descriptive baseline, not the accuracy of the average trader.

### Scope limitation

This is not a complete census of Polymarket activity during the period.

The sample intentionally prioritizes highly liquid closed markets. Potentially informed behavior occurring only in lower-volume markets may therefore be absent.

---

## 3. Primary Data Sources and Provenance

The project uses public Polymarket data.

### 3.1 Polymarket Data API v2

Official documentation:

https://data-api.polymarket.com/v2/docs

Historical trade data is retrieved from:

```text
https://data-api.polymarket.com/v2/trades
```

Relevant script:

```text
src/collect_data.py
```

The official Data API documentation describes the public trade feed and cursor-based pagination behavior used by the collector.

The collector uses:

- a fixed market `condition_id`
- cursor pagination
- request timeouts
- HTTP status handling
- rate-limit handling
- retries with backoff
- local filtering to the analysis period

### 3.2 Polymarket Gamma API

Official documentation:

https://gamma-api.polymarket.com/docs

Market discovery and historical market metadata are accessed through the Polymarket public SDK / Gamma interface.

Relevant scripts:

```text
src/market_dates.py
src/market_outcomes.py
```

The market-selection process orders closed markets by volume and applies the target date filter. Local validation rejects missing or invalid temporal ranges before a market is appended to the fixed universe.

### 3.3 Polymarket market mechanics

Official documentation:

https://docs.polymarket.com/faq

This source documents the basic mechanics of outcome shares, market prices, and settlement values used when interpreting trades and hold-to-resolution payoff.

### 3.4 Headline statistic provenance

Headline statistics are produced directly by the included pipeline.

```text
data/raw/market_dates.csv
        ↓
src/collect_data.py
        ↓
data/raw/trades.csv
        ↓
src/market_outcomes.py
        ↓
data/processed/market_outcomes.csv
        ↓
src/trades_with_outcome.py
        ↓
data/processed/trades_with_outcome.csv
        ↓
src/trader_accuracy.py
src/trader_edge.py
src/trader_market_signals.py
        ↓
src/insider_score.py
        ↓
results/insider_ranking.csv
results/insider_ranking_top100.csv
        ↓
src/candidate_details.py
        ↓
results/candidate_details.csv
```

The counts in this report correspond to the final rerun after the market-date and post-close leakage fixes.

---

## 4. Market Resolution and Timing

All 20 selected condition IDs were successfully retrieved during outcome enrichment.

All 20 selected markets had:

- recorded `closed_time`
- resolved final state
- identifiable winning outcome

All **1,253,275** in-window trades were successfully matched to market metadata.

Timing was available for every processed trade.

The enriched dataset contains:

```text
22 trades after recorded closed_time
```

Those rows are retained for diagnostics rather than deleted from the source-derived dataset.

For each trade:

```text
hours_before_close =
closed_time - trade_timestamp
```

A positive value means the trade occurred before recorded close. A negative value means it occurred after recorded close.

`closed_time` should not be interpreted as the exact moment when decisive information became public. It is used only as a consistent market-timing reference.

---

## 5. Outcome-Leakage Protection

A central review correction was to prevent post-close observations from entering predictive metrics.

The final predictive scripts require:

```text
hours_before_close >= 0
```

before updating wallet statistics.

The enriched dataset contains 22 post-close trades in total. Of those, **11 are BUY trades**.

Those 11 BUYs are excluded before calculating:

- total BUY count
- winning BUY count
- hit rate
- BUY volume
- BUY-only hold-to-resolution profit proxy
- low-price win counts
- very-low-price win counts
- late low-price win counts
- wallet + market aggregates
- final ranking inputs

The final predictive population is therefore:

```text
826,167 BUY trades
490,382 winning BUY trades
59.36% global BUY hit-rate baseline
```

The raw enriched dataset remains auditable while predictive metrics avoid post-outcome leakage.

---

## 6. Heuristics

No single metric is treated as sufficient evidence.

### 6.1 Winning BUY hit rate

A BUY is directionally correct when the purchased outcome ultimately resolves as the winner.

```text
hit_rate =
winning BUY count / predictive BUY count
```

Each wallet is compared with the global predictive baseline:

```text
59.36%
```

and:

```text
edge_vs_baseline =
wallet hit rate - 59.36%
```

SELL trades are not interpreted directionally because a SELL can represent closing a position, hedging, inventory management, or exposure reduction.

### 6.2 Low-price winning entries

Two thresholds are used:

```text
low-price win:      price <= 0.50
very-low-price win: price <= 0.25
```

A correct entry at a relatively low price is treated as more behaviorally unusual than purchasing an outcome already priced near certainty.

These thresholds are heuristic rather than formal statistical tests.

### 6.3 Late low-price winning entries

A late low-price winning BUY is defined as:

```text
side == BUY
trade outcome == final winning outcome
price <= 0.50
0 <= hours_before_close <= 24
```

This surfaces correct low-price positioning near recorded market closure without using post-close observations.

### 6.4 BUY-only hold-to-resolution profit proxy

For a winning BUY:

```text
profit_proxy = size * (1 - price)
```

For a losing BUY:

```text
profit_proxy = -size * price
```

This is **not realized P&L**.

It assumes each BUY is held to resolution and ignores SELLs, exits, hedges, offsetting positions, transfers, fees, and complete position reconstruction.

### 6.5 Wallet + market aggregation

A single economic position may be split across many fills.

To avoid treating every fill as independent evidence, the main signal pipeline first aggregates at:

```text
wallet + market
```

and then summarizes repeated evidence across markets.

For each wallet, the analysis measures:

- number of markets traded
- profitable markets under the BUY-only proxy
- low-price winning markets
- very-low-price winning markets
- late low-price winning markets
- corresponding cross-market ratios

---

## 7. Exploratory Predictive Metrics

The final trader-level rerun produced:

```text
214,824 predictive BUY wallets
3,889 wallets with at least 20 BUY trades
```

The wallet-market aggregation produced:

```text
312,933 wallet-market combinations
21,638 wallets active in at least 3 markets
```

Both `trader_accuracy.py` and `trader_edge.py` reported:

```text
11 post-close BUY excluded
0 BUY with missing/invalid timing excluded
```

`trader_market_signals.py` reported the same 11 post-close BUYs excluded before predictive aggregation.

This consistency is an internal validation check.

---

## 8. Candidate Ranking Model

Each wallet receives a final candidate score from 0 to 100.

The score is an **investigation-priority heuristic**, not a probability of insider trading.

| Component | Maximum Score |
|---|---:|
| Very-low-price cross-market evidence | 25 |
| Late low-price cross-market evidence | 20 |
| BUY hit-rate edge vs baseline | 20 |
| Profitable-market ratio | 15 |
| BUY-only hold-to-resolution profit proxy | 10 |
| Cross-market breadth | 5 |
| BUY volume | 5 |
| **Total** | **100** |

### Reliability adjustment

Small samples can generate extreme metrics by chance.

The raw candidate score is multiplied by a reliability factor based on:

- predictive BUY count
- number of distinct markets

This reduces the influence of wallets with limited evidence without automatically discarding them.

The reliability adjustment is heuristic and is not a formal significance test.

---

## 9. Signal-Level Interpretation

| Candidate Score | Signal Level |
|---:|---|
| >= 75 | VERY HIGH |
| >= 60 | HIGH |
| >= 45 | ELEVATED |
| >= 30 | MODERATE |
| < 30 | LOW |

These labels describe only how strongly observable behavior matches the selected heuristics.

They are not legal risk ratings, probabilities of insider trading, or accusations of misconduct.

---

## 10. Final Ranking

The final ranking contains:

```text
214,824 wallets
```

The top ten candidates are:

| Rank | Wallet | Score | Signal | Markets | BUY | Hit Rate | Edge vs Baseline |
|---:|---|---:|---|---:|---:|---:|---:|
| 1 | `0xcf6a714618a328c608a1c70cb62a31a6bef3f9d0` | 76.10 | VERY HIGH | 8 | 155 | 85.16% | +25.81 pp |
| 2 | `0x10b289276b2b69cac7b1bbc58601009b6ee74ceb` | 69.67 | HIGH | 10 | 851 | 81.90% | +22.55 pp |
| 3 | `0xc9db6c957b2ba169608907443f3991b8d01b2ad3` | 67.15 | HIGH | 6 | 579 | 92.23% | +32.87 pp |
| 4 | `0xad529df14c293d77984a0137990a1441b25211ac` | 66.97 | HIGH | 11 | 119 | 73.11% | +13.75 pp |
| 5 | `0xd6639bff2beb2bcc0cfedc27e0f7980964e1ca64` | 66.55 | HIGH | 6 | 138 | 73.19% | +13.83 pp |
| 6 | `0xdde1a0257ddcc19522df5128049ce5619944f1d7` | 64.80 | HIGH | 6 | 97 | 85.57% | +26.21 pp |
| 7 | `0x8f42ae0a01c0383c7ca8bd060b86a645ee74b88f` | 64.31 | HIGH | 7 | 60 | 88.33% | +28.98 pp |
| 8 | `0x86ce8bf4ea6334796156e558642f83f4df0d8af5` | 63.98 | HIGH | 8 | 114 | 92.98% | +33.63 pp |
| 9 | `0x09fe78c8b9f10fb9c7c0a584bfab4205c76876ee` | 62.76 | HIGH | 11 | 447 | 93.29% | +33.93 pp |
| 10 | `0xbb39ba863319281427a482c8714ffdf69cb7ee8a` | 62.71 | HIGH | 7 | 195 | 67.69% | +8.34 pp |

### Highest-ranked candidate

Wallet:

```text
0xcf6a714618a328c608a1c70cb62a31a6bef3f9d0
```

Summary:

```text
Candidate score:          76.10 / 100
Signal level:             VERY HIGH
Reliability:              100%
Markets:                  8
Predictive BUY trades:    155
Hit rate:                 85.16%
Global baseline:          59.36%
Edge vs baseline:         +25.81 percentage points
Profitable-market ratio:  62.5%
Very-low-price markets:   3 / 8
Late low-price markets:   1 / 8
BUY-only profit proxy:    ~$78,919.51
BUY volume:               ~$108,422.21
```

The wallet ranks highly because several different behavioral signals occur together.

This does not establish access to non-public information.

---

## 11. Candidate-Level Trade Evidence

`src/candidate_details.py` extracts low-price winning BUY examples for the top ten candidates.

The final rerun produced:

```text
613 interesting trades
```

Candidate examples are restricted to valid **pre-close** observations.

A trade is not included when:

```text
hours_before_close is missing
or
hours_before_close < 0
```

This keeps candidate examples aligned with the same anti-leakage rule used by predictive metrics.

The resulting artifact is:

```text
results/candidate_details.csv
```

The examples should be interpreted as leads for event-specific follow-up, not proof of informed trading.

---

## 12. Interpretation of High Scores

A high-scoring wallet may have several alternative explanations, including:

- specialized domain expertise
- quantitative trading
- rapid reaction to public information
- automation
- market-making behavior
- systematic exploitation of pricing inefficiencies
- portfolio strategies not reconstructed by this analysis

A high score means the wallet's public trading behavior is unusually consistent with the selected screening heuristics.

It does not explain why the pattern occurred.

---

## 13. Important Limitations

### Scoped market universe

The final universe contains only 20 selected high-volume closed markets, and only 18 contain in-window trades.

### Public data only

The project cannot determine what information a trader possessed, when they acquired it, or whether it was public.

### `closed_time` is only a proxy

Recorded market close is not necessarily the first public disclosure timestamp for the underlying event.

A stronger follow-up investigation would compare:

```text
trade timestamp
vs.
first verified public disclosure timestamp
```

### Profit proxy is not realized P&L

The BUY-only proxy does not reconstruct SELLs or complete wallet positions.

### Wallets do not equal individuals

A wallet can represent an individual, bot, firm, shared service, or automated strategy.

### Correlated markets and events

Multiple markets can represent related versions of the same real-world event, so cross-market observations are not always statistically independent.

### Price is only an approximate probability signal

Liquidity, spread, order-book effects, and temporary dislocations can influence market prices.

### Reliability factor is heuristic

The reliability adjustment is not a formal significance test.

---

## 14. Potential Improvements

Future work could strengthen the analysis through:

- event clustering
- exact public-information timelines
- BUY/SELL position reconstruction
- realized and mark-to-market P&L
- wallet clustering
- funding-flow analysis
- matched control wallets
- statistical significance testing
- category-specific peer baselines

---

## 15. Reproducibility

Execution order:

```text
src/market_dates.py
src/collect_data.py
src/market_outcomes.py
src/trades_with_outcome.py
src/trader_accuracy.py
src/trader_edge.py
src/trader_market_signals.py
src/insider_score.py
src/candidate_details.py
```

Validation:

```text
python -m compileall src checks
```

### Committed compact artifacts

```text
data/raw/market_dates.csv
data/processed/market_outcomes.csv
results/insider_ranking_top100.csv
results/candidate_details.csv
report/report.md
```

### Generated full analytical outputs

```text
results/trader_accuracy.csv
results/trader_edge.csv
results/trader_market_signals.csv
results/insider_ranking.csv
```

These complete result tables are intentionally excluded from version control because of their size.

### Generated large trade-level datasets

```text
data/raw/trades.csv
data/processed/trades_with_outcome.csv
```

These are also excluded from Git and can be regenerated from the documented public sources.

---

## 16. Conclusion

The final project provides a reproducible screening framework for identifying Polymarket wallets whose public behavior is unusually consistent with selected heuristics for potentially informed trading.

The final scoped dataset contains:

```text
20 selected markets
18 markets with in-window trades
1,253,275 in-window trades
826,167 predictive BUY trades
490,382 winning predictive BUY trades
214,824 predictive BUY wallets
```

The global predictive BUY baseline is:

```text
59.36%
```

The highest-ranked wallet received:

```text
76.10 / 100
```

with a `VERY HIGH` heuristic signal level.

The candidate-level extraction produced:

```text
613 pre-close interesting trades
```

across the top ten candidates.

The ranking should be used as a **candidate-generation and prioritization tool for further investigation**, not as evidence that a specific wallet possessed material non-public information or engaged in unlawful conduct.
