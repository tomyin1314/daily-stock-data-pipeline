# daily-stock-data-pipeline

About 80 lines of Python that download daily stock prices into SQLite and keep them up to date.

- **Incremental.** Each run only asks for the days it is missing.
- **Safe to re-run.** A primary key on `(symbol, date)` plus `INSERT OR REPLACE` means no duplicate rows, ever.
- **Source-agnostic.** Two fetch functions (yfinance and EODHD APIs) return the same columns, so switching data source is a one-function change.

The full walkthrough, including the adjusted-close pitfalls and how to schedule it, is here:
**[Build a daily stock data pipeline in Python](https://aiquantnav.com/en/guides/daily-stock-data-pipeline)**

## Quick start

Requires Python 3.10 or later.

```bash
pip install -r requirements.txt
python pipeline.py
```

First run:

```
AAPL: fetched 696 rows, 696 in the database, latest 2026-10-09
MSFT: fetched 696 rows, 696 in the database, latest 2026-10-09
```

Run it again and it re-fetches only the last stored day:

```
AAPL: fetched 1 rows, 696 in the database, latest 2026-10-09
MSFT: fetched 1 rows, 696 in the database, latest 2026-10-09
```

(Output from 12 Oct 2026. Your row counts and dates will differ.)

The data lands in `prices.db`, table `daily`:

| column | meaning |
|---|---|
| `symbol`, `date` | primary key |
| `open`, `high`, `low`, `close` | prices as traded that day |
| `adj_close` | close adjusted for splits and dividends; use this for returns |
| `volume` | shares traded |
| `source` | which fetch function wrote the row |

## Using the other data source

```bash
python pipeline.py --eodhd
```

This uses the public `demo` token of [EODHD APIs](https://eodhd.com/), which works for AAPL only. For other tickers, pass your own token to `fetch_eodhd`.

Two limits to know: a free EODHD key returns only the past year of history, so with the default `START` you will get about one year of bars rather than the full range; and EODHD's standard plans are for personal use, with separate Commercial plans for commercial use.

## Configuration

Edit the constants at the top of `pipeline.py`:

- `SYMBOLS`: tickers to download
- `START`: how far back the first run goes
- `DB`: path of the SQLite file

## Things to know

- **yfinance is unofficial.** It reads Yahoo Finance's public endpoints and can break without notice. Yahoo's terms say the data is for personal use.
- **Adjusted prices get restated.** After a new dividend, older `adj_close` values change at the source. The incremental update does not go back and refresh them. Delete `prices.db` and re-run now and then for a full reload.
- **Re-fetching the last day is deliberate.** If a run happens before the market closes, the stored bar is incomplete; the next run overwrites it.
- **Not investment advice.** Data from any source can be wrong or late. Check it before you rely on it.

## Licence

MIT. See [LICENSE](LICENSE).
