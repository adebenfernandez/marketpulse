"""Tests de bronze -> silver. Se crean ficheros bronze falsos en tmp_path con write_bronze."""

from datetime import UTC, date, datetime

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from marketpulse.common.config import load_watchlist
from marketpulse.common.storage import write_bronze
from marketpulse.transform import silver
from marketpulse.transform.tables import read_table

WATCHLIST = load_watchlist()
D20, D21 = date(2026, 10, 20), date(2026, 10, 21)


def av_payload(symbol: str, days: dict[str, str]) -> dict:
    """Respuesta mínima de Alpha Vantage: {día: cierre}, con precios como TEXTO (como la real)."""
    return {
        "Meta Data": {"2. Symbol": symbol, "5. Time Zone": "US/Eastern"},
        "Time Series (Daily)": {
            day: {"1. open": c, "2. high": c, "3. low": c, "4. close": c, "5. volume": "1000"}
            for day, c in days.items()
        },
    }


def cg_payload(ts: int, price: float) -> dict:
    return {
        "bitcoin": {
            "usd": price,
            "usd_market_cap": 1.6e12,
            "usd_24h_vol": 2.7e10,
            "usd_24h_change": 0.5,
            "last_updated_at": ts,
        }
    }


# --- Funciones por fuente ---------------------------------------------------------------


def test_stock_rows_convierte_texto_a_numero():
    rows = silver.stock_rows(av_payload("SPY", {"2026-10-19": "582.40"}), D20)
    assert rows == [
        {
            "date": date(2026, 10, 19),
            "symbol": "SPY",
            "open": 582.40,
            "high": 582.40,
            "low": 582.40,
            "close": 582.40,
            "volume": 1000,
            "ingest_date": D20,
        }
    ]


def test_stock_rows_con_precio_no_numerico_falla():
    with pytest.raises(ValueError):
        silver.stock_rows(av_payload("SPY", {"2026-10-19": "N/A"}), D20)


@pytest.mark.parametrize(
    ("ts", "dia_utc"),
    [
        (1792454399, date(2026, 10, 19)),  # 23:59:59 UTC del 19 (01:59 del 20 en España)
        (1792454400, date(2026, 10, 20)),  # 00:00:00 UTC del 20
    ],
)
def test_crypto_rows_usa_el_dia_utc(ts, dia_utc):
    (row,) = silver.crypto_rows(cg_payload(ts, 82000.0), D20, {"bitcoin": "BTC"})
    assert row["date"] == dia_utc
    assert row["price_at"] == datetime.fromtimestamp(ts, tz=UTC)
    assert row["price_at"].tzinfo is UTC  # instante con zona horaria explícita
    assert row["symbol"] == "BTC"
    assert row["vs_currency"] == "usd"


def test_fx_rows():
    payload = [{"date": "2026-10-16", "base": "EUR", "quote": "USD", "rate": 1.1253}]
    assert silver.fx_rows(payload, D20) == [
        {
            "date": date(2026, 10, 16),
            "base": "EUR",
            "quote": "USD",
            "rate": 1.1253,
            "ingest_date": D20,
        }
    ]


# --- Deduplicado ----------------------------------------------------------------------------


def test_el_viernes_repetido_el_fin_de_semana_queda_una_sola_vez(tmp_path):
    viernes = [{"date": "2026-10-16", "base": "EUR", "quote": "USD", "rate": 1.1253}]
    for dt in (date(2026, 10, 17), date(2026, 10, 18), date(2026, 10, 19)):  # sáb, dom, lun
        write_bronze("frankfurter", viernes, dt=dt, root=tmp_path)

    df = silver.build_fx_rates(tmp_path)
    assert len(df) == 1
    assert df.loc[0, "ingest_date"] == date(2026, 10, 19)  # se queda la descarga más reciente


