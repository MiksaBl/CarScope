import tkinter as tk
from tkinter import messagebox
import sqlite3
import threading
import time
import requests
import random
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

# =====================================
# TELEGRAM
# =====================================
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except:
        pass


# =====================================
# BRAND / MODEL PARSER
# =====================================
def extract_brand_model(url):
    try:
        slug = url.split("/offers/")[1].split("?")[0]
        parts = slug.split("-")

        brand = parts[0].capitalize() if len(parts) > 0 else "Unknown"
        model = parts[1].upper() if len(parts) > 1 else "Unknown"

        return brand, model
    except:
        return "Unknown", "Unknown"


# =====================================
# DATABASE (CHANGED ONLY HERE)
# =====================================
conn = sqlite3.connect("CarRating.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS radars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    url TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS cars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT,
    model TEXT,
    price INTEGER,
    km INTEGER,
    year INTEGER,
    url TEXT UNIQUE,
    created_at TEXT
)
""")

conn.commit()


# =====================================
# SAVE CAR
# =====================================
def save_car(brand, model, price, km, year, url):
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO cars
        (brand, model, price, km, year, url, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            brand,
            model,
            price,
            km,
            year,
            url,
            datetime.now().isoformat()
        ))
        conn.commit()
    except:
        pass
# =====================================
# SIMILAR CARS QUERY
# =====================================
def get_similar_cars(brand, model, year):
    cursor.execute("""
        SELECT price, km, year FROM cars
        WHERE brand=? AND model=?
    """, (brand, model))

    rows = cursor.fetchall()

    similar = []

    for price, km, y in rows:
        if price is None or km is None or y is None:
            continue

        if abs(y - year) <= 2:
            similar.append((price, km, y))

    return similar
   
# =====================================
# CAR ANALYTICS ENGINE (ADDED)
# =====================================

def get_km_group(km):
    if km is None:
        return "unknown"
    if km <= 15000:
        return "0-15k"
    elif km <= 50000:
        return "15k-50k"
    elif km <= 100000:
        return "50k-100k"
    elif km <= 200000:
        return "100k-200k"
    elif km <= 300000:
        return "200k-300k"
    elif km <= 400000:
        return "300k-400k"
    else:
        return "400k+"
    
def median(lst):
    lst = sorted(lst)
    n = len(lst)
    if n == 0:
        return 0
    mid = n // 2
    if n % 2 == 0:
        return (lst[mid - 1] + lst[mid]) / 2
    return lst[mid]

def calculate_scores(car_price, car_km, car_year, similar_cars):

    if len(similar_cars) < 2:
        return None

    prices = [x[0] for x in similar_cars]
    kms = [x[1] for x in similar_cars]
    years = [x[2] for x in similar_cars]

    median_price = median(prices)
    avg_km = sum(kms) / len(kms)
    avg_year = sum(years) / len(years)

    price_score = (median_price / car_price) * 50 if car_price else 0
    km_score = (avg_km / car_km) * 50 if car_km else 0
    year_score = (car_year / avg_year) * 50 if car_year else 0

    price_score = max(0, min(price_score, 100))
    km_score = max(0, min(km_score, 100))
    year_score = max(0, min(year_score, 100))

    final_score = (
        price_score * 0.5 +
        km_score * 0.3 +
        year_score * 0.2
    )

    price_diff = car_price - median_price
    price_diff_percent = (price_diff / median_price) * 100 if median_price else 0

    scam = (
        price_diff_percent < -30 and
        car_km < 100000 and
        car_year > 2018
    )

    if final_score >= 90:
        label = "🚨 ULTRA DEAL"
    elif final_score >= 80:
        label = "🔥 TOP DEAL"
    elif final_score >= 65:
        label = "👍 GOOD DEAL"
    elif final_score >= 50:
        label = "🤏 OK"
    else:
        label = "❌ BAD"

    return {
        "median_price": median_price,
        "avg_km": avg_km,
        "avg_year": avg_year,
        "price_score": price_score,
        "km_score": km_score,
        "year_score": year_score,
        "final_score": final_score,
        "price_diff": price_diff,
        "price_diff_percent": price_diff_percent,
        "label": label,
        "scam": scam
    }
    

# =====================================
# ✔ ADDED: URL NORMALIZER
# =====================================
def normalize_url(url):
    try:
        return url.split("?")[0]
    except:
        return url


# =====================================
# GLOBALS
# =====================================
running = False
checkboxes = []
seen_global = set()
queue = []
MAX_PER_CYCLE = 10


# =====================================
# LOG
# =====================================
def log(text):
    logs.insert(tk.END, text + "\n")
    logs.see(tk.END)


# =====================================
# SAFE INT
# =====================================
def safe_int(text):
    try:
        if not text:
            return None
        digits = "".join([c for c in str(text) if c.isdigit()])
        return int(digits) if digits else None
    except:
        return None


# =====================================
# LISTINGS EXTRACTOR
# =====================================
def extract_listings(page):
    links = set()

    anchors = page.query_selector_all("a")

    for a in anchors:
        try:
            href = a.get_attribute("href")
            if not href:
                continue

            if "offer" in href or "autoscout24" in href:
                if href.startswith("/"):
                    href = "https://www.autoscout24.com" + href

                if "autoscout24.com" in href:
                    links.add(normalize_url(href))   # FIX ADDED

        except:
            continue

    return links


# =====================================
# CAR DATA EXTRACTOR
# =====================================
def extract_car_data(page):

    price = None
    km = None
    year = None

    try:
        page.wait_for_timeout(2000)

        price_el = page.query_selector('[data-testid*="price"]')
        if price_el:
            price = safe_int(price_el.inner_text())

        km = None

        km_selectors = [
            '[data-testid*="mileage"]',
            '[data-testid*="kilomet"]',
            '[data-testid*="odometer"]'
        ]

        for sel in km_selectors:
            el = page.query_selector(sel)
            if el:
                km = safe_int(el.inner_text())
                if km and 100 <= km <= 1_000_000:
                    break
                else:
                    km = None

        if not km:
            text = page.inner_text("body")

            matches = re.findall(r"(\d{1,3}(?:[.,]\d{3})+)\s?km", text)

            cleaned = []
            for m in matches:
                val = safe_int(m)
                if val and 100 <= val <= 1_000_000:
                    cleaned.append(val)

            if cleaned:
                km = min(cleaned)

        CURRENT_YEAR = datetime.now().year

        year = None

        year_el = page.query_selector('[data-testid*="registration"]')
        if year_el:
            year = safe_int(year_el.inner_text())

        if not year:
            text = page.inner_text("body")

            years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
            years = [int(y) for y in years if 1995 <= int(y) <= CURRENT_YEAR]

            if years:
                year = years[0]

    except:
        pass

    return price, km, year


# =====================================
# RADAR LOOP (FIXED DUPLICATES)
# =====================================
def radar_loop():

    global running, seen_global, queue
    running = True
    seen_global.clear()
    queue.clear()

    selected = [x for x in checkboxes if x["var"].get()]

    if not selected:
        messagebox.showerror("Error", "Select at least one radar")
        running = False
        return

    log("🚗 RADAR STARTED")
    send_telegram("🚗 Radar STARTED")

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        first_run = True

        while running:

            try:
                for r in selected:

                    name = r["name"]
                    url = r["url"]

                    log(f"🔄 OPEN {name}")

                    page.goto(url, timeout=60000)
                    page.wait_for_timeout(4000)

                    page.mouse.wheel(0, 3000)
                    time.sleep(2)

                    listings = extract_listings(page)
                    new_links = listings - seen_global

                    if first_run:
                        log(f"📊 BASELINE {name}: {len(listings)}")
                    else:

                        queue.extend(list(new_links))

                        for link in queue[:MAX_PER_CYCLE]:

                            try:
                                time.sleep(random.uniform(2.5, 5.5))

                                clean_url = normalize_url(link)

                                if clean_url in seen_global:
                                    continue

                                page.goto(clean_url, timeout=60000)
                                page.wait_for_timeout(3000)

                                # =========================
                                # CAR DATA + SCORE ENGINE
                                # =========================
                                price, km, year = extract_car_data(page)
                                brand, model = extract_brand_model(clean_url)

                                similar = get_similar_cars(brand, model, year)

                                score_data = calculate_scores(price, km, year, similar)

                                if score_data is None:
                                    score_data = {
                                        "median_price": 0,
                                        "price_diff": 0,
                                        "price_diff_percent": 0,
                                        "price_score": 0,
                                        "km_score": 0,
                                        "year_score": 0,
                                        "final_score": None,
                                        "label": "NOT ENOUGH DATA",
                                        "scam": False
                                    }

                                save_car(brand, model, price, km, year, clean_url)

                                seen_global.add(clean_url)

                                msg = f"""
