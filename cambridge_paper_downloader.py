import aiohttp
import asyncio
import threading
import customtkinter as ctk
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import sys
import platform

# Fix for macOS asyncio compatibility
if platform.system() == 'Darwin':  # Darwin is macOS
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

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

# UI - Modern CustomTkinter Design

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ModernApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Cambridge Past Paper Downloader")
        self.root.geometry("800x600")  # More standard size
        self.root.minsize(700, 500)   # Minimum size
        self.root.resizable(True, True)  # Allow resizing
        
        # Animation variables
        self.progress_var = ctk.DoubleVar(value=0)
        self.is_downloading = False
        
        # Download directory variable
        self.download_dir = Path.home() / "Documents" / "CambridgePastPapers"
        
        self.create_main_ui()
        
    def create_main_ui(self):
        # Create a scrollable main frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self.root, 
                                                       corner_radius=15,
                                                       label_text="Cambridge Past Paper Downloader")
        self.scrollable_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Title section
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
        
        # Control panel
        self.create_controls()
        
        # Progress section
        self.create_progress_section()
        
        # Log display
        self.create_log_display()
        
        # Start button - ensure it's at the bottom
        self.create_start_button()
        
    def create_controls(self):
        controls_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=10)
        controls_frame.pack(pady=10, padx=20, fill="x")
        
        # Grid layout for controls
        controls_grid = ctk.CTkFrame(controls_frame, fg_color="transparent")
        controls_grid.pack(pady=15, padx=20)
        
        # Subject selection
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
        
        # Year range
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
        
        # Paper type
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
        
        # Download directory selection
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
        
        # Add hover animations
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
        
        # Log header
        log_header = ctk.CTkFrame(log_frame, fg_color=("gray75", "gray25"), corner_radius=8)
        log_header.pack(fill="x", padx=10, pady=(5, 5))
        
        ctk.CTkLabel(log_header, text="📋 Download Log", 
                    font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=10, pady=3)
        
        # Log text area using CTkTextbox - responsive height
        self.log_box = ctk.CTkTextbox(log_frame, 
                                     height=120,  # Smaller height
                                     font=ctk.CTkFont(family="Consolas", size=9),
                                     wrap="word")
        self.log_box.pack(pady=5, padx=10, fill="both", expand=True)
        self.log_box.insert("0.0", "Welcome to Cambridge Past Paper Downloader!\nSelect your preferences and click Start Download.\n")
        
    def create_start_button(self):
        # Create a button frame that's always at the bottom
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
        
        # Add button animation
        self.animate_button_idle()
        
    def browse_folder(self):
        """Open folder dialog to select download directory"""
        folder_path = filedialog.askdirectory(
            title="Select Download Folder",
            initialdir=str(self.download_dir)
        )
        
        if folder_path:  # If user didn't cancel
            self.download_dir = Path(folder_path)
            # Update the label to show selected path
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
            # Subtle pulsing effect when idle
            current_width = self.start_btn.cget("width")
            new_width = 200 if current_width == 205 else 205
            self.start_btn.configure(width=new_width)
            self.root.after(1000, self.animate_button_idle)
        
    def log(self, msg, color_tag=None):
        def _log():
            self.log_box.insert("end", f"{msg}\n")
            
            # Apply color if specified
            if color_tag:
                line_start = self.log_box.index("end-2l")
                line_end = self.log_box.index("end-1l")
                self.log_box.tag_add(color_tag, line_start, line_end)
                
                # Configure tag colors - use 'foreground' instead of 'text_color'
                if color_tag == "success":
                    self.log_box.tag_config(color_tag, foreground="#10b981")  # Green
                elif color_tag == "error":
                    self.log_box.tag_config(color_tag, foreground="#ef4444")  # Red
                elif color_tag == "info":
                    self.log_box.tag_config(color_tag, foreground="#3b82f6")  # Blue
            
            self.log_box.see("end")
        
        self.root.after(0, _log)
        
    def update_progress(self, value, text):
        self.progress_var.set(value)
        self.progress_label.configure(text=text)
        
    def start_download(self):
        if self.is_downloading:
            return
            
        self.is_downloading = True
        
        # Clear log
        self.log_box.delete("1.0", "end")
        
        # Update UI state
        self.start_btn.configure(text="⏳ Downloading...", state="disabled")
        self.update_progress(0.1, "● Starting download...")
        
        def runner():
            try:
                # Simulate progress updates
                self.root.after(0, lambda: self.update_progress(0.3, "● Scanning pages..."))
                self.root.after(0, lambda: self.log("🔍 Scanning pages for past papers...", "info"))
                
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(
                        main_async(
                            self.subject_var.get(),
                            int(self.year_from.get()),
                            int(self.year_to.get()),
                            self.type_var.get(),
                            self  # Pass the app instance
                        )
                    )
                finally:
                    loop.close()
                
                self.root.after(0, lambda: self.update_progress(1.0, "● Download completed!"))
                self.root.after(0, lambda: self.log("✅ All downloads completed successfully!", "success"))
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"❌ Error occurred: {str(e)}", "error"))
                self.root.after(0, lambda: self.update_progress(0, "● Download failed"))
            finally:
                # Reset UI state
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

async def fetch(session, url):
    try:
        async with session.get(url) as r:
            return await r.text() if r.status == 200 else ""
    except:
        return ""

async def download_file(session, file_url, subject, y_from, y_to, mode, app_instance):
    if not file_url.startswith("http"):
        file_url = urljoin(BASE_URL, file_url)

    filename = file_url.split("/")[-1].lower()

    if not year_allowed(filename, y_from, y_to):
        return

    # Type filtering
    if mode == "QP" and "qp" not in filename:
        return
    if mode == "MS" and "ms" not in filename:
        return
    if mode == "BOTH" and not any(x in filename for x in ("qp", "ms")):
        return

    temp_dir = app_instance.download_dir / subject / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / filename

    if temp_path.exists():
        return

    try:
        async with session.get(file_url) as r:
            if r.status != 200:
                return
            temp_path.write_bytes(await r.read())

        paper = detect_paper_from_filename(filename)

        # Destination logic - use app's download directory
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

        app_instance.log(f"✔ {paper} | {filename}", "success")

    except Exception:
        app_instance.log(f"❌ Error: {filename}", "error")


async def process_page(session, url, subject, y_from, y_to, mode, app_instance):
    soup = BeautifulSoup(await fetch(session, url), "lxml")
    links = soup.select('a[href$=".pdf"], a[href$=".zip"]')

    await asyncio.gather(*[
        download_file(session, link["href"], subject, y_from, y_to, mode, app_instance)
        for link in links
    ])

async def main_async(subject, y_from, y_to, mode, app_instance):
    app_instance.log(f"📁 Download directory: {app_instance.download_dir}", "info")
    app_instance.log("🔍 Scanning pages...", "info")

    subject_url = f"{BASE_URL}/papers/caie/as-and-a-level-{SUBJECTS[subject]}"

    async with aiohttp.ClientSession() as session:
        soup = BeautifulSoup(await fetch(session, subject_url), "lxml")
        pages = soup.select("a.kt-widget4__title, a.kt-nav__link-text")

        await asyncio.gather(*[
            process_page(session, urljoin(BASE_URL, p["href"]),
                         subject, y_from, y_to, mode, app_instance)
            for p in pages if p.get("href")
        ])

    app_instance.log("\n✅ All downloads completed.", "success")

# Start the application
if __name__ == "__main__":
    app.run()
