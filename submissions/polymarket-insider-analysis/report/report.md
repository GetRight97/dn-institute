# Polymarket Potentially Informed Trading Analysis

## 1. Objective

The objective of this analysis is to identify Polymarket wallets whose public trading behavior is unusually consistent with patterns that may warrant further investigation for potentially informed trading.

The study covers trades between:

**November 1, 2025 and May 1, 2026**

The analysis is heuristic and behavioral.

A high score does **not** prove that a wallet possessed material non-public information and should not be interpreted as an accusation of insider trading, market manipulation, or any other misconduct.

The purpose of the project is to build a reproducible screening framework that highlights wallets, markets, and trades that deserve closer manual investigation.

---

## 2. Dataset Scope

The final analysis uses a deliberately scoped market universe rather than attempting to crawl every Polymarket market in the period.

The market-selection procedure chooses:

> the 20 highest-volume closed Polymarket markets returned by the public SDK under the selected date filters.

The scheduled market end date must satisfy:

```text
2025-11-01 <= endDate < 2026-05-01
```

The selected universe is saved to:

```text
data/raw/market_dates.csv
```

All downstream trade collection uses these fixed condition IDs.

This makes the final sample explicit and reproducible.

### Final dataset

The selected universe contains:

- **20 selected markets**
- **20 / 20 markets successfully retrieved during outcome enrichment**
- **20 / 20 markets with an identified final winning outcome**
- **18 markets with trades inside the analysis window**
- **1,425,219 trades returned by the trade API for the selected markets**
- **1,187,786 trades inside the analysis period**
- **794,187 BUY trades**
- **463,273 BUY trades on the eventual winning outcome**
- **207,119 unique BUY wallets**

The resulting global BUY outcome hit rate is:

```text
463,273 / 794,187 = 58.33%
```

This value is used as a descriptive trade-weighted baseline.

It should not be interpreted as the accuracy of the average trader because highly active wallets can contribute many observations.

### Scope limitation

This is not a complete census of all Polymarket activity between November 2025 and May 2026.

The sample intentionally prioritizes highly liquid markets.

Potentially informed behavior occurring only in lower-volume markets may therefore be absent from the analysis.

---

## 3. Data Sources

The project uses public Polymarket data.

### 3.1 Market discovery and metadata

Market discovery and market metadata are retrieved through the Polymarket public SDK / Gamma market-data interface.

The relevant project script is:

```text
src/market_dates.py
```

The market request uses the following selection logic:

```text
closed = true
end_date_min = 2025-11-01
end_date_max = 2026-05-01
order = volume
ascending = false
```

The resulting condition IDs and market dates are persisted before trade collection.

### 3.2 Trade data

Historical public trade data is retrieved from the Polymarket Data API v2 endpoint:

```text
https://data-api.polymarket.com/v2/trades
```

The relevant project script is:

```text
src/collect_data.py
```

Trades are downloaded separately for each selected market using its `condition_id`.

The collector uses cursor pagination and continues until the available trade history for the market is exhausted.

The implementation includes:

- request timeout handling
- retry handling
- HTTP 429 handling
- exponential backoff
- retry handling for temporary 5xx failures

After collection, trades are restricted to:

```text
2025-11-01 <= trade timestamp < 2026-05-01
```

### 3.3 Market outcomes

Final market state and outcome metadata are retrieved using the public Polymarket SDK.

The relevant project script is:

```text
src/market_outcomes.py
```

For each selected condition ID, the script retrieves:

- market title
- closed state
- recorded `closed_time`
- scheduled end date
- final outcome prices
- winning outcome
- UMA status when exposed by the market object

The script uses retries and fails rather than silently creating an incomplete result if required market lookups fail.

---

## 4. Data Integrity Checks

All:

```text
1,187,786
```

in-window trades were successfully matched to market outcome metadata.

All trades in the processed dataset are associated with markets for which a winning outcome could be identified.

The enriched dataset contains:

```text
794,187 BUY trades
463,273 winning BUY trades
```

The BUY hit-rate baseline is therefore:

```text
58.33%
```

Timing data is available for all processed trades.