🚗 NEW {name} FOUND!

🏷 Brand: {brand}
🚘 Model: {model}

🔗 {clean_url}

💰 Price: {price if price else "N/A"}€
📊 KM: {km if km else "N/A"}
📅 Year: {year if year else "N/A"}

📊 SCORE: {score_data["final_score"]:.2f}
🏷 LABEL: {score_data["label"]}
🚨 SCAM: {score_data["scam"]}
"""

                                # ➕ DODATAK (OVDE IDE)
                                if score_data:
                                    msg += f"""

📊 Market median: {score_data['median_price']:.0f}€
📉 Difference: {score_data['price_diff']:.0f}€ ({score_data['price_diff_percent']:.1f}%)

🧠 SCORE:
💰 Price: {score_data['price_score']:.0f}
📊 KM: {score_data['km_score']:.0f}
📅 Year: {score_data['year_score']:.0f}

🏆 FINAL SCORE: {score_data['final_score']:.2f}/100 ({score_data['label']})
"""

                                    if score_data["scam"]:
                                        msg += "\n⚠ POSSIBLE SCAM DETECTED"

                                    if score_data["final_score"] and score_data["final_score"] >= 90:
                                        send_telegram("🚨 ULTRA DEAL DETECTED 🚨")

                                log(msg)
                                send_telegram(msg)

                            except:
                                continue

                        queue.clear()

                    seen_global.update(listings)

                first_run = False

            except Exception as e:
                log(f"ERROR: {e}")

            log("⏳ WAIT 30s...\n")
            time.sleep(30)
# =====================================
# START / STOP
# =====================================
def start():
    t = threading.Thread(target=radar_loop)
    t.daemon = True
    t.start()

def stop():
    global running
    running = False
    log("🛑 STOPPED")


# =====================================
# DB UI (UNCHANGED)
# =====================================
def add_radar():
    name = name_entry.get()
    url = url_entry.get()

    if not name or not url:
        return

    cursor.execute("INSERT INTO radars(name, url) VALUES (?, ?)", (name, url))
    conn.commit()

    name_entry.delete(0, tk.END)
    url_entry.delete(0, tk.END)

    refresh()


def delete_selected():
    for x in checkboxes:
        if x["var"].get():
            cursor.execute("DELETE FROM radars WHERE id=?", (x["id"],))

    conn.commit()
    refresh()


def refresh():
    for w in radar_frame.winfo_children():
        w.destroy()

    checkboxes.clear()

    cursor.execute("SELECT id, name, url FROM radars")
    rows = cursor.fetchall()

    for r in rows:
        var = tk.BooleanVar()

        cb = tk.Checkbutton(
            radar_frame,
            text=r[1],
            variable=var,
            font=("Segoe UI", 10),
            bg="#0f1115",
            fg="#d0d0d0",
            activebackground="#0f1115",
            activeforeground="#ffffff",
            selectcolor="#1e2430"
        )
        cb.pack(anchor="w")

        checkboxes.append({
            "id": r[0],
            "name": r[1],
            "url": r[2],
            "var": var
        })


# =====================================
# GUI (UNCHANGED)
# =====================================
root = tk.Tk()
root.title("🚗 Auto Radar")
root.geometry("900x700")
root.configure(bg="#0f1115")

title = tk.Label(root, text="🚗 Auto Radar",
                 font=("Segoe UI", 22, "bold"),
                 fg="#e6e6e6", bg="#0f1115")
title.pack(pady=12)

frame = tk.Frame(root, bg="#161a22", padx=10, pady=10)
frame.pack(pady=10)

name_entry = tk.Entry(frame, width=25)
name_entry.grid(row=0, column=0)

url_entry = tk.Entry(frame, width=60)
url_entry.grid(row=0, column=1)

tk.Button(frame, text="ADD", command=add_radar,
          bg="#2a7fff", fg="white").grid(row=0, column=2)

radar_frame = tk.LabelFrame(root, text="Saved Radars",
                            bg="#0f1115", fg="#bdbdbd")
radar_frame.pack(fill="x", padx=12, pady=12)

btn = tk.Frame(root, bg="#0f1115")
btn.pack(pady=10)

tk.Button(btn, text="START", command=start,
          bg="#1f8f4e", fg="white", width=12).grid(row=0, column=0)

tk.Button(btn, text="STOP", command=stop,
          bg="#b23b3b", fg="white", width=12).grid(row=0, column=1)

tk.Button(btn, text="DELETE", command=delete_selected,
          bg="#444a55", fg="white", width=12).grid(row=0, column=2)

logs = tk.Text(root, bg="#0b0d10", fg="#d6d6d6")
logs.pack(fill="both", expand=True, padx=12, pady=12)

refresh()
root.mainloop()