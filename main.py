import requests
import csv
import base64
import os
import shutil
from io import StringIO
from datetime import datetime, timedelta, timezone

# --- CẤU HÌNH CHO NETLIFY ---
# Netlify sẽ publish thư mục 'public'
PUBLISH_DIR = "public"
SAVE_DIR_NAME = "ovpn_files"
SAVE_DIR = os.path.join(PUBLISH_DIR, SAVE_DIR_NAME)
HTML_FILE = os.path.join(PUBLISH_DIR, "index.html")

VPN_API = "http://www.vpngate.net/api/iphone/"
ISP_API = "http://ip-api.com/json/{}"
CUSTOM_CIPHER = "data-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:AES-128-CBC"

def get_servers():
    print("Downloading server list...")
    try:
        res = requests.get(VPN_API, timeout=30)
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
        print(f"Error downloading: {e}")
        return []

def get_isp(ip):
    try:
        res = requests.get(ISP_API.format(ip), timeout=5).json()
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
        filepath = os.path.join(SAVE_DIR, filename)

        raw_b64 = server['OpenVPN_ConfigData_Base64']
        decoded_config = base64.b64decode(raw_b64).decode('utf-8')
        content_cleaned = clean_ovpn_content(decoded_config)
        
        final_data = f"# JP | {isp} | {ip} | {speed:.1f}Mbps\n{CUSTOM_CIPHER}\n{content_cleaned}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
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

def update_html(success_list):
    # Giờ VN
    tz_vn = timezone(timedelta(hours=7))
    time_str = datetime.now(tz_vn).strftime("%H:%M %d/%m/%Y")
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Japan VPN List</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f0f2f5; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
            .container {{ max-width: 900px; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
            h1 {{ color: #1a1a1a; font-weight: 700; font-size: 1.8rem; margin-bottom: 0; }}
            .badge-isp {{ background-color: #e4e6eb; color: #050505; font-weight: 600; font-size: 0.8rem; padding: 4px 8px; border-radius: 6px; }}
            .btn-dl {{ font-size: 0.85rem; font-weight: 500; }}
            td {{ vertical-align: middle; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1>🇯🇵 JP VPN Gate</h1>
                <div class="text-end">
                    <div class="text-muted small">Updated: {time_str}</div>
                    <div class="badge bg-success">{len(success_list)} Servers</div>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>Hostname / IP</th>
                            <th>ISP</th>
                            <th class="text-center">Ping</th>
                            <th class="text-center">Speed</th>
                            <th class="text-end">Action</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for item in success_list:
        link = f"./{SAVE_DIR_NAME}/{item['filename']}"
        html_content += f"""
                        <tr>
                            <td>
                                <div class="fw-bold text-dark">{item['hostname']}</div>
                                <div class="text-muted small">{item['ip']}</div>
                            </td>
                            <td><span class="badge-isp">{item['isp']}</span></td>
                            <td class="text-center text-muted">{item['ping']} ms</td>
                            <td class="text-center fw-bold" style="color: #218838">{item['speed']:.1f} Mbps</td>
                            <td class="text-end">
                                <a href="{link}" class="btn btn-primary btn-sm btn-dl" download>Download</a>
                            </td>
                        </tr>
        """

    html_content += """
                    </tbody>
                </table>
            </div>
            <div class="text-center mt-4 text-muted small">
                Deployed on Netlify
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    # Tạo thư mục public nếu chưa có
    if os.path.exists(PUBLISH_DIR):
        shutil.rmtree(PUBLISH_DIR)
    os.makedirs(SAVE_DIR)
            
    servers = get_servers()
    jp_list = sorted([s for s in servers if s['CountryShort'] == 'JP'], 
                     key=lambda x: int(x['Speed']), reverse=True)
    
    success_items = []
    # Lấy 80 server thôi cho nhanh build
    for s in jp_list[:80]:
        res = save_ovpn(s)
        if res: success_items.append(res)
        
    update_html(success_items)
    print("Build Success!")

if __name__ == "__main__":
    main()