A diagnostic check found:

```text
23 trades
```

whose timestamps occur after the market's recorded `closed_time`.

These trades represent only a very small fraction of the dataset.

They are retained for diagnostics but are excluded from late-trading heuristics because the late-trade condition explicitly requires:

```text
hours_before_close >= 0
```

---

## 5. Market Resolution and Timing

An earlier version of the project relied more heavily on scheduled market end dates.

The final methodology instead uses Polymarket's recorded:

```text
closed_time
```

when measuring proximity to closure.

For each trade:

```text
hours_before_close =
closed_time - trade_timestamp
```

A positive value means the trade occurred before the recorded close.

A negative value means the trade timestamp appears after the recorded close.

`closed_time` remains only a proxy for the information environment.

It does not establish when the decisive underlying information became public.

For example, a market may remain open for some time after an event becomes widely known, or its recorded close may not exactly correspond to the information-release timestamp.

Timing signals are therefore used only for candidate generation.

---

## 6. Heuristics

The analysis uses several complementary behavioral signals.

No single metric is treated as sufficient evidence on its own.

---

### 6.1 Winning BUY Hit Rate

A BUY is considered directionally correct when the purchased outcome eventually wins.

In simplified form:

```text
trade outcome == final winning outcome
```

SELL trades are excluded from directional hit-rate calculations.

A SELL can represent:

- closing an existing position
- reducing exposure
- hedging
- market-making inventory management
- portfolio rebalancing

Therefore, a SELL is not safely interpretable as a direct prediction about the final outcome.

For each wallet:

```text
hit_rate =
winning BUY count / total BUY count
```

The wallet is also compared with the dataset baseline:

```text
edge_vs_baseline =
wallet hit rate - 58.33%
```

High hit rate alone is not treated as strong evidence because traders may repeatedly buy outcomes already priced near certainty.

---

### 6.2 Low-Price Winning Entries

A correct trade is more informative when the winning outcome was relatively inexpensive at entry.

Two thresholds are used:

```text
low-price win:
price <= 0.50

very-low-price win:
price <= 0.25
```

For example:

```text
BUY eventual winner at 0.95
```

provides less unusual evidence than:

```text
BUY eventual winner at 0.15
```

because the latter was priced as substantially less likely by the market.

These thresholds are heuristic rather than formal probability tests.

---

### 6.3 Late Low-Price Winning Entries

Timing becomes more interesting when a trader buys the eventual winning outcome at a relatively low price shortly before the market closes.

A late low-price winning BUY is defined as:

```text
side == BUY
trade outcome == final winning outcome
price <= 0.50
0 <= hours_before_close <= 24
```

Trades after recorded `closed_time` do not qualify.

This heuristic attempts to surface cases where successful low-price positioning occurred close to market closure.

It does not establish whether the relevant information was already public at the time.

---

### 6.4 BUY-Only Hold-to-Resolution Profit Proxy

For BUY trades, the project calculates a hypothetical hold-to-resolution payoff proxy.

For a winning BUY:

```text
profit_proxy = size * (1 - price)
```

For a losing BUY:

```text
profit_proxy = -size * price
```

This is **not realized P&L**.

The calculation assumes that every BUY position is held until resolution.

It ignores:

- SELL trades
- partial exits
- hedging
- offsetting positions
- portfolio netting
- transfers
- execution costs
- complete position history

For that reason, the metric is described throughout the project as:

**BUY-only hold-to-resolution profit proxy**

It is used only as one behavioral feature in the ranking.

---

### 6.5 Wallet + Market Aggregation

Trade-level statistics can be misleading because a single economic position may be split into many fills.

For example:

```text
100 successful BUY fills
```

inside one market are not equivalent to 100 independent correct predictions.

To reduce this problem, the main signal pipeline first aggregates activity at:

```text
wallet + market
```

level.

For each wallet, the analysis then counts how many distinct markets contain:

- positive BUY-only profit proxy
- winning low-price BUYs
- winning very-low-price BUYs
- late winning low-price BUYs

This gives cross-market repetition more weight than repeated fills within one market.

---

### 6.6 Cross-Market Signal Ratios

