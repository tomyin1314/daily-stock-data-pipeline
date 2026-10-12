"""Daily price pipeline: fetch daily bars and store them in SQLite.

Safe to run as often as you like: it only asks for the days it is missing,
and the primary key stops duplicate rows.
"""
import sqlite3
import sys

import pandas as pd
import requests
import yfinance as yf

DB = "prices.db"
SYMBOLS = ["AAPL", "MSFT"]
START = "2024-01-01"  # how far back to go on the first run
COLUMNS = ["symbol", "date", "open", "high", "low", "close", "adj_close", "volume", "source"]


def fetch_yfinance(symbol: str, start: str) -> pd.DataFrame:
    """Daily bars from Yahoo Finance via yfinance."""
    raw = yf.download(symbol, start=start, auto_adjust=False, progress=False,
                      multi_level_index=False)
    if raw.empty:
        return pd.DataFrame(columns=COLUMNS)
    df = raw.reset_index().rename(columns={
        "Date": "date", "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Adj Close": "adj_close", "Volume": "volume",
    })
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["symbol"], df["source"] = symbol, "yfinance"
    return df[COLUMNS]


def fetch_eodhd(symbol: str, start: str, token: str = "demo") -> pd.DataFrame:
    """Daily bars from EODHD APIs. The "demo" token works for AAPL only."""
    resp = requests.get(
        f"https://eodhd.com/api/eod/{symbol}.US",  # US tickers need the .US suffix
        params={"api_token": token, "fmt": "json", "from": start},
        timeout=30,
    )
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    df = df.rename(columns={"adjusted_close": "adj_close"})
    df["symbol"], df["source"] = symbol, "eodhd"
    return df[COLUMNS]


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily (
            symbol TEXT NOT NULL, date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, adj_close REAL,
            volume INTEGER, source TEXT,
            PRIMARY KEY (symbol, date)
        )""")


def last_date(conn: sqlite3.Connection, symbol: str) -> str | None:
    return conn.execute("SELECT MAX(date) FROM daily WHERE symbol = ?", (symbol,)).fetchone()[0]


def update(conn: sqlite3.Connection, symbol: str, fetch) -> int:
    # Start again from the last stored day: if the job ran before the close,
    # that bar was incomplete, and INSERT OR REPLACE overwrites it.
    start = last_date(conn, symbol) or START
    df = fetch(symbol, start)
    conn.executemany(
        "INSERT OR REPLACE INTO daily VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        df.itertuples(index=False, name=None),
    )
    conn.commit()
    return len(df)


if __name__ == "__main__":
    fetch = fetch_eodhd if "--eodhd" in sys.argv else fetch_yfinance
    symbols = ["AAPL"] if fetch is fetch_eodhd else SYMBOLS
    with sqlite3.connect(DB) as conn:
        init_db(conn)
        for symbol in symbols:
            n = update(conn, symbol, fetch)
            total = conn.execute("SELECT COUNT(*) FROM daily WHERE symbol = ?", (symbol,)).fetchone()[0]
            print(f"{symbol}: fetched {n} rows, {total} in the database, latest {last_date(conn, symbol)}")
