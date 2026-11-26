import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="多檔股票報酬率疊圖比較", page_icon="📈", layout="centered")

st.title("📈 多檔股票區間報酬率疊圖比較")
st.caption("資料來源：Yahoo Finance（已啟用還原股價 auto_adjust 反映含息報酬）")

# ==========================================
# 🛠️ 1. 網頁互動輸入區
# ==========================================
tickers_input = st.text_input(
    "輸入股號（多檔請用半形逗號 , 隔開）",
    value="00961.TW, 0050.TW",
    help="台股上市加 .TW、上櫃加 .TWO，美股直接輸入代號（如 AAPL, NVDA）"
)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("起始日期", value=datetime.date(2026, 5, 27))
with col2:
    end_date = st.date_input("終止日期", value=datetime.date.today())

# ==========================================
# 📊 2. 核心計算與疊圖引擎
# ==========================================
if st.button("🚀 開始計算與疊圖比較", type="primary", use_container_width=True):
    # 解析並清理使用者輸入的多個股號
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    if not tickers:
        st.warning("⚠️ 請至少輸入一檔股票代號！")
    elif start_date >= end_date:
        st.error("⚠️ 終止日期必須晚於起始日期！")
    else:
        fetch_end = end_date + datetime.timedelta(days=1)
        summary_list = []
        roi_series_dict = {}

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
                start_actual_date = series_close.index[0]
                end_actual_date = series_close.index[-1]
                start_price = float(series_close.iloc[0])
                end_price = float(series_close.iloc[-1])

                # 計算總報酬率 (ROI) 與年化報酬率 (CAGR)
                roi = (end_price / start_price - 1) * 100
                holding_days = (end_actual_date - start_actual_date).days
                cagr = ((end_price / start_price) ** (365 / holding_days) - 1) * 100 if holding_days > 0 else 0.0

                # 整理成比較表格列
                summary_list.append({
                    "股票代號": ticker,
                    "起始日": start_actual_date.strftime("%Y-%m-%d"),
                    "起始價": round(start_price, 2),
                    "結束日": end_actual_date.strftime("%Y-%m-%d"),
                    "結束價": round(end_price, 2),
                    "區間總報酬 (%)": round(roi, 2),
                    "年化報酬 CAGR (%)": round(cagr, 2),
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
            st.subheader("🏆 區間報酬率比較總表")
            df_summary = pd.DataFrame(summary_list)
            st.dataframe(df_summary, use_container_width=True, hide_index=True)

            st.subheader("📊 累積報酬率走勢疊圖（%）")
            st.caption("註：所有標的皆以各自區間首日為基準（0%），可直觀比較相對漲跌幅表現")
            df_chart = pd.DataFrame(roi_series_dict)
            st.line_chart(df_chart)
          