Absolute counts can also be misleading.

For example:

```text
4 very-low-price winning markets out of 4
```

is behaviorally different from:

```text
4 very-low-price winning markets out of 18
```

The pipeline therefore calculates both:

- number of markets containing the signal
- proportion of the wallet's markets containing the signal

This is used for both very-low-price and late low-price components.

---

## 7. Exploratory Trader Metrics

### 7.1 Trader hit-rate analysis

The trader-level hit-rate script identified:

```text
207,119 unique BUY wallets
```

and:

```text
3,799 wallets
```

with at least 20 BUY trades.

The global baseline remained:

```text
58.33%
```

throughout the pipeline, confirming consistency between the enriched trade data and trader-level aggregation.

### 7.2 Cross-market aggregation

The market-signal aggregation produced:

```text
300,188 wallet-market combinations
```

and:

```text
20,234 wallets
```

that traded at least 3 distinct markets.

This stage is important because many wallets with apparently impressive trade-level hit rates are concentrated in only one market.

---

## 8. Candidate Ranking Model

Each wallet receives a final candidate score from:

```text
0 to 100
```

The score is an **investigation-priority heuristic**.

It is not a probability that the wallet engaged in insider trading.

The raw score consists of seven components:

| Component | Maximum Score |
|---|---:|
| Very-low-price cross-market evidence | 25 |
| Late low-price cross-market evidence | 20 |
| BUY hit-rate edge vs baseline | 20 |
| Positive proxy across markets | 15 |
| BUY-only hold-to-resolution profit proxy | 10 |
| Cross-market breadth | 5 |
| BUY volume | 5 |
| **Total** | **100** |

---

### 8.1 Very-Low-Price Cross-Market Evidence

Maximum contribution:

**25 points**

This component combines:

- absolute number of markets containing a winning BUY at `price <= 0.25`
- proportion of the wallet's markets containing that signal

The count component reaches its cap at approximately four affected markets.

The ratio component reaches its cap when the signal appears on approximately 75% of the wallet's markets.

---

### 8.2 Late Low-Price Cross-Market Evidence

Maximum contribution:

**20 points**

This component combines:

- number of markets containing a late low-price winning BUY
- proportion of the wallet's markets containing that signal

The count component reaches its cap at approximately three affected markets.

The ratio component reaches its cap when the signal appears on approximately 25% of the wallet's markets.

---

### 8.3 Hit-Rate Edge vs Baseline

Maximum contribution:

**20 points**

The dataset BUY baseline is:

```text
58.33%
```

Only positive edge contributes.

An edge of approximately:

```text
+25 percentage points
```

reaches the maximum score for this component.

This feature prevents wallets with hit rates below or near the overall baseline from ranking highly solely because they have many low-price fills.

---

### 8.4 Profitable-Market Ratio

Maximum contribution:

**15 points**

This measures the fraction of markets in which the wallet has positive aggregate BUY-only hold-to-resolution profit proxy.

A ratio of approximately:

```text
80%+
```

reaches the maximum contribution.

---

### 8.5 BUY-Only Profit Proxy

Maximum contribution:

**10 points**

Positive proxy profit is log-scaled.

This prevents one very large account from dominating the ranking solely through position size.

Approximately:

```text
$100,000 positive proxy
```

reaches the maximum component score.

Again, this is not realized P&L.

---

### 8.6 Cross-Market Breadth

Maximum contribution:

**5 points**

This component gives modest credit to wallets that demonstrate behavior across multiple markets.

Approximately eight markets reach the maximum breadth contribution.

The small weight is intentional because the final scoped universe contains only 18 markets with in-window trades.

---

### 8.7 BUY Volume

Maximum contribution:

**5 points**

BUY volume is log-scaled.

Approximately:

```text
$100,000 BUY volume
```

reaches the cap.

Volume alone is not treated as evidence of informed trading.

---

## 9. Reliability Adjustment

Small samples can produce extreme results by chance.

For example:

```text
3 winning BUYs out of 3
```

should not receive the same evidentiary weight as:

```text
hundreds of BUYs across several markets
```

The raw candidate score is therefore multiplied by a reliability factor based on:

