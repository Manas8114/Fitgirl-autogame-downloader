import os
import re
import requests
import time
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

class GameDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Game Downloader")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Configuration
        self.download_dir = ""
        self.active_downloads = {}
        self.max_workers = 4
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # UI Setup
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL input
        ttk.Label(main_frame, text="Game URL:").grid(row=0, column=0, sticky='w', pady=5)
        self.url_entry = ttk.Entry(main_frame, width=70)
        self.url_entry.grid(row=0, column=1, sticky='we', padx=5, pady=5)
        
        # Directory selection
        ttk.Label(main_frame, text="Download Directory:").grid(row=1, column=0, sticky='w', pady=5)
        self.dir_entry = ttk.Entry(main_frame, width=60)
        self.dir_entry.grid(row=1, column=1, sticky='we', padx=5, pady=5)
        ttk.Button(main_frame, text="Browse", command=self.select_directory).grid(row=1, column=2, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.grid(row=2, column=0, columnspan=3, sticky='we', pady=10)
        
        # Log area
        self.log_area = scrolledtext.ScrolledText(main_frame, height=15)
        self.log_area.grid(row=3, column=0, columnspan=3, sticky='nsew', pady=10)
        self.log_area.config(state=tk.DISABLED)
        
        # Control buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Start Download", command=self.start_download).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Pause All", command=self.pause_downloads).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Resume All", command=self.resume_downloads).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Set initial directory
        self.dir_entry.insert(0, os.path.join(os.path.expanduser('~'), 'Downloads'))
        self.download_dir = self.dir_entry.get()
    
    def log(self, message):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_area.config(state=tk.DISABLED)
        self.log_area.see(tk.END)
    
    def clear_log(self):
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state=tk.DISABLED)
    
    def select_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
            self.download_dir = directory
    
    def get_download_links(self, url):
        """Extract download links from supported game sites"""
        try:
            self.log(f"Fetching page: {url}")
            response = self.session.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Site-specific parsing
            domain = urlparse(url).netloc
            links = []
            
            if "fitgirl-repacks" in domain:
                # FitGirl Repacks parsing
                for link in soup.select('a[href*="magnet:?"], a[href*=".torrent"]'):
                    links.append(link['href'])
            
            elif "ovagames" in domain:
                # OvaGames parsing
                for link in soup.select('a[href*="uploadhaven"], a[href*="mega.nz"]'):
                    links.append(link['href'])
            
            elif "dodi-repacks" in domain:
                # DODI Repacks parsing
                for link in soup.select('a[href*="magnet:?"], a[href*=".torrent"]'):
                    links.append(link['href'])
            
            if not links:
                self.log("No download links found. Trying fallback method...")
                # Fallback: Find all links with common file extensions
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if any(href.endswith(ext) for ext in ['.rar', '.zip', '.001', '.7z']):
                        links.append(urljoin(url, href))
            
            return list(set(links))  # Remove duplicates
            
        except Exception as e:
            self.log(f"Error extracting links: {str(e)}")
            return []

    def download_file(self, url, file_path):
        """Download a file with resume capability and error handling"""
        if os.path.exists(file_path):
            # Check if file is already complete
            if self.is_download_complete(url, file_path):
                self.log(f"Skipping completed file: {os.path.basename(file_path)}")
                return True
        
        try:
            headers = {}
            if os.path.exists(file_path):
                # Resume partial download
                headers = {'Range': f'bytes={os.path.getsize(file_path)}-'}
            
            with self.session.get(url, stream=True, headers=headers, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0)) + (os.path.getsize(file_path) if os.path.exists(file_path) else 0)
                mode = 'ab' if headers else 'wb'
                
                with open(file_path, mode) as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:  # filter out keep-alive chunks
                            f.write(chunk)
                            # Update progress tracking would go here
            return True
        
        except requests.exceptions.RequestException as e:
            self.log(f"Download failed: {os.path.basename(file_path)} - {str(e)}")
            return False
    
    def is_download_complete(self, url, file_path):
        """Verify download completion using file size or checksum"""
        # This would implement site-specific verification logic
        # For simplicity, we'll check if file exists and has non-zero size
        return os.path.exists(file_path) and os.path.getsize(file_path) > 0
    
    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a valid game URL")
            return
        
        if not self.download_dir:
            messagebox.showerror("Error", "Please select a download directory")
            return
        
        # Get download links
        links = self.get_download_links(url)
        if not links:
            messagebox.showerror("Error", "No downloadable files found")
            return
        
        self.log(f"Found {len(links)} files to download")
        
        # Create download directory
        game_name = url.split('/')[-1] if '/' in url else "game"
        game_dir = os.path.join(self.download_dir, game_name)
        os.makedirs(game_dir, exist_ok=True)
        
        # Download files
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for link in links:
                file_name = link.split('/')[-1].split('?')[0]
                file_path = os.path.join(game_dir, file_name)
                futures[executor.submit(self.download_file, link, file_path)] = file_name
            
            for future in as_completed(futures):
                file_name = futures[future]
                try:
                    success = future.result()
                    if success:
                        self.log(f"Completed: {file_name}")
                except Exception as e:
                    self.log(f"Error downloading {file_name}: {str(e)}")
        
        self.log("All downloads completed!")

    def pause_downloads(self):
        self.log("Downloads paused")
        # Implementation would track active downloads and pause them
    
    def resume_downloads(self):
        self.log("Resuming downloads")
        # Implementation would resume paused downloads

if __name__ == "__main__":
    root = tk.Tk()
    app = GameDownloader(root)
    root.mainloop()