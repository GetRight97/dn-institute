# Polymarket Potentially Informed Trading Analysis

## 1. Objective

The objective of this analysis is to identify Polymarket wallets whose trading behavior is unusually consistent with potentially informed trading.

The study covers trades between:

**November 1, 2025 and May 1, 2026**

The analysis is heuristic and behavioral. A high score does not prove that a wallet possessed material non-public information and should not be interpreted as an accusation of insider trading.

The goal is to build a reproducible screening system that highlights accounts and trades worth further investigation.

---

## 2. Data Collection

Historical trades were collected from Polymarket's public trade API.

Market metadata and final resolution information were collected using Polymarket market data and the Polymarket Python client.

The resulting dataset contains:

- **638,808 trades**
- **103,803 unique wallets**
- **989 markets**

All 638,808 collected trades were successfully matched to market metadata.

Of those trades:

- **637,884** were associated with markets for which a winning outcome could be identified
- **418,664** were BUY trades on those markets
- **266,218** BUY trades purchased the eventual winning outcome

The resulting trade-level BUY accuracy was:

**63.59%**

This value is used only as a descriptive baseline.

A high raw accuracy is not sufficient evidence of informed trading because a trader can achieve a high hit rate simply by repeatedly purchasing outcomes that already trade near certainty.

---

## 3. Market Resolution and Timing

An early version of the analysis used the scheduled market `endDate` to estimate how close trades occurred to market resolution.

This approach was rejected after diagnostic checks showed that scheduled end dates were often far removed from actual trading and closure behavior.

For the final methodology, Polymarket's `closed_time` field is used as the timing reference.

Of the 989 analyzed markets:

- **989** had a `closed_time`
- **988** had a resolved or settled status with a clearly identifiable winning binary outcome

The remaining market was excluded from outcome-dependent calculations.

`closed_time` should still be interpreted carefully.

It indicates when Polymarket closed the market, but it does not necessarily represent the exact moment when the relevant real-world information first became publicly available.

Therefore, timing is treated as a screening signal rather than proof of informational advantage.

---

## 4. Heuristics

The analysis uses several complementary behavioral signals.

No single metric is treated as sufficient on its own.

### 4.1 Winning BUY Accuracy

A BUY is considered directionally correct when the purchased outcome eventually wins.

In simplified form:

```text
trade outcome == final winning outcome
```

SELL trades are excluded from directional accuracy.

A SELL may represent:

- closing an existing position
- reducing exposure
- inventory management
- market-making activity

Therefore, SELL activity is not safely interpretable as a direct bearish view.

---

### 4.2 Low-Price Winning Entries

A correct trade is more informative when the market assigned a low price to the winning outcome at entry.

For example:

```text
BUY winning outcome at 0.99
```

provides relatively little evidence of unusual foresight.

By contrast:

```text
BUY winning outcome at 0.20
```

is more unusual because the market was pricing that outcome as substantially less likely.

Two thresholds are used:

- **low-price win:** entry price <= 0.50
- **very-low-price win:** entry price <= 0.25

These signals are later aggregated across distinct markets.

---

### 4.3 Late Low-Price Winning Entries

Timing becomes more interesting when a trader correctly buys a relatively cheap winning outcome shortly before the market closes.

A late low-price win is defined as:

- BUY trade
- final winning outcome
- entry price <= 0.50
- trade occurred within 24 hours of `closed_time`

This heuristic is intended to capture situations where successful positioning occurred close to market closure.

Again, this does not establish that the trader possessed non-public information.

---

### 4.4 Hold-to-Resolution Profit Proxy

A settlement-value proxy is calculated for BUY trades.

For a winning BUY:

```text
profit_proxy = size * (1 - price)
```

For a losing BUY:

```text
profit_proxy = -size * price
```

This represents the hypothetical result if the BUY position were held until settlement.

It is not realized P&L.

A trader may have:

- sold before resolution
- reduced the position
- hedged elsewhere
- traded both outcomes

For this reason, the metric is labeled `profit_proxy` rather than profit.

---

### 4.5 Market-Level Aggregation

Trade-level metrics can be misleading because a single economic position may be split into many fills.

For example, 100 successful fills on one market should not necessarily be treated as 100 independent successful predictions.

To reduce this problem, the final methodology aggregates behavior at the:

```text
wallet + market
```

level.

For each wallet, the analysis measures how many distinct markets contain:

- profitable BUY positioning
- a winning low-price entry
- a winning very-low-price entry
- a late winning low-price entry

This makes repeated behavior across markets more important than repeated executions on a single market.

---

## 5. Ranking Model

Each wallet receives a behavioral score from 0 to 100.

The model consists of six components.

| Component | Maximum Score |
|---|---:|
| Very-low-price winning markets | 25 |
| Late low-price winning markets | 20 |
| Profitable market ratio | 20 |
| Profit proxy | 15 |
| Number of markets | 10 |
| BUY volume | 10 |
| **Total** | **100** |

