# etf_config.py

ETF_NAMES = {
    "0050.TW": "元大台灣50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息",
    "00919.TW": "群益台灣精選高息", "00713.TW": "元大台灣高息低波", "00961.TW": "FT臺灣永續高息",
    # 👈 在這裡貼上你完整的 ETF_NAMES 字典內容
}

BENCHMARK_OPTIONS = {
    "無（不顯示基準）": None,
    "🇹🇼 台灣加權指數 (^TWII - 不含息)": "^TWII",
    "🇹🇼 0050 元大台灣50 (含息大盤替代)": "0050.TW",
    "🇺🇸 美國標普 500 (^GSPC)": "^GSPC",
    "🇺🇸 美國那斯達克 100 (^NDX)": "^NDX",
}

ROLLING_WINDOWS = {
    "半年 (6M)": {"days": 126, "years": 0.5},
    "1 年 (1Y)": {"days": 252, "years": 1.0},
    "3 年 (3Y)": {"days": 756, "years": 3.0},
    "5 年 (5Y)": {"days": 1260, "years": 5.0},
}

def format_label(ticker: str) -> str:
    code = ticker.replace(".TW", "").replace(".TWO", "")
    name = ETF_NAMES.get(ticker, "")
    return f"{code} {name}".strip()

def get_categorized_etfs():
    market_cap = [k for k in ["0050.TW", "009816.TW"] if k in ETF_NAMES]
    active = [k for k in ETF_NAMES if k.endswith("A.TW")]
    high_div = [k for k in ETF_NAMES if k not in market_cap and k not in active]
    return market_cap, high_div, active
