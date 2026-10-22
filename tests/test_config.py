import pytest

from marketpulse.common.config import ConfigError, load_watchlist, parse_watchlist


def test_la_watchlist_real_se_carga():
    wl = load_watchlist()  # config/watchlist.yaml (pytest se ejecuta desde la raíz)
    assert wl.fx.base == "USD"  # ROTO A PROPÓSITO (6.3): no fusionar
    assert "USD" in wl.fx.quotes
    assert [a.symbol for a in wl.crypto.assets] == ["BTC", "ETH", "SOL"]
    assert len(wl.stocks.assets) >= 3


def test_normaliza_mayusculas_y_minusculas():
    wl = parse_watchlist(
        {
            "fx": {"base": "eur", "quotes": ["usd"]},
            "crypto": {
                "vs_currency": "USD",
                "assets": [{"symbol": "btc", "coingecko_id": "Bitcoin"}],
            },
            "stocks": {"assets": [{"symbol": "spy"}]},
        }
    )
    assert wl.fx.base == "EUR"
    assert wl.fx.quotes == ("USD",)
    assert wl.crypto.vs_currency == "usd"
    assert wl.crypto.assets[0].coingecko_id == "bitcoin"
    assert wl.stocks.assets[0].symbol == "SPY"


def test_falta_una_seccion_da_error_claro():
    with pytest.raises(ConfigError, match="stocks"):
        parse_watchlist({"fx": {"base": "EUR", "quotes": ["USD"]}, "crypto": {}})


def test_lista_vacia_da_error():
    with pytest.raises(ConfigError, match="fx.quotes"):
        parse_watchlist(
            {
                "fx": {"base": "EUR", "quotes": []},
                "crypto": {
                    "vs_currency": "usd",
                    "assets": [{"symbol": "BTC", "coingecko_id": "bitcoin"}],
                },
                "stocks": {"assets": [{"symbol": "SPY"}]},
            }
        )
