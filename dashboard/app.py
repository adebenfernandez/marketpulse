"""Dashboard de MarketPulse con Streamlit (D-041; rediseño D-044).

Ejecutar desde la raíz del proyecto, con `aws login --profile marketpulse` hecho:
    $env:AWS_PROFILE = "marketpulse"
    python -m streamlit run dashboard/app.py
`python -m` añade la carpeta actual a sys.path, así que `import dashboard` funciona.

Cómo funciona Streamlit: el script se ejecuta ENTERO de arriba abajo cada vez que el usuario
toca algo (un filtro, un botón). Por eso lo caro va en cachés:
- st.cache_resource: objetos que se comparten y no se copian (la sesión de AWS, el agente).
- st.cache_data: resultados (las tablas de Athena), con una copia por llamada.
Todo es de solo lectura, con las credenciales temporales del rol marketpulse-agent (D-033, D-040).

Diseño (D-044): una sola página, sin barra lateral. Cabecera → tarjetas de los 8 activos →
una fila de filtros → evolución, volatilidad y el agente como chat. Gráficos con Altair (viene
con Streamlit): líneas de 2 px, rejilla en una sola línea gris, colores fijos por activo.
"""

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from dashboard.data import (
    asset_summary,
    latest_volatility,
    load_prices,
    load_volatility,
    rebase_to_100,
)
from marketpulse.agent.runtime import MissingApiKeyError, aws_session, build_agent

CACHE_TTL_S = 60 * 60  # los datos cambian una vez al día: refrescar cada hora sobra
SESSION_TTL_S = 50 * 60  # el rol caduca a la hora: se pide uno nuevo antes (encadenamiento, 1 h)
PERIODS = {"1M": 30, "3M": 90, "6M": 180, "1A": 365}
MAX_QUESTION_CHARS = 1_000  # el mismo límite que la API (api/main.py)

# Clases de activo, en el orden en que se muestran, y sus activos (los de watchlist.yaml)
CLASSES = {
    "crypto": ("Cripto", ["BTC", "ETH", "SOL"]),
    "equity": ("Bolsa", ["SPY", "QQQ", "VT"]),
    "fx": ("Divisas", ["EUR/USD", "EUR/GBP"]),
}

# Paleta (referencia validada de la guía de visualización: los 3 primeros huecos se distinguen
# también con daltonismo). El color sigue al activo dentro de su clase: BTC siempre es azul
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SURFACE = "#ecebe6", "#c3c2b7", "#ffffff"

# Nombres cortos para las tarjetas (los de dim_asset son largos para una tarjeta)
SHORT_NAMES = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "SPY": "S&P 500",
    "QQQ": "Nasdaq-100",
    "VT": "Bolsa mundial",
    "EUR/USD": "Euro / dólar",
    "EUR/GBP": "Euro / libra",
}

EXAMPLES = [
    "¿Qué activo ha sido más volátil en los últimos 30 días?",
    "¿Cuál fue la rentabilidad de BTC en septiembre de 2026?",
    "¿Qué correlación hay entre BTC y SPY?",
]

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

load_dotenv()  # ANTHROPIC_API_KEY, solo para el agente


# --- Datos (con caché) ---------------------------------------------------------------------


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


# --- Formato en español (1.234,56) ------------------------------------------------------------


def es_number(value: float, decimals: int) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def price_text(price: float, asset_class: str, currency: str) -> str:
    if asset_class == "fx":
        return es_number(price, 4)  # un tipo de cambio no lleva símbolo: 1 EUR = 1,1193 USD
    symbol = {"USD": "$", "GBP": "£", "EUR": "€"}.get(currency, currency)
    return f"{es_number(price, 0 if price >= 1_000 else 2)} {symbol}"


def source_notes(classes) -> None:
    """Las atribuciones de las clases que se están viendo, debajo de los datos (D-039)."""
    st.caption("  \n".join(SOURCES[c] for c in CLASSES if c in classes))


