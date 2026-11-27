import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="多檔 ETF 報酬率與風險比較", page_icon="📈", layout="centered")

st.title("📈 多檔 ETF 區間報酬率與回撤比較")
st.caption("資料來源：Yahoo Finance（已啟用還原股價 auto_adjust 反映含息報酬）")

if "calc_results" not in st.session_state:
    st.session_state.calc_results = None

# ==========================================
# 🛠️ 1. ETF 中文名稱對照表與三大分類清單
# ==========================================
ETF_NAMES = {
    "0050.TW": "元大台灣50", "009816.TW": "凱基台灣TOP50",
    "00918.TW": "大華優利高填息30", "00961.TW": "FT臺灣永續高息",
    "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息",
    "00919.TW": "群益台灣精選高息", "00939.TW": "統一台灣高息動能",
    "00701.TW": "國泰股利精選30", "00915.TW": "凱基優選高股息30",
    "00938.TW": "凱基優選30", "00713.TW": "元大台灣高息低波",
    "00907.TW": "永豐優息存股", "00731.TW": "復華富時高息低波",
    "00400A.TW": "主動國泰動能高息", "00401A.TW": "主動摩根台灣鑫收",
    "00403A.TW": "主動統一升級50", "00404A.TW": "主動聯博動能50",
    "00405A.TW": "主動富邦台灣龍耀", "00406A.TW": "主動中信台灣收益",
    "00407A.TW": "主動凱基台灣", "00408A.TW": "主動第一金優股息",
    "00410A.TW": "主動永豐科技趨勢", "00413A.TW": "主動玉山關鍵科技",
    "00415A.TW": "主動群益核心50", "00416A.TW": "主動台新臺灣中小",
    "00418A.TW": "主動復華台灣新星", "00419A.TW": "主動施羅德AI台股",
    "00980A.TW": "主動野村臺灣優選", "00981A.TW": "主動統一台股增長",
    "00982A.TW": "主動群益台灣強棒", "00984A.TW": "主動安聯台灣高息",
    "00985A.TW": "主動野村台灣50", "00991A.TW": "主動復華未來50",
    "00992A.TW": "主動群益科技創新", "00993A.TW": "主動安聯台灣",
    "00994A.TW": "主動第一金台股優", "00995A.TW": "主動中信台灣卓越",
    "00996A.TW": "主動兆豐台灣豐收", "00999A.TW": "主動野村臺灣高息",
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

st.markdown("**📌 快速勾選常用 ETF（可跨類別複選）**")
cat_col1, cat_col2, cat_col3 = st.columns(3)
with cat_col1:
    sel_market = st.multiselect("📈 市值型", options=MARKET_CAP_ETFS, default=["0050.TW"], format_func=format_label)
with cat_col2:
    sel_div = st.multiselect("💰 高股息", options=HIGH_DIV_ETFS, default=["00961.TW"], format_func=format_label)
with cat_col3:
    sel_active = st.multiselect("🎯 主動式", options=ACTIVE_ETFS, default=[], format_func=format_label)

custom_tickers_input = st.text_input(
    "✍️ 額外手動輸入其他股號（選填，多檔請用半形逗號 , 隔開）",
    value="", placeholder="例如：2330.TW, VOO, QQQ"
)

# ==========================================
# 📅 2. 快捷時間區間按鈕與日曆選擇器
# ==========================================
today = datetime.date.today()
quick_range = st.radio(
    "⏱️ 快速選擇回測區間",
    options=["近一個月", "近一季", "近半年", "近一年", "今年以來", "自訂區間"],
    index=4, horizontal=True
)

range_days = {"近一個月": 30, "近一季": 90, "近半年": 182, "近一年": 365}
default_start = today - datetime.timedelta(days=range_days[quick_range]) if quick_range in range_days else datetime.date(today.year, 1, 1)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("起始日期", value=default_start)
with col2:
    end_date = st.date_input("終止日期", value=today)

# ==========================================
# 🚀 3. 核心計算引擎
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

        with st.spinner("📡 正在從 Yahoo Finance 抓取歷史資料..."):
            for ticker in tickers:
                display_name = format_label(ticker)
                data = yf.download(ticker, start=start_date, end=fetch_end, auto_adjust=True, progress=False)

                if data.empty:
                    st.warning(f"⚠️ 找不到 **{display_name}** 的資料（可能尚未掛牌或需改用 `.TWO` 後綴），已自動略過。")
                    continue

                if isinstance(data.columns, pd.MultiIndex):
                    if 'Close' in data.columns.get_level_values(0):
                        data = data.loc[:, data.columns.get_level_values(0) == 'Close']
                        data.columns = ['Close']
                    elif ticker in data.columns.get_level_values(1):
                        data = data.xs(ticker, axis=1, level=1)

                series_close = (data['Close'] if 'Close' in data.columns else data).squeeze().dropna()
                if len(series_close) < 2:
                    st.warning(f"⚠️ **{display_name}** 在此區間內的有效交易日不足 2 天，已略過。")
                    continue

                dates_list = series_close.index.tolist()
                prices_list = series_close.to_numpy().flatten().tolist()
                start_actual_date, end_actual_date = dates_list.pop(0), dates_list.pop(-1)
                start_price, end_price = float(prices_list.pop(0)), float(prices_list.pop(-1))

                roi = (end_price / start_price - 1) * 100
                holding_days = (end_actual_date - start_actual_date).days
                cagr = ((end_price / start_price) ** (365 / holding_days) - 1) * 100 if holding_days > 0 else 0.0

                # 計算年化波動度 & 夏普值（無風險利率 1.5%）
                daily_ret = series_close.pct_change().dropna()
                std_daily = float(daily_ret.std()) if len(daily_ret) > 1 else 0.0
                ann_vol = (std_daily * np.sqrt(252) * 100) if std_daily > 0 else 0.0
                sharpe = ((float(daily_ret.mean()) * 252 - 0.015) / (std_daily * np.sqrt(252))) if std_daily > 0 else 0.0

                # 計算每日回撤與最大回撤 (MDD)
                rolling_max = series_close.cummax()
                drawdown_pct = ((series_close - rolling_max) / rolling_max) * 100
                max_drawdown = float(drawdown_pct.min())

                summary_list.append({
                    "ETF 代號與名稱": display_name,
                    "起始日": start_actual_date.strftime("%Y-%m-%d"),
                    "起始價": round(start_price, 2),
                    "結束價": round(end_price, 2),
                    "區間總報酬 (%)": round(roi, 2),
                    "年化報酬 CAGR (%)": round(cagr, 2),
                    "最大回撤 MDD (%)": round(max_drawdown, 2),
                    "年化波動度 (%)": round(ann_vol, 2),
                    "夏普值": round(sharpe, 2)
                })

                roi_series_dict[display_name] = (series_close / start_price - 1) * 100
                drawdown_series_dict[display_name] = drawdown_pct

        if summary_list:
            df_roi = pd.DataFrame(roi_series_dict)
            df_dd = pd.DataFrame(drawdown_series_dict)
            df_roi.index = df_roi.index.strftime("%Y-%m-%d")
            df_dd.index = df_dd.index.strftime("%Y-%m-%d")
            st.session_state.calc_results = {"summary": pd.DataFrame(summary_list), "roi": df_roi, "dd": df_dd}

# ==========================================
# 📈 4. 顯示結果與「大拇指滑桿連續查價器」
# ==========================================
if st.session_state.calc_results is not None:
    res = st.session_state.calc_results
    df_summary, df_roi, df_dd = res["summary"], res["roi"], res["dd"]

    st.divider()
    st.subheader("🏆 區間報酬與風險比較總表")
    st.dataframe(df_summary, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🔍 大拇指連續滑動查價器")
    available_dates = df_roi.index.tolist()
    selected_date = st.select_slider(
        "👈 左右拖曳滑桿，即時連動下方兩張圖表的紅色垂直準心線：",
        options=available_dates, value=available_dates[-1]
    )

    row_roi, row_dd = df_roi.loc[selected_date], df_dd.loc[selected_date]
    cols = st.columns(min(len(df_roi.columns), 3))
    for idx, label_name in enumerate(df_roi.columns):
        val_roi, val_dd = row_roi[label_name], row_dd[label_name]
        dd_label = ("創波段新高 (0%)" if round(val_dd, 2) == 0 else f"距前高 {val_dd:.2f}%") if pd.notna(val_dd) else ""
        with cols[idx % 3]:
            st.metric(
                label=f"{label_name} ({selected_date})",
                value=f"{val_roi:+.2f}%" if pd.notna(val_roi) else "無資料",
                delta=dd_label, delta_color="off"
            )

    def build_chart(df, y_title, active_date):
        fig = go.Figure()
        for col in df.columns:
            fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=col, line=dict(width=2.5), hovertemplate="%{y:+.2f}%"))
        fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=active_date, line_width=1.5, line_dash="solid", line_color="#FF4B4B")
        fig.update_layout(
            hovermode="x unified",
            xaxis=dict(title="", fixedrange=True),
            yaxis=dict(title=y_title, ticksuffix="%", fixedrange=True),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=10, r=10, t=35, b=10), height=360
        )
        return fig

    st.subheader("📊 累積報酬率走勢疊圖（%）")
    st.plotly_chart(build_chart(df_roi, "累積報酬率 (%)", selected_date), use_container_width=True, config={"displayModeBar": False})

    st.subheader("🌊 回撤走勢水下圖（Underwater Plot, %）")
    st.plotly_chart(build_chart(df_dd, "回撤幅度 (%)", selected_date), use_container_width=True, config={"displayModeBar": False})