- number of BUY trades
- number of distinct markets

The adjustment does not eliminate small wallets completely.

It modestly reduces their score until there is a broader evidence base.

This reliability factor is itself heuristic and is not a formal statistical significance test.

---

## 10. Signal-Level Interpretation

The final score is mapped to a descriptive signal level:

| Candidate Score | Signal Level |
|---:|---|
| >= 75 | VERY HIGH |
| >= 60 | HIGH |
| >= 45 | ELEVATED |
| >= 30 | MODERATE |
| < 30 | LOW |

The labels describe only:

> how strongly the wallet matches the selected behavioral heuristics.

They are **not**:

- legal risk ratings
- insider-trading probabilities
- compliance determinations
- accusations of misconduct

---

## 11. Top Ranked Wallets

The final ranking contains:

```text
207,119 wallets
```

The ten highest-ranked candidates are:

| Rank | Wallet | Score | Signal | Markets | BUY | Hit Rate |
|---:|---|---:|---|---:|---:|---:|
| 1 | `0xcf6a714618a328c608a1c70cb62a31a6bef3f9d0` | 76.10 | VERY HIGH | 8 | 155 | 85.16% |
| 2 | `0x10b289276b2b69cac7b1bbc58601009b6ee74ceb` | 70.29 | HIGH | 11 | 852 | 81.92% |
| 3 | `0xad529df14c293d77984a0137990a1441b25211ac` | 67.79 | HIGH | 11 | 119 | 73.11% |
| 4 | `0xd6639bff2beb2bcc0cfedc27e0f7980964e1ca64` | 67.37 | HIGH | 6 | 138 | 73.19% |
| 5 | `0xc9db6c957b2ba169608907443f3991b8d01b2ad3` | 67.15 | HIGH | 6 | 579 | 92.23% |
| 6 | `0xdde1a0257ddcc19522df5128049ce5619944f1d7` | 64.80 | HIGH | 6 | 97 | 85.57% |
| 7 | `0x8f42ae0a01c0383c7ca8bd060b86a645ee74b88f` | 64.31 | HIGH | 7 | 60 | 88.33% |
| 8 | `0xb22326c1770aa89dfb2b372137e570a360433772` | 63.70 | HIGH | 4 | 139 | 89.93% |
| 9 | `0x86ce8bf4ea6334796156e558642f83f4df0d8af5` | 63.60 | HIGH | 9 | 116 | 93.10% |
| 10 | `0xbb39ba863319281427a482c8714ffdf69cb7ee8a` | 63.53 | HIGH | 7 | 195 | 67.69% |

---

## 12. Candidate Analysis

### 12.1 Rank 1 — `0xcf6a7146...`

The highest-ranked wallet has:

```text
Candidate score:        76.10 / 100
Signal level:           VERY HIGH
Reliability:            100%
Markets:                8
BUY trades:             155
Hit rate:               85.16%
Global baseline:        58.33%
Edge vs baseline:       +26.83 percentage points
Profitable-market ratio: 62.5%
Very-low-price markets: 3 / 8
Late low-price markets: 1 / 8
BUY-only profit proxy:  ~$78,919.51
BUY volume:             ~$108,422.21
```

The wallet ranks highly because several different signals occur together:

- hit rate substantially above baseline
- cross-market activity
- repeated very-low-price winning entries
- at least one late low-price winning market
- meaningful BUY volume
- substantial positive BUY-only proxy

This makes the wallet a useful candidate for manual follow-up.

It does not establish why the trading pattern occurred.

---

### 12.2 Rank 2 — `0x10b28927...`

Observed characteristics:

```text
Candidate score:        70.29 / 100
Signal level:           HIGH
Reliability:            100%
Markets:                11
BUY trades:             852
Hit rate:               81.92%
Edge vs baseline:       +23.59 percentage points
Profitable-market ratio: 72.73%
Very-low-price markets: 3 / 11
Late low-price markets: 1 / 11
BUY-only profit proxy:  ~$2,227.30
BUY volume:             ~$16,718.55
```

This wallet combines a large number of BUY observations with a hit rate materially above the dataset baseline.

