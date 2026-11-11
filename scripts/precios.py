"""Busca los precios de cada activo y arma la carpeta `site/` que se publica.

Lo corre GitHub Actions cada ~15 minutos. No necesita llaves ni cuentas:
- Acciones: Yahoo Finance
- Cripto: CoinGecko
Si una fuente falla, se queda el último precio conocido (o ninguno) y la página
lo indica; nunca se rompe la publicación por un precio.
"""
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
UA = {"User-Agent": "Mozilla/5.0 (portfolio-page)"}


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def main():
    data = json.loads((ROOT / "data.json").read_text())
    prices = {}

    for a in data["assets"]:
        sym = a.get("yahoo")
        if not sym:
            continue
        try:
            meta = get_json(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1d"
            )["chart"]["result"][0]["meta"]
            prices[a["id"]] = {
                "price": meta["regularMarketPrice"],
                "at": datetime.fromtimestamp(meta["regularMarketTime"], timezone.utc).isoformat(),
            }
        except Exception as e:  # noqa: BLE001
            print(f"Sin precio para {sym}: {e}")

    ids = {a["coingecko"]: a["id"] for a in data["assets"] if a.get("coingecko")}
    if ids:
        try:
            cg = get_json(
                "https://api.coingecko.com/api/v3/simple/price?vs_currencies=usd&ids="
                + ",".join(ids)
            )
            now = datetime.now(timezone.utc).isoformat()
            for cg_id, asset_id in ids.items():
                if cg_id in cg:
                    prices[asset_id] = {"price": cg[cg_id]["usd"], "at": now}
        except Exception as e:  # noqa: BLE001
            print(f"Sin precios de cripto: {e}")

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    for f in ("index.html", "data.json"):
        shutil.copy(ROOT / f, SITE / f)
    (SITE / "prices.json").write_text(
        json.dumps({"updated": datetime.now(timezone.utc).isoformat(), "prices": prices}, indent=2)
    )
    print(json.dumps(prices, indent=2))


if __name__ == "__main__":
    main()
