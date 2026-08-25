from datetime import datetime
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
  qiymet_siyahisi = (
      ["1.68", "1.69", "1.70", "1.71", "1.72", "1.73", "1.74", "1.75"]
      if trade_type == "BUY"
      else [
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
  )

  intervallar = {q: {"say": 0, "usdt": 0.0} for q in qiymet_siyahisi}
  intervallar["Kənar"] = {"say": 0, "usdt": 0.0}

  for elan in elanlar:
    adv = elan.get("adv", {})
    qiymet = float(adv.get("price", 0))
    usdt_miqdari = float(
        adv.get("surplusAmount", adv.get("tradableQuantity", 0))
    )
    qiymet_str = f"{round(qiymet, 2):.2f}"

    if qiymet_str in intervallar:
      intervallar[qiymet_str]["say"] += 1
      intervallar[qiymet_str]["usdt"] += usdt_miqdari
    else:
      intervallar["Kənar"]["say"] += 1
      intervallar["Kənar"]["usdt"] += usdt_miqdari

  return {"cemi_elan": len(elanlar), "intervallar": intervallar}


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