Its score is driven more by consistency and hit-rate edge than by absolute proxy profit.

---

### 12.3 Rank 3 — `0xad529df1...`

Observed characteristics:

```text
Candidate score:        67.79 / 100
Signal level:           HIGH
Reliability:            100%
Markets:                11
BUY trades:             119
Hit rate:               73.11%
Edge vs baseline:       +14.78 percentage points
Profitable-market ratio: 54.55%
Very-low-price markets: 4 / 11
Late low-price markets: 1 / 11
BUY-only profit proxy:  ~$55,209.96
BUY volume:             ~$27,208.73
```

This wallet is especially notable for repeated very-low-price winning activity across four markets.

It also generated several of the strongest individual late low-price winning BUY examples in the detailed candidate extraction.

---

### 12.4 Rank 5 — `0xc9db6c95...`

Observed characteristics:

```text
Candidate score:        67.15 / 100
Markets:                6
BUY trades:             579
Hit rate:               92.23%
Edge vs baseline:       +33.89 percentage points
Profitable-market ratio: 66.67%
Very-low-price markets: 2 / 6
Late low-price markets: 1 / 6
BUY-only profit proxy:  ~$1,165.20
BUY volume:             ~$664.25
```

The wallet's extremely high hit rate is notable, but its economic size is small.

This illustrates why the final score combines multiple features rather than ranking purely by hit rate.

---

### 12.5 Rank 7 — `0x8f42ae0a...`

Observed characteristics:

```text
Candidate score:        64.31 / 100
Reliability:            80%
Markets:                7
BUY trades:             60
Hit rate:               88.33%
Edge vs baseline:       +30.00 percentage points
Profitable-market ratio: 85.71%
Very-low-price markets: 3 / 7
Late low-price markets: 1 / 7
BUY-only profit proxy:  ~$191,294.58
BUY volume:             ~$377,026.59
```

This wallet combines a strong hit rate with substantial economic exposure.

Its reliability adjustment is below 100% because the number of BUY observations is smaller than for several other top candidates.

---

## 13. Trade-Level Candidate Evidence

The detailed extraction for the top ten candidates produced:

```text
711 interesting low-price winning BUY trades
```

The number of selected trades by candidate was:

| Rank | Wallet | Interesting Trades |
|---:|---|---:|
| 1 | `0xcf6a714618a328c608a1c70cb62a31a6bef3f9d0` | 43 |
| 2 | `0x10b289276b2b69cac7b1bbc58601009b6ee74ceb` | 53 |
| 3 | `0xad529df14c293d77984a0137990a1441b25211ac` | 63 |
| 4 | `0xd6639bff2beb2bcc0cfedc27e0f7980964e1ca64` | 31 |
| 5 | `0xc9db6c957b2ba169608907443f3991b8d01b2ad3` | 282 |
| 6 | `0xdde1a0257ddcc19522df5128049ce5619944f1d7` | 18 |
| 7 | `0x8f42ae0a01c0383c7ca8bd060b86a645ee74b88f` | 13 |
| 8 | `0xb22326c1770aa89dfb2b372137e570a360433772` | 120 |
| 9 | `0x86ce8bf4ea6334796156e558642f83f4df0d8af5` | 18 |
| 10 | `0xbb39ba863319281427a482c8714ffdf69cb7ee8a` | 70 |

### Notable market cluster

Many of the strongest timing examples in the top-30 trade-level output were concentrated in the market:

**US strikes Iran by February 28, 2026?**

This concentration is important.

It demonstrates why trade-level examples should not be interpreted as independent evidence when they arise from the same underlying event.

The main ranking partially mitigates this problem through wallet + market aggregation.

However, multiple wallets reacting to the same event can still produce correlated observations.

---

### Example 1 — Rank 7 candidate

Wallet:

```text
0x8f42ae0a01c0383c7ca8bd060b86a645ee74b88f
```

Market:

```text
US strikes Iran by February 28, 2026?
```

Trade:

```text
Outcome:                  Yes
Price:                    ~0.1548
Hours before close:       ~15.86
BUY volume:               ~$4,025.96
BUY-only profit proxy:    ~$21,974.04
Very-low-price signal:    Yes
Late low-price signal:    Yes
```

