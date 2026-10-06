import math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(
	page_title="株価分析UI総合",
	page_icon="📈",
	layout="wide",
	initial_sidebar_state="expanded",
)


THEME = {
	"bg": "#0b1020",
	"panel": "#121a31",
	"panel_2": "#17223f",
	"accent": "#68d391",
	"accent_2": "#63b3ed",
	"text": "#eef2ff",
	"muted": "#b8c1ec",
	"warning": "#f6ad55",
	"danger": "#fc8181",
}


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


TAG_MAP = {
	"#ゲーム": ["7974"],
	"#AI": ["9984", "9432"],
	"#自動車": ["7203"],
	"#エンタメ": ["6758", "7974"],
	"#通信": ["9432"],
	"#製造": ["6861"],
}


GLOSSARY = {
	"株価": "1株あたりの値段です。上がると評価が高く、下がると評価が弱いと考えられます。",
	"出来高": "その日に売買された株数です。多いほど注目度が高い傾向があります。",
	"移動平均線": "一定期間の終値の平均を線でつないだものです。値動きの方向をつかみやすくなります。",
	"前日比": "前日終値と比べてどれだけ増減したかを表します。",
	"ボラティリティ": "価格変動の大きさです。大きいほど値動きが荒いことを意味します。",
}


QUIZ = [
	{
		"question": "出来高として最も近い説明はどれ？",
		"choices": ["その日の売買株数", "1株の配当金", "会社の利益", "株主の人数"],
		"answer": 0,
		"explain": "出来高は、その日にどれだけ株が売買されたかを表します。",
	},
	{
		"question": "移動平均線の役割として適切なのはどれ？",
		"choices": ["値動きの方向を見やすくする", "配当を計算する", "会社の所在地を示す", "税金を減らす"],
		"answer": 0,
		"explain": "短期の上下をならして、トレンドを見やすくするために使います。",
	},
]


def init_state() -> None:
	defaults = {
		"selected_screen": "メインダッシュボード",
		"selected_stock": "7203",
		"selected_period": "3ヶ月",
		"selected_tags": [],
		"compare_codes": ["7203", "6758"],
		"quiz_index": 0,
		"quiz_result": None,
		"selected_term": "株価",
		"news_focus": "トヨタ自動車",
	}
	for key, value in defaults.items():
		st.session_state.setdefault(key, value)
	if st.session_state.selected_screen not in {
		"メインダッシュボード",
		"トレンド検索",
		"ニュースタイムライン",
		"詳細分析画面",
		"銘柄比較画面",
		"用語タッチ解説",
		"ラーニングセンター",
	}:
		st.session_state.selected_screen = "メインダッシュボード"


def seed_from_code(code: str) -> int:
	return sum(ord(ch) for ch in str(code))


def period_to_days(period: str) -> int:
	mapping = {
		"1ヶ月": 30,
		"3ヶ月": 90,
		"半年": 180,
		"1年": 365,
		"3年": 365 * 3,
		"5年": 365 * 5,
	}
	return mapping.get(period, 90)


def stock_label(code: str) -> str:
	row = CATALOG.loc[CATALOG["code"] == code]
	if row.empty:
		return code
	data = row.iloc[0]
	return f'{data["code"]} {data["name"]}'


def find_stock(query: str) -> str | None:
	cleaned = query.strip()
	if not cleaned:
		return None
	if cleaned in set(CATALOG["code"]):
		return cleaned
	hits = CATALOG[
		CATALOG["name"].str.contains(cleaned, case=False, na=False)
		| CATALOG["tag"].str.contains(cleaned, case=False, na=False)
	]
	if not hits.empty:
		return hits.iloc[0]["code"]
	return None


def generate_price_data(code: str, days: int) -> pd.DataFrame:
	rng = np.random.default_rng(seed_from_code(code))
	end_date = pd.Timestamp(datetime.now().date())
	dates = pd.bdate_range(end=end_date, periods=days)
	base = 1000 + (seed_from_code(code) % 2500)
	steps = rng.normal(0.0015, 0.02, len(dates)).cumsum()
	close = base * (1 + steps)
	close = np.maximum(close, 100)
	open_price = close * (1 + rng.normal(0.0, 0.008, len(dates)))
	high = np.maximum(open_price, close) * (1 + rng.random(len(dates)) * 0.02)
	low = np.minimum(open_price, close) * (1 - rng.random(len(dates)) * 0.02)
	volume = (rng.integers(120_000, 900_000, len(dates)) * (1 + np.abs(rng.normal(0, 0.2, len(dates))))).astype(int)

	df = pd.DataFrame(
		{
			"Date": dates,
			"Open": open_price,
			"High": high,
			"Low": low,
			"Close": close,
			"Volume": volume,
		}
	)
	df["MA5"] = df["Close"].rolling(5).mean()
	df["MA25"] = df["Close"].rolling(25).mean()
	df["Return"] = df["Close"].pct_change().fillna(0)
	df["Volatility"] = df["Return"].rolling(10).std().fillna(0)
	return df


