# Scrape-the-CAIE-A-levels-
A Python GUI tool for downloading CAIE AS and A Level past papers from pastpapers.papacambridge.com. It asynchronously fetches PDFs by subject, year range, and paper type, then auto-sorts them into a structured folder hierarchy using PDF text analysis.

## Disclaimer

This project does not host or distribute any copyrighted materials.
It only automates the downloading of publicly accessible files from third-party websites.

All copyrights remain with their respective owners.
This tool is intended for personal and educational use only.
Users are responsible for ensuring their usage complies with applicable laws
and the terms of service of the source website.


## Features:
- Graphical user interface built with Tkinter
- Subject-wise selection for CAIE AS & A Level papers
- Year range filtering
- Download modes: Question Papers, Mark Schemes, Both, or All files
- Automatic paper number detection using PDF text analysis
- Asynchronous downloads for improved performance
- Organized folder structure by subject, paper, and document type

## You can easily add additional subjects by modifying the SUBJECTS dictionary

## Installation : 

Step 1 : Install git ( https://git-scm.com/install/ ) 
Step 2 : use this command in cmd : git clone https://github.com/Sulav-subedi/Scrape-the-CAIE-A-levels-
Step 3 : navigate to the file path of the cloned folder and copy file as path
Step 4 : Use this command in cmd : " cd <Paste your file path> " 
Step 5 : now use this command in cmd ( Run in administrator )  : pip install -r requirements.txt
Step 6 : run the python file in cloned folder


## Requirements:
1. Python 3.9+
2. aiohttp
3. beautifulsoup4
4. lxml
5. customtkinter

## macOS Compatibility
Yes — this app can run on macOS because it uses cross-platform Python libraries (`aiohttp`, `BeautifulSoup`, `customtkinter`, and the built-in `tkinter`).

Quick setup on macOS:
1. Install Python 3.9+ (python.org installer is recommended so `tkinter` is included).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt.txt
   ```
3. Run the app:
   ```bash
   python "Scrape the CAIE ( A levels ).py"
   ```

If you get a `tkinter`/Tcl-Tk error, reinstall Python from python.org or install a Tk-enabled Python build.

## How It Works
Scrapes publicly accessible CAIE past paper listings
Fetches PDF and ZIP files using asynchronous HTTP requests
Extracts basic text from the first page of PDFs to detect paper numbers
Sorts files into a structured directory hierarchy on the local system


## Motivation : As a student myself, it is really a headache to go to websites and watch lots of ads and individually find and download question papers. Furthermore, also have to find related marking schemes ( URL method doesn't work most of the times )
And, It really is also a headache to download and organize those tons of files not to mention differentiating between Paper numbers too ( like paper 1, paper 2 and so on ). 


## This project was created for learning purposes to explore asynchronous programming, GUI development, web scraping, and file organization in Python. 