# --- Gráficos (Altair) ---------------------------------------------------------------------


def _axis_x() -> alt.X:
    return alt.X(
        "date:T",
        title=None,
        axis=alt.Axis(
            format="%d/%m",
            labelColor=MUTED,
            grid=False,
            domainColor=BASELINE,
            tickColor=BASELINE,
            labelPadding=6,
        ),
    )


def line_chart(
    data: pd.DataFrame, field: str, assets: list[str], number_format: str, tooltip_title: str
) -> alt.LayerChart:
    """Líneas de 2 px, un color fijo por activo, cruz y ficha al pasar el ratón."""
    color = alt.Color(
        "asset:N",
        scale=alt.Scale(domain=assets, range=SERIES[: len(assets)]),
        legend=alt.Legend(
            orient="top",
            title=None,
            labelColor=INK_2,
            symbolType="stroke",
            symbolStrokeWidth=2,
            symbolSize=200,
            labelFontSize=13,
            padding=0,
            offset=12,
        ),
    )
    y = alt.Y(
        f"{field}:Q",
        title=None,
        scale=alt.Scale(zero=False, nice=True),
        axis=alt.Axis(
            format=number_format,
            labelColor=MUTED,
            gridColor=GRID,
            domain=False,
            ticks=False,
            labelPadding=8,
            tickCount=5,
        ),
    )
    base = alt.Chart(data).encode(x=_axis_x(), y=y, color=color)
    hover = alt.selection_point(
        nearest=True, on="pointerover", fields=["date"], empty=False, clear="pointerout"
    )
    lines = base.mark_line(strokeWidth=2, strokeCap="round", strokeJoin="round")
    points = (
        base.mark_point(size=70, filled=True, stroke=SURFACE, strokeWidth=2, opacity=1)
        .encode(
            opacity=alt.condition(hover, alt.value(1), alt.value(0)),
            tooltip=[
                alt.Tooltip("date:T", title="Fecha", format="%d/%m/%Y"),
                alt.Tooltip("asset:N", title="Activo"),
                alt.Tooltip(f"{field}:Q", title=tooltip_title, format=number_format),
            ],
        )
        .add_params(hover)
    )
    rule = (
        alt.Chart(data)
        .mark_rule(color=BASELINE, strokeWidth=1)
        .encode(x="date:T")
        .transform_filter(hover)
    )
    return (
        alt.layer(lines, rule, points)
        .properties(height=320)
        .configure_view(stroke=None)
        .configure_axis(labelFontSize=12)
    )


def ranking_chart(last: pd.DataFrame) -> alt.LayerChart:
    """Barras horizontales de un solo color (es un ranking, no categorías), valor en la punta."""
    data = last.assign(
        label=last["asset"],
        pct=last["annualized_volatility_30"] * 100,
        text=[es_number(v * 100, 1) + " %" for v in last["annualized_volatility_30"]],
    )
    y = alt.Y(
        "label:N",
        sort=alt.SortField("pct", order="descending"),
        title=None,
        axis=alt.Axis(
            domain=False, ticks=False, labelColor=INK_2, labelFontSize=13, labelPadding=10
        ),
    )
    # El 30 % de margen a la derecha deja sitio al valor en la punta de la barra más larga
    x = alt.X("pct:Q", title=None, axis=None, scale=alt.Scale(domain=[0, data["pct"].max() * 1.3]))
    tooltip = [alt.Tooltip("label:N", title="Activo"), alt.Tooltip("text:N", title="Volatilidad")]
    bars = (
        alt.Chart(data)
        .mark_bar(color=SERIES[0], size=16, cornerRadiusEnd=4)
        .encode(x=x, y=y, tooltip=tooltip)
    )
    labels = (
        alt.Chart(data)
        .mark_text(align="left", dx=6, color=INK_2, fontSize=12)
        .encode(x=x, y=y, text="text:N")
    )
    return alt.layer(bars, labels).properties(height=alt.Step(30)).configure_view(stroke=None)


