"""Dashboard de MarketPulse con Streamlit (paso 8.4, D-041).

Ejecutar desde la raíz del proyecto, con `aws login --profile marketpulse` hecho:
    $env:AWS_PROFILE = "marketpulse"
    python -m streamlit run dashboard/app.py
`python -m` añade la carpeta actual a sys.path, así que `import dashboard` funciona.

Cómo funciona Streamlit: el script se ejecuta ENTERO de arriba abajo cada vez que el usuario
toca algo (un filtro, un botón). Por eso lo caro va en cachés:
- st.cache_resource: objetos que se comparten y no se copian (la sesión de AWS, el agente).
- st.cache_data: resultados (las tablas de Athena), con una copia por llamada.
Todo es de solo lectura, con las credenciales temporales del rol marketpulse-agent (D-033, D-040).
"""

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from dashboard.data import (
    latest_volatility,
    load_assets,
    load_prices,
    load_volatility,
    rebase_to_100,
)
from marketpulse.agent.runtime import MissingApiKeyError, aws_session, build_agent

CACHE_TTL_S = 60 * 60  # los datos cambian una vez al día: refrescar cada hora sobra
SESSION_TTL_S = 50 * 60  # el rol caduca a la hora: se pide uno nuevo antes (encadenamiento, 1 h)
PERIODS = {"1 mes": 30, "3 meses": 90, "6 meses": 180, "1 año": 365}
MAX_QUESTION_CHARS = 1_000  # el mismo límite que la API (api/main.py)

# Atribuciones obligatorias o de cortesía, junto a los datos (D-039)
SOURCES = {
    "crypto": "Criptomonedas: [Powered by CoinGecko](https://www.coingecko.com/en/api).",
    "fx": (
        "Divisas: fuente [Banco Central Europeo (BCE)](https://www.ecb.europa.eu/stats/"
        "policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html), tipos de "
        "referencia del euro, a través de [Frankfurter](https://frankfurter.dev)."
    ),
    "equity": (
        "Bolsa: datos de [Alpha Vantage](https://www.alphavantage.co), cierres sin ajustar "
        "por dividendos."
    ),
}
TRANSFORMED = (
    "Las rentabilidades y volatilidades las calcula MarketPulse a partir de los datos "
    "originales: no son cifras del BCE ni de los demás proveedores."
)
DISCLAIMER = (
    "Proyecto personal y sin fines comerciales. Nada de lo que se muestra es asesoramiento "
    "financiero."
)

load_dotenv()  # ANTHROPIC_API_KEY, solo para la caja de preguntas


@st.cache_resource(ttl=SESSION_TTL_S, show_spinner="Asumiendo el rol de solo lectura...")
def get_session():
    return aws_session(assume_role=True)


@st.cache_resource(ttl=SESSION_TTL_S, show_spinner=False)
def get_agent():
    return build_agent(get_session())  # MissingApiKeyError si falta la clave


@st.cache_data(ttl=CACHE_TTL_S, show_spinner="Consultando Athena...")
def cached_prices(days: int) -> pd.DataFrame:
    return load_prices(get_session().client("athena"), days)


@st.cache_data(ttl=CACHE_TTL_S, show_spinner="Consultando Athena...")
def cached_volatility(days: int) -> pd.DataFrame:
    return load_volatility(get_session().client("athena"), days)


@st.cache_data(ttl=CACHE_TTL_S, show_spinner=False)
def cached_assets() -> pd.DataFrame:
    return load_assets(get_session().client("athena"))


def source_notes(classes) -> None:
    """Las atribuciones de las clases de activo que se están viendo, debajo del gráfico."""
    for asset_class in ("crypto", "fx", "equity"):
        if asset_class in classes:
            st.caption(SOURCES[asset_class])


def prices_section(prices: pd.DataFrame, selected: list[str]) -> None:
    st.subheader("Evolución de precios")
    st.caption(
        "Base 100: cada activo empieza en 100 en su primer dato del periodo, así que 110 "
        "significa +10 %. Sirve para comparar activos de precios muy distintos."
    )
    shown = rebase_to_100(prices[prices["asset"].isin(selected)])
    if shown.empty:
        st.info("No hay datos para esta selección.")
        return
    st.line_chart(shown, x="date", y="index_100", color="asset", x_label="", y_label="Base 100")
    source_notes(set(shown["asset_class"]))


