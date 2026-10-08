# Polymarket Potentially Informed Trading Analysis

This project investigates public Polymarket trading behavior that may be consistent with potentially informed trading.

The analysis window is:

**November 1, 2025 — May 1, 2026**

The goal is **not** to identify or accuse traders of insider trading. Instead, the project builds transparent behavioral heuristics and ranks wallets according to how strongly their public trading activity matches those heuristics.

---

## Dataset Scope

To keep the analysis reproducible and computationally manageable, the final dataset uses a deliberately scoped market universe:

- the **20 highest-volume closed Polymarket markets** returned by the Polymarket SDK within the analysis date window;
- all available public trades returned by the Polymarket Data API for those selected markets;
- trades are filtered to `2025-11-01 <= trade_date < 2026-05-01`.

Final pipeline statistics:

- **20 selected markets**
- **18 markets with trades inside the analysis window**
- **1,425,219 trades returned by the API for the selected markets**
- **1,187,786 trades inside the analysis window**
- **794,187 BUY trades**
- **463,273 BUY trades on the eventual winning outcome**
- **58.33% global BUY outcome hit-rate baseline**
- **207,119 unique BUY wallets**
- **20 / 20 selected markets resolved with an identified winner**
- **23 trades with timestamps after recorded `closed_time`**, retained for diagnostics and excluded from late-trade heuristics

This is **not a complete census of all Polymarket markets** during the period. The market-selection procedure intentionally favors highly liquid markets and may miss potentially informed behavior in lower-volume markets.

---

## Data Sources

The project uses public Polymarket data.

### Market discovery and metadata

Market metadata is retrieved through the Polymarket public SDK / Gamma API interface.

The market-selection script requests closed markets with scheduled end dates inside the target period and orders them by volume.

Relevant project file:

```text
src/market_dates.py
```

### Trades

Trade data is retrieved from:

```text
https://data-api.polymarket.com/v2/trades
```

Trades are paginated by market `condition_id`.

Relevant project file:

```text
src/collect_data.py
```

### Market outcomes

Final market state, outcome prices, close time, and winning outcome are retrieved through the Polymarket SDK.

Relevant project file:

```text
src/market_outcomes.py
```

The pipeline fails if required market metadata cannot be retrieved, rather than silently dropping unresolved lookups.

---

## Trade-Level Fields

The collected trade data includes fields such as:

- wallet / proxy wallet
- market condition ID
- BUY / SELL side
- selected outcome
- trade price
- size
- timestamp
- transaction hash
- market title

The enriched dataset additionally contains:

- winning outcome
- recorded market `closed_time`
- `hours_before_close`
- whether a BUY was on the eventual winning outcome
- resolution metadata

---

## Project Structure

