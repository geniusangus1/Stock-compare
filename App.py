import datetime, re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="多檔 ETF 報酬率與風險比較", page_icon="📈", layout="centered")
st.title("📈 多檔 ETF 區間報酬率與回撤比較")
st.caption("資料來源：Yahoo Finance（含息還原股價）＆ ETF資訊網（近12個月54C佔比）")

if "calc_results" not in st.session_state:
    st.session_state.calc_results = None

# 1. ETF 分類清單（可在此字典自行補充中文名稱）
ETF_NAMES = {"0050.TW": "元大台灣50", "00961.TW": "FT臺灣永續高息"}

def format_label(ticker):
    code = ticker.replace(".TW", "").replace(".TWO", "")
    return f"{code} {ETF_NAMES.get(ticker, '')}".strip()

MARKET_CAP_ETFS = ["0050.TW", "009816.TW"]
HIGH_DIV_ETFS = ["00918.TW", "00961.TW", "0056.TW", "00878.TW", "00919.TW", "00939.TW", "00701.TW", "00915.TW", "00938.TW", "00713.TW", "00907.TW", "00731.TW"]
ACTIVE_ETFS = [
    "00400A.TW", "00401A.TW", "00403A.TW", "00404A.TW", "00405A.TW", "00406A.TW", "00407A.TW", "00408A.TW",
    "00410A.TW", "00413A.TW", "00415A.TW", "00416A.TW", "00418A.TW", "00419A.TW", "00980A.TW", "00981A.TW",
    "00982A.TW", "00984A.TW", "00985A.TW", "00991A.TW", "00992A.TW", "00993A.TW", "00994A.TW", "00995A.TW", "00996A.TW", "00999A.TW"
]

