import aiohttp
import asyncio
import os
import threading
import tkinter as tk
from tkinter import ttk
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import shutil
import fitz  

#Config

BASE_URL = "https://pastpapers.papacambridge.com"

SUBJECTS = {
    "Physics": "physics-9702",
    "Chemistry": "chemistry-9701",
    "Computer Science": "computer-science-for-first-examination-in-2021-9618",
    "Maths": "mathematics-9709",
    "Biology": "biology-9700",
    "English General Paper": "english-general-paper-8021",
    "Economics": "economics-9708",
    "Business": "business-9609",
    "Accounting": "accounting-9706"
}

#UI SETUP

root = tk.Tk()
root.title("Cambridge Past Paper Downloader")
root.geometry("760x560")
root.configure(bg="#0b1220")
root.resizable(False, False)

FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_TEXT = ("Segoe UI", 11)
FONT_LOG = ("Consolas", 9)

ACCENT = "#38bdf8"
CARD_BG = "#111827"
LOG_BG = "#020617"

card = tk.Frame(root, bg=CARD_BG)
card.place(relx=0.5, rely=0.5, anchor="center", width=720, height=520)

tk.Label(card, text="Cambridge Past Paper Downloader",
         font=FONT_TITLE, fg="white", bg=CARD_BG).pack(pady=(16, 5))

tk.Label(card, text="Download & auto-sort AS/A Level past papers",
         font=FONT_TEXT, fg="#94a3b8", bg=CARD_BG).pack()

controls = tk.Frame(card, bg=CARD_BG)
controls.pack(pady=15)

tk.Label(controls, text="Subject", fg="white", bg=CARD_BG).grid(row=0, column=0, padx=6)
subject_var = tk.StringVar()
subject_box = ttk.Combobox(
    controls, textvariable=subject_var,
    values=list(SUBJECTS.keys()), state="readonly", width=28
)
subject_box.grid(row=0, column=1, padx=6)
subject_box.current(0)

tk.Label(controls, text="From", fg="white", bg=CARD_BG).grid(row=0, column=2, padx=6)
year_from = ttk.Combobox(controls, values=[str(y) for y in range(2000, 2026)], width=6)
year_from.grid(row=0, column=3)
year_from.set("2018")

tk.Label(controls, text="To", fg="white", bg=CARD_BG).grid(row=0, column=4, padx=6)
year_to = ttk.Combobox(controls, values=[str(y) for y in range(2000, 2026)], width=6)
year_to.grid(row=0, column=5)
year_to.set("2024")

# Download type
tk.Label(controls, text="Type", fg="white", bg=CARD_BG).grid(row=1, column=0, padx=6, pady=8)
type_var = tk.StringVar(value="ALL")
type_box = ttk.Combobox(
    controls,
    textvariable=type_var,
    values=["QP", "MS", "BOTH", "ALL"],
    state="readonly",
    width=10
)
type_box.grid(row=1, column=1, padx=6)
type_box.current(3)

log_box = tk.Text(card, height=16, width=86,
                  bg=LOG_BG, fg="#e5e7eb",
                  font=FONT_LOG, bd=0)
log_box.pack(pady=10)
log_box.config(state="disabled")

def log(msg, color="#e5e7eb"):
    log_box.config(state="normal")
    log_box.insert(tk.END, msg + "\n")
    log_box.tag_add(color, "end-2l", "end-1l")
    log_box.tag_config(color, foreground=color)
    log_box.see(tk.END)
    log_box.config(state="disabled")

# Years feature

def year_allowed(filename, y_from, y_to):
    matches = re.findall(r"[msw](\d{2})", filename.lower())
    if not matches:
        return True
    for yy in matches:
        year = 2000 + int(yy)
        if y_from <= year <= y_to:
            return True
    return False

