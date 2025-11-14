#!/usr/bin/env python3
import os
import platform
import socket
import json
import subprocess
import psutil
try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Install it with: pip install requests")
    exit()

def get_public_ip():
    """جيب الـ IP العام للسيرفر."""
    try:
        # بينخدم أكتر من سورس عشان لو واحد معطل
        ip_services = [
            'https://api.ipify.org?format=json',
            'https://ifconfig.me/all.json',
            'https://ipinfo.io/json'
        ]
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                response.raise_for_status()
                data = response.json()
                # بتحقق من الـ response key لأن كل سيرفر بيرجع هيئة مختلفة شوية
                return data.get('ip') or data.get('ip_addr')
            except (requests.RequestException, json.JSONDecodeError, KeyError):
                continue
        return "Could not determine public IP"
    except Exception:
        return "Could not determine public IP"

def get_system_info():
    """جيب معلومات نظام التشغيل والنواة."""
    uname_info = platform.uname()
    return {
        "system": uname_info.system,
        "node_name": uname_info.node,
        "release": uname_info.release,
        "version": uname_info.version,
        "machine": uname_info.machine,
        "processor": uname_info.processor,
        "architecture": platform.architecture()[0],
    }

def get_user_info():
    """جيب اسم المستخدم الحالي وبيانات SSH."""
    user_info = {
        "current_user": os.getenv('USER') or os.getenv('LOGNAME') or "Unknown",
        "home_directory": os.path.expanduser('~'),
        "ssh_keys": {}
    }
    
    # بدل الباسورد، بنشوف إذا في مفاتيح SSH (أهم من الباسورد نفسه)
    ssh_dir = os.path.join(user_info["home_directory"], ".ssh")
    if os.path.isdir(ssh_dir):
        user_info["ssh_keys"]["id_rsa_present"] = os.path.isfile(os.path.join(ssh_dir, "id_rsa"))
        user_info["ssh_keys"]["authorized_keys_present"] = os.path.isfile(os.path.join(ssh_dir, "authorized_keys"))
    
    return user_info

def get_hardware_info():
    """جيب معلومات الهاردوير: معالج، رام، مساحة تخزين."""
    cpu_info = {
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "max_frequency": f"{psutil.cpu_freq().max:.2f}Mhz" if psutil.cpu_freq() else "N/A",
        "current_usage": f"{psutil.cpu_percent()}%"
    }
    
    mem = psutil.virtual_memory()
    memory_info = {
        "total": f"{mem.total / (1024**3):.2f} GB",
        "available": f"{mem.available / (1024**3):.2f} GB",
        "used": f"{mem.used / (1024**3):.2f} GB",
        "percentage": f"{mem.percent}%"
    }
    
    disk_info = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total": f"{usage.total / (1024**3):.2f} GB",
                "used": f"{usage.used / (1024**3):.2f} GB",
                "free": f"{usage.free / (1024**3):.2f} GB",
                "percentage": f"{(usage.used / usage.total) * 100:.1f}%"
            })
        except PermissionError:
            continue # Skip partitions we can't access
            
    return {
        "cpu": cpu_info,
        "memory": memory_info,
        "disk": disk_info
    }

def get_network_info():
    """جيب معلومات عن واجهات الشبكة والـ IPs."""
    net_if_addrs = psutil.net_if_addrs()
    interfaces = {}
    for interface_name, snic_list in net_if_addrs.items():
        ip_list = [snic.address for snic in snic_list if snic.family == socket.AF_INET]
        if ip_list:
            interfaces[interface_name] = ip_list
    return interfaces

def get_open_ports():
    """جيب قائمة بالبورتات المفتوحة والبرامج اللي بتستخدمها."""
    try:
        # بنستخدم ss لأنه أحدث وأسرع من netstat
        result = subprocess.run(['ss', '-tulpn'], capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except (FileNotFoundError, subprocess.CalledProcessError):
        try:
            # لو ss مش موجود، بنجرب netstat
            result = subprocess.run(['netstat', '-tulpn'], capture_output=True, text=True, check=True)
            return result.stdout.strip().split('\n')
        except (FileNotFoundError, subprocess.CalledProcessError):
            return ["Could not retrieve open ports (ss or netstat not found)."]

def main():
    """الدالة الرئيسية اللي بتجمع كل البيانات."""
    print("جاري جمع معلومات الـ VPS... استنى شوية.")
    
    vps_data = {
        "public_ip": get_public_ip(),
        "system": get_system_info(),
        "user": get_user_info(),
        "hardware": get_hardware_info(),
        "network": get_network_info(),
        "open_ports": get_open_ports()
    }
    
    print("\n" + "="*50)
    print("بيانات الـ VPS كاملة:")
    print("="*50)
    
    print(json.dumps(vps_data, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
