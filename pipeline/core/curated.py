"""精選存股 25 檔（沿用既有清單）與 ETF 六大分群定義。"""
from __future__ import annotations

# ── 25 檔精選存股清單（沿用 v1 TARGET_STOCKS）──────────────────────────
CURATED_STOCKS: list[dict] = [
    # ETF (6)
    {"code": "0056",  "name": "元大高股息",      "sector": "ETF"},
    {"code": "00878", "name": "國泰永續高股息",  "sector": "ETF"},
    {"code": "00919", "name": "群益台灣精選高息", "sector": "ETF"},
    {"code": "00929", "name": "復華台灣科技優息", "sector": "ETF"},
    {"code": "00900", "name": "富邦特選高股息30", "sector": "ETF"},
    {"code": "00713", "name": "元大台灣高息低波", "sector": "ETF"},
    # 金融保險 (7)
    {"code": "2892",  "name": "第一金",          "sector": "Finance"},
    {"code": "2838",  "name": "聯邦銀",          "sector": "Finance"},
    {"code": "2887",  "name": "台新金",          "sector": "Finance"},
    {"code": "2884",  "name": "玉山金",          "sector": "Finance"},
    {"code": "2886",  "name": "兆豐金",          "sector": "Finance"},
    {"code": "2890",  "name": "永豐金",          "sector": "Finance"},
    {"code": "5880",  "name": "合庫金",          "sector": "Finance"},
    # 營建工程 (2)
    {"code": "2542",  "name": "興富發",          "sector": "Construction"},
    {"code": "5522",  "name": "遠雄",            "sector": "Construction"},
    # 電信公用 (3)
    {"code": "2412",  "name": "中華電",          "sector": "Telecom"},
    {"code": "3045",  "name": "台灣大",          "sector": "Telecom"},
    {"code": "4904",  "name": "遠傳",            "sector": "Telecom"},
    # 食品消費 (3)
    {"code": "1216",  "name": "統一",            "sector": "Food"},
    {"code": "1210",  "name": "大成",            "sector": "Food"},
    {"code": "2912",  "name": "統一超",          "sector": "Food"},
    # 其他穩健龍頭 (4)
    {"code": "9917",  "name": "中保科",          "sector": "Other"},
    {"code": "1102",  "name": "亞泥",            "sector": "Other"},
    {"code": "2347",  "name": "聯強",            "sector": "Other"},
    {"code": "2633",  "name": "台灣高鐵",        "sector": "Other"},
]

CURATED_STOCK_CODES: set[str] = {s["code"] for s in CURATED_STOCKS}

# ── ETF 六大分群（市值型 / 高股息 / 科技AI / 債券 / 海外 / 自訂）────────
ETF_GROUPS: dict[str, str] = {
    "market_cap":    "市值型",
    "high_dividend": "高股息",
    "tech_ai":       "科技 AI",
    "bond":          "債券型",
    "global":        "海外主題",
    "custom":        "自訂追蹤",
}

