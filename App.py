import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="多檔 ETF 報酬率與風險比較", page_icon="📈", layout="centered")
st.title("📈 多檔 ETF 區間報酬率與回撤比較")
st.caption("資料來源：Yahoo Finance（含息還原股價）＆ 臺灣證券交易所公開配息資料")

if "calc_results" not in st.session_state:
    st.session_state.calc_results = None

# ==========================================
# 🛠️ 1. ETF 分類清單（可在下方字典自行補充中文名稱）
# ==========================================
ETF_NAMES = {
    "0050.TW": "元大台灣50",
    "00961.TW": "FT臺灣永續高息",
}

def format_label(ticker):
    code = ticker.replace(".TW", "").replace(".TWO", "")
    name = ETF_NAMES.get(ticker, "")
    return f"{code} {name}".strip()

MARKET_CAP_ETFS = ["0050.TW", "009816.TW"]
HIGH_DIV_ETFS = [
    "00918.TW", "00961.TW", "0056.TW", "00878.TW", "00919.TW", "00939.TW",
    "00701.TW", "00915.TW", "00938.TW", "00713.TW", "00907.TW", "00731.TW"
]
ACTIVE_ETFS = [
    "00400A.TW", "00401A.TW", "00403A.TW", "00404A.TW", "00405A.TW", "00406A.TW",
    "00407A.TW", "00408A.TW", "00410A.TW", "00413A.TW", "00415A.TW", "00416A.TW",
    "00418A.TW", "00419A.TW", "00980A.TW", "00981A.TW", "00982A.TW", "00984A.TW",
    "00985A.TW", "00991A.TW", "00992A.TW", "00993A.TW", "00994A.TW", "00995A.TW",
    "00996A.TW", "00999A.TW"
]