```text
polymarket-insider-analysis/
│
├── src/
│   ├── collect_data.py
│   ├── market_dates.py
│   ├── market_outcomes.py
│   ├── trades_with_outcome.py
│   ├── trader_stats.py
│   ├── trader_accuracy.py
│   ├── trader_edge.py
│   ├── trader_market_signals.py
│   ├── insider_score.py
│   └── candidate_details.py
│
├── data/
│   ├── raw/
│   │   ├── market_dates.csv
│   │   └── trades.csv
│   │
│   └── processed/
│       ├── market_outcomes.csv
│       └── trades_with_outcome.csv
│
├── results/
│   ├── insider_ranking_top100.csv
│   └── candidate_details.csv
│
├── checks/
│   ├── check_condition_lookup.py
│   ├── check_sdk_market.py
│   ├── check_data.py
│   ├── check_resolution.py
│   └── check_closed_market.py
│
├── archive/
│   ├── heuristics_old.py
│   ├── trade_timing_old.py
│   └── heuristics_results_old.csv
│
├── report/
│   └── report.md
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

# Methodology

The main analysis focuses on **BUY trades on resolved markets**.

SELL activity is preserved in the raw data but is not interpreted directionally in the main heuristic model because a SELL can represent profit-taking, position reduction, hedging, or other portfolio management rather than a bearish prediction.

---

## 1. BUY Outcome Hit Rate

A BUY is counted as a winning BUY when the purchased outcome eventually resolves as the winner.

The global BUY baseline in the scoped dataset is:

```text
463,273 winning BUY
---------------------- = 58.33%
794,187 total BUY
```

This baseline is a **trade-weighted outcome hit rate**, not the probability that an average trader is correct.

Highly active wallets can contribute many trades to the baseline.

Accuracy alone is not treated as evidence of informed trading because a trader can achieve a high hit rate by repeatedly buying outcomes that are already strongly favored by the market.

---

## 2. Low-Price Winning BUYs

Winning BUYs entered at relatively low prices are treated as more informative.

Two thresholds are used:

```text
price <= 0.50
price <= 0.25
```

A winning BUY at `0.20` is considered more unusual than a winning BUY at `0.99`, because the market price assigned substantially lower probability to that outcome at entry.

These thresholds are heuristic and should not be interpreted as statistical proof of informed behavior.

---

## 3. Late Low-Price Winning BUYs

Trade timestamps are compared with the market's recorded `closed_time`.

A trade is considered a late low-price winning BUY when:

```text
BUY is on eventual winner
price <= 0.50
0 <= hours_before_close <= 24
```

Trades with negative `hours_before_close` are **not** counted as late signals.

The pipeline identified 23 trades with timestamps after recorded `closed_time`. These rows are retained for diagnostics but excluded from timing heuristics.

`closed_time` is only a proxy for the timing of market closure. It does not necessarily represent the exact moment when relevant public or non-public information became available.

---

## 4. BUY-Only Hold-to-Resolution Profit Proxy

For BUY trades, the project calculates a hypothetical hold-to-resolution payoff proxy.

For a winning BUY:

```text
profit_proxy = size * (1 - price)
```

For a losing BUY:

```text
profit_proxy = -size * price
```

This metric is **not realized P&L**.

It assumes each BUY position is held until market resolution and ignores:

- SELL trades
- partial exits
- hedging
- offsetting positions
- transfers
- portfolio-level netting
- execution costs

The metric is used only as one behavioral signal in the ranking.

---

## 5. Wallet + Market Aggregation

Repeated fills in the same market can heavily distort trade-level statistics.

For example, 100 successful fills on one market should not necessarily be treated as 100 independent successful predictions.

The project therefore aggregates important signals first at:

```text
wallet + market
```

and then across markets for each wallet.

For each wallet, the pipeline calculates:

- number of markets traded
- number of profitable markets under the BUY-only proxy
- markets containing winning BUYs at `price <= 0.50`
- markets containing winning BUYs at `price <= 0.25`
- markets containing late low-price winning BUYs
- ratios of these signals to total markets

This gives more weight to repeated behavior across separate markets than to many fills inside a single market.

---

# Candidate Ranking Model

The final candidate score ranges from:

```text
0 — 100
```

The score is designed as an explainable investigation-priority heuristic.

It is **not** an estimate of the probability that a wallet engaged in insider trading.

The raw score contains the following components:

| Signal | Maximum |
|---|---:|
| Very-low-price cross-market evidence | 25 |
| Late low-price cross-market evidence | 20 |
| Hit-rate edge vs global baseline | 20 |
| Profitable market ratio | 15 |
| BUY-only profit proxy | 10 |
| Cross-market breadth | 5 |
| BUY volume | 5 |
| **Total** | **100** |

---

## Very-Low-Price Signal — 25 points

This component combines:

- number of markets with winning BUYs at `price <= 0.25`
- proportion of a wallet's markets containing such activity

This prevents the ranking from relying entirely on either absolute counts or ratios.

---

## Late Low-Price Signal — 20 points

This component combines:

- number of markets containing late low-price winning BUYs
- proportion of the wallet's markets containing the timing signal

A qualifying trade must occur no more than 24 hours before recorded market closure.

---

## Hit-Rate Edge — 20 points

The global resolved BUY hit rate is:

```text
58.33%
```

Only positive performance relative to this baseline contributes to the score.

A wallet performing below the global baseline receives no points from this component.

---

## Profitable Market Ratio — 15 points

This measures the fraction of markets in which the wallet has positive aggregate BUY-only hold-to-resolution profit proxy.

The purpose is to reward cross-market consistency rather than a single highly profitable market.

---

## Profit Proxy — 10 points

Positive BUY-only hold-to-resolution profit proxy contributes to the score.

A logarithmic transformation is used so that one extremely large wallet cannot dominate the entire ranking.

---

## Cross-Market Breadth — 5 points

Wallets active across more markets receive a small breadth contribution.

This helps distinguish repeated behavior from one-market activity.

---

## BUY Volume — 5 points

BUY volume contributes modestly to the ranking.

Volume is logarithmically scaled to reduce domination by extremely large wallets.

---

# Reliability Adjustment

Small samples can produce extreme statistics by chance.

For example:

```text
3 successful BUYs out of 3
```

should not receive the same evidentiary weight as:

```text
500 successful BUYs across multiple markets
```

The raw candidate score is therefore multiplied by a reliability factor based on:

- number of BUY observations
- number of markets traded

The reliability adjustment does not completely discard small wallets but reduces the influence of limited evidence.

The final ranking field is:

```text
candidate_score
```

---

# Signal Levels

Candidate scores are mapped to descriptive investigation-priority categories:

```text
>= 75    VERY HIGH
>= 60    HIGH
>= 45    ELEVATED
>= 30    MODERATE
< 30     LOW
```

These labels describe **heuristic signal strength only**.

They are not legal risk assessments and do not imply misconduct.

---

# Main Results

The ranking covers:

```text
207,119 wallets
```

The current five highest-ranked candidates are:

| Rank | Wallet | Score | Signal |
|---:|---|---:|---|
| 1 | `0xcf6a714618a328c608a1c70cb62a31a6bef3f9d0` | 76.10 | VERY HIGH |
| 2 | `0x10b289276b2b69cac7b1bbc58601009b6ee74ceb` | 70.29 | HIGH |
| 3 | `0xad529df14c293d77984a0137990a1441b25211ac` | 67.79 | HIGH |
| 4 | `0xd6639bff2beb2bcc0cfedc27e0f7980964e1ca64` | 67.37 | HIGH |
| 5 | `0xc9db6c957b2ba169608907443f3991b8d01b2ad3` | 67.15 | HIGH |

---

## Leading Candidate

The highest-ranked wallet is:

```text
0xcf6a714618a328c608a1c70cb62a31a6bef3f9d0
```

Summary:

```text
Candidate score:         76.10 / 100
Signal level:            VERY HIGH
Reliability:             100%
Markets:                 8
BUY trades:              155
BUY hit rate:            85.16%
Global baseline:         58.33%
Edge vs baseline:        +26.83 percentage points
Profitable markets:      62.5%
Very-low-price markets:  3 / 8
Late low-price markets:  1 / 8
BUY volume:              ~$108,422
BUY-only profit proxy:   ~$78,920
```

The wallet is a candidate for further investigation because several signals occur together: elevated outcome hit rate, low-price winning entries, cross-market repetition, substantial activity, and at least one late low-price winning market.

These observations do **not** establish access to material non-public information.

---

# Example Trade-Level Signals

The detailed candidate extraction produced:

```text
711 interesting low-price winning BUY trades
```

across the top 10 ranked wallets.

One notable example is associated with:

```text
Market:
US strikes Iran by February 28, 2026?

