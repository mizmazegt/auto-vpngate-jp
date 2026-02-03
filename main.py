import requests
import csv
import base64
import os
import time
import shutil
from io import StringIO
from datetime import datetime, timezone, timedelta

# --- CẤU HÌNH ---
VPN_API = "http://www.vpngate.net/api/iphone/"
ISP_API = "http://ip-api.com/json/{}"
SAVE_DIR = "ovpn_files"
README_FILE = "README.md"
CUSTOM_CIPHER = "data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:AES-128-CBC"

def get_servers():
    print(f"[*] Đang tải danh sách server...")
    try:
        res = requests.get(VPN_API, timeout=20)
        raw = []
        for line in res.text.splitlines():
            line = line.strip()
            if line.startswith('*') or not line: continue
            if line.startswith('#HostName'):
                line = line.replace('#HostName', 'HostName')
            raw.append(line)

        if raw and "HostName" not in raw[0]:
            header = "HostName,IP,Score,Ping,Speed,CountryLong,CountryShort,NumVpnSessions,Uptime,TotalUsers,TotalTraffic,LogType,Operator,Message,OpenVPN_ConfigData_Base64"
            raw.insert(0, header)
            
        return list(csv.DictReader(StringIO("\n".join(raw))))
    except Exception as e:
        print(f"[!] Lỗi tải VPN API: {e}")
        return []

def get_isp(ip):
    try:
        res = requests.get(ISP_API.format(ip), timeout=3).json()
        return res.get('isp', 'Unknown').replace(" ", "")
    except:
        return "Unknown"

def clean_ovpn_content(text):
    return "\n".join([line for line in text.splitlines() if line.strip()])

def save_ovpn(server):
    try:
        ip = server['IP']
        speed = int(server['Speed']) / 1000000
        isp = get_isp(ip)
        
        filename = f"JP_{isp}_{ip}_{speed:.1f}Mbps.ovpn"
        path = os.path.join(SAVE_DIR, filename)

        raw_b64 = server['OpenVPN_ConfigData_Base64']
        decoded_config = base64.b64decode(raw_b64).decode('utf-8')
        content_cleaned = clean_ovpn_content(decoded_config)
        
        final_data = f"# JP | {isp} | {ip} | {speed:.1f}Mbps\n{CUSTOM_CIPHER}\n{content_cleaned}"
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(final_data)
        
        return {
            "filename": filename,
            "hostname": server.get('HostName', '-'),
            "ip": ip,
            "isp": isp,
            "ping": server.get('Ping', '0'),
            "speed": speed
        }
    except:
        return None

def update_readme(success_list):
    tz_vn = timezone(timedelta(hours=7))
    now = datetime.now(tz_vn).strftime("%H:%M %d/%m")
    
    # --- CẤU HÌNH BẢNG ---
    # Đã xóa cột Country
    # ISP Name: Căn trái (:---|)
    # Các cột khác: Căn giữa (:---:)
    
    md_content = f"""# 🇯🇵 VPN Gate List (JP)
*Updated: {now} (GMT+7) | Servers: {len(success_list)}*

| Hostname | IP | ISP Name | Ping (ms) | Speed (Mbps) | Download |
|:---:|:---:|:---|:---:|:---:|:---:|
"""
    
    for item in success_list:
        relative_link = f"./{SAVE_DIR}/{item['filename']}"
        
        try:
            ping_val = int(item['ping'])
        except:
            ping_val = 0
            
        speed_val = f"{item['speed']:.1f}"
        
        # Format ISP: Chữ nhỏ + In đậm
        isp_display = f"**<small>{item['isp']}</small>**"
        
        row = f"| {item['hostname']} | {item['ip']} | {isp_display} | {ping_val} | {speed_val} | [📥]({relative_link}) |\n"
        md_content += row
    
    md_content += "\n*Auto-updated by GitHub Actions*"
    
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print("[*] Đã cập nhật README.md")

def main():
    if os.path.exists(SAVE_DIR): shutil.rmtree(SAVE_DIR)
    os.makedirs(SAVE_DIR)
    
    servers = get_servers()
    jp_list = sorted([s for s in servers if s['CountryShort'] == 'JP'], 
                     key=lambda x: int(x['Speed']), reverse=True)
    
    print(f"[*] Tìm thấy {len(jp_list)} server JP. Bắt đầu xử lý...")

    success_items = []
    for s in jp_list[:100]: 
        result = save_ovpn(s)
        if result: success_items.append(result)
        time.sleep(1)

    update_readme(success_items)
    print(f"[*] Xong!")

if __name__ == "__main__":
    main()