This trade combines:

- a relatively low entry price
- the eventual winning outcome
- meaningful size
- proximity to market closure

It is therefore a strong example of the type of trade the screening framework is designed to surface.

It does not establish whether the trader acted on public or non-public information.

---

### Example 2 — Rank 1 candidate

Wallet:

```text
0xcf6a714618a328c608a1c70cb62a31a6bef3f9d0
```

Market:

```text
US strikes Iran by February 28, 2026?
```

Trade:

```text
Outcome:                  Yes
Price:                    0.08
Hours before close:       ~23.44
BUY volume:               ~$240.00
BUY-only profit proxy:    ~$2,760.00
Very-low-price signal:    Yes
Late low-price signal:    Yes
```

This entry occurred at a price that implied a much lower market probability than the eventual outcome.

The timing also falls inside the final 24 hours before recorded closure.

---

### Example 3 — Rank 3 candidate

Wallet:

```text
0xad529df14c293d77984a0137990a1441b25211ac
```

Market:

```text
US strikes Iran by February 28, 2026?
```

One notable trade:

```text
Outcome:                  Yes
Price:                    0.17
Hours before close:       ~12.35
BUY volume:               ~$566.61
BUY-only profit proxy:    ~$2,766.39
Very-low-price signal:    Yes
Late low-price signal:    Yes
```

The same wallet also executed several additional winning entries in the same market near prices around `0.08` to `0.18`.

This illustrates why repeated fills on one market should not be treated as independent predictions.

---

## 14. Why Some Apparently Strong Wallets Rank Lower

The reliability adjustment materially changes the ranking.

For example, wallet:

```text
0x6a8328b1ae11569f7b27600073558879885e4c59
```

showed:

```text
4 markets
46 BUY trades
97.83% hit rate
+39.49 percentage-point edge
4 / 4 very-low-price win markets
100% profitable-market ratio
~$118,962.79 BUY-only profit proxy
```

Despite these strong raw metrics, it ranked only:

```text
29th
```

with a final score of:

```text
57.14
```

because its reliability factor was only:

```text
63.27%
```

This demonstrates the purpose of the reliability adjustment.

A highly concentrated but small sample should not automatically dominate a broader evidence base.

---

## 15. Interpretation of High Scores

Several alternative explanations may produce behavior that resembles informed trading.

A high-scoring wallet may represent:

- a sophisticated quantitative trader
- a specialized domain expert
- an automated strategy
- a market maker
- a trader reacting rapidly to public information
- a wallet executing a broader portfolio strategy
- multiple users sharing infrastructure
- a trader specializing in a narrow event category
- an account systematically exploiting pricing inefficiencies

Therefore, the ranking is best viewed as a triage mechanism.

A high candidate score means:

> the wallet's public trading behavior is unusually consistent with the selected screening heuristics.

It does not determine why the behavior occurred.

---

## 16. Important Limitations

### 16.1 Scoped market universe

The final universe contains only the 20 highest-volume closed markets selected under the date filter.

Only 18 of those markets contain in-window trades.

This prioritizes liquid markets but may miss unusual behavior in smaller markets.

---

### 16.2 Public data only

The analysis uses only public Polymarket data.

It cannot determine:

- what information a trader possessed
- when the trader acquired that information
- whether the information was public
- why the trade was placed

---

### 16.3 `closed_time` is only a proxy

The project does not reconstruct the exact timeline of public information for every event.

A trade occurring a few hours before recorded market closure may still have occurred after decisive information had already become public.

A stronger event-level investigation would compare:

```text
trade timestamp
```

with:

```text
first public disclosure timestamp
```

using event-specific sources.

---

### 16.4 Profit proxy is not realized P&L

The BUY-only hold-to-resolution metric ignores SELL activity and complete position management.

Actual behavior may include:

- partial exits
- full exits
- hedges
- opposite-side trades
- cross-market hedging
- inventory management

The metric is therefore a standardized heuristic rather than an accounting result.

---

### 16.5 Wallets do not equal individuals