### Very-Low-Price Wins

Maximum contribution:

**25 points**

Ten or more distinct markets containing a winning BUY at price <= 0.25 receive the maximum score.

### Late Low-Price Wins

Maximum contribution:

**20 points**

Five or more distinct markets containing a winning low-price entry within 24 hours of closure receive the maximum score.

### Profitable Market Ratio

Maximum contribution:

**20 points**

A profitable-market ratio of 80% or higher receives the maximum score.

### Profit Proxy

Maximum contribution:

**15 points**

Profit proxy uses logarithmic scaling.

This prevents extremely large accounts from dominating the entire ranking solely because of absolute position size.

### Market Repetition

Maximum contribution:

**10 points**

Thirty or more analyzed markets receive the maximum repetition score.

### BUY Volume

Maximum contribution:

**10 points**

BUY volume also uses logarithmic scaling to reduce the influence of extreme outliers.

---

## 6. Score Interpretation

The resulting score is not:

> the probability that a wallet is an insider

Instead, it means:

> the degree to which the wallet's observable behavior matches the selected heuristics for potentially informed trading.

The output is designed for candidate prioritization.

The risk labels used by the pipeline are:

| Score | Label |
|---:|---|
| 80+ | VERY HIGH |
| 65–79.99 | HIGH |
| 50–64.99 | ELEVATED |
| 35–49.99 | MODERATE |
| Below 35 | LOW |

These labels refer only to heuristic ranking intensity.

They are not legal or compliance determinations.

---

## 7. Top Ranked Wallets

The five highest-ranked wallets were:

| Rank | Wallet | Score | Markets | Profitable Market Ratio |
|---:|---|---:|---:|---:|
| 1 | `0x8a9777a7d3079e208afc08de2ccdf744de78593d` | 96.91 | 166 | 72.29% |
| 2 | `0x14b0a3270a36102734d81a77ec8167a0791d8d0e` | 89.89 | 115 | 44.35% |
| 3 | `0xc9f9a7610efa67b8614c3152f50af2bd9db6c5e8` | 84.92 | 48 | 70.83% |
| 4 | `0x3078db4a9737866b4d6529f655025b3a20f80389` | 81.01 | 179 | 24.02% |
| 5 | `0xa3e9a711841e655def080044768452b60f4263d0` | 80.66 | 210 | 80.48% |

These wallets rank highly for different reasons.

This is important because the ranking is multi-dimensional rather than being driven by one single statistic.

---

## 8. Candidate Analysis

### 8.1 Wallet `0x8a9777...`

This wallet ranked first with a score of:

**96.91 / 100**

Observed characteristics:

- **166 markets**
- **72.29% profitable-market ratio**
- **10 very-low-price winning markets**
- **8 late low-price winning markets**
- approximately **$450,429 BUY volume**
- approximately **$21,686 profit proxy**

The wallet's score is particularly notable because its signal is spread across many markets.

It is not driven by one isolated high-profit trade.

This makes it a strong candidate for further manual investigation.

---

### 8.2 Wallet `0xc9f9a7...`

This wallet ranked third with a score of:

**84.92 / 100**

Observed characteristics:

- **48 markets**
- **70.83% profitable-market ratio**
- **12 very-low-price winning markets**
- **2 late low-price winning markets**
- approximately **$40,521 BUY volume**
- approximately **$88,635 profit proxy**

One of the largest individual trade-level signals occurred on:

**Opinion FDV above $500M one day after launch?**

The wallet purchased the eventual winning:

```text
No
```

outcome at approximately:

```text
0.034
```

The BUY notional was approximately:

```text
$680
```

The hold-to-resolution profit proxy for this trade was approximately:

```text
$19,320
```

However, the trade occurred approximately:

```text
1,136 hours before market closure
```

or roughly 47 days before closure.

This makes the trade a strong example of successful low-price positioning, but not a strong timing anomaly.

The wallet also displayed similar successful positioning across multiple FDV-related markets.

That raises an important interpretation issue: correlated markets may reflect one broad investment thesis rather than multiple independent informational advantages.

---

### 8.3 Wallet `0xd7eee5...`

This wallet was not in the top five overall, but it produced several of the strongest trade-level timing examples.

On the market:

**Over $7M committed to the Infinex public sale?**

the wallet purchased the eventual winning:

```text
Yes
```

outcome at:

```text
0.25
```

approximately:

```text
3.24 hours before market closure
```

The corresponding hold-to-resolution profit proxy was approximately:

```text
$2,625
```

A second notable trade occurred on:

**Kodiak FDV above $50M one day after launch?**

The wallet purchased the eventual winning:

```text
No
```

outcome at:

```text
0.05
```

approximately:

```text
4.11 hours before market closure
```

The hold-to-resolution profit proxy was approximately:

```text
$1,948
```

These trades are notable because they combine:

- low entry price
- correct eventual outcome
- short time to market closure
- meaningful payoff proxy

They represent the type of trade that the screening framework is designed to surface for manual investigation.

