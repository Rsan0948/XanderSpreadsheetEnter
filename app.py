"""Simple local income tracker.

Runs a tiny Flask web app that lets you log income per location per date,
broken down by payment method, and saves everything to income.csv next to
this file. Just run it and your browser opens automatically.
"""

import csv
import json
import os
import socket
import threading
import urllib.request
import webbrowser

from flask import Flask, jsonify, render_template, request

HOST = "127.0.0.1"
PORT = 5000
URL = f"http://{HOST}:{PORT}/"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "income.csv")
LOCATIONS_PATH = os.path.join(BASE_DIR, "locations.json")
LOG_PATH = os.path.join(BASE_DIR, "setup.log")


def log(msg):
    """Append a timestamped line to setup.log; never crash if it fails."""
    try:
        import datetime
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {msg}\n")
    except OSError:
        pass

PAYMENT_METHODS = ["Cash", "Venmo", "PayPal", "Stripe", "Zelle"]
COLUMNS = ["Date", "Location"] + PAYMENT_METHODS + ["Total"]

# Bump this whenever the page changes so you can confirm at a glance
# (shown in the page footer) which version is actually being served.
APP_VERSION = "2026-05-18.1"

app = Flask(__name__)
# Re-read templates on every request so swapping index.html only needs a
# browser refresh - no app restart required.
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
_lock = threading.Lock()


def _money(value):
    """Parse a value into a non-negative float, defaulting to 0.0."""
    try:
        n = float(str(value).replace(",", "").replace("$", "").strip() or 0)
    except ValueError:
        n = 0.0
    return round(max(n, 0.0), 2)


def ensure_csv():
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(COLUMNS)


def read_rows():
    ensure_csv()
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append({c: r.get(c, "") for c in COLUMNS})
        return rows


def write_rows(rows):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in COLUMNS})


def recalc(row):
    total = sum(_money(row.get(m, 0)) for m in PAYMENT_METHODS)
    for m in PAYMENT_METHODS:
        row[m] = f"{_money(row.get(m, 0)):.2f}"
    row["Total"] = f"{total:.2f}"
    return row


def read_locations():
    locs = set()
    if os.path.exists(LOCATIONS_PATH):
        try:
            with open(LOCATIONS_PATH, encoding="utf-8") as f:
                locs.update(json.load(f))
        except (ValueError, OSError):
            pass
    for r in read_rows():
        if r.get("Location", "").strip():
            locs.add(r["Location"].strip())
    return sorted(locs, key=str.lower)


def save_location(name):
    name = (name or "").strip()
    if not name:
        return
    locs = set(read_locations())
    locs.add(name)
    with open(LOCATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(locs, key=str.lower), f, indent=2)


def get_state():
    return {
        "payment_methods": PAYMENT_METHODS,
        "columns": COLUMNS,
        "locations": read_locations(),
        "rows": read_rows(),
    }


@app.route("/")
def index():
    # Embed the initial state so the page paints data on first paint,
    # with no extra round trip to /api/state.
    payload = json.dumps(get_state()).replace("<", "\\u003c")
    return render_template("index.html", initial_state=payload, version=APP_VERSION)


@app.route("/api/state")
def state():
    return jsonify(**get_state())


@app.route("/api/entry", methods=["POST"])
def add_entry():
    data = request.get_json(force=True)
    with _lock:
        rows = read_rows()
        row = {
            "Date": (data.get("Date") or "").strip(),
            "Location": (data.get("Location") or "").strip(),
        }
        for m in PAYMENT_METHODS:
            row[m] = data.get(m, 0)
        recalc(row)
        if row["Location"]:
            save_location(row["Location"])
        rows.append(row)
        write_rows(rows)
        new_index = len(rows) - 1
    return jsonify(ok=True, row=row, index=new_index, locations=read_locations())


@app.route("/api/update", methods=["POST"])
def update_cell():
    data = request.get_json(force=True)
    idx = int(data.get("index", -1))
    col = data.get("column")
    value = data.get("value", "")
    if col not in COLUMNS or col == "Total":
        return jsonify(ok=False, error="That column can't be edited."), 400
    with _lock:
        rows = read_rows()
        if not (0 <= idx < len(rows)):
            return jsonify(ok=False, error="Row not found."), 404
        rows[idx][col] = value.strip() if isinstance(value, str) else value
        recalc(rows[idx])
        if col == "Location" and rows[idx]["Location"]:
            save_location(rows[idx]["Location"])
        write_rows(rows)
        result = rows[idx]
    return jsonify(ok=True, row=result, locations=read_locations())


@app.route("/api/delete", methods=["POST"])
def delete_row():
    data = request.get_json(force=True)
    idx = int(data.get("index", -1))
    with _lock:
        rows = read_rows()
        if not (0 <= idx < len(rows)):
            return jsonify(ok=False, error="Row not found."), 404
        rows.pop(idx)
        write_rows(rows)
    return jsonify(ok=True)


@app.route("/api/location", methods=["POST"])
def add_location():
    data = request.get_json(force=True)
    with _lock:
        save_location(data.get("name"))
    return jsonify(ok=True, locations=read_locations())


def port_in_use():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        return s.connect_ex((HOST, PORT)) == 0


def open_when_ready():
    """Open the browser the instant the server responds (not a fixed wait)."""
    for _ in range(200):  # up to ~10s, but typically fires in well under 1s
        try:
            with urllib.request.urlopen(URL, timeout=0.25):
                break
        except OSError:
            pass
    webbrowser.open(URL)


if __name__ == "__main__":
    # Already running? Just surface the existing instance instead of crashing.
    if port_in_use():
        log("Already running on port %d - opened the existing window." % PORT)
        webbrowser.open(URL)
    else:
        ensure_csv()
        log("App starting, serving at %s (data file: %s)" % (URL, CSV_PATH))
        threading.Thread(target=open_when_ready, daemon=True).start()
        try:
            app.run(host=HOST, port=PORT, debug=False, threaded=True)
        except Exception as e:  # noqa: BLE001 - log anything before exiting
            log("App stopped with an error: %r" % e)
            raise