No identity attribution is attempted.

A wallet can represent:

- one individual
- multiple individuals
- a trading firm
- an automated strategy
- a bot
- an execution service

---

### 16.6 Correlated markets and events

Different prediction markets can refer to the same underlying real-world event.

A trader positioned correctly across several related markets may be expressing one underlying thesis rather than repeatedly obtaining independent informational advantages.

Likewise, several wallets may react to the same information event.

This is an important limitation for future refinement.

---

### 16.7 Market price is only an approximate probability signal

Prediction-market prices can be interpreted approximately as probabilities, but they are also affected by:

- liquidity
- spread
- order-book imbalance
- temporary dislocations
- market-maker behavior
- execution effects

A price of `0.20` should therefore not be treated as a perfectly calibrated 20% probability.

---

### 16.8 Reliability factor is heuristic

The reliability adjustment reduces the influence of very small samples.

It is not a formal significance test.

The current ranking should therefore be interpreted as explainable candidate prioritization rather than statistical proof.

---

## 17. Potential Improvements

Several extensions could strengthen the methodology.

### Event clustering

Markets referring to the same underlying event could be clustered.

This would avoid treating correlated markets as fully independent evidence.

### Public-information timelines

For the strongest candidates, the analysis could reconstruct exact timelines using:

- official announcements
- news publications
- regulatory releases
- project social-media posts
- government statements
- election reporting
- sports results
- blockchain events

The strongest follow-up comparison would be:

```text
trade timestamp
vs.
first verified public disclosure timestamp
```

### Position reconstruction

BUY and SELL trades could be combined into wallet-level positions over time.

This would support more realistic:

- realized P&L
- mark-to-market P&L
- position exposure
- net outcome exposure

### Wallet clustering

Funding flows and related wallet behavior could be analyzed to detect whether several wallets may belong to one actor or coordinated strategy.

### Statistical testing

Observed outcomes could be tested against:

- market-implied probabilities
- matched control wallets
- peer traders in the same market category
- simulated random strategies

This would allow estimation of how unusual the observed performance is under explicit null models.

### Category controls

Wallets could be compared against peers who trade similar market categories.

This would help distinguish specialized expertise from broadly unusual performance.

---

## 18. Reproducibility

The main pipeline is implemented in Python.

The current execution order is:

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

The main analytical outputs are:

```text
results/trader_accuracy.csv
results/trader_edge.csv
results/trader_market_signals.csv
results/insider_ranking.csv
results/candidate_details.csv
```

The fixed market universe is stored in:

```text
data/raw/market_dates.csv
```

and final market outcomes are stored in:

```text
data/processed/market_outcomes.csv
```

Large trade-level files are excluded from Git because of their size.

The main ignored generated files are:

```text
data/raw/trades.csv
data/processed/trades_with_outcome.csv
data/processed/trades_with_timing.csv
```

`trades_with_timing.csv` is deprecated and is not part of the current pipeline.

The active datasets can be regenerated through the documented scripts.

---

## 19. Conclusion

The project produced a reproducible screening framework for identifying Polymarket wallets whose behavior is unusually consistent with selected heuristics for potentially informed trading.

The final scoped dataset contains:

```text
20 selected markets
18 markets with in-window trades
1,187,786 in-window trades
794,187 BUY trades
207,119 BUY wallets
```

The global BUY outcome hit-rate baseline is:

```text
58.33%
```

The highest-ranked wallet received:

```text
76.10 / 100
```

with a:

```text
VERY HIGH
```

heuristic signal level.

The strongest candidate patterns combine several features:

- successful low-price entries
- successful very-low-price entries
- positive hit-rate edge relative to the global baseline
- repetition across multiple markets
- late successful positioning
- positive BUY-only hold-to-resolution payoff proxy
- meaningful activity volume
- sufficient sample reliability

The trade-level candidate extraction produced:

```text
711
```

interesting low-price winning BUYs across the top ten candidates.

The ranking should therefore be used as a:

**candidate-generation and prioritization tool for further investigation**

rather than as evidence that any specific wallet possessed material non-public information or engaged in unlawful activity.
