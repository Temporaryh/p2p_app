from datetime import datetime
from collections import defaultdict
from curl_cffi import requests
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import pytz

app = Flask(__name__)
CORS(app)  # Allows your browser to talk directly to Python


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


def intervallari_tehlil_et(trade_type="BUY"):
  elanlar = binance_p2p_cek(trade_type, max_pages=20)

  # Define base price range order
  if trade_type == "BUY":
    ana_qiymetler = [
        "1.68",
        "1.69",
        "1.70",
        "1.71",
        "1.72",
        "1.73",
        "1.74",
        "1.75",
    ]
  else:
    ana_qiymetler = [
        "1.68",
        "1.67",
        "1.66",
        "1.65",
        "1.64",
        "1.63",
        "1.62",
        "1.61",
        "1.60",
        "1.59",
    ]

  # Temporary storage to aggregate all price levels dynamically
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

  # Final response structure
  son_intervallar = {}
  diger_say = 0
  diger_usdt = 0.0

  # 1. Process main defined prices first (always keep them in order)
  for q in ana_qiymetler:
    son_intervallar[q] = qiymet_bag.pop(
        q, {"say": 0, "usdt": 0.0}
    )

  # 2. Process all external prices dynamically
  # Sort outer prices naturally depending on trade type
  kardani_qiymetler = sorted(
      qiymet_bag.keys(), reverse=(trade_type == "SELL")
  )

  for q in kardani_qiymetler:
    data = qiymet_bag[q]
    if data["usdt"] >= 5000:
      # Individual row for external prices with >= 5,000 USDT
      son_intervallar[q] = data
    else:
      # Group small liquidity into "Digər (< 5,000 USDT)"
      diger_say += data["say"]
      diger_usdt += data["usdt"]

  # 3. Append small volume aggregator if any exists
  if diger_say > 0:
    son_intervallar["Digər"] = {
        "say": diger_say,
        "usdt": diger_usdt,
    }

  return {"cemi_elan": len(elanlar), "intervallar": son_intervallar}


@app.route("/")
def serve_homepage():
  return send_from_directory(".", "index.html")


@app.route("/api/p2p-tehlil", methods=["GET"])
def api_tehlil():
  baku_tz = pytz.timezone("Asia/Baku")
  baku_time = datetime.now(baku_tz).strftime("%Y-%m-%d %H:%M:%S (Bakı vaxtı)")

  return jsonify({
      "timestamp": baku_time,
      "buy": intervallari_tehlil_et("BUY"),
      "sell": intervallari_tehlil_et("SELL"),
  })


if __name__ == "__main__":
  app.run(host="127.0.0.1", port=5000, debug=True)
