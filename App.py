import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="多檔股票報酬率與風險比較", page_icon="📈", layout="centered")

st.title("📈 多檔股票區間報酬率與回撤比較")
st.caption("資料來源：Yahoo Finance（已啟用還原股價 auto_adjust 反映含息報酬）")

# ==========================================
# 🛠️ 1. 分類常用 ETF 快捷清單與輸入區
# ==========================================
MARKET_CAP_ETFS = [
    "0050.TW", "009816.TW"
]

HIGH_DIV_ETFS = [
    "00918.TW", "00961.TW", "0056.TW", "00878.TW",
    "00919.TW", "00939.TW", "00701.TW"
]

ACTIVE_ETFS = [
    "00400A.TW", "00401A.TW", "00403A.TW", "00404A.TW", "00405A.TW",
    "00406A.TW", "00407A.TW", "00408A.TW", "00410A.TW", "00413A.TW",
    "00415A.TW", "00416A.TW", "00418A.TW", "00419A.TW", "00980A.TW",
    "00981A.TW", "00982A.TW", "00984A.TW", "00985A.TW", "00991A.TW",
    "00992A.TW", "00993A.TW", "00994A.TW", "00995A.TW", "00996A.TW",
    "00999A.TW"
]

st.markdown("**📌 快速勾選常用 ETF（可跨類別複選）**")
cat_col1, cat_col2, cat_col3 = st.columns(3)

with cat_col1:
    sel_market = st.multiselect(
        "📈 市值型",
        options=MARKET_CAP_ETFS,
        default=["0050.TW"]
    )

with cat_col2:
    sel_div = st.multiselect(
        "💰 高股息",
        options=HIGH_DIV_ETFS,
        default=["00961.TW"]
    )

with cat_col3:
    sel_active = st.multiselect(
        "🎯 主動式",
        options=ACTIVE_ETFS,
        default=[]
    )

custom_tickers_input = st.text_input(
    "✍️ 額外手動輸入其他股號（選填，多檔請用半形逗號 , 隔開）",
    value="",
    placeholder="例如：2330.TW, VOO, QQQ",
    help="台股上市加 .TW、上櫃加 .TWO，美股直接輸入代號"
)

# ==========================================
# 📅 2. 快捷時間區間按鈕與日曆選擇器
# ==========================================
today = datetime.date.today()

quick_range = st.radio(
    "⏱️ 快速選擇回測區間",
    options=["近一個月", "近一季", "近半年", "近一年", "今年以來", "自訂區間"],
    index=4,  # 預設選取「今年以來」
    horizontal=True
)

if quick_range == "近一個月":
    default_start = today - datetime.timedelta(days=30)
elif quick_range == "近一季":
    default_start = today - datetime.timedelta(days=90)
elif quick_range == "近半年":
    default_start = today - datetime.timedelta(days=182)
elif quick_range == "近一年":
    default_start = today - datetime.timedelta(days=365)
elif quick_range == "今年以來":
    default_start = datetime.date(today.year, 1, 1)
else:
    default_start = datetime.date(today.year, 1, 1)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("起始日期", value=default_start)
with col2:
    end_date = st.date_input("終止日期", value=today)