# 2. 抓取 ETF資訊網 近12個月 54C 佔比
@st.cache_data(ttl=43200)
def fetch_etfinfo_54c_map():
    ratio_map = {}
    try:
        resp = requests.get("https://etfinfo.tw", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.encoding = "utf-8"
        for df in pd.read_html(resp.text):
            col_etf = next((c for c in df.columns if "ETF" in str(c) or "代號" in str(c)), None)
            col_54c = next((c for c in df.columns if "54C" in str(c)), None)
            if col_etf is not None and col_54c is not None:
                for _, row in df.iterrows():
                    m_code = re.search(r"(00\d{3,4}[A-Z]?)", str(row[col_etf]))
                    m_pct = re.search(r"(\d+(?:\.\d+)?)\s*%", str(row[col_54c]))
                    if m_code and m_pct:
                        ratio_map[m_code.group(1)] = f"{float(m_pct.group(1)):.2f}%"
                if ratio_map:
                    break
    except Exception:
        pass
    return ratio_map

st.markdown("**📌 快速勾選常用 ETF（可跨類別複選）**")
c1, c2, c3 = st.columns(3)
with c1: sel_market = st.multiselect("📈 市值型", MARKET_CAP_ETFS, default=["0050.TW"], format_func=format_label)
with c2: sel_div = st.multiselect("💰 高股息", HIGH_DIV_ETFS, default=["00961.TW"], format_func=format_label)
with c3: sel_active = st.multiselect("🎯 主動式", ACTIVE_ETFS, default=[], format_func=format_label)

custom_tickers_input = st.text_input("✍️ 額外手動輸入其他股號（多檔用半形逗號 , 隔開）", placeholder="例如：2330.TW, VOO, QQQ")

# 3. 快捷時間區間與日曆
today = datetime.date.today()
quick_range = st.radio("⏱️ 快速選擇回測區間", ["近一個月", "近一季", "近半年", "近一年", "今年以來", "自訂區間"], index=4, horizontal=True)
range_days = {"近一個月": 30, "近一季": 90, "近半年": 182, "近一年": 365}
default_start = today - datetime.timedelta(days=range_days[quick_range]) if quick_range in range_days else datetime.date(today.year, 1, 1)

d1, d2 = st.columns(2)
with d1: start_date = st.date_input("起始日期", value=default_start)
with d2: end_date = st.date_input("終止日期", value=today)

# 4. 核心計算引擎
if st.button("🚀 開始計算與疊圖比較", type="primary", use_container_width=True):
    tickers = list(dict.fromkeys(sel_market + sel_div + sel_active + [t.strip().upper() for t in custom_tickers_input.split(",") if t.strip()]))
    if not tickers:
        st.warning("⚠️ 請至少勾選或輸入一檔股票代號！")
    elif start_date >= end_date:
        st.error("⚠️ 終止日期必須晚於起始日期！")
    else:
        fetch_end = end_date + datetime.timedelta(days=1)
        summary_list, roi_dict, dd_dict = [], {}, {}
        rf = 0.015
        with st.spinner("📡 正在抓取股價與 ETF資訊網 54C 佔比..."):
            map_54c = fetch_etfinfo_54c_map()
            for ticker in tickers:
                display_name = format_label(ticker)
                clean_code = ticker.replace(".TW", "").replace(".TWO", "")
                data = yf.download(ticker, start=start_date, end=fetch_end, auto_adjust=True, progress=False)
                if data.empty:
                    st.warning(f"⚠️ 找不到 **{display_name}** 資料，已略過。")
                    continue
                if isinstance(data.columns, pd.MultiIndex):
                    data = data.loc[:, data.columns.get_level_values(0) == 'Close'] if 'Close' in data.columns.get_level_values(0) else data.xs(ticker, axis=1, level=1)
                series_close = (data['Close'] if 'Close' in data.columns else data).squeeze().dropna()
                if len(series_close) < 2:
                    st.warning(f"⚠️ **{display_name}** 有效交易日不足 2 天，已略過。")
                    continue

                dates_l, prices_l = series_close.index.tolist(), series_close.to_numpy().flatten().tolist()
                s_date, e_date = dates_l.pop(0), dates_l.pop(-1)
                s_price, e_price = float(prices_l.pop(0)), float(prices_l.pop(-1))

                roi = (e_price / s_price - 1) * 100
                days = (e_date - s_date).days
                cagr = ((e_price / s_price) ** (365 / days) - 1) * 100 if days > 0 else 0.0

                d_ret = series_close.pct_change().dropna()
                ann_ret = float(d_ret.mean()) * 252 if len(d_ret) > 0 else 0.0
                std_d = float(d_ret.std()) if len(d_ret) > 1 else 0.0
                ann_vol = (std_d * np.sqrt(252) * 100) if std_d > 0 else 0.0
                sharpe = ((ann_ret - rf) / (std_d * np.sqrt(252))) if std_d > 0 else 0.0

                ds_diff = np.minimum(0.0, d_ret - (rf / 252))
                ds_std = float(np.sqrt((ds_diff ** 2).mean()) * np.sqrt(252)) if len(d_ret) > 1 else 0.0
                sortino = ((ann_ret - rf) / ds_std) if ds_std > 0 else 0.0

                dd_pct = ((series_close - series_close.cummax()) / series_close.cummax()) * 100
                mdd = float(dd_pct.min())
                calmar = (cagr / abs(mdd)) if mdd < 0 else 0.0

                summary_list.append({
                    "ETF": display_name, "起始日": s_date.strftime("%Y-%m-%d"), "起始價": round(s_price, 2), "結束價": round(e_price, 2),
                    "總報酬 (%)": round(roi, 2), "年化 CAGR (%)": round(cagr, 2), "最大回撤 (%)": round(mdd, 2),
                    "波動度 (%)": round(ann_vol, 2), "夏普 Sharpe": round(sharpe, 2), "索提諾 Sortino": round(sortino, 2),
                    "卡瑪 Calmar": round(calmar, 2), "近1年54C佔比": map_54c.get(clean_code, "—")
                })
                roi_dict[display_name] = (series_close / s_price - 1) * 100
                dd_dict[display_name] = dd_pct

        if summary_list:
            df_roi, df_dd = pd.DataFrame(roi_dict), pd.DataFrame(dd_dict)
            df_roi.index, df_dd.index = df_roi.index.strftime("%Y-%m-%d"), df_dd.index.strftime("%Y-%m-%d")
            st.session_state.calc_results = {"summary": pd.DataFrame(summary_list), "roi": df_roi, "dd": df_dd}

# 5. 顯示結果與滑桿查價器
def build_chart(df, y_title, active_date):
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=col, line=dict(width=2.5), hovertemplate="%{y:+.2f}%"))
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=active_date, line_width=1.5, line_dash="solid", line_color="#FF4B4B")
    fig.update_layout(hovermode="x unified", xaxis=dict(title="", fixedrange=True), yaxis=dict(title=y_title, ticksuffix="%", fixedrange=True), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), margin=dict(l=10, r=10, t=35, b=10), height=360)
    return fig

