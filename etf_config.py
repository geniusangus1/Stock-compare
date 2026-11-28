# etf_config.py

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
    "00985A.TW": "主動野村台灣50", "00987A.TW": "主動台新優勢成長", "00991A.TW": "主動復華未來50",
    "00992A.TW": "主動群益科技創新", "00993A.TW": "主動安聯台灣",
    "00994A.TW": "主動第一金台股優", "00995A.TW": "主動中信台灣卓越",
    "00996A.TW": "主動兆豐台灣豐收", "00999A.TW": "主動野村臺灣高息",
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