@st.cache_data(show_spinner=False)
def load_stock_data(code: str, period: str) -> pd.DataFrame:
	return generate_price_data(code, period_to_days(period))


def get_latest_metrics(df: pd.DataFrame) -> dict:
	latest = df.iloc[-1]
	prev = df.iloc[-2] if len(df) > 1 else latest
	return {
		"current": float(latest["Close"]),
		"open": float(latest["Open"]),
		"high": float(latest["High"]),
		"low": float(latest["Low"]),
		"volume": int(latest["Volume"]),
		"change": float(latest["Close"] - prev["Close"]),
		"change_rate": float((latest["Close"] / prev["Close"] - 1) * 100) if prev["Close"] else 0.0,
	}


def make_comment(df: pd.DataFrame) -> tuple[str, str]:
	latest = df.iloc[-1]
	ma5 = latest.get("MA5")
	ma25 = latest.get("MA25")
	change_rate = latest.get("Return", 0) * 100
	volatility = df["Volatility"].iloc[-1] * 100

	if not math.isnan(ma5) and not math.isnan(ma25) and ma5 > ma25:
		return "良い傾向", "短期移動平均線が長期移動平均線を上回っており、上昇の流れが見えています。"
	if change_rate >= 2:
		return "上昇中", "直近の上昇率が大きく、勢いがあります。"
	if change_rate <= -2:
		return "注意", "直近で大きく下落しています。急な値動きに気をつけてください。"
	if volatility >= 3:
		return "変動大", "値動きが大きめです。短期売買ではリスク管理が重要です。"
	return "安定", "大きな変動は少なく、比較的落ち着いた動きです。"


def news_items(name: str) -> list[dict[str, str]]:
	now = datetime.now()
	return [
		{
			"time": (now - timedelta(minutes=25)).strftime("%m/%d %H:%M"),
			"title": f"{name}の業績見通しに注目が集まる",
			"body": "市場では次の決算発表とガイダンスが注目されています。",
			"url": "https://finance.yahoo.com/",
		},
		{
			"time": (now - timedelta(hours=3)).strftime("%m/%d %H:%M"),
			"title": f"{name}関連のニュースが増加",
			"body": "関連キーワードの検索数が増えており、短期的な関心が高まっています。",
			"url": "https://news.yahoo.co.jp/",
		},
	]


def apply_style() -> None:
	st.markdown(
		f"""
		<style>
			.stApp {{
				background: radial-gradient(circle at top left, #16213e 0%, #0b1020 45%, #080b14 100%);
				color: {THEME['text']};
			}}
			section[data-testid="stSidebar"] {{
				background: linear-gradient(180deg, rgba(18,26,49,0.96), rgba(11,16,32,0.98));
			}}
			.hero {{
				padding: 1.1rem 1.2rem;
				border: 1px solid rgba(255,255,255,0.08);
				border-radius: 20px;
				background: linear-gradient(135deg, rgba(24,34,63,0.9), rgba(18,26,49,0.8));
				box-shadow: 0 18px 45px rgba(0,0,0,0.25);
			}}
			.hero h1 {{ margin: 0; font-size: 2rem; }}
			.hero p {{ margin: 0.35rem 0 0 0; color: {THEME['muted']}; }}
			.panel {{
				padding: 1rem;
				border-radius: 18px;
				background: rgba(18,26,49,0.78);
				border: 1px solid rgba(255,255,255,0.06);
				box-shadow: 0 10px 24px rgba(0,0,0,0.18);
			}}
			.small-title {{ font-size: 0.9rem; color: {THEME['muted']}; letter-spacing: 0.04em; }}
			.metric-card {{
				padding: 0.9rem 1rem;
				border-radius: 16px;
				background: rgba(23,34,63,0.88);
				border: 1px solid rgba(255,255,255,0.06);
			}}
			.tag-pill {{
				display: inline-block;
				padding: 0.35rem 0.7rem;
				margin: 0.15rem 0.25rem 0.15rem 0;
				border-radius: 999px;
				background: rgba(99,179,237,0.15);
				border: 1px solid rgba(99,179,237,0.35);
				color: #dceeff;
				font-size: 0.85rem;
			}}
			div[data-testid="stTextInput"] input,
			div[data-testid="stTextInput"] textarea,
			div[data-testid="stSelectbox"] [data-baseweb="select"],
			div[data-testid="stSelectbox"] [role="combobox"],
			div[data-testid="stSelectbox"] [data-baseweb="select"] *,
			div[data-testid="stMultiSelect"] [data-baseweb="select"] *,
			div[data-testid="stRadio"] label,
			div[data-testid="stCheckbox"] label {{
				color: #ffffff !important;
				-webkit-text-fill-color: #ffffff !important;
			}}
			div[data-testid="stTextInput"] input,
			div[data-testid="stTextInput"] textarea,
			div[data-testid="stSelectbox"] [role="combobox"] {{
				background-color: rgba(23, 34, 63, 0.96) !important;
				border: 1px solid rgba(99, 179, 237, 0.35) !important;
			}}
			div[data-testid="stTextInput"] input::placeholder,
			div[data-testid="stTextInput"] textarea::placeholder {{
				color: rgba(255, 255, 255, 0.65) !important;
			}}
			div[data-baseweb="select"] span,
			div[data-baseweb="select"] div {{
				color: #ffffff !important;
			}}
			button[kind="secondary"] {{
				background: linear-gradient(135deg, #2f5cff, #68d391) !important;
				color: #ffffff !important;
				border: 0 !important;
			}}
			button[kind="secondary"] p {{
				color: #ffffff !important;
			}}
		</style>
		""",
		unsafe_allow_html=True,
	)