# ==========================================
# 🌐 2. 串接證交所公開 API 計算近 12 個月 54C 佔比
# ==========================================
@st.cache_data(ttl=86400)
def fetch_twse_54c_map():
    """從證交所公開 API 抓取近 12 個月 ETF 收益分配組成並計算加權 54C 佔比"""
    today_dt = datetime.date.today()
    start_dt = today_dt - datetime.timedelta(days=365)
    url = (
        f"https://twse.com.tw"
        f"?startDate={start_dt.strftime('%Y%m%d')}&endDate={today_dt.strftime('%Y%m%d')}&response=json"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    ratio_map = {}
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        js = resp.json()
        fields = js.get("fields", [])
        rows = js.get("data", [])
        if not fields or not rows:
            return ratio_map

        # 動態定位「代號」、「分配金額」與「股利所得(54C)占比」欄位索引
        idx_code = next((i for i, f in enumerate(fields) if "代號" in f), 0)
        idx_amt = next((i for i, f in enumerate(fields) if "分配金額" in f or "每單位" in f), -1)
        idx_54c = next((i for i, f in enumerate(fields) if "54C" in f or "股利" in f), -1)
        if idx_amt == -1 or idx_54c == -1:
            return ratio_map

        acc = {}
        for r in rows:
            code = str(r[idx_code]).strip()
            try:
                amt = float(str(r[idx_amt]).replace(",", "").strip())
                pct_str = str(r[idx_54c]).replace("%", "").replace(",", "").strip()
                if pct_str in ("", "-", "--", "不適用"):
                    continue
                pct = float(pct_str)
                if code not in acc:
                    acc[code] = [0.0, 0.0]
                acc[code][0] += amt * pct
                acc[code][1] += amt
            except ValueError:
                continue

        for code, (weighted_sum, total_amt) in acc.items():
            if total_amt > 0:
                ratio_map[code] = round(weighted_sum / total_amt, 2)
    except Exception:
        pass
    return ratio_map

st.markdown("**📌 快速勾選常用 ETF（可跨類別複選）**")
cat_col1, cat_col2, cat_col3 = st.columns(3)
with cat_col1:
    sel_market = st.multiselect("📈 市值型", options=MARKET_CAP_ETFS, default=["0050.TW"], format_func=format_label)
with cat_col2:
    sel_div = st.multiselect("💰 高股息", options=HIGH_DIV_ETFS, default=["00961.TW"], format_func=format_label)
with cat_col3:
    sel_active = st.multiselect("🎯 主動式", options=ACTIVE_ETFS, default=[], format_func=format_label)

custom_tickers_input = st.text_input("✍️ 額外手動輸入其他股號（多檔用半形逗號 , 隔開）", placeholder="例如：2330.TW, VOO, QQQ")

# ==========================================
# 📅 3. 快捷時間區間按鈕與日曆選擇器
# ==========================================
today = datetime.date.today()
quick_range = st.radio("⏱️ 快速選擇回測區間", ["近一個月", "近一季", "近半年", "近一年", "今年以來", "自訂區間"], index=4, horizontal=True)

range_days = {"近一個月": 30, "近一季": 90, "近半年": 182, "近一年": 365}
default_start = today - datetime.timedelta(days=range_days[quick_range]) if quick_range in range_days else datetime.date(today.year, 1, 1)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("起始日期", value=default_start)
with col2:
    end_date = st.date_input("終止日期", value=today)

# ==========================================
# 🚀 4. 核心計算引擎
# ==========================================
if st.button("🚀 開始計算與疊圖比較", type="primary", use_container_width=True):
    selected_tickers = sel_market + sel_div + sel_active
    custom_tickers = [t.strip().upper() for t in custom_tickers_input.split(",") if t.strip()]
    tickers = list(dict.fromkeys(selected_tickers + custom_tickers))

    if not tickers:
        st.warning("⚠️ 請至少勾選或輸入一檔股票代號！")
    elif start_date >= end_date:
        st.error("⚠️ 終止日期必須晚於起始日期！")
    else:
        fetch_end = end_date + datetime.timedelta(days=1)
        summary_list, roi_series_dict, drawdown_series_dict = [], {}, {}
        rf_rate = 0.015

        with st.spinner("📡 正在抓取股價與證交所 54C 配息組成資料..."):
            twse_54c_dict = fetch_twse_54c_map()

            for ticker in tickers:
                display_name = format_label(ticker)
                clean_code = ticker.replace(".TW", "").replace(".TWO", "")
                data = yf.download(ticker, start=start_date, end=fetch_end, auto_adjust=True, progress=False)

                if data.empty:
                    st.warning(f"⚠️ 找不到 **{display_name}** 的資料（可能尚未掛牌或需改用 `.TWO`），已略過。")
                    continue

                if isinstance(data.columns, pd.MultiIndex):
                    if 'Close' in data.columns.get_level_values(0):
                        data = data.loc[:, data.columns.get_level_values(0) == 'Close']
                        data.columns = ['Close']
                    elif ticker in data.columns.get_level_values(1):
                        data = data.xs(ticker, axis=1, level=1)

                series_close = (data['Close'] if 'Close' in data.columns else data).squeeze().dropna()
                if len(series_close) < 2:
                    st.warning(f"⚠️ **{display_name}** 有效交易日不足 2 天，已略過。")
                    continue

                dates_list = series_close.index.tolist()
                prices_list = series_close.to_numpy().flatten().tolist()
                start_actual_date, end_actual_date = dates_list.pop(0), dates_list.pop(-1)
                start_price, end_price = float(prices_list.pop(0)), float(prices_list.pop(-1))

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

                val_54c = twse_54c_dict.get(clean_code, None)
                str_54c = f"{val_54c:.2f}%" if val_54c is not None else "—"

                summary_list.append({
                    "ETF": display_name,
                    "起始日": start_actual_date.strftime("%Y-%m-%d"),
                    "起始價": round(start_price, 2),
                    "結束價": round(end_price, 2),
                    "總報酬 (%)": round(roi, 2),
                    "年化 CAGR (%)": round(cagr, 2),
                    "最大回撤 (%)": round(max_drawdown, 2),
                    "波動度 (%)": round(ann_vol, 2),
                    "夏普 Sharpe": round(sharpe, 2),
                    "索提諾 Sortino": round(sortino, 2),
                    "卡瑪 Calmar": round(calmar, 2),
                    "近1年54C佔比": str_54c
                })

                roi_series_dict[display_name] = (series_close / start_price - 1) * 100
                drawdown_series_dict[display_name] = drawdown_pct

        if summary_list:
            df_roi, df_dd = pd.DataFrame(roi_series_dict), pd.DataFrame(drawdown_series_dict)
            df_roi.index, df_dd.index = df_roi.index.strftime("%Y-%m-%d"), df_dd.index.strftime("%Y-%m-%d")
            st.session_state.calc_results = {"summary": pd.DataFrame(summary_list), "roi": df_roi, "dd": df_dd}

# ==========================================
# 📈 5. 顯示結果、頒獎台、指標說明與滑桿查價器
# ==========================================
def build_chart(df, y_title, active_date):
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=col, line=dict(width=2.5), hovertemplate="%{y:+.2f}%"))
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=active_date, line_width=1.5, line_dash="solid", line_color="#FF4B4B")
    fig.update_layout(
        hovermode="x unified", xaxis=dict(title="", fixedrange=True), yaxis=dict(title=y_title, ticksuffix="%", fixedrange=True),
legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), margin=dict(l=10, r=10, t=35, b=10), height=360
)
return fig
if st.session_state.calc_results is not None:
res = st.session_state.calc_results
df_summary, df_roi, df_dd = res["summary"], res["roi"], res["dd"]
st.divider()
if len(df_summary) >= 2:
best_roi = df_summary.loc[df_summary["總報酬 (%)"].idxmax()]
best_mdd = df_summary.loc[df_summary["最大回撤 (%)"].idxmax()]
best_shp = df_summary.loc[df_summary["夏普 Sharpe"].idxmax()]
w1, w2, w3 = st.columns(3)
w1.metric("🥇 區間報酬王", best_roi["ETF"], f"{best_roi['總報酬 (%)']:+.2f}%")
w2.metric("🛡️ 區間抗跌王", best_mdd["ETF"], f"MDD {best_mdd['最大回撤 (%)']:.2f}%", delta_color="off")
w3.metric("⚖️ CP值之王 (Sharpe)", best_shp["ETF"], f"{best_shp['夏普 Sharpe']:.2f}")
st.subheader("🏆 區間報酬與風險比較總表")
st.dataframe(df_summary, use_container_width=True, hide_index=True)
with st.expander("📖 指標公式與判讀說明（Sharpe / Sortino / Calmar / 54C 怎麼看？）"):
st.markdown("""
* 夏普比率 (Sharpe)：(年化平均報酬 - 1.5%) / 年化總波動度 — 衡量每單位「總波動」換到的超額報酬，適合當第一道通用篩選（大於 1 屬優秀）。
* 索提諾比率 (Sortino)：(年化平均報酬 - 1.5%) / 年化下檔波動度 — 只懲罰「下跌」波動、不把大漲算成風險，適合評估飆漲快或高股息抗跌標的。
* 卡瑪比率 (Calmar)：年化報酬 CAGR / |最大回撤 MDD| — 衡量承受「最痛那一刀虧損」所換來的年化報酬，越高代表抗跌且解套快。
* 近1年54C佔比：自動向臺灣證券交易所抓取近 365 天除息公告之「股利或盈餘所得 (54C)」占比，並依每次配息金額加權平均（尚未配息或無資料顯示 —）。
""")
st.divider()
st.subheader("🔍 大拇指連續滑動查價器")
available_dates = df_roi.index.tolist()
selected_date = st.select_slider("👈 左右拖曳滑桿，即時連動下方圖表：", options=available_dates, value=available_dates[-1])
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
