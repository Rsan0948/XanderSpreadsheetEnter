"""Simple local income tracker.

Runs a tiny Flask web app that lets you log income per location per date,
broken down by payment method, and saves everything to income.csv next to
this file. Just run it and your browser opens automatically.
"""

import csv
import json
import os
import threading
import webbrowser

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "income.csv")
LOCATIONS_PATH = os.path.join(BASE_DIR, "locations.json")

PAYMENT_METHODS = ["Cash", "Venmo", "PayPal", "Stripe", "Zelle"]
COLUMNS = ["Date", "Location"] + PAYMENT_METHODS + ["Total"]

app = Flask(__name__)
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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def state():
    return jsonify(
        payment_methods=PAYMENT_METHODS,
        columns=COLUMNS,
        locations=read_locations(),
        rows=read_rows(),
    )


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
    return jsonify(ok=True)


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
    return jsonify(ok=True, row=rows[idx])


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


def open_browser():
    webbrowser.open("http://127.0.0.1:5000/")


if __name__ == "__main__":
    ensure_csv()
    threading.Timer(1.2, open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
