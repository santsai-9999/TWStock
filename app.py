"""台股即時五檔 - 後端
執行: python app.py          (抓證交所真實資料)
      python app.py --demo   (模擬資料，用來測試畫面)
"""
import os
import random
import re
import sys
import time

import requests
from flask import Flask, jsonify, send_file

app = Flask(__name__)
TWSE_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
DEMO = "--demo" in sys.argv or os.environ.get("DEMO") == "1"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_SECONDS = 3          # 同一檔股票 3 秒內不重複向證交所查詢，避免被封鎖
_cache = {}                # code -> (timestamp, data)
_exchange = {}             # code -> "tse" / "otc"，記住是上市或上櫃
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
           "Referer": "https://mis.twse.com.tw/stock/index.jsp"}
_session = None


def get_session():
    """證交所 MIS 需要先瀏覽首頁取得 cookie，之後的查詢才會回資料"""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        _session.get("https://mis.twse.com.tw/stock/index.jsp", timeout=5)
    return _session


def query_twse(ex_ch):
    params = {"ex_ch": ex_ch, "json": 1, "delay": 0, "_": int(time.time() * 1000)}
    r = get_session().get(TWSE_URL, params=params, timeout=5)
    r.raise_for_status()
    j = r.json()
    if not j.get("msgArray") and j.get("rtcode") != "0000":
        # cookie 可能過期，重新取得一次再試
        global _session
        _session = None
        r = get_session().get(TWSE_URL, params=params, timeout=5)
        r.raise_for_status()
        j = r.json()
    return j


def _split(s):
    return [x for x in (s or "").split("_") if x]


def _num(s):
    """'1005.0000' -> 1005.0；'-' 或空字串 -> None"""
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _book(prices, vols):
    """把 '1005.0000_1010.0000_' 和 '12_30_' 組成五檔；'-' 或 0 的欄位不會讓程式出錯"""
    rows = []
    for p, v in zip(_split(prices), _split(vols)):
        price, vol = _num(p), _num(v)
        if price is None and vol is None:
            continue
        rows.append({"price": price or None,      # 0 代表市價單
                     "vol": int(vol) if vol is not None else 0})
    return rows


def _parse(d):
    asks = _book(d.get("a"), d.get("f"))
    bids = _book(d.get("b"), d.get("g"))
    return {
        "code": d.get("c"),
        "name": d.get("n"),
        "fullname": d.get("nf"),
        "market": "上市" if d.get("ex") == "tse" else "上櫃",
        # z = 最近成交價；盤中這 5 秒內沒成交時 z 會是 "-"，改用 pz（前一筆成交價）
        "last": _num(d.get("z")) if _num(d.get("z")) is not None else _num(d.get("pz")),
        "prev": _num(d.get("y")),
        "open": _num(d.get("o")),
        "high": _num(d.get("h")),
        "low": _num(d.get("l")),
        "volume": _num(d.get("v")),
        "time": f'{d.get("d", "")} {d.get("t", "")}'.strip(),
        "asks": asks,   # 賣價：由低到高
        "bids": bids,   # 買價：由高到低
    }


def fetch_twse(code):
    order = [_exchange[code]] if code in _exchange else ["tse", "otc"]
    for ex in order:
        arr = query_twse(f"{ex}_{code}.tw").get("msgArray", [])
        if arr:
            _exchange[code] = ex
            return _parse(arr[0])
    return None


def fetch_demo(code):
    base = 100 + int(code[:4]) % 900 if code[:4].isdigit() else 100
    last = round(base + random.uniform(-2, 2), 1)
    tick = 0.5
    return {
        "code": code, "name": f"示範{code}", "fullname": "模擬資料", "market": "示範",
        "last": last, "prev": base, "open": base, "high": base + 3, "low": base - 3,
        "volume": random.randint(1000, 50000), "time": time.strftime("%Y%m%d %H:%M:%S"),
        "asks": [{"price": round(last + tick * (i + 1), 2), "vol": random.randint(1, 500)} for i in range(5)],
        "bids": [{"price": round(last - tick * i, 2), "vol": random.randint(1, 500)} for i in range(5)],
    }


@app.get("/api/quote/<code>")
def quote(code):
    code = code.strip().upper()
    if not re.fullmatch(r"[0-9A-Z]{4,6}", code):
        return jsonify({"error": "股票代號格式不正確"}), 400

    hit = _cache.get(code)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return jsonify(hit[1])
    try:
        data = fetch_demo(code) if DEMO else fetch_twse(code)
    except Exception as e:
        return jsonify({"error": f"資料來源連線失敗：{e}"}), 502
    if not data:
        return jsonify({"error": f"查無股票代號 {code}"}), 404
    _cache[code] = (time.time(), data)
    return jsonify(data)


@app.get("/api/raw/<code>")
def raw(code):
    """除錯用：直接顯示證交所回傳的原始資料"""
    code = code.strip().upper()
    try:
        return jsonify({ex: query_twse(f"{ex}_{code}.tw") for ex in ("tse", "otc")})
    except Exception as e:
        return jsonify({"error": repr(e)}), 502


@app.get("/")
def index():
    return send_file(os.path.join(HERE, "index.html"))


if __name__ == "__main__":
    print("示範模式（模擬資料）" if DEMO else "即時模式（證交所資料）")
    print("請開啟 http://127.0.0.1:5000")
    # 雲端主機會用 gunicorn 啟動，不會跑到這裡；本機執行才會用這段
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)))
