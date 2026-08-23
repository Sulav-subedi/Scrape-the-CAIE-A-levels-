import aiohttp
import asyncio
import ssl
import threading
import traceback
import customtkinter as ctk
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# CONFIG

BASE_URL = "https://pastpapers.papacambridge.com"

SUBJECTS = {
    "Physics": "physics-9702",
    "Chemistry": "chemistry-9701",
    "Computer Science": "computer-science-for-first-examination-in-2021-9618",
    "Maths": "mathematics-9709",
    "Biology": "biology-9700",
    "English General Paper": "english-general-paper-8021",
    "Economics": "economics-9708",
    "Business": "business9609",
    "Accounting": "accounting-9706",
    "Further Maths": "mathematics-9231"
}

BASE_DIR = Path.home() / "Documents" / "CambridgePastPapers"  # Default directory
DOWNLOAD_DIR = BASE_DIR  # This will be updated by user selection

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10)
MAX_RETRIES = 3

# --- SSL setup ---
# On macOS, Python installed from python.org (unlike the system Python or Homebrew's)
# does not ship with root certificates wired up, so EVERY https request fails instantly
# with a certificate verification error. aiohttp swallows that as a normal ClientConnectorError,
# which made the app finish "successfully" in under a second with 0 files. We fix this by
# building an SSL context from `certifi`'s bundle (pip installable, no admin rights needed)
# instead of relying on the system trust store.
CERTIFI_AVAILABLE = True
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # certifi isn't installed - fall back to the system default, which is what was failing.
    CERTIFI_AVAILABLE = False
    SSL_CONTEXT = ssl.create_default_context()


def is_cert_error(exc: BaseException) -> bool:
    """Detect a certificate-verification failure regardless of which aiohttp/ssl
    exception class actually got raised - this varies across aiohttp versions,
    so string/cause inspection is more reliable than isinstance checks alone."""
    text = str(exc)
    if "CERTIFICATE_VERIFY_FAILED" in text or "certificate verify failed" in text.lower():
        return True
    cause = getattr(exc, "__cause__", None)
    if isinstance(cause, ssl.SSLCertVerificationError):
        return True
    if isinstance(exc, ssl.SSLCertVerificationError):
        return True
    return False


CERT_ERROR_HINT = (
    "SSL certificate verification failed - Python can't find a trusted certificate authority "
    "bundle. On macOS this is almost always because Python isn't using your system's trust store. "
    "Fix: run 'pip install --upgrade certifi' (or 'pip3 install --upgrade certifi'), then restart "
    "this app. If that doesn't fix it, run the 'Install Certificates.command' file inside your "
    "Python installation folder (e.g. /Applications/Python 3.12/Install Certificates.command)."
)

# UI - Modern CustomTkinter Design

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DownloadStats:
    """Tracks what happened during a run so we can report something useful at the end."""
    def __init__(self):
        self.downloaded = 0
        self.skipped_existing = 0
        self.skipped_filter = 0
        self.pages_failed = 0
        self.files_failed = 0
        self.errors = []  # list of (context, error_type, message)

    def add_error(self, context, exc):
        self.errors.append((context, type(exc).__name__, str(exc)))


class ModernApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Cambridge Past Paper Downloader")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        self.root.resizable(True, True)

        self.progress_var = ctk.DoubleVar(value=0)
        self.is_downloading = False

        self.download_dir = Path.home() / "Documents" / "CambridgePastPapers"

        self.create_main_ui()

    def create_main_ui(self):
        self.scrollable_frame = ctk.CTkScrollableFrame(self.root,
                                                        corner_radius=15,
                                                        label_text="Cambridge Past Paper Downloader")
        self.scrollable_frame.pack(pady=10, padx=10, fill="both", expand=True)

        title_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=10)
        title_frame.pack(pady=10, padx=20, fill="x")

        title_label = ctk.CTkLabel(title_frame,
                                    text="📚 Cambridge Past Paper Downloader",
                                    font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=8)

        subtitle_label = ctk.CTkLabel(title_frame,
                                       text="Download & auto-sort AS/A Level past papers with style",
                                       font=ctk.CTkFont(size=11),
                                       text_color=("gray70", "gray40"))
        subtitle_label.pack(pady=2)

        self.create_controls()
        self.create_progress_section()
        self.create_log_display()
        self.create_start_button()

    def create_controls(self):
        controls_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=10)
        controls_frame.pack(pady=10, padx=20, fill="x")

        controls_grid = ctk.CTkFrame(controls_frame, fg_color="transparent")
        controls_grid.pack(pady=15, padx=20)

        ctk.CTkLabel(controls_grid, text="📖 Subject",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=8, pady=8, sticky="w")

        self.subject_var = ctk.StringVar(value=list(SUBJECTS.keys())[0])
        self.subject_box = ctk.CTkComboBox(controls_grid,
                                            variable=self.subject_var,
                                            values=list(SUBJECTS.keys()),
                                            width=180,
                                            height=30,
                                            font=ctk.CTkFont(size=11))
        self.subject_box.grid(row=0, column=1, padx=8, pady=8)

        ctk.CTkLabel(controls_grid, text="📅 From",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=2, padx=8, pady=8, sticky="w")

        self.year_from = ctk.CTkComboBox(controls_grid,
                                          values=[str(y) for y in range(2000, 2026)],
                                          width=70,
                                          height=30,
                                          font=ctk.CTkFont(size=11))
        self.year_from.grid(row=0, column=3, padx=8, pady=8)
        self.year_from.set("2018")

        ctk.CTkLabel(controls_grid, text="📅 To",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=4, padx=8, pady=8, sticky="w")

        self.year_to = ctk.CTkComboBox(controls_grid,
                                        values=[str(y) for y in range(2000, 2026)],
                                        width=70,
                                        height=30,
                                        font=ctk.CTkFont(size=11))
        self.year_to.grid(row=0, column=5, padx=8, pady=8)
        self.year_to.set("2024")

        ctk.CTkLabel(controls_grid, text="📄 Type",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, padx=8, pady=8, sticky="w")

        self.type_var = ctk.StringVar(value="ALL")
        self.type_box = ctk.CTkComboBox(controls_grid,
                                         variable=self.type_var,
                                         values=["QP", "MS", "BOTH", "ALL"],
                                         width=100,
                                         height=30,
                                         font=ctk.CTkFont(size=11))
        self.type_box.grid(row=1, column=1, padx=8, pady=8)

        ctk.CTkLabel(controls_grid, text="📁 Download To",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(row=2, column=0, padx=8, pady=8, sticky="w")

        self.dir_label = ctk.CTkLabel(controls_grid,
                                       text=str(self.download_dir),
                                       font=ctk.CTkFont(size=10),
                                       text_color=("gray70", "gray40"))
        self.dir_label.grid(row=2, column=1, columnspan=3, padx=8, pady=8, sticky="w")

        self.browse_btn = ctk.CTkButton(controls_grid,
                                         text="Browse",
                                         width=80,
                                         height=30,
                                         font=ctk.CTkFont(size=10),
                                         command=self.browse_folder)
        self.browse_btn.grid(row=2, column=4, padx=8, pady=8)

        self.add_combobox_animation(self.subject_box)
        self.add_combobox_animation(self.year_from)
        self.add_combobox_animation(self.year_to)
        self.add_combobox_animation(self.type_box)

    def create_progress_section(self):
        progress_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=10)
        progress_frame.pack(pady=8, padx=20, fill="x")

        self.progress_label = ctk.CTkLabel(progress_frame,
                                            text="● Ready to download",
                                            font=ctk.CTkFont(size=11),
                                            text_color=("green", "green"))
        self.progress_label.pack(pady=8)

        self.progress_bar = ctk.CTkProgressBar(progress_frame,
                                                variable=self.progress_var,
                                                width=350,
                                                height=6,
                                                corner_radius=3)
        self.progress_bar.pack(pady=8)
        self.progress_bar.set(0)

    def create_log_display(self):
        log_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=10)
        log_frame.pack(pady=8, padx=20, fill="both", expand=True)

        log_header = ctk.CTkFrame(log_frame, fg_color=("gray75", "gray25"), corner_radius=8)
        log_header.pack(fill="x", padx=10, pady=(5, 5))

        ctk.CTkLabel(log_header, text="📋 Download Log",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=3)

        self.log_box = ctk.CTkTextbox(log_frame,
                                       height=120,
                                       font=ctk.CTkFont(family="Consolas", size=9),
                                       wrap="word")
        self.log_box.pack(pady=5, padx=10, fill="both", expand=True)
        self.log_box.insert("0.0", "Welcome to Cambridge Past Paper Downloader!\nSelect your preferences and click Start Download.\n")

        if not CERTIFI_AVAILABLE:
            self.log_box.insert(
                "end",
                "\n⚠ 'certifi' package not found - falling back to your system's certificate "
                "store. If downloads fail with an SSL/certificate error, run:\n"
                "    pip install certifi\n"
                "then restart this app.\n"
            )

    def create_start_button(self):
        button_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        button_frame.pack(pady=15, padx=20, fill="x")

        self.start_btn = ctk.CTkButton(button_frame,
                                        text="🚀 Start Download",
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        width=200,
                                        height=35,
                                        corner_radius=8,
                                        command=self.start_download,
                                        hover_color=("#3a7bd5", "#5a9fd4"))
        self.start_btn.pack(pady=10)

        self.animate_button_idle()

    def browse_folder(self):
        try:
            folder_path = filedialog.askdirectory(
                title="Select Download Folder",
                initialdir=str(self.download_dir)
            )
        except Exception as e:
            self.log(f"❌ Could not open folder picker: {type(e).__name__}: {e}", "error")
            return

        if not folder_path:
            return  # user cancelled - not an error

        candidate = Path(folder_path)

        # Verify we can actually write here before committing to it
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
        except PermissionError:
            self.log(f"❌ Permission denied: cannot write to {candidate}. Choose a different folder.", "error")
            return
        except OSError as e:
            self.log(f"❌ Cannot use this folder ({type(e).__name__}: {e}). Choose a different one.", "error")
            return

        self.download_dir = candidate
        self.dir_label.configure(text=str(self.download_dir))
        self.log(f"📁 Download directory changed to: {self.download_dir}", "info")

    def add_combobox_animation(self, combobox):
        def on_enter(event):
            combobox.configure(border_width=2, border_color=("#3b82f6", "#60a5fa"))

        def on_leave(event):
            combobox.configure(border_width=1, border_color=("gray65", "gray40"))

        combobox.bind("<Enter>", on_enter)
        combobox.bind("<Leave>", on_leave)

    def animate_button_idle(self):
        if not self.is_downloading:
            current_width = self.start_btn.cget("width")
            new_width = 200 if current_width == 205 else 205
            self.start_btn.configure(width=new_width)
            self.root.after(1000, self.animate_button_idle)

    def log(self, msg, color_tag=None):
        def _log():
            self.log_box.insert("end", f"{msg}\n")

            if color_tag:
                line_start = self.log_box.index("end-2l")
                line_end = self.log_box.index("end-1l")
                self.log_box.tag_add(color_tag, line_start, line_end)

                if color_tag == "success":
                    self.log_box.tag_config(color_tag, foreground="#10b981")
                elif color_tag == "error":
                    self.log_box.tag_config(color_tag, foreground="#ef4444")
                elif color_tag == "info":
                    self.log_box.tag_config(color_tag, foreground="#3b82f6")
                elif color_tag == "warning":
                    self.log_box.tag_config(color_tag, foreground="#f59e0b")

            self.log_box.see("end")

        self.root.after(0, _log)

    def update_progress(self, value, text):
        self.progress_var.set(value)
        self.progress_label.configure(text=text)

    def start_download(self):
        if self.is_downloading:
            return

        # --- Validate inputs up front, with a specific message for each problem ---
        try:
            y_from = int(self.year_from.get())
        except ValueError:
            self.log(f"❌ 'From' year is not a valid number: '{self.year_from.get()}'", "error")
            return

        try:
            y_to = int(self.year_to.get())
        except ValueError:
            self.log(f"❌ 'To' year is not a valid number: '{self.year_to.get()}'", "error")
            return

        if y_from > y_to:
            self.log(f"❌ 'From' year ({y_from}) is after 'To' year ({y_to}). Fix the range and try again.", "error")
            return

        subject = self.subject_var.get()
        if subject not in SUBJECTS:
            self.log(f"❌ Unknown subject selected: '{subject}'", "error")
            return

        try:
            self.download_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            self.log(f"❌ Permission denied creating {self.download_dir}. Pick a different download folder.", "error")
            return
        except OSError as e:
            self.log(f"❌ Cannot create download folder ({type(e).__name__}: {e}).", "error")
            return

        self.is_downloading = True
        self.log_box.delete("1.0", "end")

        self.start_btn.configure(text="⏳ Downloading...", state="disabled")
        self.update_progress(0.1, "● Starting download...")

        def runner():
            stats = DownloadStats()
            try:
                self.root.after(0, lambda: self.update_progress(0.3, "● Scanning pages..."))
                self.root.after(0, lambda: self.log("🔍 Scanning pages for past papers...", "info"))

                asyncio.run(
                    main_async(subject, y_from, y_to, self.type_var.get(), self, stats)
                )

                # The old code always showed "Download completed!" here, even when nothing
                # was actually downloaded (e.g. every request failed instantly due to a
                # network/SSL problem, or the site returned no matching pages). Reflect
                # what actually happened instead of a blanket success message.
                total_attempted = stats.downloaded + stats.files_failed
                total_page_activity = stats.pages_failed  # >0 means pages were seen and some failed

                if stats.downloaded > 0:
                    progress_text = "● Download completed!"
                elif stats.files_failed > 0 or stats.pages_failed > 0:
                    progress_text = "● Finished with errors — see log"
                else:
                    progress_text = "● Finished — nothing matched"

                self.root.after(0, lambda t=progress_text: self.update_progress(1.0, t))

                summary = (f"{'✅' if stats.downloaded > 0 else '⚠'} Done. {stats.downloaded} downloaded, "
                           f"{stats.skipped_existing} already had, "
                           f"{stats.skipped_filter} skipped by filter, "
                           f"{stats.files_failed} file errors, "
                           f"{stats.pages_failed} page errors.")
                tag = "success" if (stats.downloaded > 0 and stats.files_failed == 0 and stats.pages_failed == 0) else "warning"
                self.root.after(0, lambda: self.log(summary, tag))

                if stats.downloaded == 0 and stats.files_failed == 0 and stats.pages_failed == 0:
                    self.root.after(0, lambda: self.log(
                        "⚠ No files matched. Check the year range, paper type filter, "
                        "or whether the site's page layout has changed.", "warning"))
                elif stats.downloaded == 0 and (stats.files_failed > 0 or stats.pages_failed > 0):
                    self.root.after(0, lambda: self.log(
                        "⚠ Nothing was downloaded — every request failed. Scroll up for the "
                        "specific error (often an SSL certificate issue on macOS, or no "
                        "internet connection).", "warning"))

                if stats.errors:
                    # Show up to 5 distinct error messages so the user knows *what* broke, not just *that* it broke
                    seen = set()
                    shown = 0
                    for context, err_type, err_msg in stats.errors:
                        key = (context, err_type, err_msg)
                        if key in seen:
                            continue
                        seen.add(key)
                        self.root.after(0, lambda c=context, t=err_type, m=err_msg:
                                         self.log(f"   ↳ [{t}] {c}: {m}", "error"))
                        shown += 1
                        if shown >= 5:
                            break
                    if len(stats.errors) > shown:
                        remaining = len(stats.errors) - shown
                        self.root.after(0, lambda r=remaining:
                                         self.log(f"   ↳ ...and {r} more error(s) of the same kind.", "error"))

            except aiohttp.ClientConnectorError as e:
                self.root.after(0, lambda: self.log(
                    f"❌ Could not connect to {BASE_URL} — check your internet connection. ({e})", "error"))
                self.root.after(0, lambda: self.update_progress(0, "● Download failed: no connection"))
            except asyncio.TimeoutError:
                self.root.after(0, lambda: self.log(
                    "❌ The site took too long to respond (timeout). It may be down or overloaded.", "error"))
                self.root.after(0, lambda: self.update_progress(0, "● Download failed: timeout"))
            except aiohttp.ClientError as e:
                self.root.after(0, lambda: self.log(
                    f"❌ Network error talking to the site: {type(e).__name__}: {e}", "error"))
                self.root.after(0, lambda: self.update_progress(0, "● Download failed: network error"))
            except Exception as e:
                tb = traceback.format_exc()
                print(tb)  # full traceback goes to the console for debugging
                self.root.after(0, lambda: self.log(
                    f"❌ Unexpected error: {type(e).__name__}: {e} (full details printed to console)", "error"))
                self.root.after(0, lambda: self.update_progress(0, "● Download failed"))
            finally:
                self.root.after(1500, self.reset_ui_state)

        threading.Thread(target=runner, daemon=True).start()

    def reset_ui_state(self):
        self.is_downloading = False
        self.start_btn.configure(text="🚀 Start Download", state="normal")
        self.update_progress(0, "● Ready to download")
        self.animate_button_idle()

    def run(self):
        self.root.mainloop()