CURATED_ETFS: list[dict] = [
    # 1. 市值型
    {"code": "0050",   "name": "元大台灣50",            "group": "market_cap",    "tags": ["市值型", "半年配"]},
    {"code": "006208", "name": "富邦台50",              "group": "market_cap",    "tags": ["市值型", "半年配"]},
    {"code": "00692",  "name": "富邦公司治理",          "group": "market_cap",    "tags": ["市值型", "ESG", "半年配"]},
    {"code": "00850",  "name": "元大臺灣ESG永續",       "group": "market_cap",    "tags": ["市值型", "ESG", "季配"]},
    {"code": "00905",  "name": "FT臺灣Smart",           "group": "market_cap",    "tags": ["多因子", "季配"]},
    {"code": "00922",  "name": "國泰台灣領袖50",        "group": "market_cap",    "tags": ["市值型", "半年配"]},
    {"code": "00923",  "name": "群益台ESG低碳50",       "group": "market_cap",    "tags": ["市值型", "低碳", "半年配"]},
    # 2. 高股息
    {"code": "0056",   "name": "元大高股息",            "group": "high_dividend", "tags": ["高股息", "季配", "1/4/7/10"]},
    {"code": "00878",  "name": "國泰永續高股息",        "group": "high_dividend", "tags": ["高股息", "季配", "2/5/8/11"]},
    {"code": "00919",  "name": "群益台灣精選高息",      "group": "high_dividend", "tags": ["高股息", "季配", "3/6/9/12"]},
    {"code": "00713",  "name": "元大台灣高息低波",      "group": "high_dividend", "tags": ["高股息", "低波動", "季配", "3/6/9/12"]},
    {"code": "00915",  "name": "凱基優選高股息30",      "group": "high_dividend", "tags": ["高股息", "季配", "3/6/9/12"]},
    {"code": "00918",  "name": "大華優利高填息30",      "group": "high_dividend", "tags": ["高股息", "季配", "3/6/9/12"]},
    {"code": "00929",  "name": "復華台灣科技優息",      "group": "high_dividend", "tags": ["高股息", "科技", "月配"]},
    {"code": "00939",  "name": "統一台灣高息動能",      "group": "high_dividend", "tags": ["高股息", "月配"]},
    {"code": "00940",  "name": "元大台灣價值高息",      "group": "high_dividend", "tags": ["高股息", "月配"]},
    {"code": "00946",  "name": "群益科技高息成長",      "group": "high_dividend", "tags": ["高股息", "科技", "月配"]},
    {"code": "00943",  "name": "兆豐電子高息等權",      "group": "high_dividend", "tags": ["高股息", "等權重", "月配"]},
    {"code": "00900",  "name": "富邦特選高股息30",      "group": "high_dividend", "tags": ["高股息", "季配"]},
    # 3. 科技 AI（保留既有全數科技/AI ETF）
    {"code": "0052",   "name": "富邦科技",              "group": "tech_ai",       "tags": ["科技", "年配"]},
    {"code": "0053",   "name": "元大電子",              "group": "tech_ai",       "tags": ["科技", "年配"]},
    {"code": "00881",  "name": "國泰台灣科技龍頭",      "group": "tech_ai",       "tags": ["科技", "AI", "半年配"]},
    {"code": "00935",  "name": "野村臺灣創新科技50",    "group": "tech_ai",       "tags": ["科技", "半年配"]},
    {"code": "00947",  "name": "台新臺灣IC設計",        "group": "tech_ai",       "tags": ["IC設計", "季配"]},
    {"code": "00952",  "name": "凱基台灣AI50",          "group": "tech_ai",       "tags": ["AI", "月配"]},
    {"code": "00962",  "name": "台新AI優息動能",        "group": "tech_ai",       "tags": ["AI", "月配"]},
    # 4. 債券型（上櫃 .TWO，官方 TPEx + MoneyDJ 完整支援）
    {"code": "00679B", "name": "元大美債20年",          "group": "bond",          "tags": ["美債", "季配", "2/5/8/11"]},
    {"code": "00687B", "name": "國泰20年美債",          "group": "bond",          "tags": ["美債", "季配", "3/6/9/12"]},
    {"code": "00720B", "name": "元大投資級公司債",      "group": "bond",          "tags": ["投等債", "季配", "1/4/7/10"]},
    {"code": "00751B", "name": "元大AAA至A公司債",      "group": "bond",          "tags": ["投等債", "季配", "3/6/9/12"]},
    {"code": "00937B", "name": "群益ESG投等債20+",      "group": "bond",          "tags": ["投等債", "月配"]},
    {"code": "00933B", "name": "國泰10Y+金融債",        "group": "bond",          "tags": ["金融債", "月配"]},
    # 5. 海外主題（保留既有跨境科技/AI ETF + 美股指數）
    {"code": "00735",  "name": "國泰臺韓科技",          "group": "global",        "tags": ["台韓", "科技", "半年配"]},
    {"code": "00757",  "name": "統一FANG+",             "group": "global",        "tags": ["美股", "科技巨頭"]},
    {"code": "00830",  "name": "國泰費城半導體",        "group": "global",        "tags": ["美股", "半導體", "年配"]},
    {"code": "00851",  "name": "台新全球AI",            "group": "global",        "tags": ["全球", "AI", "年配"]},
    {"code": "00762",  "name": "元大全球AI",            "group": "global",        "tags": ["全球", "AI"]},
    {"code": "00876",  "name": "元大全球5G",            "group": "global",        "tags": ["全球", "5G"]},
    {"code": "00861",  "name": "元大全球未來通訊",      "group": "global",        "tags": ["全球", "通訊"]},
]

CURATED_ETF_MAP: dict[str, dict] = {e["code"]: e for e in CURATED_ETFS}

