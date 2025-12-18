# Scrape-the-CAIE-A-levels-
A Python GUI tool for downloading CAIE AS and A Level past papers from pastpapers.papacambridge.com. It asynchronously fetches PDFs by subject, year range, and paper type, then auto-sorts them into a structured folder hierarchy using PDF text analysis.

## Disclaimer

This project does not host or distribute any copyrighted materials.
It only automates the downloading of publicly accessible files from third-party websites.

All copyrights remain with their respective owners.
This tool is intended for personal and educational use only.
Users are responsible for ensuring their usage complies with applicable laws
and the terms of service of the source website.

Motivation : As a student myself, it is really a headache to go to websites and watch lots of ads and individually find and download question papers. Furthermore, also have to find related marking schemes ( URL method doesn't work most of the times )
It really is a headache to download and organize those tons of files not to mention differentiating between Paper numbers too ( like paper 1, paper 2 and so on ) and also to learn python stuffs. Except App GUI was made using Tkinter with the help of AI.

Features:
-Graphical user interface built with Tkinter
-Subject-wise selection for CAIE AS & A Level papers
-Year range filtering
-Download modes: Question Papers, Mark Schemes, Both, or All files
-Automatic paper number detection using PDF text analysis
-Asynchronous downloads for improved performance
-Organized folder structure by subject, paper, and document type
## -Easily add additional subjects by modifying the SUBJECTS dictionary


How It Works
Scrapes publicly accessible CAIE past paper listings
Fetches PDF and ZIP files using asynchronous HTTP requests
Extracts basic text from the first page of PDFs to detect paper numbers
Sorts files into a structured directory hierarchy on the local system

Requirements:
1. Python 3.9+
2. aiohttp
3. beautifulsoup4


## This project was created for learning purposes to explore asynchronous programming, GUI development, web scraping, and file organization in Python.