def test_alpha_vantage_solapado_se_deduplica_y_gana_la_correccion(tmp_path):
    # Día 20: trae el 16 y el 19. Día 21: vuelve a traer el 19 (corregido) y añade el 20.
    write_bronze(
        "alphavantage",
        av_payload("SPY", {"2026-10-16": "100", "2026-10-19": "101"}),
        dt=D20,
        name="SPY",
        root=tmp_path,
    )
    write_bronze(
        "alphavantage",
        av_payload("SPY", {"2026-10-19": "101.5", "2026-10-20": "102"}),
        dt=D21,
        name="SPY",
        root=tmp_path,
    )

    df = silver.build_stock_prices(tmp_path)
    assert list(df["date"]) == [date(2026, 10, 16), date(2026, 10, 19), date(2026, 10, 20)]
    assert df.set_index("date").loc[date(2026, 10, 19), "close"] == 101.5  # la versión nueva


def test_dos_precios_cripto_el_mismo_dia_se_queda_el_ultimo(tmp_path):
    write_bronze("coingecko", cg_payload(1792454500, 81000.0), dt=D20, root=tmp_path)
    write_bronze("coingecko", cg_payload(1792490000, 82000.0), dt=D20, root=tmp_path)  # sobrescribe
    write_bronze(
        "coingecko", cg_payload(1792460000, 81500.0), dt=D21, root=tmp_path
    )  # mismo día UTC
    df = silver.build_crypto_prices(tmp_path, WATCHLIST)
    assert len(df) == 1
    assert df.loc[0, "price"] == 82000.0  # el más tardío (price_at), no el de la descarga más nueva


# --- Tabla completa en Parquet --------------------------------------------------------------


@pytest.fixture
def bronze(tmp_path):
    """Un bronze con las tres fuentes, como el de un día real."""
    fx = [{"date": "2026-10-20", "base": "EUR", "quote": "USD", "rate": 1.1215}]
    write_bronze("frankfurter", fx, dt=D20, root=tmp_path)
    write_bronze("coingecko", cg_payload(1792509891, 82388.0), dt=D20, root=tmp_path)
    for s in ("SPY", "VT"):
        write_bronze(
            "alphavantage", av_payload(s, {"2026-10-19": "10"}), dt=D20, name=s, root=tmp_path
        )
    return tmp_path


def test_build_silver_escribe_parquet_con_los_tipos_del_esquema(bronze):
    written = silver.build_silver(WATCHLIST, root=bronze)
    assert set(written) == {"fx_rates", "crypto_prices", "stock_prices"}

    path = bronze / "silver" / "stock_prices" / "year=2026" / "part-0.parquet"
    schema = pq.read_schema(path)
    assert schema.field("date").type == pa.date32()
    assert schema.field("close").type == pa.float64()
    assert schema.field("volume").type == pa.int64()
    crypto = pq.read_schema(bronze / "silver" / "crypto_prices" / "year=2026" / "part-0.parquet")
    assert crypto.field("price_at").type == pa.timestamp("us", tz="UTC")

    df = read_table(written["stock_prices"])
    assert sorted(df["symbol"]) == ["SPY", "VT"]


def test_reconstruir_dos_veces_da_lo_mismo_y_no_deja_restos(bronze):
    silver.build_silver(WATCHLIST, root=bronze)
    first = read_table(bronze / "silver" / "stock_prices")
    silver.build_silver(WATCHLIST, root=bronze)
    second = read_table(bronze / "silver" / "stock_prices")

    assert first.equals(second)
    leftovers = [p.name for p in (bronze / "silver").iterdir() if p.name.startswith(".")]
    assert leftovers == []  # ni .tmp ni .old
    files = sorted(p.name for p in (bronze / "silver" / "stock_prices").rglob("*.parquet"))
    assert files == ["part-0.parquet"]  # sustituido, no duplicado


def test_una_fuente_sin_datos_no_crea_tabla(tmp_path):
    fx = [{"date": "2026-10-20", "base": "EUR", "quote": "USD", "rate": 1.1}]
    write_bronze("frankfurter", fx, dt=D20, root=tmp_path)
    written = silver.build_silver(WATCHLIST, root=tmp_path)
    assert set(written) == {"fx_rates"}