# --- Secciones ---------------------------------------------------------------------------------


def header(prices: pd.DataFrame) -> None:
    left, right = st.columns([3, 2], vertical_alignment="bottom")
    with left:
        st.title("MarketPulse")
        st.caption("Cripto, bolsa y divisas, cargados cada mañana en AWS y listos para preguntar.")
    with right:
        last = prices["date"].max()
        st.caption(
            f"Datos hasta el **{last:%d/%m/%Y}** · se actualizan a diario a las 06:30 UTC",
            text_alignment="right",
        )


def kpi_cards(summary: pd.DataFrame) -> None:
    order = [a for _, assets in CLASSES.values() for a in assets]
    rows = summary.set_index("asset").reindex([a for a in order if a in set(summary["asset"])])
    for start in range(0, len(rows), 4):
        for col, (asset, row) in zip(
            st.columns(4), rows.iloc[start : start + 4].iterrows(), strict=False
        ):
            sign = "+" if row["change_pct"] >= 0 else "-"
            with col:
                st.metric(
                    label=f"{asset} · {SHORT_NAMES.get(asset, asset)}",
                    value=price_text(row["last_price"], row["asset_class"], row["currency"]),
                    delta=f"{sign}{es_number(abs(row['change_pct']), 1)} % en 30 días",
                    delta_arrow="auto",
                    chart_data=row["spark"],
                    chart_type="line",
                    border=True,
                )


def filters() -> tuple[str, int]:
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        asset_class = st.segmented_control(
            "Clase de activo",
            list(CLASSES),
            default="crypto",
            required=True,
            format_func=lambda c: CLASSES[c][0],
            label_visibility="collapsed",
        )
        period = st.segmented_control(
            "Periodo", list(PERIODS), default="6M", required=True, label_visibility="collapsed"
        )
    return asset_class, PERIODS[period]


def evolution_section(prices: pd.DataFrame, asset_class: str) -> None:
    st.subheader("Evolución")
    st.caption("Base 100: cada activo empieza en 100 en su primer dato del periodo (110 = +10 %).")
    assets = CLASSES[asset_class][1]
    data = rebase_to_100(prices[prices["asset"].isin(assets)])
    if data.empty:
        st.info("No hay datos para este periodo.")
        return
    st.altair_chart(line_chart(data, "index_100", assets, ",.0f", "Base 100"), width="stretch")
    with st.expander("Ver los datos"):
        st.dataframe(
            data[["date", "asset", "price", "index_100"]].sort_values(["date", "asset"]),
            hide_index=True,
            column_config={
                "date": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
                "asset": "Activo",
                "price": st.column_config.NumberColumn("Precio", format="%.4f"),
                "index_100": st.column_config.NumberColumn("Base 100", format="%.1f"),
            },
        )
    source_notes({asset_class})


def volatility_section(volatility: pd.DataFrame, asset_class: str) -> None:
    st.subheader("Volatilidad anualizada")
    st.caption(
        "Desviación típica de las rentabilidades diarias en 30 sesiones, anualizada con 365 "
        "sesiones en cripto y 252 en bolsa y divisas."
    )
    if volatility.empty:
        st.info("No hay datos para este periodo.")
        return
    left, right = st.columns([3, 2], gap="large")
    with left:
        assets = CLASSES[asset_class][1]
        data = volatility[volatility["asset"].isin(assets)].assign(
            pct=lambda d: d["annualized_volatility_30"] * 100
        )
        st.altair_chart(line_chart(data, "pct", assets, ",.0f", "Volatilidad (%)"), width="stretch")
    with right:
        st.markdown("**Ranking actual**")
        last = latest_volatility(volatility)
        st.altair_chart(ranking_chart(last), width="stretch")
        st.caption("Último dato de cada activo: bolsa y divisas no cotizan el fin de semana.")
    source_notes(set(volatility["asset_class"]))
    st.caption(TRANSFORMED)


