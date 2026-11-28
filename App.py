import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from etf_config import BENCHMARK_OPTIONS, ROLLING_WINDOWS, format_label, get_categorized_etfs
from metrics import calc_period_metrics, calc_rolling_stats, fetch_full_history

st.set_page_config(page_title="多檔 ETF 報酬率與風險比較", page_icon="📈", layout="centered")
st.title("📈 多檔 ETF 區間報酬率與回撤比較")
st.caption("資料來源：Yahoo Finance（已啟用還原股價 auto_adjust 反映含息報酬）")

if "calc_results" not in st.session_state:
    st.session_state.calc_results = None

# 1. 選單與基準線設定
MARKET_CAP_ETFS, HIGH_DIV_ETFS, ACTIVE_ETFS = get_categorized_etfs()

st.markdown("**📌 快速勾選常用 ETF（可跨類別複選）**")
cat_col1, cat_col2, cat_col3 = st.columns(3)
with cat_col1:
    sel_market = st.multiselect("📈 市值型", options=MARKET_CAP_ETFS, default=MARKET_CAP_ETFS[:1], format_func=format_label)
with cat_col2:
    sel_div = st.multiselect("💰 高股息", options=HIGH_DIV_ETFS, default=HIGH_DIV_ETFS[:2], format_func=format_label)
with cat_col3:
    sel_active = st.multiselect("🎯 主動式", options=ACTIVE_ETFS, default=[], format_func=format_label)

in_col1, in_col2 = st.columns([3, 2])
with in_col1:
    custom_tickers_input = st.text_input("✍️ 手動輸入其他股號（半形逗號隔開）", placeholder="例如：2330.TW, VOO, QQQ")
with in_col2:
    bench_choice = st.selectbox("🏁 大盤基準線 (Benchmark)", options=list(BENCHMARK_OPTIONS.keys()), index=1)

# 2. 時間區間設定
today = datetime.date.today()
quick_range = st.radio("⏱️ 快速選擇回測區間", ["近一個月", "近一季", "近半年", "近一年", "今年以來", "自訂區間"], index=4, horizontal=True)
range_days = {"近一個月": 30, "近一季": 90, "近半年": 182, "近一年": 365}
default_start = today - datetime.timedelta(days=range_days[quick_range]) if quick_range in range_days else datetime.date(today.year, 1, 1)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("起始日期", value=default_start)
with col2:
    end_date = st.date_input("終止日期", value=today)

# 3. 執行計算
if st.button("🚀 開始計算與疊圖比較", type="primary", use_container_width=True):
    selected_tickers = sel_market + sel_div + sel_active
    custom_tickers = [t.strip().upper() for t in custom_tickers_input.split(",") if t.strip()]
    tickers = list(dict.fromkeys(selected_tickers + custom_tickers))
    bench_ticker = BENCHMARK_OPTIONS[bench_choice]

    if not tickers:
        st.warning("⚠️ 請至少勾選或輸入一檔股票代號！")
    elif start_date >= end_date:
        st.error("⚠️ 終止日期必須晚於起始日期！")
    else:
        summary_list, roi_dict, dd_dict, rolling_stats_list = [], {}, {}, []
        rolling_curves = {k: {} for k in ROLLING_WINDOWS.keys()}

        calc_queue = [(t, format_label(t)) for t in tickers]
        if bench_ticker and bench_ticker not in tickers:
            bench_label = f"🏁 [基準] {bench_choice.split(' ')[1]}"
            calc_queue.append((bench_ticker, bench_label))
        else:
            bench_label = format_label(bench_ticker) if bench_ticker else None

        with st.spinner("📡 正在抓取歷史資料並計算風險與滾動報酬..."):
            for ticker, display_name in calc_queue:
                full_series = fetch_full_history(ticker)
                if full_series.empty:
                    st.warning(f"⚠️ 找不到 **{display_name}** 的資料，已略過。")
                    continue

                rolling_stats_list.append(calc_rolling_stats(full_series, display_name, rolling_curves))

                mask = (full_series.index.date >= start_date) & (full_series.index.date <= end_date)
                series_close = full_series.loc[mask]
                if len(series_close) < 2:
                    st.warning(f"⚠️ **{display_name}** 在所選區間內交易日不足 2 天，已略過區間比較。")
                    continue

                s_row, r_ser, d_ser = calc_period_metrics(series_close, display_name)
                summary_list.append(s_row)
                roi_dict[display_name], dd_dict[display_name] = r_ser, d_ser

        if summary_list or rolling_stats_list:
            df_roi, df_dd = pd.DataFrame(roi_dict), pd.DataFrame(dd_dict)
            if not df_roi.empty:
                df_roi.index = df_roi.index.strftime("%Y-%m-%d")
                df_dd.index = df_dd.index.strftime("%Y-%m-%d")
            st.session_state.calc_results = {
                "summary": pd.DataFrame(summary_list), "roi": df_roi, "dd": df_dd,
                "rolling_stats": pd.DataFrame(rolling_stats_list),
                "rolling_curves": rolling_curves, "bench_label": bench_label
            }

