import math
import random
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# サイドバーを折りたためるように設定
st.set_page_config(
    page_title="リアルタイム株価分析ダッシュボード",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 【デザイン】視認性に優れたモダン・ダークテーマ
THEME = {
    "bg": "#0f172a",
    "panel": "#1e293b",
    "panel_2": "#334155",
    "accent": "#38bdf8",     # チャートや強調用のスカイブルー
    "accent_2": "#22c55e",   # 上昇時のグリーン
    "muted": "#cbd5e1",      # 文字をより明るいグレーに
    "warning": "#eab308",
    "danger": "#ef4444",     # 下落時のレッド
    "text": "#ffffff",       # 完全な白
}

# 日本の主要銘柄カタログ
CATALOG = pd.DataFrame(
    [
        {"code": "7203", "name": "トヨタ自動車", "tag": "#自動車"},
        {"code": "6758", "name": "ソニーグループ", "tag": "#エンタメ"},
        {"code": "9984", "name": "ソフトバンクグループ", "tag": "#AI"},
        {"code": "9432", "name": "日本電信電話", "tag": "#通信"},
        {"code": "6861", "name": "キーエンス", "tag": "#製造"},
        {"code": "7974", "name": "任天堂", "tag": "#ゲーム"},
    ]
)

# ランキングに表示するトレンドキーワード
TAG_MAP = {
    "#AI・半導体": ["9984", "#8b5cf6"],
    "#自動車・EV": ["7203", "#3b82f6"],
    "#円安・為替": ["", "#eab308"],       # ニュース専用のフリーワード
    "#エンタメ": ["6758", "#ec4899"],
    "#ゲーム": ["7974", "#10b981"],
    "#高配当・増配": ["", "#f97316"],     # ニュース専用のフリーワード
}

GLOSSARY = {
    "株価": "1株あたりの値段です。買いたい人と売りたい人のバランスでリアルタイムに変動します。",
    "出来高": "期間中に成立した売買の総数です。市場の注目度や流動性の高さを測る指標になります。",
    "移動平均線": "過去の一定期間の株価の平均値を結んだ線です。トレンドの方向性を探るのに用います。",
    "前日比": "前日の取引終了時の価格（終値）と現在の価格を比較した差額です。",
    "ボラティリティ": "価格の変動率の大きさです。これが高いほど値動きが激しくリスクが高めになります。",
}

# 全20問の株・投資クイズ
QUIZ = [
    {"question": "出来高（ボリューム）の説明として最も適切なものはどれ？", "choices": ["その期間中に売買が成立した株数", "1株あたりの配当金の額", "企業の純利益の総額", "現在の株主の総人数"], "answer": 0, "explain": "出来高は、市場でどれだけ活発に取引されたかを示す重要な指標です。"},
    {"question": "短期の移動平均線が長期の移動平均線を下から上に突き抜ける現象（ゴールデンクロス）は何を示唆する？", "choices": ["買いのサイン（上昇トレンドへの転換）", "売りのサイン（下落トレンドへの転換）", "会社が倒産する危機", "配当金が減額される予兆"], "answer": 0, "explain": "短期的な勢いが長期的な平均を上回るため、一般的に上昇への転換（買いサイン）とされます。"},
    {"question": "デッドクロスとはどのような状態を指す言葉？", "choices": ["短期移動平均線が長期移動平均線を上から下へ突き抜けること", "株価が前日比でストップ高になること", "出来高が急激にゼロになること", "決算発表で赤字が出ること"], "answer": 0, "explain": "デッドクロスは一般的に「売りのサイン（下落トレンドへの転換）」として知られています。"},
    {"question": "PER（株価収益率）は何を判断するための指標？", "choices": ["株価が企業の利益に対して割安か割高か", "会社の社員数がどれくらい多いか", "企業の借金がどれくらいあるか", "1日あたりの最大売買株数"], "answer": 0, "explain": "PERは「株価÷1株あたり純利益」で計算され、数字が低いほど割安と評価されます。"},
    {"question": "PBR（株価純資産倍率）が1倍を下回るというのはどういう状態？", "choices": ["会社の解散価値よりも株価が安い（割安）", "株価が絶対に上がらない状態", "企業が今すぐ倒産する状態", "配当金が10倍になる状態"], "answer": 0, "explain": "PBR1倍割れは、企業が持つ純資産価値よりも株価が安く評価されている割安な状態です。"},
    {"question": "配当利回りの正しい計算式はどれ？", "choices": ["（1株あたり配当金 ÷ 株価） × 100", "（株価 ÷ 1株あたり配当金） × 100", "（売上高 ÷ 純利益） × 100", "（出来高 ÷ 株式総数） × 100"], "answer": 0, "explain": "投資した金額（株価）に対して、年間どれくらいの割合で配当金がもらえるかを示します。"},
    {"question": "株式市場において「損切り（ロスカット）」を行う最大の目的は？", "choices": ["損失の拡大を一定ラインで防ぐため", "税金をゼロにするため", "必ず配当金をもらうため", "証券会社の口座を凍結させないため"], "answer": 0, "explain": "思惑と反対に動いた際、致命的な傷を負う前に小さな損失で撤退することは長期生存で最も重要です。"},
    {"question": "「成行（なりゆき）注文」の特徴として正しいものはどれ？", "choices": ["価格を指定せず、いくらでもいいのですぐに買いたい（売りたい）注文", "自分で買いたい上限価格をミリ単位で指定する注文", "来週の月曜日にしか成立しない注文", "証券会社に電話しないと出せない注文"], "answer": 0, "explain": "成行注文は「価格より成立の速さを優先」する注文方法で、指値注文より優先して約定します。"},
    {"question": "「指値（さしね）注文」のメリットはどれ？", "choices": ["自分が指定した価格（またはそれより有利な価格）でしか成立しない", "必ず1秒以内に取引が成立する", "株価が10倍になる保証がある", "取引手数料が絶対に無料になる"], "answer": 0, "explain": "指値注文は高値掴みを防げる反面、指定価格まで株価が届かなかった場合は取引が成立しないデメリットもあります。"},
    {"question": "日本の証券取引所（東証）で、通常の株取引ができる時間は平日の何時から何時まで？（昼休み除く）", "choices": ["9:00 〜 15:30", "8:00 〜 17:00", "10:00 〜 16:00", "24時間いつでも"], "answer": 0, "explain": "東京証券取引所（東証）は長年15:00終了でしたが、2024年11月5日より「15:30」に30分延伸されました。"},
    {"question": "株の日足チャート（ローソク足）で、始値よりも終値が高く終わったローソク足のことを何と呼ぶ？", "choices": ["陽線（ようせん）", "陰線（いんせん）", "十字線（じゅうじせん）", "ゴールデン足"], "answer": 0, "explain": "値上がりして終わった日は「陽線」（多くは赤や白）、値下がりして終わった日は「陰線」（青や黒）で表されます。"},
    {"question": "ローソク足の「上ヒゲ」が非常に長い形が出現したとき、一般的な解釈として適切なのは？", "choices": ["高値まで上がったものの、強い売り戻しに押された（高値圏なら反落のシグナル）", "これからストップ高に向けて急上昇する合図", "市場の取引時間が残り1分である合図", "出来高が完全にゼロになった証拠"], "answer": 0, "explain": "上ヒゲは「買い上げた勢いよりも、売り戻す勢いが強かった」ことを示すため、上昇トレンドの天井圏で出ると下落転換の警戒サインとなります。"},
    {"question": "企業の決算発表後に、業績予想を従来の数字より高く引き上げることを何と言う？", "choices": ["上方修正（じょうほうしゅうせい）", "下方修正（かほうしゅうせい）", "株式分割（かぶしきぶんかつ）", "TOB（株式公開買付）"], "answer": 0, "explain": "上方修正が発表されると、企業の価値が見直されて株価が好感（急上昇）しやすい傾向があります。"},
    {"question": "1つの銘柄だけでなく、複数の異なる企業や資産に分けて投資を行う考え方を何と呼ぶ？", "choices": ["分散投資", "集中投資", "信用買い", "インサイダー取引"], "answer": 0, "explain": "「卵を一つのカゴに盛るな」という格言があるように、分散投資はリスクを軽減するための基本手法です。"},
    {"question": "日本株を通常の現物取引で買う場合、原則として何株単位（単元株）で取引するのが基本？", "choices": ["100株単位", "1株単位", "1,000株単位", "10株単位"], "answer": 0, "explain": "現在の日本株は証券取引所のルールで「100株 = 1単元」に統一されています（※ミニ株サービス除く）。"},
    {"question": "企業の株価が1日で変動できる上限（これ以上上がらない価格）のことを何と言う？", "choices": ["ストップ高", "ストップ安", "サーキットブレーカー", "年初来高値"], "answer": 0, "explain": "株価の異常な過熱を防ぐため、前日終値を基準とした制限値幅の上限に達すると「ストップ高」となり、その日はそれ以上上がらなくなります。"},
    {"question": "チャート分析において、過去に株価が何度も下げ止まった下限の価格ラインのことを何と言う？", "choices": ["下値支持線（サポートライン）", "上値抵抗線（レジスタンスライン）", "トレンドライン", "移動平均線"], "answer": 0, "explain": "「この価格帯になると買いが入る」という目安になるラインで、ここを割り込むとさらに急落する危険があります。"},
    {"question": "企業が利益の一部を現金として株主に還元するお金のことを何と呼ぶ？", "choices": ["配当金", "株主優待", "キャピタルゲイン", "譲渡益"], "answer": 0, "explain": "企業の業績や方針によって年に1〜2回、保有株数に応じて現金（配当金）が支払われます。"},
    {"question": "投資家が自らの手で企業を調査せず、株価指数（日経平均など）と同じ動きを目指す投資信託を何と言う？", "choices": ["インデックスファンド", "アクティブファンド", "ヘッジファンド", "ベンチャーキャピタル"], "answer": 0, "explain": "インデックスファンドは市場全体の平均的な成長を享受でき、手数料（信託報酬）も低いため初心者にも人気です。"},
    {"question": "株式市場において「ボラティリティが高い」と表現された場合、どのような状況を意味する？", "choices": ["価格の上下のブレ幅が非常に大きい", "株価が絶対に1円も動かない", "すべての株がストップ高になっている", "証券取引所のシステムが停止している"], "answer": 0, "explain": "ボラティリティ（変動率）が高い時は、短期間で大きな利益を得られる可能性がある一方、大損失を被るリスクも高まります。"},
]


def init_state() -> None:
    defaults = {
        "selected_screen": "メインダッシュボード",
        "selected_stock": "",                  
        "selected_period": "3ヶ月",
        "selected_tags": [],
        "compare_codes": ["7203", "6758"],
        "quiz_current_q": random.choice(QUIZ),
        "news_page": 0,
        "news_keyword": "",  # ニュース検索用のキーワード状態
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def period_to_yf_param(period: str) -> str:
    mapping = {
        "1週間": "5d",
        "1ヶ月": "1mo",
        "3ヶ月": "3mo",
        "半年": "6mo",
        "1年": "1y",
        "3年": "3y",
        "5年": "5y",
    }
    return mapping.get(period, "3mo")


@st.cache_data(ttl=86400, show_spinner=False)
def get_stock_name(code: str) -> str:
    if not code:
        return ""
    
    row = CATALOG.loc[CATALOG["code"] == str(code)]
    if not row.empty:
        return str(row.iloc[0]["name"])
    
    try:
        ticker = f"{code}.T"
        stock = yf.Ticker(ticker)
        name = stock.info.get("longName") or stock.info.get("shortName")
        if name:
            return str(name)
    except Exception:
        pass
        
    return str(code)


def stock_label(code: str) -> str:
    if not code:
        return "未選択（検索してください）"
    name = get_stock_name(code)
    return f"{code} {name}" if name != code else str(code)


def find_stock(query: str) -> str | None:
    cleaned = query.strip()
    if not cleaned:
        return None
    if len(cleaned) == 4:
        return cleaned.upper()
        
    hits = CATALOG[
        CATALOG["name"].str.contains(cleaned, case=False, na=False)
        | CATALOG["tag"].str.contains(cleaned, case=False, na=False)
    ]
    if not hits.empty:
        return str(hits.iloc[0]["code"])
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def load_stock_data(code: str, period: str) -> pd.DataFrame:
    if not code:
        return pd.DataFrame()
    yf_period = period_to_yf_param(period)
    ticker = f"{code}.T"
    
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=yf_period)
        if df.empty:
            return pd.DataFrame()
            
        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        
        df["MA5"] = df["Close"].rolling(5).mean()
        df["MA25"] = df["Close"].rolling(25).mean()
        df["Return"] = df["Close"].pct_change().fillna(0)
        df["Volatility"] = df["Return"].rolling(10).std().fillna(0)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_real_news(keyword: str) -> list[dict]:
    all_news = []
    seen_links = set()
    name = get_stock_name(keyword) if keyword else ""
    
    if keyword:
        try:
            if name and name != keyword:
                if re.match(r'^[A-Za-z0-9\s\-\&\.]+$', name) and len(name) > 8:
                    query_str = f"{keyword} 株 site:yahoo.co.jp"
                else:
                    query_str = f"{name} OR {keyword} 株 site:yahoo.co.jp"
            else:
                query_str = f"{keyword} site:yahoo.co.jp"
                
            encoded_query = urllib.parse.quote(query_str)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"
            
            req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as response:
                xml_data = response.read()
                
            root = ET.fromstring(xml_data)
            for item in root.findall(".//item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date_str = item.findtext("pubDate", "")
                source = item.find("source").text if item.find("source") is not None else "Yahoo!ニュース"
                
                if link and link not in seen_links:
                    seen_links.add(link)
                    try:
                        dt = datetime.strptime(pub_date_str[:25], "%a, %d %b %Y %H:%M:%S")
                        time_display = dt.strftime("%Y/%m/%d %H:%M")
                        ts = dt.timestamp()
                    except Exception:
                        time_display = "最新ニュース"
                        ts = datetime.now().timestamp()
                        
                    all_news.append({
                        "time": time_display,
                        "timestamp": ts,
                        "title": title,
                        "body": source,
                        "url": link
                    })
        except Exception:
            pass

        return sorted(all_news, key=lambda x: x["timestamp"], reverse=True)

    try:
        rss_url = "https://news.yahoo.co.jp/rss/topics/business.xml"
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date_str = item.findtext("pubDate", "")
            
            if link and link not in seen_links:
                seen_links.add(link)
                try:
                    dt = datetime.strptime(pub_date_str[:25], "%a, %d %b %Y %H:%M:%S")
                    time_display = dt.strftime("%Y/%m/%d %H:%M")
                    ts = dt.timestamp()
                except Exception:
                    time_display = "最新ニュース"
                    ts = datetime.now().timestamp()
                    
                all_news.append({
                    "time": time_display,
                    "timestamp": ts,
                    "title": title,
                    "body": "Yahoo!ニュース (経済・市場)",
                    "url": link
                })
    except Exception:
        all_news.append({
            "time": datetime.now().strftime("%Y/%m/%d %H:%M"),
            "timestamp": datetime.now().timestamp(),
            "title": "日本の株式市場・最新経済トピックスはこちらから確認できます",
            "body": "Yahoo!ニュース 経済総合",
            "url": "https://news.yahoo.co.jp/categories/business"
        })
        
    return sorted(all_news, key=lambda x: x["timestamp"], reverse=True)


def get_latest_metrics(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 2:
        return {"current": 0, "open": 0, "high": 0, "low": 0, "volume": 0, "change": 0, "change_rate": 0}
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    return {
        "current": float(latest["Close"]),
        "open": float(latest["Open"]),
        "high": float(latest["High"]),
        "low": float(latest["Low"]),
        "volume": int(latest["Volume"]),
        "change": float(latest["Close"] - prev["Close"]),
        "change_rate": float((latest["Close"] / prev["Close"] - 1) * 100),
    }


def make_comment(df: pd.DataFrame) -> tuple[str, str]:
    if df.empty or len(df) < 5:
        return "データ不足", "分析に必要な日数が不足しています。"
    latest = df.iloc[-1]
    ma5 = latest.get("MA5")
    ma25 = latest.get("MA25")
    change_rate = latest.get("Return", 0) * 100
    volatility = df["Volatility"].iloc[-1] * 100

    if not math.isnan(ma5) and not math.isnan(ma25) and ma5 > ma25:
        return "良い傾向", "短期の移動平均線が長期を上回るゴールデンクロス状態です。上昇トレンドの可能性があります。"
    if change_rate >= 2.5:
        return "急上昇中", "直近の単日上昇率が高く、市場で買いが強まっています。"
    if change_rate <= -2.5:
        return "下落注意", "直近で大きく売り込まれています。押し目か急落かの極め見が必要です。"
    if volatility >= 3.5:
        return "乱高下", "価格のブレ幅（ボラティリティ）が拡大しています。リスク管理を徹底してください。"
    return "保ち合い", "上値も下値も限定的で、方向感を探る小動きな展開です。"


def apply_style() -> None:
    st.markdown(
        f"""
        <style>
            div.block-container {{
                padding-top: 1.5rem !important;
                padding-bottom: 2rem !important;
            }}
            
            .stApp {{
                background-color: {THEME['bg']};
                color: {THEME['text']} !important;
            }}
            
            [data-testid="stMain"] *, 
            [data-testid="stMarkdownContainer"] *, 
            .stTabs *, 
            div[data-testid="stExpander"] *, 
            div[data-testid="stRadio"] *, 
            div[data-testid="stCheckbox"] label span {{
                color: #ffffff !important;
            }}
            
            div[data-testid="stDataFrame"] div {{
                color: #ffffff !important;
            }}
            
            button[data-baseweb="tab"] p {{
                color: #ffffff !important;
                font-weight: 600 !important;
            }}
            
            section[data-testid="stSidebar"] {{
                background-color: #0b1120;
                border-right: 1px solid #1e293b;
            }}
            section[data-testid="stSidebar"],
            section[data-testid="stSidebar"] h1,
            section[data-testid="stSidebar"] h2,
            section[data-testid="stSidebar"] h3,
            section[data-testid="stSidebar"] p,
            section[data-testid="stSidebar"] span,
            section[data-testid="stSidebar"] label,
            section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] *,
            section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] * {{
                color: #ffffff !important;
            }}
            section[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] span {{
                color: #f8fafc !important;
                font-weight: 500;
            }}
            
            .hero {{
                padding: 1.2rem 1.5rem;
                border: 1px solid #334155;
                border-radius: 14px;
                background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
                margin-top: 0 !important;
                margin-bottom: 1rem !important;
            }}
            .hero h1 {{ margin: 0; font-size: 1.7rem; color: #ffffff !important; font-weight: 700; }}
            .hero p {{ margin: 0.3rem 0 0 0; color: #cbd5e1 !important; font-size: 0.9rem; }}
            
            .custom-panel {{
                padding: 1.2rem 1.5rem;
                border-radius: 10px;
                background-color: {THEME['panel']};
                border: 1px solid {THEME['panel_2']};
                margin-top: 0 !important;
                margin-bottom: 1rem !important;
            }}
            
            .small-title {{ font-size: 0.85rem; color: #cbd5e1 !important; font-weight: 600; }}
            .metric-card {{
                padding: 1.2rem;
                border-radius: 10px;
                background-color: {THEME['panel']};
                border: 1px solid {THEME['panel_2']};
            }}

            div[data-baseweb="select"] > div {{
                background-color: #1e293b !important;
                color: #ffffff !important;
                border: 1px solid #334155 !important;
            }}
            div[data-baseweb="select"] span {{
                color: #ffffff !important;
            }}
            ul[data-baseweb="menu"] li {{
                background-color: #1e293b !important;
                color: #ffffff !important;
            }}

            div[data-baseweb="input"] > div {{
                background-color: #1e293b !important;
                color: #ffffff !important;
                border: 1px solid #334155 !important;
            }}
            div[data-baseweb="input"] input {{
                background-color: #1e293b !important;
                color: #ffffff !important;
            }}
            
            button[kind="secondary"] {{
                background-color: #1e293b !important;
                color: #ffffff !important;
                border: 1px solid #334155 !important;
            }}
            button[kind="secondary"]:hover {{
                border: 1px solid #38bdf8 !important;
                color: #38bdf8 !important;
            }}
            button[kind="secondary"] p {{
                color: inherit !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def render_metric_row(metrics: dict) -> None:
    cols = st.columns(4)
    color = THEME["accent_2"] if metrics["change"] >= 0 else THEME["danger"]
    
    items = [
        ("現在株価 (終値)", f"{metrics['current']:,.1f} 円", f"前日比 {metrics['change']:+,.1f} 円 ({metrics['change_rate']:+.2f}%)"),
        ("始値", f"{metrics['open']:,.1f} 円", "本日のセッション開始価格"),
        ("高値 / 安値", f"{metrics['high']:,.1f} / {metrics['low']:,.1f} 円", "当日の値幅レンジ"),
        ("当日の出来高", f"{metrics['volume']:,} 株", "取引の活発度"),
    ]
    for col, (label, value, note) in zip(cols, items):
        with col:
            note_style = f"color:{color} !important;font-weight:600;" if "前日比" in note else "color:#cbd5e1 !important;"
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="small-title">{label}</div>
                    <div style="font-size:1.6rem;font-weight:700;color:#ffffff;margin-top:0.3rem;">{value}</div>
                    <div style="font-size:0.85rem;{note_style}margin-top:0.2rem;">{note}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_dashboard() -> None:
    render_header("メインダッシュボード (リアルタイム版)", "yfinanceから直接取得した生の株価・チャート・指標を表示しています。")
    
    st.markdown("<h3 style='color:#38bdf8 !important; margin-top:0; margin-bottom:0.4rem;'>🔍 銘柄・期間の変更</h3>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])
    with col1:
        query = st.text_input(
            "企業名・コード・タグで検索", 
            value=st.session_state.selected_stock,
            placeholder="例: トヨタ, パナソニック, 6752, #AI"
        )
    with col2:
        period_options = ["1週間", "1ヶ月", "3ヶ月", "半年", "1年", "3年", "5年"]
        current_idx = period_options.index(st.session_state.selected_period) if st.session_state.selected_period in period_options else 2
        period = st.selectbox("表示期間", period_options, index=current_idx)
    with col3:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True) 
        if st.button("更新・分析する", use_container_width=True, type="primary"):
            stock_code = find_stock(query)
            if stock_code is None:
                if len(query) == 4:
                    stock_code = query.upper()
                elif query == "":
                    stock_code = ""
                else:
                    st.error("見つかりませんでした。")
            
            st.session_state.selected_stock = stock_code
            st.session_state.selected_period = period
            st.session_state.news_keyword = stock_code
            st.session_state.news_page = 0
            st.success("適用しました！")
            st.rerun()
    with col4:
        st.markdown("<div style='height: 1.85rem;'></div>", unsafe_allow_html=True) 
        if st.button("クリア", use_container_width=True):
            st.session_state.selected_stock = ""
            st.session_state.news_keyword = ""
            st.session_state.news_page = 0
            st.rerun()
            
    st.write("---")

    code = st.session_state.selected_stock
    
    if not code:
        st.info("👈 上のボックスから検索したい銘柄（例: パナソニック, 6752, トヨタ）を入力して「更新・分析する」を押してください！")
        return

    name = get_stock_name(code)
    df = load_stock_data(code, st.session_state.selected_period)
    
    if df.empty:
        st.error("ヤフーファイナンスから株価データを取得できませんでした。コードが正しいか確認してください。")
        return

    metrics = get_latest_metrics(df)
    render_metric_row(metrics)

    st.divider()
    left, right = st.columns([2, 1])
    with left:
        st.markdown(f"<h2 style='color:#38bdf8 !important; margin-bottom: 0px;'>📊 {code} ： {name}</h2>", unsafe_allow_html=True)
        st.subheader("株価終値チャート")
        st.line_chart(df.set_index("Date")["Close"], color=THEME["accent"])
    with right:
        st.subheader("自動テクニカル診断")
        label, message = make_comment(df)
        if label in ["注意", "下落注意", "乱高下"]:
            st.warning(f"【{label}】{message}")
        elif label == "良い傾向":
            st.success(f"【{label}】{message}")
        else:
            st.info(f"【{label}】{message}")
        st.metric("最新のボラティリティ", f"{df['Volatility'].iloc[-1] * 100:.2f}%")

    st.divider()
    st.subheader(f"💬 {name} に関する最新の市場ニュース（最新順）")
    news = fetch_real_news(code)
    if not news:
        st.caption("現在この銘柄に関する直近のニュースは見つかりませんでした。")
    else:
        for item in news[:5]:
            with st.chat_message("assistant"):
                st.markdown(f"⏱ **{item['time']}** | 配信元: {item['body']}")
                st.write(f"**{item['title']}**")
                st.link_button("👉 記事を開く（Yahoo!ニュース等）", item["url"])


# 【完全統合】ニュースタイムライン画面にトレンドランキングを組み込む！
def render_news() -> None:
    render_header("ニュースタイムライン", f"Yahoo!等から取得した最新の市場・経済関連の【完全日本語・最新順】ニュースフィードを掲載しています。")
    
    # メイン列（ニュース検索・一覧）と トレンドランキング列（右端）を分割
    col_main, col_gap, col_trend = st.columns([7, 0.5, 3])
    
    with col_main:
        st.markdown("<h3 style='color:#38bdf8 !important; margin-top:0; margin-bottom:0.4rem;'>🔍 ニュース専用キーワード検索</h3>", unsafe_allow_html=True)
        
        scol1, scol2, scol3 = st.columns([4, 1.5, 1])
        with scol1:
            current_kw = st.session_state.news_keyword if "news_keyword" in st.session_state else ""
            query = st.text_input(
                "キーワード（企業名・テーマ・コードなど）", 
                value=current_kw,
                placeholder="例: トヨタ, 半導体, 円安, AI",
                label_visibility="collapsed" # 見栄えを良くするためラベルを非表示に調整
            )
        with scol2:
            if st.button("ニュースを検索", use_container_width=True, type="primary"):
                st.session_state.news_keyword = query
                st.session_state.news_page = 0
                st.rerun()
        with scol3:
            if st.button("クリア", key="clear_news", use_container_width=True):
                st.session_state.news_keyword = ""
                st.session_state.news_page = 0
                st.rerun()
                
        st.write("---")
        
        kw = st.session_state.news_keyword
        
        if kw:
            name = get_stock_name(kw)
            display_kw = f"{kw} {name}" if name and name != kw else kw
            st.markdown(f"<h3 style='color:#38bdf8 !important;'>🔍 「{display_kw}」に関する最新ニュース</h3>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h3 style='color:#22c55e !important;'>🌐 キーワード未指定 ： 「株式市場全体」の最新ニュース</h3>", unsafe_allow_html=True)
        
        news = fetch_real_news(kw)
        if not news:
            st.error("現在ニュースが見つかりませんでした。別のキーワードをお試しください。")
        else:
            items_per_page = 10
            total_pages = max(1, math.ceil(len(news) / items_per_page))
            
            if st.session_state.news_page >= total_pages:
                st.session_state.news_page = 0
                
            start_idx = st.session_state.news_page * items_per_page
            end_idx = start_idx + items_per_page
            current_news = news[start_idx:end_idx]
            
            pcol1, pcol2, pcol3 = st.columns([1, 2, 1])
            with pcol1:
                if st.button("⬅️ 前の10件", disabled=(st.session_state.news_page == 0), use_container_width=True):
                    st.session_state.news_page -= 1
                    st.rerun()
            with pcol2:
                st.markdown(f"<div style='text-align:center; font-weight:700; font-size:1.1rem; padding-top:0.5rem;'>ページ {st.session_state.news_page + 1} / {total_pages} (全 {len(news)} 件中)</div>", unsafe_allow_html=True)
            with pcol3:
                if st.button("次の10件 ➡️", disabled=(st.session_state.news_page >= total_pages - 1), use_container_width=True):
                    st.session_state.news_page += 1
                    st.rerun()
                    
            st.write("")
            
            for idx, item in enumerate(current_news, start=start_idx + 1):
                st.markdown(
                    f"""
                    <div class="custom-panel">
                        <div style="font-size:0.85rem; color:#cbd5e1 !important;">No.{idx} | 配信時刻: <span style="color:#38bdf8 !important; font-weight:600;">{item['time']}</span> | 配信元: {item['body']}</div>
                        <h3 style="margin-top:0.4rem; margin-bottom:0.8rem; color:#ffffff !important;">{item['title']}</h3>
                        <div style="font-size:0.85rem; color:#cbd5e1 !important; margin-bottom:0.5rem;">🔗 リンク先URL: <span style="color:#94a3b8 !important;">{item['url'][:65]}...</span></div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                st.link_button("👉 記事を読む", item["url"], key=f"btn_news_{idx}_{item['timestamp']}")
                st.write("")
                
            st.write("---")
            bcol1, bcol2, bcol3 = st.columns([1, 2, 1])
            with bcol1:
                if st.button("⬅️ 前の10件 ", key="btn_prev_bottom", disabled=(st.session_state.news_page == 0), use_container_width=True):
                    st.session_state.news_page -= 1
                    st.rerun()
            with bcol3:
                if st.button(" 次の10件 ➡️", key="btn_next_bottom", disabled=(st.session_state.news_page >= total_pages - 1), use_container_width=True):
                    st.session_state.news_page += 1
                    st.rerun()

    # 右端にトレンドキーワードランキングを表示
    with col_trend:
        st.markdown("<h3 style='color:#eab308 !important; margin-top:0; margin-bottom: 0.5rem; text-align:center;'>🔥 注目トレンド</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color:#cbd5e1 !important; font-size:0.85rem; text-align:center; margin-bottom:1rem;'>クリックで関連ニュースを検索</p>", unsafe_allow_html=True)
        
        for i, tag in enumerate(TAG_MAP.keys()):
            rank_icon = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"][i] if i < 6 else f"{i+1}位"
            if st.button(f"{rank_icon} {tag}", key=f"trend_rank_{tag}", use_container_width=True):
                st.session_state.news_keyword = tag
                st.session_state.news_page = 0
                st.rerun()


def render_detail() -> None:
    code = st.session_state.selected_stock
    if not code:
        render_header("詳細テクニカル分析", "移動平均線（MA）とボリューム（出来高）を重ねて分析します。")
        st.info("👈 メインダッシュボードから分析したい銘柄を検索してください！")
        return

    name = get_stock_name(code)
    render_header("詳細テクニカル分析", "移動平均線（MA）とボリューム（出来高）を重ねて分析します。")
    st.markdown(f"<h2 style='color:#38bdf8 !important; margin-bottom:0px;'>📊 {code} ： {name}</h2>", unsafe_allow_html=True)
    
    df = load_stock_data(code, st.session_state.selected_period)
    if df.empty:
        st.error("データがありません。")
        return

    show_ma = st.checkbox("移動平均線 (5日 / 25日) をオーバーレイ", value=True)
    show_volume = st.checkbox("下部に出来高チャートを表示", value=True)

    chart_data = df.set_index("Date")[["Close"]].copy()
    if show_ma:
        chart_data["5日平均"] = df.set_index("Date")["MA5"]
        chart_data["25日平均"] = df.set_index("Date")["MA25"]
    
    st.line_chart(chart_data)

    if show_volume:
        st.subheader("出来高の推移")
        st.bar_chart(df.set_index("Date")["Volume"], color="#475569")


def render_compare() -> None:
    render_header("複数銘柄の比較画面", "最大3社を選び、ある時点を100とした場合の『パフォーマンス（騰落率）』を相対比較します。")
    choices = [f"{row.code} {row.name}" for row in CATALOG.itertuples(index=False)]
    selected = st.multiselect("比較対象の銘柄（最大3社）", choices, default=[stock_label(c) for c in st.session_state.compare_codes if c])
    
    codes = [item.split()[0] for item in selected][:3]
    if not codes:
        st.info("上のボックスから企業を選択してください。")
        return

    compare_frames = []
    for code in codes:
        df = load_stock_data(code, st.session_state.selected_period)
        if not df.empty:
            base_val = df["Close"].iloc[0]
            nd = df[["Date", "Close"]].copy()
            nd["相対パフォーマンス (%)"] = (nd["Close"] / base_val) * 100
            nd["銘柄"] = stock_label(code)
            compare_frames.append(nd)

    if compare_frames:
        total_df = pd.concat(compare_frames)
        pivot_df = total_df.pivot(index="Date", columns="銘柄", values="相対パフォーマンス (%)")
        st.line_chart(pivot_df)


def render_glossary() -> None:
    render_header("用語解説ヘルプ", "投資判断や画面内の数字の意味をスムーズに学ぶための機能です。")
    term = st.selectbox("詳しく知りたい用語を選択", list(GLOSSARY.keys()))
    st.markdown(f"### 💡 {term}とは？")
    st.info(GLOSSARY[term])


def render_learning_center() -> None:
    render_header("ラーニング＆クイズ検証", "全20問の厳選投資クイズをランダムで解いて、知識の定着度をテストできます。")
    tab1, tab2 = st.tabs(["💡 基礎知識（用語集）", "🎯 ランダム理解度クイズ (全20問)"])
    
    with tab1:
        for k, v in GLOSSARY.items():
            with st.expander(f"📌 {k}"):
                st.write(v)
                
    with tab2:
        quiz = st.session_state.quiz_current_q
        
        st.markdown(f"<div class='custom-panel'><h3 style='color:#38bdf8 !important; margin-top:0;'>Q. {quiz['question']}</h3></div>", unsafe_allow_html=True)
        
        ans = st.radio("正しいと思う選択肢を1つ選んでください:", quiz["choices"], index=None)
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("この回答で確定する", type="primary", use_container_width=True):
                if ans is None:
                    st.warning("選択肢を選んでからボタンを押してください。")
                else:
                    idx = quiz["choices"].index(ans)
                    if idx == quiz["answer"]:
                        st.success("🎉 素晴らしい！大正解です！")
                        st.balloons()
                    else:
                        st.error("❌ 残念、不正解です...")
                    st.info(f"**【解説】**\n{quiz['explain']}")
        with col2:
            if st.button("🔄 別の問題をランダムで出題する", use_container_width=True):
                remaining_quiz = [q for q in QUIZ if q["question"] != quiz["question"]]
                st.session_state.quiz_current_q = random.choice(remaining_quiz)
                st.rerun()


# サイドバーから「トレンド検索」を削除してスッキリ！
def render_sidebar() -> None:
    st.sidebar.title("📱 画面メニュー")
    screen = st.sidebar.radio(
        "表示する画面を選択",
        ["メインダッシュボード", "ニュースタイムライン", "詳細分析画面", "銘柄比較画面", "用語タッチ解説", "ラーニングセンター"]
    )
    st.session_state.selected_screen = screen
    
    st.sidebar.divider()
    st.sidebar.caption("💡 現在選択中の銘柄")
    st.sidebar.write(f"**銘柄:** {stock_label(st.session_state.selected_stock)}")
    st.sidebar.write(f"**期間:** {st.session_state.selected_period}")


def main() -> None:
    init_state()
    apply_style()
    render_sidebar()

    s = st.session_state.selected_screen
    if s == "メインダッシュボード":
        render_dashboard()
    elif s == "ニュースタイムライン":
        render_news()
    elif s == "詳細分析画面":
        render_detail()
    elif s == "銘柄比較画面":
        render_compare()
    elif s == "用語タッチ解説":
        render_glossary()
    elif s == "ラーニングセンター":
        render_learning_center()


if __name__ == "__main__":
    main()