def _use_example() -> None:
    st.session_state["pending_question"] = st.session_state["example"]
    st.session_state["example"] = None  # sin selección, para no repetir la pregunta


def _answer_message(answer) -> dict:
    return {
        "role": "assistant",
        "outcome": answer.outcome,
        "content": answer.answer,
        "sql": answer.sql,
        "explanation": answer.explanation,
        "meta": (
            f"{answer.usage.get('calls', 0)} llamadas al modelo · "
            f"{answer.usage.get('cost_usd', 0):.4f} USD · "
            f"{answer.bytes_scanned:,} bytes leídos en Athena".replace(",", ".")
        ),
    }


def _show_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["content"])
            return
        if message["outcome"] == "respondida":
            st.markdown(message["content"])
        elif message["outcome"] in ("rechazada", "bloqueada"):
            st.warning(f"No se ha ejecutado ({message['outcome']}). {message['content']}")
        else:
            st.error(f"No se ha podido responder. {message['content']}")
        if message.get("sql"):
            with st.expander("SQL ejecutada"):
                st.code(message["sql"], language="sql")
                if message.get("explanation"):
                    st.caption(message["explanation"])
        st.caption(message["meta"])


def agent_section() -> None:
    st.subheader("Pregunta a los datos")
    st.caption(
        "Un agente con Claude escribe la SQL, la valida y la ejecuta en Athena con un rol de "
        "solo lectura. Cada pregunta cuesta en torno a 0,001 USD."
    )
    history = st.session_state.setdefault("chat", [])
    st.pills(
        "Prueba con",
        EXAMPLES,
        key="example",
        on_change=_use_example,
        label_visibility="collapsed",
    )
    conversation = st.container()  # los mensajes van aquí, por encima de la caja de texto
    with conversation:
        for message in history:
            _show_message(message)

    # Dentro de un contenedor, la caja de chat se queda en su sitio (en el cuerpo de la página,
    # Streamlit la fijaría al pie de la ventana)
    with st.container():
        typed = st.chat_input(
            "Escribe una pregunta sobre los datos...", max_chars=MAX_QUESTION_CHARS, key="question"
        )
    source_notes(set(CLASSES))  # las respuestas pueden usar cualquier fuente (D-039)
    question = typed or st.session_state.pop("pending_question", None)
    if not question:
        return
    question = question.strip()
    with conversation:
        if len(question) < 3:
            st.warning("Escribe una pregunta un poco más larga.")
            return
        try:
            agent = get_agent()
        except MissingApiKeyError:
            st.error("Falta ANTHROPIC_API_KEY en .env: los gráficos funcionan, pero el agente no.")
            return
        history.append({"role": "user", "content": question})
        _show_message(history[-1])
        with st.spinner("Consultando..."):
            history.append(_answer_message(agent.ask(question)))
        _show_message(history[-1])


# --- Página ------------------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(
        page_title="MarketPulse", page_icon="📈", layout="wide", initial_sidebar_state="collapsed"
    )
    try:
        prices_year = cached_prices(365)  # un año para las tarjetas (y el resto, de aquí)
    except Exception as e:  # sin credenciales o con la sesión de aws login caducada
        st.title("MarketPulse")
        st.error(
            "No se han podido leer los datos de AWS. Comprueba `aws login --profile marketpulse` "
            f"y `$env:AWS_PROFILE`. Detalle: {type(e).__name__}"
        )
        st.stop()

    header(prices_year)
    kpi_cards(asset_summary(prices_year))
    st.space("medium")

    asset_class, days = filters()
    since = prices_year["date"].max() - pd.Timedelta(days=days)
    evolution_section(prices_year[prices_year["date"] >= since], asset_class)
    st.divider()
    volatility_section(cached_volatility(days), asset_class)
    st.divider()
    agent_section()
    st.divider()
    st.caption(DISCLAIMER)


main()