def volatility_section(volatility: pd.DataFrame, selected: list[str]) -> None:
    st.subheader("Volatilidad anualizada (30 sesiones)")
    shown = volatility[volatility["asset"].isin(selected)]
    if shown.empty:
        st.info("No hay datos para esta selección.")
        return
    left, right = st.columns([2, 1])
    with left:
        chart = shown.assign(volatility_pct=shown["annualized_volatility_30"] * 100)
        st.line_chart(chart, x="date", y="volatility_pct", color="asset", x_label="", y_label="%")
    with right:
        last = latest_volatility(shown)
        st.dataframe(
            last.assign(
                volatility_pct=last["annualized_volatility_30"] * 100,
                date=last["date"].dt.date,
            )[["asset", "volatility_pct", "date"]],
            hide_index=True,
            column_config={
                "asset": "Activo",
                "volatility_pct": st.column_config.NumberColumn("Volatilidad", format="%.1f %%"),
                "date": "Último dato",
            },
        )
    st.caption(
        "Cada activo con su último dato: la bolsa y las divisas no cotizan el fin de semana. "
        "Se anualiza con 365 sesiones en cripto y 252 en bolsa y divisas."
    )
    source_notes(set(shown["asset_class"]))
    st.caption(TRANSFORMED)


def agent_section() -> None:
    st.subheader("Pregunta al agente")
    st.caption(
        "Escribe una pregunta en español sobre los datos. El agente (Claude Haiku) genera la SQL "
        "y la ejecuta en Athena con el rol de solo lectura; solo se admiten consultas SELECT."
    )
    with st.form("pregunta", clear_on_submit=False):
        question = st.text_input(
            "Pregunta",
            max_chars=MAX_QUESTION_CHARS,
            placeholder="¿Qué activo ha sido más volátil en los últimos 30 días?",
        )
        asked = st.form_submit_button("Preguntar", type="primary")
    if not asked:
        return
    if len(question.strip()) < 3:
        st.warning("Escribe una pregunta un poco más larga.")
        return
    try:
        agent = get_agent()
    except MissingApiKeyError:
        st.error("Falta ANTHROPIC_API_KEY en .env: los gráficos funcionan, pero el agente no.")
        return
    with st.spinner("El agente está pensando y consultando Athena..."):
        answer = agent.ask(question.strip())

    if answer.outcome == "respondida":
        st.success(answer.answer)
    elif answer.outcome in ("rechazada", "bloqueada"):
        st.warning(f"No se ha ejecutado ({answer.outcome}): {answer.answer}")
    else:
        st.error(f"No se ha podido responder: {answer.answer}")
    if answer.sql:
        with st.expander("SQL que se ha ejecutado"):
            st.code(answer.sql, language="sql")
            if answer.explanation:
                st.write(answer.explanation)
    cost = answer.usage.get("cost_usd", 0)
    st.caption(
        f"{answer.usage.get('calls', 0)} llamadas al modelo · {cost:.4f} USD · "
        f"{answer.bytes_scanned:,} bytes leídos en Athena · id {answer.request_id}"
    )
    source_notes({"crypto", "fx", "equity"})  # la respuesta puede usar cualquier fuente


def main() -> None:
    st.set_page_config(page_title="MarketPulse", layout="wide")
    st.title("MarketPulse")
    st.caption(
        "Precios diarios de criptomonedas, bolsa y divisas, cargados cada mañana en AWS "
        "(Lambda → S3 → Athena)."
    )

    try:
        assets = cached_assets()
    except Exception as e:  # sin credenciales o con la sesión de aws login caducada
        st.error(
            "No se han podido leer los datos de AWS. Comprueba `aws login --profile marketpulse` "
            f"y `$env:AWS_PROFILE`. Detalle: {type(e).__name__}"
        )
        st.stop()

    with st.sidebar:
        period = st.segmented_control("Periodo", list(PERIODS), default="6 meses", required=True)
        names = dict(zip(assets["asset"], assets["asset_name"], strict=True))
        selected = st.multiselect(
            "Activos",
            list(names),
            default=list(names),
            format_func=lambda a: f"{a} · {names[a]}",
        )
    days = PERIODS[period]

    tab_prices, tab_vol, tab_agent = st.tabs(["Precios", "Volatilidad", "Agente"])
    with tab_prices:
        prices_section(cached_prices(days), selected)
    with tab_vol:
        volatility_section(cached_volatility(days), selected)
    with tab_agent:
        agent_section()

    st.divider()  # las fuentes van junto a cada gráfico o respuesta (D-039); aquí, el aviso
    st.caption(DISCLAIMER)


main()