# ==========================================
# 📊 3. 互動式圖表繪製函式（支援連續滑動準心）
# ==========================================
def build_interactive_chart(df, y_title):
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[col],
            mode="lines",
            name=col,
            line=dict(width=2.2),
            hovertemplate="%{y:+.2f}%"
        ))

    fig.update_layout(
        hovermode="x unified",  # 關鍵設定：滑動時垂直準心同步顯示所有股票數據
        xaxis=dict(
            title="日期",
            tickformat="%Y-%m-%d",
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=1,
            spikedash="dot",
            fixedrange=True  # 鎖定縮放，確保手機手指左右滑動順暢不誤觸
        ),
        yaxis=dict(
            title=y_title,
            ticksuffix="%",
            fixedrange=True
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        height=400
    )
    # 加上 0% 基準參考線
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", opacity=0.5)
    return fig

# ==========================================
# 🚀 4. 核心計算與疊圖引擎
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
        summary_list = []
        roi_series_dict = {}
        drawdown_series_dict = {}

        with st.spinner("📡 正在從 Yahoo Finance 抓取歷史資料..."):
            for ticker in tickers:
                data = yf.download(ticker, start=start_date, end=fetch_end, auto_adjust=True, progress=False)

                if data.empty:
                    st.warning(f"⚠️ 找不到 **{ticker}** 的資料（可能尚未掛牌或需改用 `.TWO` 上櫃後綴），已自動略過。")
                    continue

                # 處理新版 yfinance MultiIndex 結構
                if isinstance(data.columns, pd.MultiIndex):
                    if 'Close' in data.columns.get_level_values(0):
                        data = data.loc[:, data.columns.get_level_values(0) == 'Close']
                        data.columns = ['Close']
                    elif ticker in data.columns.get_level_values(1):
                        data = data.xs(ticker, axis=1, level=1)

                series_close = data['Close'] if 'Close' in data.columns else data
                series_close = series_close.squeeze().dropna()

                if len(series_close) < 2:
                    st.warning(f"⚠️ **{ticker}** 在此區間內的有效交易日不足 2 天，已略過。")
                    continue

                # 安全取值取得首尾交易日與價格
                dates_list = series_close.index.tolist()
                prices_list = series_close.to_numpy().flatten().tolist()

                start_actual_date = dates_list.pop(0)
                end_actual_date = dates_list.pop(-1)
                start_price = float(prices_list.pop(0))
                end_price = float(prices_list.pop(-1))

                # 計算總報酬率 (ROI) 與年化報酬率 (CAGR)
                roi = (end_price / start_price - 1) * 100
                holding_days = (end_actual_date - start_actual_date).days
                cagr = ((end_price / start_price) ** (365 / holding_days) - 1) * 100 if holding_days > 0 else 0.0

                # 計算每日回撤 (%) 與最大回撤 (Max Drawdown, MDD)
                rolling_max = series_close.cummax()
                drawdown_pct = ((series_close - rolling_max) / rolling_max) * 100
                max_drawdown = float(drawdown_pct.min())

                # 整理成比較表格列
                summary_list.append({
                    "股票代號": ticker,
                    "起始日": start_actual_date.strftime("%Y-%m-%d"),
                    "起始價": round(start_price, 2),
                    "結束日": end_actual_date.strftime("%Y-%m-%d"),
                    "結束價": round(end_price, 2),
                    "區間總報酬 (%)": round(roi, 2),
                    "年化報酬 CAGR (%)": round(cagr, 2),
                    "最大回撤 MDD (%)": round(max_drawdown, 2),
                    "持有天數": holding_days
                })

                # 儲存每日累積報酬率與每日回撤序列
                cumulative_roi = (series_close / start_price - 1) * 100
                roi_series_dict[ticker] = cumulative_roi
                drawdown_series_dict[ticker] = drawdown_pct

        # ==========================================
        # 📈 5. 顯示比較總表、累積報酬疊圖與水下圖
        # ==========================================
        if summary_list:
            st.divider()
            st.subheader("🏆 區間報酬與風險比較總表")
            df_summary = pd.DataFrame(summary_list)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)

            st.subheader("📊 累積報酬率走勢疊圖（%）")
            st.caption("💡 提示：手指點在圖上並左右滑動，即可同步檢視各檔標的當日累積報酬率")
            df_roi_chart = pd.DataFrame(roi_series_dict)
            st.plotly_chart(build_interactive_chart(df_roi_chart, "累積報酬率 (%)"), use_container_width=True, config={"displayModeBar": False})

            st.subheader("🌊 回撤走勢水下圖（Underwater Plot, %）")
            st.caption("💡 提示：0% 代表創新高，手指左右滑動可查看各檔標的在特定日期的回檔深度")
            df_dd_chart = pd.DataFrame(drawdown_series_dict)
            st.plotly_chart(build_interactive_chart(df_dd_chart, "回撤幅度 (%)"), use_container_width=True, config={"displayModeBar": False})