# Initialize the app
app = ModernApp()
root = app.root


# HELPERS

def year_allowed(filename, y_from, y_to):
    matches = re.findall(r"[msw](\d{2})", filename.lower())
    if not matches:
        return True
    return any(y_from <= 2000 + int(yy) <= y_to for yy in matches)


def detect_paper_from_filename(filename: str):
    match = re.search(r"(qp|ms|sp|sm)_([1-9])\d", filename.lower())
    if match:
        return f"Paper {match.group(2)}"
    return "Other Papers"


# ASYNC CORE

async def fetch(session, url, app_instance, stats, context="page fetch"):
    """Fetch a URL's text, logging *why* it failed instead of failing silently."""
    try:
        async with session.get(url) as r:
            if r.status == 200:
                return await r.text()
            else:
                app_instance.log(f"⚠ Server returned HTTP {r.status} for {url}", "warning")
                stats.add_error(context, RuntimeError(f"HTTP {r.status} at {url}"))
                stats.pages_failed += 1
                return ""
    except aiohttp.ClientConnectorError as e:
        if is_cert_error(e):
            app_instance.log(f"⚠ {CERT_ERROR_HINT}", "warning")
        else:
            app_instance.log(f"⚠ Connection failed for {url}: {e}", "warning")
        stats.add_error(context, e)
        stats.pages_failed += 1
        return ""
    except asyncio.TimeoutError as e:
        app_instance.log(f"⚠ Timed out loading {url}", "warning")
        stats.add_error(context, e)
        stats.pages_failed += 1
        return ""
    except aiohttp.ClientError as e:
        app_instance.log(f"⚠ Network error loading {url}: {type(e).__name__}: {e}", "warning")
        stats.add_error(context, e)
        stats.pages_failed += 1
        return ""
    except Exception as e:
        app_instance.log(f"⚠ Unexpected error loading {url}: {type(e).__name__}: {e}", "warning")
        stats.add_error(context, e)
        stats.pages_failed += 1
        return ""


