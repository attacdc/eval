import json
import math
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (accuracy_score, balanced_accuracy_score,
                             classification_report, precision_score,
                             recall_score)
from sklearn.model_selection import TimeSeriesSplit
import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent
SUMMARY_PATH = DATA_DIR / "taiex_trend_summary.json"
PLOT_PATH = DATA_DIR / "taiex_trend_plot.png"

SYMBOL = os.environ.get("TAIEX_SYMBOL", "^TWII")  # Proxy for TX futures
START_DATE = os.environ.get("TAIEX_START", "2010-01-01")
FORECAST_HORIZON = int(os.environ.get("TAIEX_FORECAST_DAYS", "5"))
RANDOM_STATE = 42


def fetch_price_history(symbol: str, start: str) -> pd.DataFrame:
    data = yf.download(symbol, start=start, auto_adjust=False, progress=False)
    if data.empty:
        raise RuntimeError(f"No data returned for symbol {symbol}")

    if isinstance(data.columns, pd.MultiIndex):
        try:
            data = data.xs(symbol, axis=1, level=1)
        except KeyError:
            # Some versions use ticker name in uppercase without suffix
            data = data.droplevel(0, axis=1)
    data.columns = [c.capitalize() for c in data.columns]
    return data


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def engineer_features(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()
    df["return_1d"] = df["Close"].pct_change()
    df["return_5d"] = df["Close"].pct_change(5)
    df["return_10d"] = df["Close"].pct_change(10)
    df["volatility_10d"] = df["return_1d"].rolling(10).std()
    df["volatility_20d"] = df["return_1d"].rolling(20).std()

    for window in (5, 10, 20, 60, 120):
        df[f"ma_{window}"] = df["Close"].rolling(window).mean()
    for window in (5, 10, 12, 20, 26, 60, 120):
        df[f"ema_{window}"] = df["Close"].ewm(span=window, adjust=False).mean()

    df["ma5_ma20_ratio"] = df["ma_5"] / df["ma_20"] - 1
    df["ma20_ma60_ratio"] = df["ma_20"] / df["ma_60"] - 1
    df["ema12_ema26_spread"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["ema12_ema26_spread"].ewm(span=9, adjust=False).mean()
    df["rsi_14"] = compute_rsi(df["Close"], 14)
    df["atr_14"] = compute_atr(df["High"], df["Low"], df["Close"], 14)
    df["atr_pct"] = df["atr_14"] / df["Close"]

    volume_mean = df["Volume"].rolling(20).mean()
    volume_std = df["Volume"].rolling(20).std().replace(0, np.nan)
    df["volume_z"] = (df["Volume"] - volume_mean) / volume_std
    df["volume_change_5d"] = df["Volume"].pct_change(5)

    df["future_return"] = df["Close"].shift(-FORECAST_HORIZON) / df["Close"] - 1
    df["future_direction"] = (df["future_return"] > 0).astype(int)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    return df


def build_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    feature_cols = [
        "return_1d",
        "return_5d",
        "return_10d",
        "volatility_10d",
        "volatility_20d",
        "ma5_ma20_ratio",
        "ma20_ma60_ratio",
        "ema12_ema26_spread",
        "macd_signal",
        "rsi_14",
        "atr_pct",
        "volume_change_5d",
    ]
    matrix = df[feature_cols + ["future_direction"]].dropna()
    return matrix[feature_cols], matrix["future_direction"]


@dataclass
class ModelMetrics:
    holdout_accuracy: float
    holdout_balanced_accuracy: float
    holdout_precision: float
    holdout_recall: float
    cross_val_accuracy: float
    cross_val_balanced_accuracy: float


@dataclass
class TrendSignal:
    latest_date: str
    latest_price: float
    probability_bullish: float
    classification: str
    ma5_vs_ma20: float
    ma20_vs_ma60: float
    rsi: float
    atr_pct: float


@dataclass
class AnalysisSummary:
    symbol: str
    start_date: str
    forecast_horizon_days: int
    metrics: ModelMetrics
    latest_signal: TrendSignal
    feature_importance: List[Tuple[str, float]]
    test_period: Dict[str, str]


def evaluate_model(model, X_train, y_train, X_test, y_test) -> ModelMetrics:
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    accuracy = accuracy_score(y_test, y_pred)
    bal_accuracy = balanced_accuracy_score(y_test, y_pred)

    tscv = TimeSeriesSplit(n_splits=5)
    cv_acc = []
    cv_bal = []
    for train_idx, val_idx in tscv.split(X_train):
        model_cv = GradientBoostingClassifier(random_state=RANDOM_STATE)
        model_cv.fit(X_train.iloc[train_idx], y_train.iloc[train_idx])
        preds = model_cv.predict(X_train.iloc[val_idx])
        cv_acc.append(accuracy_score(y_train.iloc[val_idx], preds))
        cv_bal.append(balanced_accuracy_score(y_train.iloc[val_idx], preds))

    return ModelMetrics(
        holdout_accuracy=accuracy,
        holdout_balanced_accuracy=bal_accuracy,
        holdout_precision=precision,
        holdout_recall=recall,
        cross_val_accuracy=float(np.mean(cv_acc)),
        cross_val_balanced_accuracy=float(np.mean(cv_bal)),
    )


def derive_signal(model, X: pd.DataFrame, df: pd.DataFrame) -> TrendSignal:
    latest_idx = X.index[-1]
    prob = model.predict_proba(X.iloc[[-1]])[0, 1]
    if prob >= 0.6:
        classification = "Bullish bias"
    elif prob <= 0.4:
        classification = "Bearish bias"
    else:
        classification = "Range / Neutral"

    recent = df.loc[latest_idx]
    return TrendSignal(
        latest_date=latest_idx.strftime("%Y-%m-%d"),
        latest_price=float(recent["Close"]),
        probability_bullish=float(prob),
        classification=classification,
        ma5_vs_ma20=float(recent["ma5_ma20_ratio"]),
        ma20_vs_ma60=float(recent["ma20_ma60_ratio"]),
        rsi=float(recent["rsi_14"]),
        atr_pct=float(recent["atr_pct"]),
    )


def compute_feature_importance(model, feature_names: List[str]) -> List[Tuple[str, float]]:
    importance = model.feature_importances_
    pairs = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)
    return [(name, float(weight)) for name, weight in pairs]


def train_pipeline() -> AnalysisSummary:
    raw = fetch_price_history(SYMBOL, START_DATE)
    enriched = engineer_features(raw)
    X, y = build_feature_matrix(enriched)

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = GradientBoostingClassifier(random_state=RANDOM_STATE)
    metrics = evaluate_model(model, X_train, y_train, X_test, y_test)

    # Refit on all data for inference
    model.fit(X, y)
    latest_signal = derive_signal(model, X, enriched)
    feature_importance = compute_feature_importance(model, X.columns.tolist())

    summary = AnalysisSummary(
        symbol=SYMBOL,
        start_date=START_DATE,
        forecast_horizon_days=FORECAST_HORIZON,
        metrics=metrics,
        latest_signal=latest_signal,
        feature_importance=feature_importance,
        test_period={
            "start": X_test.index.min().strftime("%Y-%m-%d"),
            "end": X_test.index.max().strftime("%Y-%m-%d"),
        },
    )
    return summary, enriched, model


def plot_trends(enriched: pd.DataFrame, model, X: pd.DataFrame) -> None:
    latest_years = enriched.iloc[-500:]
    fig, (ax_price, ax_prob) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax_price.plot(latest_years.index, latest_years["Close"], label="Close", color="#1f77b4")
    ax_price.plot(latest_years.index, latest_years["ma_20"], label="MA 20", color="#ff7f0e")
    ax_price.plot(latest_years.index, latest_years["ma_60"], label="MA 60", color="#2ca02c")
    ax_price.set_ylabel("Price")
    ax_price.grid(True, alpha=0.3)
    ax_price.legend(loc="upper left")

    probs = pd.Series(model.predict_proba(X)[:, 1], index=X.index)
    probs = probs.loc[latest_years.index.intersection(probs.index)]
    ax_prob.plot(probs.index, probs.values, color="#d62728", label="Bullish probability")
    ax_prob.axhline(0.6, color="gray", linestyle="--", linewidth=0.8)
    ax_prob.axhline(0.4, color="gray", linestyle="--", linewidth=0.8)
    ax_prob.set_ylabel("Prob")
    ax_prob.set_xlabel("Date")
    ax_prob.grid(True, alpha=0.3)
    ax_prob.legend(loc="upper left")

    fig.suptitle("TAIEX trend analysis (price & model signal)")
    fig.tight_layout()
    fig.savefig(PLOT_PATH, dpi=200)
    plt.close(fig)


def serialize_summary(summary: AnalysisSummary):
    with SUMMARY_PATH.open("w", encoding="utf-8") as fp:
        json.dump(asdict(summary), fp, indent=2)


def main():
    summary, enriched, model = train_pipeline()
    serialize_summary(summary)
    X, _ = build_feature_matrix(enriched)
    plot_trends(enriched, model, X)
    print(json.dumps(asdict(summary), indent=2))
    print(f"Summary saved to {SUMMARY_PATH}")
    print(f"Plot saved to {PLOT_PATH}")


if __name__ == "__main__":
    main()
