import datetime
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from etf_config import ROLLING_WINDOWS

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_full_history(ticker: str, _v: int = 3) -> pd.Series:
    # 台股 (.TW / .TWO) 在 Yahoo Finance 2015 年以前的早期歷史資料常有配息/分割未對齊的斷層
    # 美股或其他市場則保留自 2000 年起的完整歷史
    is_tw = ticker.endswith(".TW") or ticker.endswith(".TWO")
    fetch_start = "2015-01-01" if is_tw else "2000-01-01"
    end_dt = datetime.date.today() + datetime.timedelta(days=1)

    try:
        t_obj = yf.Ticker(ticker)
        data = t_obj.history(start=fetch_start, end=end_dt.strftime("%Y-%m-%d"), auto_adjust=True)
    except Exception:
        return pd.Series(dtype=float)

    if data is None or data.empty or "Close" not in data.columns:
        return pd.Series(dtype=float)

    series_close = data["Close"].squeeze().dropna()
    if series_close.empty:
        return pd.Series(dtype=float)

    series_close.index = pd.to_datetime(series_close.index).tz_localize(None)

    # 🛡️ 偵測單日異常價格跳動（單日漲跌 > 15% 对台股 ETF 來說必為資料異常）
    threshold = 0.15 if is_tw else 0.25
    daily_pct = series_close.pct_change().abs()
    price_anomalies = daily_pct[daily_pct > threshold]
    if not price_anomalies.empty:
        last_price_date = price_anomalies.index[-1]
        cleaned = series_close.loc[series_close.index > last_price_date]
        if len(cleaned) > 10:
            series_close = cleaned

    return series_close

def calc_rolling_stats(full_series: pd.Series, display_name: str, rolling_curves: dict) -> dict:
    roll_row = {
        "標的": display_name,
        "起始日": full_series.index[0].strftime("%Y-%m-%d"),
    }
    for win_label, cfg in ROLLING_WINDOWS.items():
        days, yrs = cfg["days"], cfg["years"]
        if len(full_series) > days:
            raw_ret = full_series.pct_change(periods=days).dropna()
            r_pct = (((1 + raw_ret) ** (1.0 / yrs) - 1) * 100) if yrs >= 1.0 else (raw_ret * 100)
            roll_row[f"{win_label} 平均"] = f"{float(r_pct.mean()):+.2f}%"
            roll_row[f"{win_label} 勝率"] = f"{float((r_pct > 0).mean() * 100):.1f}%"
            roll_row[f"{win_label} 高/低"] = f"{float(r_pct.max()):+.1f}% / {float(r_pct.min()):+.1f}%"
            rolling_curves[win_label][display_name] = r_pct
        else:
            roll_row[f"{win_label} 平均"] = "資料不足"
            roll_row[f"{win_label} 勝率"] = "-"
            roll_row[f"{win_label} 高/低"] = "-"
    return roll_row

def calc_period_metrics(series_close: pd.Series, display_name: str, rf_rate: float = 0.015):
    start_actual_date = series_close.index[0]
    end_actual_date = series_close.index[-1]
    start_price = float(series_close.iloc[0])
    end_price = float(series_close.iloc[-1])

    roi = (end_price / start_price - 1) * 100
    holding_days = (end_actual_date - start_actual_date).days
    cagr = ((end_price / start_price) ** (365 / holding_days) - 1) * 100 if holding_days > 0 else 0.0

    daily_ret = series_close.pct_change().dropna()
    ann_ret = float(daily_ret.mean()) * 252 if len(daily_ret) > 0 else 0.0
    std_daily = float(daily_ret.std()) if len(daily_ret) > 1 else 0.0
    ann_vol = (std_daily * np.sqrt(252) * 100) if std_daily > 0 else 0.0
    sharpe = ((ann_ret - rf_rate) / (std_daily * np.sqrt(252))) if std_daily > 0 else 0.0

    downside_diff = np.minimum(0.0, daily_ret - (rf_rate / 252))
    downside_std_ann = float(np.sqrt((downside_diff ** 2).mean()) * np.sqrt(252)) if len(daily_ret) > 1 else 0.0
    sortino = ((ann_ret - rf_rate) / downside_std_ann) if downside_std_ann > 0 else 0.0

    rolling_max = series_close.cummax()
    drawdown_pct = ((series_close - rolling_max) / rolling_max) * 100
    max_drawdown = float(drawdown_pct.min())
    calmar = (cagr / abs(max_drawdown)) if max_drawdown < 0 else 0.0

    summary_row = {
        "標的": display_name,
        "起始日": start_actual_date.strftime("%Y-%m-%d"),
        "起始價": round(start_price, 2),
        "結束價": round(end_price, 2),
        "總報酬 (%)": round(roi, 2),
        "年化 CAGR (%)": round(cagr, 2),
        "最大回撤 (%)": round(max_drawdown, 2),
        "波動度 (%)": round(ann_vol, 2),
        "夏普 Sharpe": round(sharpe, 2),
        "索提諾 Sortino": round(sortino, 2),
        "卡瑪 Calmar": round(calmar, 2)
    }
    roi_series = (series_close / start_price - 1) * 100
    return summary_row, roi_series, drawdown_pct