def get_first_page_text(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = doc.load_page(0).get_text().lower()
        doc.close()
        return text
    except:
        return ""

#Paper number detector
def detect_paper(text):
    match = re.search(r"paper\s*([1-5])", text)
    return f"Paper {match.group(1)}" if match else "Other Papers"

#Async core

async def fetch(session, url):
    try:
        async with session.get(url) as r:
            return await r.text() if r.status == 200 else ""
    except:
        return ""

async def download_file(session, file_url, subject, y_from, y_to, mode):
    if not file_url.startswith("http"):
        file_url = urljoin(BASE_URL, file_url)

    filename = file_url.split("/")[-1].lower()

    if not year_allowed(filename, y_from, y_to):
        return

    # Sorts files
    if mode == "QP" and "qp" not in filename:
        return
    if mode == "MS" and "ms" not in filename:
        return
    if mode == "BOTH" and not any(x in filename for x in ("qp", "ms")):
        return

    temp_dir = os.path.join(subject, "_temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, filename)

    if os.path.exists(temp_path):
        return

    try:
        async with session.get(file_url) as r:
            if r.status != 200:
                return
            with open(temp_path, "wb") as f:
                f.write(await r.read())

        paper = "Papers"
        if mode != "ALL":
            text = get_first_page_text(temp_path)
            paper = detect_paper(text)

        # ---- DESTINATION ----
        if mode == "QP":
            dest = os.path.join(subject, paper, "Question Papers")
        elif mode == "MS":
            dest = os.path.join(subject, paper, "Mark Schemes")
        elif mode == "BOTH":
            dest = os.path.join(
                subject,
                paper,
                "Question Papers" if "qp" in filename else "Mark Schemes"
            )
        else:  # ALL
            if "qp" in filename:
                dest = os.path.join(subject, paper, "Question Papers")
            elif "ms" in filename:
                dest = os.path.join(subject, paper, "Mark Schemes")
            else:
                dest = os.path.join(subject, paper, "Misc")

        os.makedirs(dest, exist_ok=True)
        shutil.move(temp_path, os.path.join(dest, filename))

        log(f"✔ {paper} | {filename}", "#22c55e")

    except:
        log(f"❌ Error: {filename}", "#ef4444")

async def process_page(session, url, subject, y_from, y_to, mode):
    soup = BeautifulSoup(await fetch(session, url), "lxml")
    links = soup.select('a[href$=".pdf"], a[href$=".zip"]')

    await asyncio.gather(*[
        download_file(session, link["href"], subject, y_from, y_to, mode)
        for link in links
    ])

async def main_async(subject, y_from, y_to, mode):
    subject_dir = subject.lower()
    os.makedirs(subject_dir, exist_ok=True)

    subject_url = f"{BASE_URL}/papers/caie/as-and-a-level-{SUBJECTS[subject]}"
    log("🔍 Scanning pages...", "#38bdf8")

    async with aiohttp.ClientSession() as session:
        soup = BeautifulSoup(await fetch(session, subject_url), "lxml")
        pages = soup.select("a.kt-widget4__title, a.kt-nav__link-text")

        await asyncio.gather(*[
            process_page(session, urljoin(BASE_URL, p["href"]),
                         subject_dir, y_from, y_to, mode)
            for p in pages if p.get("href")
        ])

    log("\n✅ All downloads completed.", "#38bdf8")



def start():
    log_box.config(state="normal")
    log_box.delete(1.0, tk.END)
    log_box.config(state="disabled")

    def runner():
        asyncio.run(
            main_async(
                subject_var.get(),
                int(year_from.get()),
                int(year_to.get()),
                type_var.get()
            )
        )

    threading.Thread(target=runner, daemon=True).start()

start_btn = tk.Label(card, text="Start Download",
                     bg=ACCENT, fg="#020617",
                     font=("Segoe UI", 12, "bold"),
                     padx=20, pady=8, cursor="hand2")
start_btn.pack(pady=10)
start_btn.bind("<Button-1>", lambda e: start())

root.mainloop()