def render_header(title: str, subtitle: str) -> None:
	st.markdown(
		f"""
		<div class="hero">
			<h1>{title}</h1>
			<p>{subtitle}</p>
		</div>
		""",
		unsafe_allow_html=True,
	)


def render_metric_row(metrics: dict) -> None:
	cols = st.columns(4)
	items = [
		("現在株価", f"{metrics['current']:,.2f} 円", f"前日比 {metrics['change_rate']:+.2f}%"),
		("始値", f"{metrics['open']:,.2f} 円", "当日開始時の価格"),
		("高値 / 安値", f"{metrics['high']:,.2f} / {metrics['low']:,.2f}", "当日のレンジ"),
		("出来高", f"{metrics['volume']:,}", "売買の活発さ"),
	]
	for col, (label, value, note) in zip(cols, items):
		with col:
			st.markdown(
				f"""
				<div class="metric-card">
					<div class="small-title">{label}</div>
					<div style="font-size:1.5rem;font-weight:700;margin-top:0.2rem;">{value}</div>
					<div style="font-size:0.85rem;color:{THEME['muted']};margin-top:0.1rem;">{note}</div>
				</div>
				""",
				unsafe_allow_html=True,
			)


def select_stock_block() -> str:
	st.subheader("銘柄検索")
	query = st.text_input("企業名または証券コードを入力", value=stock_label(st.session_state.selected_stock))
	col1, col2, col3 = st.columns([1, 1, 1])
	with col1:
		period = st.selectbox("表示期間", ["1ヶ月", "3ヶ月", "半年", "1年", "3年", "5年"], index=["1ヶ月", "3ヶ月", "半年", "1年", "3年", "5年"].index(st.session_state.selected_period))
	with col2:
		if st.button("検索する", use_container_width=True):
			cleaned = query.strip()
			if not cleaned:
				st.warning("企業名または証券コードを入力してください。")
				return st.session_state.selected_stock
			stock_code = find_stock(query)
			if stock_code is None:
				st.error("銘柄が見つかりません。企業名または証券コードを確認してください。")
			else:
				st.session_state.selected_stock = stock_code
				st.session_state.selected_period = period
				st.session_state.news_focus = CATALOG.loc[CATALOG["code"] == stock_code].iloc[0]["name"]
				st.success(f"{stock_label(stock_code)} を選択しました。")
	with col3:
		st.info("検索後に下の分析画面へ反映されます。")

	return st.session_state.selected_stock


