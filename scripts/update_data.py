"""
Atualiza os dados do NoobShark Insights.

Fontes públicas usadas no MVP:
- yfinance para preços
- alternative.me para Fear & Greed, quando disponível

Este script:
1. Baixa preços.
2. Calcula retornos, médias e correlações rolantes.
3. Gera scores proprietários.
4. Atualiza docs/data/dashboard.json.
5. Atualiza docs/data/history.json.
6. Envia Telegram opcionalmente, caso secrets existam.

Uso:
    python scripts/update_data.py
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
import requests
import yfinance as yf


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "docs" / "data"
DASHBOARD_PATH = DATA_DIR / "dashboard.json"
HISTORY_PATH = DATA_DIR / "history.json"

ROLLING_CORR_WINDOW = int(os.getenv("ROLLING_CORR_WINDOW", "30"))

TICKERS = {
    "BTC": {"ticker": "BTC-USD", "name": "Bitcoin"},
    "ETH": {"ticker": "ETH-USD", "name": "Ethereum"},
    "GOLD": {"ticker": "GC=F", "name": "Ouro"},
    "SPX": {"ticker": "^GSPC", "name": "S&P 500"},
    "NASDAQ": {"ticker": "^IXIC", "name": "Nasdaq"},
    "DXY": {"ticker": "DX-Y.NYB", "name": "Dólar DXY"},
    "IGV": {"ticker": "IGV", "name": "iShares Expanded Tech-Software ETF"},
}


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    if value is None or math.isnan(value):
        return 50
    return max(low, min(high, value))


def normalize(value: float, low: float, high: float) -> float:
    """Normaliza value para escala 0-100."""
    if value is None or math.isnan(value):
        return 50
    return clamp(100 * (value - low) / (high - low))


def safe_last(series: pd.Series) -> float | None:
    series = series.dropna()
    if series.empty:
        return None
    return float(series.iloc[-1])


def pct_change(series: pd.Series, periods: int) -> float | None:
    series = series.dropna()
    if len(series) <= periods:
        return None
    return float((series.iloc[-1] / series.iloc[-periods] - 1) * 100)


def fetch_prices(period: str = "1y") -> pd.DataFrame:
    symbols = [v["ticker"] for v in TICKERS.values()]
    raw = yf.download(
        symbols,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )

    close = pd.DataFrame()
    for key, meta in TICKERS.items():
        ticker = meta["ticker"]
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                close[key] = raw[ticker]["Close"]
            else:
                close[key] = raw["Close"]
        except Exception:
            close[key] = np.nan

    close = close.ffill().dropna(how="all")
    return close


def fetch_fear_greed() -> Dict[str, Any] | None:
    try:
        response = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        response.raise_for_status()
        payload = response.json()
        item = payload["data"][0]
        return {
            "value": int(item["value"]),
            "classification": item["value_classification"],
        }
    except Exception:
        return None


def calc_correlations(prices: pd.DataFrame) -> Dict[str, Any]:
    returns = prices.pct_change()
    corr_map = {}

    for asset in ["GOLD", "SPX", "DXY", "NASDAQ", "IGV"]:
        corr_map[asset] = returns["BTC"].rolling(ROLLING_CORR_WINDOW).corr(returns[asset])

    corr_df = pd.DataFrame(corr_map).dropna(how="all")
    latest = {k: safe_last(corr_df[k]) for k in corr_df.columns}

    series = []
    tail = corr_df.tail(160)
    for idx, row in tail.iterrows():
        series.append({
            "date": idx.strftime("%Y-%m-%d"),
            "gold": round_or_none(row.get("GOLD"), 4),
            "spx": round_or_none(row.get("SPX"), 4),
            "dxy": round_or_none(row.get("DXY"), 4),
            "nasdaq": round_or_none(row.get("NASDAQ"), 4),
            "igv": round_or_none(row.get("IGV"), 4),
        })

    return {
        "window": ROLLING_CORR_WINDOW,
        "current": {k: round_or_none(v, 4) for k, v in latest.items()},
        "series": series,
    }


def round_or_none(value, ndigits: int = 2):
    try:
        if value is None or pd.isna(value):
            return None
        return round(float(value), ndigits)
    except Exception:
        return None


def build_market_snapshot(prices: pd.DataFrame) -> Dict[str, Any]:
    snapshot = {}
    for key, meta in TICKERS.items():
        series = prices[key] if key in prices else pd.Series(dtype=float)
        snapshot[key] = {
            "name": meta["name"],
            "last": round_or_none(safe_last(series), 2),
            "change_7d_pct": round_or_none(pct_change(series, 7), 2),
            "change_30d_pct": round_or_none(pct_change(series, 30), 2),
            "change_90d_pct": round_or_none(pct_change(series, 90), 2),
            "ma_200": round_or_none(series.rolling(200).mean().iloc[-1] if len(series.dropna()) >= 200 else np.nan, 2),
        }
    return snapshot


def calc_scores(prices: pd.DataFrame, correlations: Dict[str, Any], fear_greed: Dict[str, Any] | None) -> Dict[str, float]:
    btc = prices["BTC"].dropna()
    eth = prices["ETH"].dropna()
    nasdaq = prices["NASDAQ"].dropna()
    spx = prices["SPX"].dropna()
    dxy = prices["DXY"].dropna()

    btc_30 = pct_change(btc, 30) or 0
    btc_90 = pct_change(btc, 90) or 0
    nasdaq_30 = pct_change(nasdaq, 30) or 0
    spx_30 = pct_change(spx, 30) or 0
    dxy_30 = pct_change(dxy, 30) or 0

    btc_last = safe_last(btc) or 0
    btc_ma200 = safe_last(btc.rolling(200).mean()) or btc_last
    btc_high_1y = float(btc.max()) if not btc.empty else btc_last
    btc_drawdown = (btc_last / btc_high_1y - 1) * 100 if btc_high_1y else 0

    ethbtc = (eth / btc).dropna()
    ethbtc_30 = pct_change(ethbtc, 30) or 0

    corr_current = correlations.get("current", {})
    spx_corr = corr_current.get("SPX") or 0
    nasdaq_corr = corr_current.get("NASDAQ") or 0
    igv_corr = corr_current.get("IGV") or 0
    tech_corr = np.nanmean([spx_corr, nasdaq_corr, igv_corr])

    fear_value = fear_greed["value"] if fear_greed else 50

    global_risk = np.mean([
        normalize(btc_30, -20, 20),
        normalize(nasdaq_30, -10, 10),
        normalize(spx_30, -8, 8),
        100 - normalize(dxy_30, -4, 4),
        70 if btc_last > btc_ma200 else 30,
        normalize(tech_corr, -0.2, 0.8),
        100 - max(0, fear_value - 75) * 1.2,
    ])

    btc_cycle = np.mean([
        75 if btc_last > btc_ma200 else 25,
        normalize(btc_30, -25, 25),
        normalize(btc_90, -35, 45),
        100 - normalize(abs(btc_drawdown), 0, 60),
        normalize(tech_corr, -0.4, 0.8),
        normalize(fear_value, 10, 85),
    ])

    altseason = np.mean([
        normalize(ethbtc_30, -15, 15),
        normalize(btc_30, -15, 18),
        normalize(nasdaq_30, -8, 8),
        100 - normalize(dxy_30, -4, 4),
        normalize(tech_corr, -0.1, 0.7),
        100 - max(0, fear_value - 75) * 1.5,
    ])

    return {
        "global_risk": round(float(clamp(global_risk)), 0),
        "btc_cycle": round(float(clamp(btc_cycle)), 0),
        "altseason_window": round(float(clamp(altseason)), 0),
        "tech_correlation": round(float(tech_corr), 4),
    }


def classify(scores: Dict[str, float], correlations: Dict[str, Any]) -> Dict[str, str]:
    global_risk = scores["global_risk"]
    btc_cycle = scores["btc_cycle"]
    altseason = scores["altseason_window"]
    tech_corr = scores["tech_correlation"]

    if global_risk >= 65 and btc_cycle >= 55:
        traffic = {
            "color": "green",
            "label": "Verde",
            "text": "Ambiente construtivo para risco, desde que entradas respeitem setup, stop e gestão."
        }
        posture = "Risk-on controlado"
    elif global_risk >= 42 and btc_cycle >= 40:
        traffic = {
            "color": "yellow",
            "label": "Amarelo",
            "text": "Mercado misto. Priorizar confirmação, menor tamanho e evitar alavancagem excessiva."
        }
        posture = "Neutro com cautela"
    elif global_risk >= 25:
        traffic = {
            "color": "red",
            "label": "Vermelho",
            "text": "Ambiente defensivo. Reduzir impulso, proteger capital e aguardar melhora da estrutura."
        }
        posture = "Defensivo"
    else:
        traffic = {
            "color": "black",
            "label": "Preto",
            "text": "Risco extremo de desalavancagem ou estresse. Caixa e proteção ganham prioridade."
        }
        posture = "Risco extremo"

    if tech_corr >= 0.45:
        market_regime = "BTC como tech/growth"
    elif tech_corr <= -0.25:
        market_regime = "BTC descorrelacionado de tech"
    else:
        market_regime = "BTC em regime misto"

    if btc_cycle >= 70:
        btc_regime = "BTC em expansão/euforia"
    elif btc_cycle >= 55:
        btc_regime = "BTC construtivo"
    elif btc_cycle >= 40:
        btc_regime = "BTC em transição"
    else:
        btc_regime = "BTC defensivo"

    if altseason >= 70:
        alt_regime = "Altseason aberta/eufórica"
    elif altseason >= 55:
        alt_regime = "Janela de altcoins abrindo"
    elif altseason >= 40:
        alt_regime = "Altcoins em preparação"
    else:
        alt_regime = "Altcoins fechadas"

    return {
        "traffic_light": traffic,
        "model_posture": posture,
        "market_regime": market_regime,
        "btc_regime": btc_regime,
        "altseason_regime": alt_regime,
    }


def build_insights(scores: Dict[str, float], correlations: Dict[str, Any], markets: Dict[str, Any], fear_greed: Dict[str, Any] | None) -> list[Dict[str, str]]:
    current = correlations.get("current", {})
    insights = []

    tech_corr = scores["tech_correlation"]
    if tech_corr >= 0.45:
        insights.append({
            "title": "BTC conectado a tecnologia/growth",
            "text": "A correlação com SPX, Nasdaq e IGV está positiva. A leitura de juros, liquidez e índices americanos deve pesar mais no curto prazo."
        })
    elif tech_corr <= -0.25:
        insights.append({
            "title": "BTC menos dependente de tech",
            "text": "A correlação com tecnologia está baixa ou negativa. Price action próprio, derivativos e fluxo cripto ganham peso."
        })
    else:
        insights.append({
            "title": "Regime misto de correlação",
            "text": "As correlações não apontam uma dominância clara. O modelo deve tratar sinais isolados com cautela."
        })

    dxy_30 = markets.get("DXY", {}).get("change_30d_pct")
    if dxy_30 is not None and dxy_30 > 1.5:
        insights.append({
            "title": "Dólar em alta pressiona risco",
            "text": "DXY subindo em 30 dias costuma reduzir o apetite por cripto e tecnologia. Longs exigem mais confirmação."
        })
    elif dxy_30 is not None and dxy_30 < -1.5:
        insights.append({
            "title": "Dólar fraco melhora liquidez",
            "text": "DXY em queda tende a aliviar ativos de risco e pode favorecer BTC e altcoins, se a estrutura confirmar."
        })

    if fear_greed:
        insights.append({
            "title": f"Fear & Greed: {fear_greed['value']} — {fear_greed['classification']}",
            "text": "Sentimento extremo deve ser lido como filtro de risco, não como gatilho isolado de compra ou venda."
        })

    if scores["altseason_window"] < 45:
        insights.append({
            "title": "Altseason ainda seletiva",
            "text": "A janela de altcoins não está claramente aberta. Priorizar líderes, força relativa e stops técnicos."
        })
    elif scores["altseason_window"] >= 55:
        insights.append({
            "title": "Altseason em melhora",
            "text": "O conjunto de fatores começa a favorecer altcoins, mas euforia e funding excessivo devem ser monitorados."
        })

    return insights[:5]


def build_headline(scores: Dict[str, float], classifications: Dict[str, str]) -> tuple[str, str]:
    traffic = classifications["traffic_light"]["label"]
    market = classifications["market_regime"]
    alt = classifications["altseason_regime"]

    headline = f"Semáforo {traffic}: {classifications['model_posture']}"

    summary = (
        f"O modelo classifica o mercado como {classifications['model_posture'].lower()}. "
        f"O regime atual indica {market.lower()}, enquanto o sinalizador de altcoins aponta: {alt.lower()}. "
        "A postura recomendada é operar por processo: confirmação, stop definido, tamanho controlado e sem promessa de direção."
    )

    return headline, summary


def send_telegram_if_configured(payload: Dict[str, Any]) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    text = (
        f"🦈 *NoobShark Insights*\n\n"
        f"*{payload['headline']}*\n\n"
        f"Semáforo: *{payload['traffic_light']['label']}*\n"
        f"Global Risk: *{payload['scores']['global_risk']}/100*\n"
        f"BTC Cycle: *{payload['scores']['btc_cycle']}/100*\n"
        f"Altseason: *{payload['scores']['altseason_window']}/100*\n"
        f"Tech Corr: *{payload['scores']['tech_correlation']}*\n\n"
        f"{payload['executive_summary']}\n\n"
        f"_Não é recomendação financeira._"
    )

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            timeout=15,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
        ).raise_for_status()
    except Exception as exc:
        print(f"[telegram] falha ao enviar: {exc}")


def load_history() -> list[Dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_fallback_dashboard(error: str) -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    brt = now_utc.astimezone(timezone(timedelta(hours=-3)))

    return {
        "updated_at": now_utc.isoformat(),
        "updated_at_brt": brt.strftime("%d/%m/%Y %H:%M"),
        "headline": "Dados indisponíveis no momento",
        "executive_summary": f"O script não conseguiu atualizar as fontes. Erro: {error}",
        "traffic_light": {"color": "yellow", "label": "Amarelo", "text": "Falha de dados. Não tomar decisão com base nesta leitura."},
        "model_posture": "Dados insuficientes",
        "market_regime": "Indefinido",
        "btc_regime": "Indefinido",
        "altseason_regime": "Indefinido",
        "scores": {"global_risk": 50, "btc_cycle": 50, "altseason_window": 50, "tech_correlation": 0},
        "correlations": {"window": ROLLING_CORR_WINDOW, "current": {}, "series": []},
        "markets": {},
        "fear_greed": None,
        "insights": [{"title": "Falha de atualização", "text": "Verifique logs do GitHub Actions e conectividade das fontes."}],
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:
        prices = fetch_prices()
        if prices.empty or "BTC" not in prices:
            raise RuntimeError("não foi possível obter preços suficientes")

        fear_greed = fetch_fear_greed()
        markets = build_market_snapshot(prices)
        correlations = calc_correlations(prices)
        scores = calc_scores(prices, correlations, fear_greed)
        classifications = classify(scores, correlations)
        headline, summary = build_headline(scores, classifications)
        insights = build_insights(scores, correlations, markets, fear_greed)

        now_utc = datetime.now(timezone.utc)
        brt = now_utc.astimezone(timezone(timedelta(hours=-3)))

        dashboard = {
            "updated_at": now_utc.isoformat(),
            "updated_at_brt": brt.strftime("%d/%m/%Y %H:%M"),
            "headline": headline,
            "executive_summary": summary,
            **classifications,
            "scores": scores,
            "correlations": correlations,
            "markets": markets,
            "fear_greed": fear_greed,
            "insights": insights,
        }

    except Exception as exc:
        print(f"[erro] {exc}")
        dashboard = build_fallback_dashboard(str(exc))

    save_json(DASHBOARD_PATH, dashboard)

    history = load_history()
    history_item = {
        "date": dashboard["updated_at_brt"],
        "traffic_light": dashboard["traffic_light"]["label"],
        "global_risk": dashboard["scores"]["global_risk"],
        "btc_cycle": dashboard["scores"]["btc_cycle"],
        "altseason_window": dashboard["scores"]["altseason_window"],
        "tech_correlation": dashboard["scores"]["tech_correlation"],
        "btc_price": dashboard.get("markets", {}).get("BTC", {}).get("last"),
    }
    history.append(history_item)
    history = history[-500:]
    save_json(HISTORY_PATH, history)

    send_telegram_if_configured(dashboard)

    print("Dashboard atualizado com sucesso.")
    print(json.dumps({
        "headline": dashboard["headline"],
        "scores": dashboard["scores"],
        "traffic": dashboard["traffic_light"]["label"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