async def download_file(session, file_url, subject, y_from, y_to, mode, app_instance, stats):
    if not file_url.startswith("http"):
        file_url = urljoin(BASE_URL, file_url)

    filename = file_url.split("/")[-1].lower()

    if not filename:
        return

    if not year_allowed(filename, y_from, y_to):
        stats.skipped_filter += 1
        return

    # Type filtering
    if mode == "QP" and "qp" not in filename:
        stats.skipped_filter += 1
        return
    if mode == "MS" and "ms" not in filename:
        stats.skipped_filter += 1
        return
    if mode == "BOTH" and not any(x in filename for x in ("qp", "ms")):
        stats.skipped_filter += 1
        return

    try:
        temp_dir = app_instance.download_dir / subject / "_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        app_instance.log(f"❌ Permission denied creating folder for {subject}: {e}", "error")
        stats.add_error(f"folder creation for {subject}", e)
        stats.files_failed += 1
        return
    except OSError as e:
        app_instance.log(f"❌ Filesystem error creating folder for {subject}: {type(e).__name__}: {e}", "error")
        stats.add_error(f"folder creation for {subject}", e)
        stats.files_failed += 1
        return

    temp_path = temp_dir / filename

    if temp_path.exists():
        stats.skipped_existing += 1
        return

    # --- Network download ---
    try:
        async with session.get(file_url) as r:
            if r.status != 200:
                app_instance.log(f"⚠ HTTP {r.status} downloading {filename}, skipping.", "warning")
                stats.add_error(filename, RuntimeError(f"HTTP {r.status}"))
                stats.files_failed += 1
                return
            data = await r.read()
    except aiohttp.ClientConnectorCertificateError as e:
        app_instance.log(f"❌ {CERT_ERROR_HINT}", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1
        return
    except aiohttp.ClientConnectorError as e:
        if is_cert_error(e):
            app_instance.log(f"❌ {CERT_ERROR_HINT}", "error")
        else:
            app_instance.log(f"❌ Connection failed for {filename}: {e}", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1
        return
    except asyncio.TimeoutError as e:
        app_instance.log(f"❌ Timed out downloading {filename}", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1
        return
    except aiohttp.ClientPayloadError as e:
        app_instance.log(f"❌ Download of {filename} was interrupted/corrupted: {e}", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1
        return
    except aiohttp.ClientError as e:
        app_instance.log(f"❌ Network error downloading {filename}: {type(e).__name__}: {e}", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1
        return

    # --- Write to disk ---
    try:
        temp_path.write_bytes(data)
    except PermissionError as e:
        app_instance.log(f"❌ Permission denied writing {filename}: {e}", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1
        return
    except OSError as e:
        # Covers disk full (ENOSPC), path too long, invalid filename, etc.
        app_instance.log(f"❌ Could not save {filename} ({type(e).__name__}: {e}). "
                          f"Check disk space and folder permissions.", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1
        return

    # --- Move into its final destination ---
    try:
        paper = detect_paper_from_filename(filename)

        if mode == "QP":
            dest = app_instance.download_dir / subject / paper / "Question Papers"
        elif mode == "MS":
            dest = app_instance.download_dir / subject / paper / "Mark Schemes"
        elif mode == "BOTH":
            dest = app_instance.download_dir / subject / paper / (
                "Question Papers" if "qp" in filename else "Mark Schemes"
            )
        else:  # ALL
            if "qp" in filename:
                dest = app_instance.download_dir / subject / paper / "Question Papers"
            elif "ms" in filename:
                dest = app_instance.download_dir / subject / paper / "Mark Schemes"
            else:
                dest = app_instance.download_dir / subject / paper / "Misc"

        dest.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_path), str(dest / filename))

        stats.downloaded += 1
        app_instance.log(f"✔ {paper} | {filename}", "success")

    except PermissionError as e:
        app_instance.log(f"❌ Permission denied moving {filename} into place: {e}", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1
    except shutil.Error as e:
        app_instance.log(f"❌ Could not move {filename} ({e}).", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1
    except OSError as e:
        app_instance.log(f"❌ Filesystem error placing {filename}: {type(e).__name__}: {e}", "error")
        stats.add_error(filename, e)
        stats.files_failed += 1


async def process_page(session, url, subject, y_from, y_to, mode, app_instance, stats):
    html = await fetch(session, url, app_instance, stats, context=f"page {url}")
    if not html:
        return  # fetch() already logged the specific reason

    try:
        soup = BeautifulSoup(html, "lxml")
        links = soup.select('a[href$=".pdf"], a[href$=".zip"]')
    except Exception as e:
        app_instance.log(f"❌ Could not parse page {url}: {type(e).__name__}: {e}", "error")
        stats.add_error(f"parsing {url}", e)
        stats.pages_failed += 1
        return

    if not links:
        app_instance.log(f"⚠ No downloadable files found on {url} — page layout may have changed.", "warning")
        return

    results = await asyncio.gather(*[
        download_file(session, link["href"], subject, y_from, y_to, mode, app_instance, stats)
        for link in links if link.get("href")
    ], return_exceptions=True)

    for r in results:
        if isinstance(r, Exception):
            app_instance.log(f"❌ Unexpected error while downloading a file from {url}: "
                              f"{type(r).__name__}: {r}", "error")
            stats.add_error(f"download task on {url}", r)
            stats.files_failed += 1


async def main_async(subject, y_from, y_to, mode, app_instance, stats):
    app_instance.log(f"📁 Download directory: {app_instance.download_dir}", "info")
    app_instance.log("🔍 Scanning pages...", "info")

    subject_url = f"{BASE_URL}/papers/caie/as-and-a-level-{SUBJECTS[subject]}"

    connector = aiohttp.TCPConnector(ssl=SSL_CONTEXT)
    async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT, connector=connector) as session:
        html = await fetch(session, subject_url, app_instance, stats, context="subject index page")
        if not html:
            app_instance.log(
                "❌ Could not load the subject page at all. Check your internet connection, "
                "or the site may be temporarily down.", "error")
            return

        try:
            soup = BeautifulSoup(html, "lxml")
            pages = soup.select("a.kt-widget4__title, a.kt-nav__link-text")
        except Exception as e:
            app_instance.log(f"❌ Could not parse the subject page: {type(e).__name__}: {e}", "error")
            stats.add_error("parsing subject index", e)
            return

        if not pages:
            app_instance.log(
                "⚠ No year/session pages found for this subject. The site's page structure "
                "may have changed, or this subject page may be empty.", "warning")
            return

        results = await asyncio.gather(*[
            process_page(session, urljoin(BASE_URL, p["href"]),
                         subject, y_from, y_to, mode, app_instance, stats)
            for p in pages if p.get("href")
        ], return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                app_instance.log(f"❌ Unexpected error processing a page: {type(r).__name__}: {r}", "error")
                stats.add_error("page processing", r)
                stats.pages_failed += 1

    app_instance.log("\n✅ Scan finished.", "success")


# Start the application
if __name__ == "__main__":
    app.run()
