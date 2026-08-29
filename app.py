Here is the updated implementation that adds a 2nd set of tables to analyze market liquidity broken down by Minimum Limit (AZN) for both USDT Sellers (BUY) and Buyers (SELL), exactly as your father requested.

Key Changes Made
New Analytics Function (min_limit_tehlil_et):
Groups ads into 4 min-limit buckets:

< 50 AZN

51 – 100 AZN

101 – 200 AZN

> 200 AZN

Calculates the Seller/Buyer count (say) and Total Capital (usdt) for each tier.

Combined API Output (/api/p2p-tehlil):
The response now delivers both Table 1 (Price Brackets) and Table 2 (Minimum Limit Buckets).

Updated UI (index.html):
Adds a secondary section for "Təhlil 2: Minimum Limitə Göyrə Bölgü" displaying side-by-side tables for BUY and SELL ads.

1. Updated app.py
Python
from datetime import datetime
from collections import defaultdict
from curl_cffi import requests
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import pytz

app = Flask(__name__)
CORS(app)


def binance_p2p_cek(trade_type="BUY", max_pages=20):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
        "Origin": "https://p2p.binance.com",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"
        ),
        "clienttype": "web",
    }
    butun_elanlar = []

    for page in range(1, max_pages + 1):
        payload = {
            "asset": "USDT",
            "fiat": "AZN",
            "merchantCheck": False,
            "page": page,
            "rows": 20,
            "tradeType": trade_type,
            "payTypes": [],
            "publisherType": None,
            "classifies": ["mass", "profession"],
        }
        try:
            res = requests.post(
                url, json=payload, headers=headers, impersonate="chrome120"
            )
            if res.status_code != 200:
                break
            res_json = res.json()
            if res_json.get("code") == "000000" and res_json.get("data"):
                elanlar = res_json["data"]
                if not elanlar:
                    break
                butun_elanlar.extend(elanlar)
            else:
                break
        except Exception:
            break
    return butun_elanlar


def intervallari_tehlil_et(elanlar, trade_type="BUY"):
    """Table 1: Price bracket analysis"""
    if trade_type == "BUY":
        ana_qiymetler = [
            "1.68", "1.69", "1.70", "1.71", "1.72", "1.73", "1.74", "1.75"
        ]
    else:
        ana_qiymetler = [
            "1.68", "1.67", "1.66", "1.65", "1.64", "1.63", "1.62", "1.61", "1.60", "1.59"
        ]

    qiymet_bag = defaultdict(lambda: {"say": 0, "usdt": 0.0})

    for elan in elanlar:
        adv = elan.get("adv", {})
        qiymet = float(adv.get("price", 0))
        usdt_miqdari = float(
            adv.get("surplusAmount", adv.get("tradableQuantity", 0))
        )
        qiymet_str = f"{round(qiymet, 2):.2f}"

        qiymet_bag[qiymet_str]["say"] += 1
        qiymet_bag[qiymet_str]["usdt"] += usdt_miqdari

    son_intervallar = {}
    diger_say = 0
    diger_usdt = 0.0

    for q in ana_qiymetler:
        son_intervallar[q] = qiymet_bag.pop(q, {"say": 0, "usdt": 0.0})

    kardani_qiymetler = sorted(
        qiymet_bag.keys(), reverse=(trade_type == "SELL")
    )

    for q in kardani_qiymetler:
        data = qiymet_bag[q]
        if data["usdt"] >= 1000:
            son_intervallar[q] = data
        else:
            diger_say += data["say"]
            diger_usdt += data["usdt"]

    if diger_say > 0:
        son_intervallar["Digər"] = {
            "say": diger_say,
            "usdt": diger_usdt,
        }

    return {"cemi_elan": len(elanlar), "intervallar": son_intervallar}


def min_limit_tehlil_et(elanlar):
    """Table 2: Minimum Limit analysis (AZN brackets)"""
    limit_buckets = {
        "< 50 AZN": {"say": 0, "usdt": 0.0},
        "51 - 100 AZN": {"say": 0, "usdt": 0.0},
        "101 - 200 AZN": {"say": 0, "usdt": 0.0},
        "> 200 AZN": {"say": 0, "usdt": 0.0},
    }

    for elan in elanlar:
        adv = elan.get("adv", {})
        min_limit = float(adv.get("minSingleTransAmount", 0))
        usdt_miqdari = float(
            adv.get("surplusAmount", adv.get("tradableQuantity", 0))
        )

        if min_limit <= 50:
            key = "< 50 AZN"
        elif 51 <= min_limit <= 100:
            key = "51 - 100 AZN"
        elif 101 <= min_limit <= 200:
            key = "101 - 200 AZN"
        else:
            key = "> 200 AZN"

        limit_buckets[key]["say"] += 1
        limit_buckets[key]["usdt"] += usdt_miqdari

    return limit_buckets


@app.route("/")
def serve_homepage():
    return send_from_directory(".", "index.html")


@app.route("/api/p2p-tehlil", methods=["GET"])
def api_tehlil():
    baku_tz = pytz.timezone("Asia/Baku")
    baku_time = datetime.now(baku_tz).strftime("%Y-%m-%d %H:%M:%S (Bakı vaxtı)")

    buy_elanlar = binance_p2p_cek("BUY", max_pages=20)
    sell_elanlar = binance_p2p_cek("SELL", max_pages=20)

    return jsonify({
        "timestamp": baku_time,
        "buy": intervallari_tehlil_et(buy_elanlar, "BUY"),
        "sell": intervallari_tehlil_et(sell_elanlar, "SELL"),
        "limit_buy": min_limit_tehlil_et(buy_elanlar),
        "limit_sell": min_limit_tehlil_et(sell_elanlar),
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