---

## 9. Why Some High-Accuracy Wallets Were Not Top Ranked

During exploratory analysis, several wallets showed 100% BUY accuracy.

However, some of them traded only one market.

For example, a wallet might show:

```text
166 winning BUY trades
100% accuracy
1 market
```

This can be misleading because those 166 executions may represent one economic position split across many fills.

The final ranking therefore emphasizes market-level repetition rather than raw trade-level accuracy.

This adjustment prevents execution fragmentation from dominating the results.

---

## 10. Interpretation of High Scores

Several alternative explanations may produce behavior that resembles informed trading.

A high-scoring wallet may represent:

- a sophisticated quantitative trader
- a specialized domain expert
- a market-making strategy
- an automated bot
- a trader who systematically identifies mispriced probabilities
- an account focused on a narrow category of related markets
- a participant reacting quickly to public information
- multiple individuals operating through one wallet

Therefore, the score should be viewed as a triage mechanism.

A high score means that the wallet deserves closer investigation.

It does not determine why the trading pattern occurred.

---

## 11. Limitations

### 11.1 Public Data Only

The analysis relies entirely on public Polymarket trade and market data.

It cannot determine what information a trader possessed at the time of a trade.

---

### 11.2 `closed_time` Is a Proxy

The exact time when relevant information became publicly available is not reconstructed.

A trade occurring three hours before market closure may still have occurred after decisive information was already public.

A stronger investigation would compare each trade timestamp against:

- news publication times
- official announcements
- project social-media posts
- token launch data
- regulatory announcements
- election results
- sports results
- other event-specific information sources

---

### 11.3 Profit Proxy Is Not Realized P&L

The settlement-value calculation assumes BUY positions were held to resolution.

Actual trading behavior may include:

- partial exits
- complete exits
- hedging
- opposite-side trades
- cross-market hedging

Therefore, `profit_proxy` is a standardized heuristic metric rather than an accounting result.

---

### 11.4 Wallets Do Not Equal Individuals

One blockchain wallet cannot automatically be mapped to one natural person.

A wallet may belong to:

- an individual
- a firm
- a bot
- multiple users
- an automated service

No identity attribution was attempted.

---

### 11.5 Correlated Markets

Some markets are strongly related.

Examples include multiple FDV thresholds for the same token launch.

A trader correctly positioning across several thresholds may be expressing a single underlying view.

Counting each market independently can therefore overstate the degree of independent repetition.

This is one of the most important limitations for future refinement.

---

### 11.6 Market Price as Probability

Prediction-market price is treated as an approximate implied probability.

This is useful for behavioral screening, but prices may also reflect:

- liquidity constraints
- spread
- order-book imbalance
- market-maker behavior
- temporary price dislocations

Therefore, a price of `0.20` should not be interpreted as a perfectly calibrated 20% probability.

---

## 12. Potential Improvements

Several improvements could strengthen the methodology.

### Event Clustering

Related markets could be grouped into common underlying events.

This would prevent multiple thresholds on the same event from being treated as fully independent signals.

### Public Information Timeline

For top candidates, the exact timeline of public announcements could be reconstructed.

The strongest follow-up test would compare:

```text
trade timestamp
vs.
first public disclosure timestamp
```

### Position Reconstruction

BUY and SELL trades could be combined to estimate net positions over time.

This would provide more realistic realized or mark-to-market P&L estimates.

### Statistical Significance

Wallet performance could be tested against market-implied probabilities.

For example, the observed sequence of winning low-price trades could be compared with the probability of achieving the same performance by chance.

### Category Controls

Traders could be compared only against peers operating in similar market categories.

This could help distinguish domain specialization from anomalous informational advantage.

---

## 13. Reproducibility

The main pipeline is implemented in Python.

The primary scripts are:

```text
src/collect_data.py
src/market_outcomes.py
src/trades_with_outcome.py
src/trader_accuracy.py
src/trader_edge.py
src/trader_market_signals.py
src/insider_score.py
src/candidate_details.py
```

The main final analytical artifacts are:

```text
results/trader_market_signals.csv
results/insider_ranking.csv
results/candidate_details.csv
```

Large trade-level datasets are not committed because they exceed practical Git repository size limits.

They can be reproduced through the collection and processing scripts.

---

## 14. Conclusion

The analysis produced a reproducible screening framework for identifying Polymarket wallets whose behavior is unusually consistent with potentially informed trading.

The strongest signals were combinations of:

- successful low-price entries
- successful very-low-price entries
- repetition across multiple markets
- successful positioning close to market closure
- positive settlement-value proxy
- meaningful trading activity

The highest-ranked wallets show substantially different behavioral profiles.

Some display broad consistency across many markets.

Others show unusually profitable low-price entries.

A smaller number show particularly strong timing signals shortly before market closure.

The resulting ranking should therefore be used as a:

**candidate-generation and prioritization tool for further investigation**

rather than as evidence that any specific wallet engaged in insider trading.