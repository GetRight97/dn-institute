# Polymarket Potentially Informed Trading Analysis

This project investigates trading behavior on Polymarket that may be consistent with potentially informed trading.

The analysis covers trades between:

**November 1, 2025 — May 1, 2026**

The goal is not to identify or accuse traders of insider trading. Instead, the project develops transparent behavioral heuristics and ranks wallets according to how strongly their activity matches those heuristics.

## Dataset

The dataset was collected from public Polymarket APIs.

Final dataset:

- 638,808 trades
- 103,803 unique traders
- 989 markets
- 988 resolved/settled markets with an identified winning outcome

Trade data includes:

- wallet address
- market condition ID
- BUY / SELL side
- outcome
- price
- size
- timestamp
- transaction hash

Market metadata includes:

- market title
- scheduled end date
- actual closed time
- final outcome prices
- winning outcome
- UMA resolution status

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
│   │   ├── trades.csv
│   │   └── market_dates.csv
│   │
│   └── processed/
│       ├── market_outcomes.csv
│       └── trades_with_outcome.csv
│
├── results/
│   ├── trader_accuracy.csv
│   ├── trader_edge.csv
│   ├── trader_market_signals.csv
│   ├── insider_ranking.csv
│   └── candidate_details.csv
│
├── checks/
│   ├── check_data.py
│   ├── check_resolution.py
│   ├── check_closed_market.py
│   ├── test_condition_lookup.py
│   ├── test_sdk_market.py
│   └── timing_check.py
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

## Methodology

The analysis focuses primarily on BUY trades on resolved markets.

Several behavioral signals are calculated.

### Winning BUY Accuracy

A BUY is considered directionally correct when the purchased outcome eventually wins.

Accuracy alone is not treated as evidence of informed trading because traders may simply buy high-probability outcomes.

### Low-Price Winning Trades

Winning BUYs entered at low prices are treated as more informative.

Two thresholds are used:

- winning outcome purchased at price <= 0.50
- winning outcome purchased at price <= 0.25

For example, a correct BUY at `0.20` is considered more unusual than a correct BUY at `0.99`.

### Timing

Trades are compared with Polymarket's `closed_time`.

A low-price winning BUY occurring within 24 hours of market closure is treated as a timing signal.

`closed_time` is only a proxy for market resolution timing and does not necessarily represent the exact moment when relevant information became public.

### Profit Proxy

For BUY trades, a hold-to-resolution payoff proxy is calculated.

For a winning BUY:

```text
profit_proxy = size * (1 - price)
```

For a losing BUY:

```text
profit_proxy = -size * price
```

This is not realized P&L because a trader may have sold or otherwise changed the position before settlement.

### Market-Level Aggregation

Repeated fills on the same market can exaggerate trade-level statistics.

For this reason, the main ranking aggregates signals at the:

```text
wallet + market
```

level.

This allows repeated unusual behavior across different markets to carry more weight than many individual fills on a single market.

## Ranking Model

The final behavioral score ranges from 0 to 100.

| Signal | Maximum score |
|---|---:|
| Very-low-price winning markets | 25 |
| Late low-price winning markets | 20 |
| Profitable market ratio | 20 |
| Profit proxy | 15 |
| Number of markets | 10 |
| BUY volume | 10 |
| **Total** | **100** |

The score is a heuristic behavioral ranking.

It must **not** be interpreted as the probability that a wallet engaged in insider trading.

## Running the Pipeline

Install dependencies:

```bash
pip install -r requirements.txt
```

Collect historical trades:

```bash
python src/collect_data.py
```

Collect market metadata:

```bash
python src/market_dates.py
python src/market_outcomes.py
```

Enrich trades with final outcomes and market closing time:

```bash
python src/trades_with_outcome.py
```

Run exploratory trader statistics:

```bash
python src/trader_stats.py
```

Run trader-level analytical metrics:

```bash
python src/trader_accuracy.py
python src/trader_edge.py
python src/trader_market_signals.py
```

Create the final ranking:

```bash
python src/insider_score.py
```

Extract detailed trades for the leading candidates:

```bash
python src/candidate_details.py
```

The main final artifacts are:

```text
results/insider_ranking.csv
results/candidate_details.csv
results/trader_market_signals.csv
report/report.md
```

## Large Data Files

The full trade-level datasets are intentionally not committed to the repository because of their size.

Excluded generated files:

- `data/raw/trades.csv` — approximately 174 MB
- `data/processed/trades_with_outcome.csv` — approximately 203 MB
- deprecated `trades_with_timing.csv` — approximately 206 MB

These datasets can be reproduced using the scripts in `src/`.

For the main analysis pipeline:

```bash
python src/collect_data.py
python src/market_outcomes.py
python src/trades_with_outcome.py
```

Final analytical CSV artifacts used in the report are included in the `results/` directory.

## Main Results

The final ranking was calculated across 98,229 wallets with resolved BUY activity.

The five highest-ranked wallets were:

| Rank | Wallet | Score |
|---:|---|---:|
| 1 | `0x8a9777a7d3079e208afc08de2ccdf744de78593d` | 96.91 |
| 2 | `0x14b0a3270a36102734d81a77ec8167a0791d8d0e` | 89.89 |
| 3 | `0xc9f9a7610efa67b8614c3152f50af2bd9db6c5e8` | 84.92 |
| 4 | `0x3078db4a9737866b4d6529f655025b3a20f80389` | 81.01 |
| 5 | `0xa3e9a711841e655def080044768452b60f4263d0` | 80.66 |

Different wallets reached high scores for different reasons.

For example, the highest-ranked wallet traded across 166 markets, had a 72.29% profitable-market ratio, recorded 10 very-low-price winning markets and 8 late low-price winning markets.

Another notable wallet, `0xc9f9a7610efa67b8614c3152f50af2bd9db6c5e8`, produced a hold-to-resolution profit proxy of approximately $88,635 across 48 markets.

Detailed candidate trades are available in:

```text
results/candidate_details.csv
```

## Important Limitations

The analysis identifies unusual trading patterns, not legal insider trading.

Important limitations include:

- Public trade data cannot reveal a trader's actual information set.
- Wallets may represent bots, market makers, multiple users, or automated strategies.
- `closed_time` is not necessarily the time information first became public.
- Profit proxy assumes BUY positions were held to resolution.
- SELL trades are not interpreted directionally because they may represent position reductions rather than bearish bets.
- Multiple related prediction markets may share the same underlying event.
- Market prices are treated as approximate implied probabilities for heuristic purposes.
- The analysis does not reconstruct the complete public-information timeline for every underlying event.

Therefore, high-ranked wallets should be interpreted as candidates for further investigation rather than evidence of misconduct.

## Disclaimer

The ranking identifies wallets whose trading behavior is unusually consistent with the selected heuristics for potentially informed trading.

It does **not** establish that any trader possessed material non-public information or engaged in unlawful activity.