def render_dashboard() -> None:
	render_header(
		"メインダッシュボード",
		"銘柄検索、期間選択、株価チャート、主要指標を1画面にまとめたA担当の中心UIです。",
	)
	code = select_stock_block()
	df = load_stock_data(code, st.session_state.selected_period)
	if df.empty:
		st.error("銘柄データが取得できませんでした。")
		return

	metrics = get_latest_metrics(df)
	render_metric_row(metrics)

	st.divider()
	left, right = st.columns([2, 1])
	with left:
		st.subheader("終値チャート")
		st.line_chart(df.set_index("Date")["Close"])
		st.caption("終値の推移を折れ線で表示しています。")
	with right:
		st.subheader("簡単コメント")
		label, message = make_comment(df)
		if label == "注意":
			st.warning(message)
		elif label == "良い傾向":
			st.success(message)
		elif label == "変動大":
			st.warning(message)
		else:
			st.info(message)
		st.metric("直近変化率", f"{metrics['change_rate']:+.2f}%")
		st.metric("ボラティリティ", f"{df['Volatility'].iloc[-1] * 100:.2f}%")

	st.divider()
	st.subheader("最近のニュース")
	for item in news_items(CATALOG.loc[CATALOG["code"] == code].iloc[0]["name"]):
		with st.chat_message("assistant"):
			st.markdown(f"**{item['time']}**  ")
			st.write(item["title"])
			st.caption(item["body"])
			st.link_button("詳細を見る", item["url"])


def render_trend() -> None:
	render_header(
		"トレンド検索",
		"タグを押して関連銘柄の入口を作る、初心者向けの導線画面です。",
	)
	st.write("興味のあるテーマを選ぶと、関連銘柄の候補を自動で切り替えます。")
	tag_cols = st.columns(3)
	all_tags = list(TAG_MAP.keys())
	for idx, tag in enumerate(all_tags):
		with tag_cols[idx % 3]:
			if st.button(tag, use_container_width=True):
				st.session_state.selected_tags = [tag]
				st.session_state.selected_stock = TAG_MAP[tag][0]
				st.session_state.selected_screen = "ニュースタイムライン"
				st.session_state.news_focus = CATALOG.loc[CATALOG["code"] == TAG_MAP[tag][0]].iloc[0]["name"]
				st.rerun()
	st.markdown("<div class='panel'>選択中のタグ: " + " ".join(f"<span class='tag-pill'>{tag}</span>" for tag in st.session_state.selected_tags) + "</div>", unsafe_allow_html=True)


def render_news() -> None:
	render_header(
		"ニュースタイムライン",
		"トレンド検索から引き継いだ銘柄を、SNS風の縦並びレイアウトで表示します。",
	)
	focus_name = st.session_state.news_focus
	items = news_items(focus_name)
	if not items:
		st.info("現在表示できるニュースはありません。")
		return
	tabs = st.tabs(["ニュース一覧", "銘柄へ戻る"])
	with tabs[0]:
		for item in items:
			with st.chat_message("assistant"):
				st.markdown(f"**{item['time']}**")
				st.write(item["title"])
				st.caption(item["body"])
				st.link_button("元記事へ", item["url"])
				if st.button(f"この企業の株価を見る: {focus_name}", key=f"news_to_stock_{item['time']}"):
					code = find_stock(focus_name)
					if code:
						st.session_state.selected_stock = code
						st.session_state.selected_screen = "メインダッシュボード"
						st.rerun()
	with tabs[1]:
		st.write("ニュースからメイン画面に戻れます。")
		if st.button("メインダッシュボードへ", use_container_width=True):
			st.session_state.selected_screen = "メインダッシュボード"
			st.rerun()


def render_detail() -> None:
	render_header(
		"詳細分析画面",
		"移動平均線と出来高を重ねて、値動きの流れを読み取りやすくします。",
	)
	code = st.session_state.selected_stock
	df = load_stock_data(code, st.session_state.selected_period)
	if len(df) < 25:
		st.warning("表示期間が短いため、一部の分析を表示できません。")

	st.subheader("テクニカル指標")
	show_ma = st.checkbox("移動平均線を表示", value=True)
	show_volume = st.checkbox("出来高を表示", value=True)

	chart = df.set_index("Date")["Close"].to_frame()
	if show_ma:
		chart["MA5"] = df.set_index("Date")["MA5"]
		chart["MA25"] = df.set_index("Date")["MA25"]
	st.line_chart(chart)

	if show_volume:
		st.bar_chart(df.set_index("Date")["Volume"])

	label, message = make_comment(df)
	if label in {"注意", "変動大"}:
		st.warning(message)
	elif label == "良い傾向":
		st.success(message)
	else:
		st.info(message)