# 4. 視覺化呈現
def build_chart(df, y_title, bench_label, active_date=None, title=""):
    fig = go.Figure()
    for col in df.columns:
        line_style = dict(width=2.8, dash="dot", color="#888888") if col == bench_label else dict(width=2.3)
        fig.add_trace(go.Scatter(x=df.index, y=df[col], mode="lines", name=col, line=line_style, hovertemplate="%{y:+.2f}%"))
    fig.add_hline(y=0, line_width=1.2, line_dash="dash", line_color="#FF4B4B" if not active_date else "gray", opacity=0.6)
    if active_date:
        fig.add_vline(x=active_date, line_width=1.5, line_dash="solid", line_color="#FF4B4B")
    fig.update_layout(
        title=title, hovermode="x unified", xaxis=dict(title="", fixedrange=True),
        yaxis=dict(title=y_title, ticksuffix="%", fixedrange=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=45 if title else 35, b=10), height=360
    )
    return fig

if st.session_state.calc_results is not None:
    res = st.session_state.calc_results
    df_summary, df_roi, df_dd = res["summary"], res["roi"], res["dd"]
    df_rolling_stats, rolling_curves, bench_label = res["rolling_stats"], res["rolling_curves"], res["bench_label"]

    if not df_summary.empty:
        st.divider()
        etf_only = df_summary[~df_summary["標的"].str.startswith("🏁")]
        if len(etf_only) >= 2:
            w1, w2, w3 = st.columns(3)
            b_roi = etf_only.loc[etf_only["總報酬 (%)"].idxmax()]
            b_mdd = etf_only.loc[etf_only["最大回撤 (%)"].idxmax()]
            b_shp = etf_only.loc[etf_only["夏普 Sharpe"].idxmax()]
            w1.metric("🥇 區間報酬王", b_roi["標的"], f"{b_roi['總報酬 (%)']:+.2f}%")
            w2.metric("🛡️ 區間抗跌王", b_mdd["標的"], f"MDD {b_mdd['最大回撤 (%)']:.2f}%", delta_color="off")
            w3.metric("⚖️ CP值之王 (Sharpe)", b_shp["標的"], f"{b_shp['夏普 Sharpe']:.2f}")

        st.subheader("🏆 區間報酬與風險比較總表")        
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        with st.expander("📖 風險指標怎麼看？（Sharpe / Sortino / Calmar 白話說明）"):
            st.markdown("""
            * **夏普比率 (Sharpe)**：`(年化平均報酬 - 1.5%) / 年化總波動度` — 衡量每承受一單位「總波動」換到的超額報酬（大於 **1** 屬優秀）。
            * **索提諾比率 (Sortino)**：`(年化平均報酬 - 1.5%) / 年化下檔波動度` — 只懲罰「下跌」波動、不把大漲算成風險，適合評估飆漲快或高股息抗跌標的。
            * **卡瑪比率 (Calmar)**：`年化報酬 CAGR / |最大回撤 MDD|` — 衡量承受「歷史最痛那一刀虧損」所換來的年化報酬，越高代表抗跌且解套越快。
            """)

        st.divider()
        st.subheader("🔍 大拇指連續滑動查價器")
        avail_dates = df_roi.index.tolist()
        sel_date = st.select_slider("👈 左右拖曳滑桿，即時連動下方圖表：", options=avail_dates, value=avail_dates[-1])

        row_roi, row_dd = df_roi.loc[sel_date], df_dd.loc[sel_date]
        cols = st.columns(min(len(df_roi.columns), 3))
        for idx, name in enumerate(df_roi.columns):
            v_roi, v_dd = row_roi[name], row_dd[name]
            dd_txt = ("創波段新高 (0%)" if round(v_dd, 2) == 0 else f"距前高 {v_dd:.2f}%") if pd.notna(v_dd) else ""
            with cols[idx % 3]:
                st.metric(label=f"{name} ({sel_date})", value=f"{v_roi:+.2f}%" if pd.notna(v_roi) else "無資料", delta=dd_txt, delta_color="off")

        st.subheader("📊 累積報酬率走勢疊圖（%）")
        st.plotly_chart(build_chart(df_roi, "累積報酬率 (%)", bench_label, sel_date), use_container_width=True, config={"displayModeBar": False})

        st.subheader("🌊 回撤走勢水下圖（Underwater Plot, %）")
        st.plotly_chart(build_chart(df_dd, "回撤幅度 (%)", bench_label, sel_date), use_container_width=True, config={"displayModeBar": False})

    if not df_rolling_stats.empty:
        st.divider()
        st.subheader("🔄 歷史滾動報酬與正報酬勝率（上市以來完整統計）")
        st.caption("💡 半年為累計報酬；1年/3年/5年為年化報酬 (CAGR)。`^TWII` 為不含息指數，含息基準請選 `0050.TW`。")
        st.dataframe(df_rolling_stats, use_container_width=True, hide_index=True)

        with st.expander("📖 什麼是滾動報酬？「勝率」與「高 / 低」怎麼看？"):
            st.markdown("""
            * **為什麼要看滾動報酬？**：一般回測只看單一買賣時間，容易受運氣影響。滾動報酬模擬**「歷史上每一天單筆買進、並死抱活抱剛好滿 N 年後賣出」**的所有平行宇宙結果，能消除挑時間進場的運氣成分。
            * **勝率（正報酬機率）**：在歷史上所有持有滿 N 年的進場時機中，**最終賣出是賺錢（報酬率 > 0%）的機率**。例如「五年勝率 100%」，代表過去任何一天買進（就算買在最高點），只要抱滿 5 年從未賠錢過。
            * **高 / 低（極端年化報酬）**：歷史上運氣最好（買在低點）與最差（買在高點）的**年化報酬率 (CAGR)**。若「五年低」仍是正數，代表這檔標的具備極強的長期修復與抗跌能力。
            """)


        sel_win = st.radio("📈 選擇滾動報酬走勢週期：", options=list(ROLLING_WINDOWS.keys()), index=1, horizontal=True)
        curve_dict = rolling_curves.get(sel_win, {})
        if curve_dict:
            df_roll = pd.DataFrame(curve_dict)
            df_roll.index = df_roll.index.strftime("%Y-%m-%d")
            y_lbl = "累計滾動報酬 (%)" if sel_win == "半年 (6M)" else "年化滾動報酬 CAGR (%)"
            st.plotly_chart(build_chart(df_roll, y_lbl, bench_label, title=f"{sel_win} 滾動報酬率走勢（灰色虛線為基準）"), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info(f"ℹ️ 目前勾選的標的掛牌時間皆未滿 **{sel_win}**，請改選較短週期。")
