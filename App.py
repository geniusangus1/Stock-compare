import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="多檔股票報酬率與風險比較", page_icon="📈", layout="centered")

st.title("📈 多檔股票區間報酬率與回撤比較")
st.caption("資料來源：Yahoo Finance（已啟用還原股價 auto_adjust 反映含息報酬）")

# ==========================================
# 🛠️ 1. 預設常用 ETF 快捷清單與輸入區
# ==========================================
PRESET_ETFS = {
    "00961.TW (FT臺灣永續高息)": "00961.TW",
    "0050.TW (元大台灣50)": "0050.TW",
    "00918.TW (大華優利高填息30)": "00918.TW",
    "0056.TW (元大高股息)": "0056.TW",
    "00878.TW (國泰永續高股息)": "00878.TW",
    "00919.TW (群益台灣精選高息)": "00919.TW",
    "00929.TW (復華台灣科技優息)": "00929.TW",
    "00713.TW (元大台灣高息低波)": "00713.TW",
    "VOO (Vanguard 標普500)": "VOO",
    "QQQ (Invesco 納斯達克100)": "QQQ",
    "VT (Vanguard 全世界股票)": "VT",
}

selected_labels = st.multiselect(
    "📌 快速勾選常用 ETF（可複選）",
    options=list(PRESET_ETFS.keys()),
    default=["00961.TW (FT臺灣永續高息)", "0050.TW (元大台灣50)"]
)

custom_tickers_input = st.text_input(
    "✍️ 額外手動輸入其他股號（選填，多檔請用半形逗號 , 隔開）",
    value="",
    placeholder="例如：2330.TW, AAPL, NVDA",
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

# 根據選擇的快捷按鈕自動計算起始日
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
# 📊 3. 核心計算與疊圖引擎
# ==========================================
if st.button("🚀 開始計算與疊圖比較", type="primary", use_container_width=True):
    # 合併「快捷勾選」與「手動輸入」的股號，並維持順序去除重複
    selected_tickers = [PRESET_ETFS[label] for label in selected_labels]
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
                    st.warning(f"⚠️ 找不到 **{ticker}** 的資料，已自動略過（請確認股號或 .TW 後綴）。")
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

                # 取得首尾交易日與價格
                start_actual_date = series_close.index
                end_actual_date = series_close.index[-1]
                start_price = float(series_close.iloc)
                end_price = float(series_close.iloc[-1])

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
        # 📈 4. 顯示比較總表、累積報酬疊圖與水下圖
        # ==========================================
        if summary_list:
            st.divider()
            st.subheader("🏆 區間報酬與風險比較總表")
            df_summary = pd.DataFrame(summary_list)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)

            st.subheader("📊 累積報酬率走勢疊圖（%）")
            st.caption("註：所有標的皆以各自區間首日為基準（0%），可直觀比較相對漲跌幅表現")
            df_roi_chart = pd.DataFrame(roi_series_dict)
            st.line_chart(df_roi_chart)

            st.subheader("🌊 回撤走勢水下圖（Underwater Plot, %）")
            st.caption("註：0% 代表創新高，數值越負代表距離前波高點跌得越深，可比較抗跌與解套速度")
            df_dd_chart = pd.DataFrame(drawdown_series_dict)
            st.line_chart(df_dd_chart)


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

                # 取得首尾交易日與價格
                start_actual_date = series_close.index[0]
                end_actual_date = series_close.index[-1]
                start_price = float(series_close.iloc[0])
                end_price = float(series_close.iloc[-1])

                # 計算總報酬率 (ROI) 與年化報酬率 (CAGR)
                roi = (end_price / start_price - 1) * 100
                holding_days = (end_actual_date - start_actual_date).days
                cagr = ((end_price / start_price) ** (365 / holding_days) - 1) * 100 if holding_days > 0 else 0.0

                # 計算最大回撤 (Max Drawdown, MDD)
                rolling_max = series_close.cummax()
                drawdown = (series_close - rolling_max) / rolling_max
                max_drawdown = float(drawdown.min()) * 100

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

                # 計算每日累積報酬率 (%)，讓所有股票從 0% 起跑方便疊圖
                cumulative_roi = (series_close / start_price - 1) * 100
                roi_series_dict[ticker] = cumulative_roi

        # ==========================================
        # 📈 3. 顯示比較總表與走勢疊圖
        # ==========================================
        if summary_list:
            st.divider()
            st.subheader("🏆 區間報酬與風險比較總表")
            df_summary = pd.DataFrame(summary_list)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)

            st.subheader("📊 累積報酬率走勢疊圖（%）")
            st.caption("註：所有標的皆以各自區間首日為基準（0%），可直觀比較相對漲跌幅表現")
            df_chart = pd.DataFrame(roi_series_dict)
            st.line_chart(df_chart)