def render_compare() -> None:
	render_header(
		"銘柄比較画面",
		"最大3社の株価変化率を比較し、初心者でも違いを見つけやすいようにします。",
	)
	choices = [f"{row.code} {row.name}" for row in CATALOG.itertuples(index=False)]
	selected = st.multiselect("比較したい銘柄を選択", choices, default=[stock_label(code) for code in st.session_state.compare_codes])
	codes = [item.split()[0] for item in selected][:3]
	if not codes:
		st.info("比較したい銘柄を上のボックスから最大3社まで選択してください。")
		return
	if len(selected) > 3:
		st.warning("比較できる銘柄は最大3社までです。")

	compare_days = st.selectbox("比較期間", ["1ヶ月", "3ヶ月", "半年", "1年"], index=1)
	compare_frames = []
	metrics_rows = []
	for code in codes:
		df = load_stock_data(code, compare_days)
		base = df["Close"].iloc[0]
		normalized = df[["Date", "Close"]].copy()
		normalized["Normalized"] = normalized["Close"] / base * 100
		normalized["Code"] = code
		compare_frames.append(normalized)
		metrics_rows.append(
			{
				"銘柄": stock_label(code),
				"騰落率": f"{(df['Close'].iloc[-1] / base - 1) * 100:+.2f}%",
				"出来高平均": f"{int(df['Volume'].mean()):,}",
			}
		)

	chart_df = pd.concat(compare_frames)
	st.line_chart(chart_df.pivot(index="Date", columns="Code", values="Normalized"))
	st.dataframe(pd.DataFrame(metrics_rows), use_container_width=True)

	best = max(compare_frames, key=lambda frame: frame["Normalized"].iloc[-1])
	st.info(f"最も上昇した銘柄は {stock_label(best['Code'].iloc[0])} です。")


def render_glossary() -> None:
	render_header(
		"用語タッチ解説",
		"画面内で分からない言葉をすぐ確認できる、初心者向けのヘルプ画面です。",
	)
	cols = st.columns(2)
	with cols[0]:
		term = st.selectbox("用語を選ぶ", list(GLOSSARY.keys()), index=list(GLOSSARY.keys()).index(st.session_state.selected_term))
		st.session_state.selected_term = term
		with st.expander("用語の説明"):
			st.write(GLOSSARY.get(term, "この用語の説明はまだ登録されていません。"))
	with cols[1]:
		st.markdown("### 画面内の補助")
		st.markdown("- 株価チャート")
		st.markdown("- 出来高")
		st.markdown("- 移動平均線")
		st.markdown("- 前日比")


def render_learning_center() -> None:
	render_header(
		"ラーニングセンター",
		"用語集と4択クイズをまとめ、学習と確認を一体化した画面です。",
	)
	tab_terms, tab_quiz = st.tabs(["用語集", "クイズ"])
	with tab_terms:
		for word, description in GLOSSARY.items():
			with st.expander(word):
				st.write(description)
	with tab_quiz:
		quiz = QUIZ[st.session_state.quiz_index % len(QUIZ)]
		st.write(quiz["question"])
		answer = st.radio("回答を選択", quiz["choices"], index=None)
		if st.button("回答する"):
			if answer is None:
				st.warning("選択肢をどれか1つ選択してから回答ボタンを押してください。")
			else:
				picked = quiz["choices"].index(answer)
				if picked == quiz["answer"]:
					st.success("正解です。")
					st.balloons()
				else:
					st.error("不正解です。")
				st.info(quiz["explain"])
				st.session_state.quiz_index += 1


def render_sidebar() -> None:
	st.sidebar.title("画面切替")
	st.sidebar.caption("A担当のUI総合")
	screen = st.sidebar.radio(
		"表示する画面",
		[
			"メインダッシュボード",
			"トレンド検索",
			"ニュースタイムライン",
			"詳細分析画面",
			"銘柄比較画面",
			"用語タッチ解説",
			"ラーニングセンター",
		],
		index=[
			"メインダッシュボード",
			"トレンド検索",
			"ニュースタイムライン",
			"詳細分析画面",
			"銘柄比較画面",
			"用語タッチ解説",
			"ラーニングセンター",
		].index(st.session_state.selected_screen),
	)
	st.session_state.selected_screen = screen
	st.sidebar.divider()
	st.sidebar.subheader("現在の選択")
	st.sidebar.write(stock_label(st.session_state.selected_stock))
	st.sidebar.write(f"期間: {st.session_state.selected_period}")
	st.sidebar.write(f"タグ: {', '.join(st.session_state.selected_tags) if st.session_state.selected_tags else '未選択'}")


def main() -> None:
	init_state()
	apply_style()
	render_sidebar()

	screen = st.session_state.selected_screen
	if screen == "メインダッシュボード":
		render_dashboard()
	elif screen == "トレンド検索":
		render_trend()
	elif screen == "ニュースタイムライン":
		render_news()
	elif screen == "詳細分析画面":
		render_detail()
	elif screen == "銘柄比較画面":
		render_compare()
	elif screen == "用語タッチ解説":
		render_glossary()
	elif screen == "ラーニングセンター":
		render_learning_center()


if __name__ == "__main__":
	main()