Outcome:
Yes

Entry price:
~0.1548

Hours before recorded close:
~15.86

BUY volume:
~$4,025.96

BUY-only hold-to-resolution profit proxy:
~$21,974.04
```

Another top-ranked candidate purchased the eventual winning outcome in the same market at:

```text
price: ~0.08
hours before recorded close: ~23.44
```

These examples illustrate why the late low-price signal is useful for candidate generation.

They do not establish when relevant information became public, why the trades were placed, or whether the traders possessed non-public information.

Detailed candidate-level records are stored in:

```text
results/candidate_details.csv
```

---

# Running the Pipeline

Install dependencies:

```bash
pip install -r requirements.txt
```

## 1. Select the market universe

```bash
python src/market_dates.py
```

This creates:

```text
data/raw/market_dates.csv
```

## 2. Collect trades

```bash
python src/collect_data.py
```

This creates:

```text
data/raw/trades.csv
```

The collector uses cursor pagination, request timeouts, retry handling, and rate-limit handling.

## 3. Collect final market outcomes

```bash
python src/market_outcomes.py
```

This creates:

```text
data/processed/market_outcomes.csv
```

The script retries temporary failures and fails rather than silently omitting markets when required metadata cannot be retrieved.

## 4. Enrich trades

```bash
python src/trades_with_outcome.py
```

This creates:

```text
data/processed/trades_with_outcome.csv
```

## 5. Trader-level metrics

```bash
python src/trader_accuracy.py
python src/trader_edge.py
python src/trader_market_signals.py
```

## 6. Final ranking

```bash
python src/insider_score.py
```

This creates both:

```text
results/insider_ranking.csv
results/insider_ranking_top100.csv
```

The complete ranking remains local, while the compact TOP-100 ranking is committed for review.

## 7. Candidate trade details

```bash
python src/candidate_details.py
```

This creates:

```text
results/candidate_details.csv
```

---

# Main Output Artifacts

The repository includes the compact final artifacts:

```text
results/insider_ranking_top100.csv
results/candidate_details.csv
report/report.md
```

The following full generated result tables are intentionally excluded from version control because of their size:

```text
results/insider_ranking.csv
results/trader_accuracy.csv
results/trader_edge.csv
results/trader_market_signals.csv
```

They are reproduced automatically by the analysis scripts.

`src/insider_score.py` generates both:

```text
results/insider_ranking.csv
results/insider_ranking_top100.csv
```

The TOP-100 file is committed as a compact review artifact, while the complete ranking remains local.

---

# Large Data Files

Large trade-level datasets are intentionally excluded from version control.

Ignored generated files include:

```text
data/raw/trades.csv
data/processed/trades_with_outcome.csv
data/processed/trades_with_timing.csv
```

`trades_with_timing.csv` is a deprecated artifact from an earlier version of the analysis and is not part of the current pipeline.

The current raw and enriched trade datasets can be reproduced using the scripts in `src/`.

---

# Reproducibility Notes

The final market universe is saved in:

```text
data/raw/market_dates.csv
```

This makes the selected market sample explicit.

The final outcomes are saved in:

```text
data/processed/market_outcomes.csv
```

The ranking is derived entirely from public trade and market data through the documented pipeline.

Because public APIs can change over time, exact reproduction may depend on continued availability and consistency of the Polymarket endpoints.

---

# Important Limitations

This analysis identifies unusual public trading patterns, **not legal insider trading**.

Major limitations include:

- public trade data cannot reveal a trader's actual information set;
- wallet addresses may represent bots, automated strategies, multiple users, or coordinated systems;
- `closed_time` does not necessarily correspond to the moment relevant information became public;
- the BUY-only profit proxy is not realized P&L;
- SELL trades are not interpreted directionally;
- related prediction markets may share the same underlying event;
- repeated trades may be generated by algorithmic execution;
- market price is treated as an approximate probability signal for heuristic purposes;
- the analysis does not reconstruct the complete public-information timeline for each event;
- the selected universe contains only the 20 highest-volume closed markets under the chosen date filter;
- lower-volume markets are therefore outside the final analysis;
- only 18 of the 20 selected markets contain trades within the analysis window;
- the reliability adjustment is heuristic rather than a formal statistical significance test.

For these reasons, high-ranked wallets should be interpreted only as **candidates for further investigation**.

---

# Interpretation

A high candidate score means:

> the wallet's public trading activity is unusually consistent with the selected behavioral heuristics.

It does **not** mean:

> the wallet has been proven to possess inside information.

A stronger investigation would additionally require:

- event-specific information timelines;
- news timestamps;
- public announcements;
- blockchain-level position reconstruction;
- BUY and SELL position netting;
- wallet clustering;
- funding-source analysis;
- comparison with matched control groups;
- formal statistical testing.

---

# Disclaimer

This project is an exploratory behavioral analysis using public Polymarket data.

The ranking identifies wallets whose trading patterns are unusually consistent with selected heuristics for potentially informed trading.

It does not establish that any wallet possessed material non-public information, violated Polymarket rules, or engaged in unlawful conduct.