if st.session_state.calc_results is not None:
    res = st.session_state.calc_results
    df_summary, df_roi, df_dd = res["summary"], res["roi"], res["dd"]
    st.divider()
    if len(df_summary) >= 2:
        b_roi, b_mdd, b_shp = df_summary.loc[df_summary["總報酬 (%)"].idxmax()], df_summary.loc[df_summary["最大回撤 (%)"].idxmax()], df_summary.loc[df_summary["夏普 Sharpe"].idxmax()]
        w1, w2, w3 = st.columns(3)
        w1.metric("🥇 區間報酬王", b_roi["ETF"], f"{b_roi['總報酬 (%)']:+.2f}%")
        w2.metric("🛡️ 區間抗跌王", b_mdd["ETF"], f"MDD {b_mdd['最大回撤 (%)']:.2f}%", delta_color="off")
        w3.metric("⚖️ CP值之王 (Sharpe)", b_shp["ETF"], f"{b_shp['夏普 Sharpe']:.2f}")

    st.subheader("🏆 區間報酬與風險比較總表")
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

    with st.expander("📖 指標公式與判讀說明（Sharpe / Sortino / Calmar / 54C 怎麼看？）"):
        st.markdown("* **夏普 Sharpe**：`(年化報酬 - 1.5%) / 總波動度`（衡量每單位總波動的超額報酬）\n* **索提諾 Sortino**：`(年化報酬 - 1.5%) / 下檔波動度`（只懲罰下跌波動）\n* **卡瑪 Calmar**：`CAGR / |最大回撤 MDD|`（衡量承受最深虧損的年化回報）\n* **近1年54C佔比**：抓取 ETF資訊網近 12 個月配息金額加權股利所得佔比（無資料顯示 `—`）")

    st.divider()
    st.subheader("🔍 大拇指連續滑動查價器")
    selected_date = st.select_slider("👈 左右拖曳滑桿，即時連動下方圖表：", options=df_roi.index.tolist(), value=df_roi.index.tolist()[-1])
    row_roi, row_dd = df_roi.loc[selected_date], df_dd.loc[selected_date]
    cols = st.columns(min(len(df_roi.columns), 3))
    for idx, label_name in enumerate(df_roi.columns):
        val_roi, val_dd = row_roi[label_name], row_dd[label_name]
        dd_label = ("創波段新高 (0%)" if round(val_dd, 2) == 0 else f"距前高 {val_dd:.2f}%") if pd.notna(val_dd) else ""
        with cols[idx % 3]:
            st.metric(label=f"{label_name} ({selected_date})", value=f"{val_roi:+.2f}%" if pd.notna(val_roi) else "無資料", delta=dd_label, delta_color="off")

    st.subheader("📊 累積報酬率走勢疊圖（%）")
    st.plotly_chart(build_chart(df_roi, "累積報酬率 (%)", selected_date), use_container_width=True, config={"displayModeBar": False})
    st.subheader("🌊 回撤走勢水下圖（Underwater Plot, %）")
    st.plotly_chart(build_chart(df_dd, "回撤幅度 (%)", selected_date), use_container_width=True, config={"displayModeBar": False})
