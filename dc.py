import shareithub
import json
import threading
import time
import os
import random
import re
import requests
from shareithub import shareithub
from dotenv import load_dotenv
from datetime import datetime
from colorama import init, Fore, Style
from flask import Flask, render_template_string, jsonify, request
from flask_socketio import SocketIO, emit
import webbrowser
from urllib.parse import quote

# Initialize colorama and load environment
init(autoreset=True)
load_dotenv()

# Global variables for web dashboard
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Bot statistics
bot_stats = {
    'status': 'offline',
    'uptime': 0,
    'start_time': None,
    'messages_sent': 0,
    'messages_received': 0,
    'last_activity': None,
    'active_channels': 0,
    'api_keys_total': 0,
    'api_keys_used': 0,
    'logs': []
}

# Discord token configuration
discord_tokens_env = os.getenv('DISCORD_TOKENS', '')
if discord_tokens_env:
    discord_tokens = [token.strip() for token in discord_tokens_env.split(',') if token.strip()]
else:
    discord_token = os.getenv('DISCORD_TOKEN')
    if not discord_token:
        raise ValueError("Tidak ada Discord token yang ditemukan! Harap atur DISCORD_TOKENS atau DISCORD_TOKEN di .env.")
    discord_tokens = [discord_token]

# Google API configuration
google_api_keys = os.getenv('GOOGLE_API_KEYS', '').split(',')
google_api_keys = [key.strip() for key in google_api_keys if key.strip()]
if not google_api_keys:
    raise ValueError("Tidak ada Google API Key yang ditemukan! Harap atur GOOGLE_API_KEYS di .env.")

bot_stats['api_keys_total'] = len(google_api_keys)

# Bot state variables
processed_message_ids = set()
used_api_keys = set()
last_generated_text = None
cooldown_time = 86400
bot_threads = []
bot_running = False

def emit_log(message, level="INFO"):
    """Emit log to web dashboard"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = {
        'timestamp': timestamp,
        'message': message,
        'level': level.lower()
    }
    bot_stats['logs'].append(log_entry)
    
    # Keep only last 100 logs
    if len(bot_stats['logs']) > 100:
        bot_stats['logs'] = bot_stats['logs'][-100:]
    
    # Emit to dashboard
    socketio.emit('new_log', log_entry)

def log_message(message, level="INFO"):
    """Enhanced logging function with web dashboard integration"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Color mapping
    if level.upper() == "SUCCESS":
        color, icon = Fore.GREEN, "✅"
    elif level.upper() == "ERROR":
        color, icon = Fore.RED, "🚨"
    elif level.upper() == "WARNING":
        color, icon = Fore.YELLOW, "⚠️"
    elif level.upper() == "WAIT":
        color, icon = Fore.CYAN, "⌛"
    else:
        color, icon = Fore.WHITE, "ℹ️"
    
    border = f"{Fore.MAGENTA}{'=' * 80}{Style.RESET_ALL}"
    formatted_message = f"{color}[{timestamp}] {icon} {message}{Style.RESET_ALL}"
    
    print(border)
    print(formatted_message)
    print(border)
    
    # Emit to web dashboard
    emit_log(message, level)

def update_bot_stats(**kwargs):
    """Update bot statistics"""
    for key, value in kwargs.items():
        if key in bot_stats:
            bot_stats[key] = value
    
    # Emit updated stats to dashboard
    socketio.emit('stats_update', bot_stats)

def get_random_api_key():
    available_keys = [key for key in google_api_keys if key not in used_api_keys]
    if not available_keys:
        log_message("Semua API key terkena error 429. Menunggu 24 jam sebelum mencoba lagi...", "ERROR")
        update_bot_stats(api_keys_used=len(used_api_keys))
        time.sleep(cooldown_time)
        used_api_keys.clear()
        update_bot_stats(api_keys_used=0)
        return get_random_api_key()
    return random.choice(available_keys)

def get_random_message_from_file():
    try:
        with open("pesan.txt", "r", encoding="utf-8") as file:
            messages = [line.strip() for line in file.readlines() if line.strip()]
            return random.choice(messages) if messages else "Tidak ada pesan tersedia di file."
    except FileNotFoundError:
        return "File pesan.txt tidak ditemukan!"

def generate_language_specific_prompt(user_message, prompt_language):
    if prompt_language == 'id':
        return f"Balas pesan berikut dalam bahasa Indonesia: {user_message}"
    elif prompt_language == 'en':
        return f"Reply to the following message in English: {user_message}"
    else:
        log_message(f"Bahasa prompt '{prompt_language}' tidak valid. Pesan dilewati.", "WARNING")
        return None

def generate_reply(prompt, prompt_language, use_google_ai=True):
    global last_generated_text
    
    if use_google_ai:
        google_api_key = get_random_api_key()
        lang_prompt = generate_language_specific_prompt(prompt, prompt_language)
        if lang_prompt is None:
            return None
        
        ai_prompt = f"{lang_prompt}\n\nBuatlah menjadi 1 kalimat menggunakan bahasa sehari hari manusia."
        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={google_api_key}'
        headers = {'Content-Type': 'application/json'}
        data = {'contents': [{'parts': [{'text': ai_prompt}]}]}
        
        while True:
            try:
                response = requests.post(url, headers=headers, json=data)
                if response.status_code == 429:
                    log_message(f"API key {google_api_key} terkena rate limit (429). Menggunakan API key lain...", "WARNING")
                    used_api_keys.add(google_api_key)
                    update_bot_stats(api_keys_used=len(used_api_keys))
                    return generate_reply(prompt, prompt_language, use_google_ai)
                
                response.raise_for_status()
                result = response.json()
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                
                if generated_text == last_generated_text:
                    log_message("AI menghasilkan teks yang sama, meminta teks baru...", "WAIT")
                    continue
                
                last_generated_text = generated_text
                return generated_text
                
            except requests.exceptions.RequestException as e:
                log_message(f"Request failed: {e}", "ERROR")
                time.sleep(2)
    else:
        return get_random_message_from_file()

def get_channel_info(channel_id, token):
    headers = {'Authorization': token}
    channel_url = f"https://discord.com/api/v9/channels/{channel_id}"
    
    try:
        channel_response = requests.get(channel_url, headers=headers)
        channel_response.raise_for_status()
        channel_data = channel_response.json()
        
        channel_name = channel_data.get('name', 'Unknown Channel')
        guild_id = channel_data.get('guild_id')
        server_name = "Direct Message"
        
        if guild_id:
            guild_url = f"https://discord.com/api/v9/guilds/{guild_id}"
            guild_response = requests.get(guild_url, headers=headers)
            guild_response.raise_for_status()
            guild_data = guild_response.json()
            server_name = guild_data.get('name', 'Unknown Server')
        
        return server_name, channel_name
    except requests.exceptions.RequestException as e:
        log_message(f"Error mengambil info channel: {e}", "ERROR")
        return "Unknown Server", "Unknown Channel"

def get_bot_info(token):
    headers = {'Authorization': token}
    try:
        response = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
        response.raise_for_status()
        data = response.json()
        username = data.get("username", "Unknown")
        discriminator = data.get("discriminator", "")
        bot_id = data.get("id", "Unknown")
        return username, discriminator, bot_id
    except requests.exceptions.RequestException as e:
        log_message(f"Gagal mengambil info akun bot: {e}", "ERROR")
        return "Unknown", "", "Unknown"

def auto_reply(channel_id, settings, token):
    headers = {'Authorization': token}
    
    if settings["use_google_ai"]:
        try:
            bot_info_response = requests.get('https://discord.com/api/v9/users/@me', headers=headers)
            bot_info_response.raise_for_status()
            bot_user_id = bot_info_response.json().get('id')
        except requests.exceptions.RequestException as e:
            log_message(f"[Channel {channel_id}] Gagal mengambil info bot: {e}", "ERROR")
            return
        
        while bot_running:
            prompt = None
            reply_to_id = None
            log_message(f"[Channel {channel_id}] Menunggu {settings['read_delay']} detik sebelum membaca pesan...", "WAIT")
            time.sleep(settings["read_delay"])
            
            if not bot_running:
                break
                
            try:
                response = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers)
                response.raise_for_status()
                messages = response.json()
                
                if messages:
                    most_recent_message = messages[0]
                    message_id = most_recent_message.get('id')
                    author_id = most_recent_message.get('author', {}).get('id')
                    message_type = most_recent_message.get('type', '')
                    
                    if author_id != bot_user_id and message_type != 8 and message_id not in processed_message_ids:
                        user_message = most_recent_message.get('content', '').strip()
                        attachments = most_recent_message.get('attachments', [])
                        
                        if attachments or not re.search(r'\w', user_message):
                            log_message(f"[Channel {channel_id}] Pesan tidak diproses (bukan teks murni).", "WARNING")
                        else:
                            log_message(f"[Channel {channel_id}] Received: {user_message}", "INFO")
                            bot_stats['messages_received'] += 1
                            bot_stats['last_activity'] = datetime.now().strftime('%H:%M:%S')
                            update_bot_stats(messages_received=bot_stats['messages_received'], 
                                           last_activity=bot_stats['last_activity'])
                            
                            if settings["use_slow_mode"]:
                                slow_mode_delay = get_slow_mode_delay(channel_id, token)
                                log_message(f"[Channel {channel_id}] Slow mode aktif, menunggu {slow_mode_delay} detik...", "WAIT")
                                time.sleep(slow_mode_delay)
                            
                            prompt = user_message
                            reply_to_id = message_id
                            processed_message_ids.add(message_id)
                else:
                    prompt = None
                    
            except requests.exceptions.RequestException as e:
                log_message(f"[Channel {channel_id}] Request error: {e}", "ERROR")
                prompt = None
            
            if prompt and bot_running:
                result = generate_reply(prompt, settings["prompt_language"], settings["use_google_ai"])
                if result is None:
                    log_message(f"[Channel {channel_id}] Bahasa prompt tidak valid. Pesan dilewati.", "WARNING")
                else:
                    response_text = result if result else "Maaf, tidak dapat membalas pesan."
                    if response_text.strip().lower() == prompt.strip().lower():
                        log_message(f"[Channel {channel_id}] Balasan sama dengan pesan yang diterima. Tidak mengirim balasan.", "WARNING")
                    else:
                        if settings["use_reply"]:
                            send_message(channel_id, response_text, token, reply_to=reply_to_id, 
                                       delete_after=settings["delete_bot_reply"], delete_immediately=settings["delete_immediately"])
                        else:
                            send_message(channel_id, response_text, token, 
                                       delete_after=settings["delete_bot_reply"], delete_immediately=settings["delete_immediately"])
            else:
                log_message(f"[Channel {channel_id}] Tidak ada pesan baru atau pesan tidak valid.", "INFO")
            
            if bot_running:
                log_message(f"[Channel {channel_id}] Menunggu {settings['delay_interval']} detik sebelum iterasi berikutnya...", "WAIT")
                time.sleep(settings["delay_interval"])
    else:
        while bot_running:
            delay = settings["delay_interval"]
            log_message(f"[Channel {channel_id}] Menunggu {delay} detik sebelum mengirim pesan dari file...", "WAIT")
            time.sleep(delay)
            
            if not bot_running:
                break
                
            message_text = generate_reply("", settings["prompt_language"], use_google_ai=False)
            if settings["use_reply"]:
                send_message(channel_id, message_text, token, delete_after=settings["delete_bot_reply"], 
                           delete_immediately=settings["delete_immediately"])
            else:
                send_message(channel_id, message_text, token, delete_after=settings["delete_bot_reply"], 
                           delete_immediately=settings["delete_immediately"])

def send_message(channel_id, message_text, token, reply_to=None, delete_after=None, delete_immediately=False):
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    payload = {'content': message_text}
    
    if reply_to:
        payload["message_reference"] = {"message_id": reply_to}
    
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        if response.status_code in [200, 201]:
            data = response.json()
            message_id = data.get("id")
            log_message(f"[Channel {channel_id}] Pesan terkirim: \"{message_text}\" (ID: {message_id})", "SUCCESS")
            
            bot_stats['messages_sent'] += 1
            bot_stats['last_activity'] = datetime.now().strftime('%H:%M:%S')
            update_bot_stats(messages_sent=bot_stats['messages_sent'], 
                           last_activity=bot_stats['last_activity'])
            
            if delete_after is not None:
                if delete_immediately:
                    log_message(f"[Channel {channel_id}] Menghapus pesan segera tanpa delay...", "WAIT")
                    threading.Thread(target=delete_message, args=(channel_id, message_id, token), daemon=True).start()
                elif delete_after > 0:
                    log_message(f"[Channel {channel_id}] Pesan akan dihapus dalam {delete_after} detik...", "WAIT")
                    threading.Thread(target=delayed_delete, args=(channel_id, message_id, delete_after, token), daemon=True).start()
        else:
            log_message(f"[Channel {channel_id}] Gagal mengirim pesan. Status: {response.status_code}", "ERROR")
            log_message(f"[Channel {channel_id}] Respons API: {response.text}", "ERROR")
            
    except requests.exceptions.RequestException as e:
        log_message(f"[Channel {channel_id}] Kesalahan saat mengirim pesan: {e}", "ERROR")

def delayed_delete(channel_id, message_id, delay, token):
    time.sleep(delay)
    delete_message(channel_id, message_id, token)

def delete_message(channel_id, message_id, token):
    headers = {'Authorization': token, 'Content-Type': 'application/json'}
    url = f'https://discord.com/api/v9/channels/{channel_id}/messages/{message_id}'
    
    try:
        response = requests.delete(url, headers=headers)
        if response.status_code == 204:
            log_message(f"[Channel {channel_id}] Pesan dengan ID {message_id} berhasil dihapus.", "SUCCESS")
        else:
            log_message(f"[Channel {channel_id}] Gagal menghapus pesan. Status: {response.status_code}", "ERROR")
            log_message(f"[Channel {channel_id}] Respons API: {response.text}", "ERROR")
    except requests.exceptions.RequestException as e:
        log_message(f"[Channel {channel_id}] Kesalahan saat menghapus pesan: {e}", "ERROR")

def get_slow_mode_delay(channel_id, token):
    headers = {'Authorization': token, 'Accept': 'application/json'}
    url = f"https://discord.com/api/v9/channels/{channel_id}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        slow_mode_delay = data.get("rate_limit_per_user", 0)
        log_message(f"[Channel {channel_id}] Slow mode delay: {slow_mode_delay} detik", "INFO")
        return slow_mode_delay
    except requests.exceptions.RequestException as e:
        log_message(f"[Channel {channel_id}] Gagal mengambil informasi slow mode: {e}", "ERROR")
        return 5

def get_server_settings(channel_id, channel_name):
    print(f"\nMasukkan pengaturan untuk channel {channel_id} (Nama Channel: {channel_name}):")
    use_google_ai = input("  Gunakan Google Gemini AI? (y/n): ").strip().lower() == 'y'
    
    if use_google_ai:
        prompt_language = input("  Pilih bahasa prompt (en/id): ").strip().lower()
        if prompt_language not in ["en", "id"]:
            print("  Input tidak valid. Default ke 'id'.")
            prompt_language = "id"
        enable_read_message = True
        read_delay = int(input("  Masukkan delay membaca pesan (detik): "))
        delay_interval = int(input("  Masukkan interval (detik) untuk setiap iterasi auto reply: "))
        use_slow_mode = input("  Gunakan slow mode? (y/n): ").strip().lower() == 'y'
    else:
        prompt_language = input("  Pilih bahasa pesan dari file (en/id): ").strip().lower()
        if prompt_language not in ["en", "id"]:
            print("  Input tidak valid. Default ke 'id'.")
            prompt_language = "id"
        enable_read_message = False
        read_delay = 0
        delay_interval = int(input("  Masukkan delay (detik) untuk mengirim pesan dari file: "))
        use_slow_mode = False
    
    use_reply = input("  Kirim pesan sebagai reply? (y/n): ").strip().lower() == 'y'
    hapus_balasan = input("  Hapus balasan bot setelah beberapa detik? (y/n): ").strip().lower() == 'y'
    
    if hapus_balasan:
        delete_bot_reply = int(input("  Setelah berapa detik balasan dihapus? (0 untuk tidak, atau masukkan delay): "))
        delete_immediately = input("  Hapus pesan langsung tanpa delay? (y/n): ").strip().lower() == 'y'
    else:
        delete_bot_reply = None
        delete_immediately = False
    
    return {
        "prompt_language": prompt_language,
        "use_google_ai": use_google_ai,
        "enable_read_message": enable_read_message,
        "read_delay": read_delay,
        "delay_interval": delay_interval,
        "use_slow_mode": use_slow_mode,
        "use_reply": use_reply,
        "delete_bot_reply": delete_bot_reply,
        "delete_immediately": delete_immediately
    }

# Web Dashboard Routes
@app.route('/')
def dashboard():
    return open('dashboard.html').read()

@app.route('/api/stats')
def get_stats():
    if bot_stats['start_time']:
        bot_stats['uptime'] = int(time.time() - bot_stats['start_time'])
    return jsonify(bot_stats)

@app.route('/api/start', methods=['POST'])
def start_bot_api():
    global bot_running, bot_threads
    if not bot_running:
        bot_running = True
        bot_stats['status'] = 'online'
        bot_stats['start_time'] = time.time()
        update_bot_stats(status='online', start_time=bot_stats['start_time'])
        log_message("Bot started via web dashboard", "SUCCESS")
        return jsonify({'status': 'success', 'message': 'Bot started'})
    return jsonify({'status': 'error', 'message': 'Bot already running'})

@app.route('/api/stop', methods=['POST'])
def stop_bot_api():
    global bot_running
    bot_running = False
    bot_stats['status'] = 'offline'
    update_bot_stats(status='offline')
    log_message("Bot stopped via web dashboard", "WARNING")
    return jsonify({'status': 'success', 'message': 'Bot stopped'})

@app.route('/api/restart', methods=['POST'])
def restart_bot_api():
    global bot_running, bot_stats
    bot_running = False
    time.sleep(2)
    bot_running = True
    bot_stats['start_time'] = time.time()
    bot_stats['status'] = 'online'
    update_bot_stats(status='online', start_time=bot_stats['start_time'])
    log_message("Bot restarted via web dashboard", "SUCCESS")
    return jsonify({'status': 'success', 'message': 'Bot restarted'})

@app.route('/api/clear_logs', methods=['POST'])
def clear_logs_api():
    bot_stats['logs'] = []
    socketio.emit('logs_cleared')
    log_message("Logs cleared via web dashboard", "INFO")
    return jsonify({'status': 'success', 'message': 'Logs cleared'})

def run_web_dashboard():
    """Run the web dashboard in a separate thread"""
    socketio.run(app, host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def start_bot_with_dashboard(channel_ids, server_settings, channel_infos):
    """Start bot with web dashboard"""
    global bot_running, bot_threads
    
    # Start web dashboard
    dashboard_thread = threading.Thread(target=run_web_dashboard, daemon=True)
    dashboard_thread.start()
    
    # Open browser
    time.sleep(2)
    webbrowser.open('http://127.0.0.1:5000')
    
    log_message("Web Dashboard tersedia di: http://127.0.0.1:5000", "SUCCESS")
    
    # Start bot threads
    bot_running = True
    bot_stats['status'] = 'online'
    bot_stats['start_time'] = time.time()
    bot_stats['active_channels'] = len(channel_ids)
    update_bot_stats(status='online', start_time=bot_stats['start_time'], active_channels=len(channel_ids))
    
    token_index = 0
    for channel_id in channel_ids:
        token = discord_tokens[token_index % len(discord_tokens)]
        token_index += 1
        
        thread = threading.Thread(
            target=auto_reply,
            args=(channel_id, server_settings[channel_id], token),
            daemon=True
        )
        thread.start()
        bot_threads.append(thread)
        
        log_message(f"[Channel {channel_id}] Bot thread started", "SUCCESS")

if __name__ == "__main__":
    # Get bot info
    bot_accounts = {}
    for token in discord_tokens:
        username, discriminator, bot_id = get_bot_info(token)
        bot_accounts[token] = {"username": username, "discriminator": discriminator, "bot_id": bot_id}
        log_message(f"Akun Bot: {username}#{discriminator} (ID: {bot_id})", "SUCCESS")
    
    # Input channel IDs
    channel_ids = [cid.strip() for cid in input("Masukkan ID channel (pisahkan dengan koma jika lebih dari satu): ").split(",") if cid.strip()]
    token = discord_tokens[0]
    
    # Get channel info
    channel_infos = {}
    for channel_id in channel_ids:
        server_name, channel_name = get_channel_info(channel_id, token)
        channel_infos[channel_id] = {"server_name": server_name, "channel_name": channel_name}
        log_message(f"[Channel {channel_id}] Terhubung ke server: {server_name} | Nama Channel: {channel_name}", "SUCCESS")
    
    # Get server settings
    server_settings = {}
    for channel_id in channel_ids:
        channel_name = channel_infos.get(channel_id, {}).get("channel_name", "Unknown Channel")
        server_settings[channel_id] = get_server_settings(channel_id, channel_name)
    
    # Display settings
    for cid, settings in server_settings.items():
        info = channel_infos.get(cid, {"server_name": "Unknown Server", "channel_name": "Unknown Channel"})
        hapus_str = ("Langsung" if settings['delete_immediately'] else 
                     (f"Dalam {settings['delete_bot_reply']} detik" if settings['delete_bot_reply'] and settings['delete_bot_reply'] > 0 else "Tidak"))
        log_message(
            f"[Channel {cid} | Server: {info['server_name']} | Channel: {info['channel_name']}] "
            f"Pengaturan: Gemini AI = {'Aktif' if settings['use_google_ai'] else 'Tidak'}, "
            f"Bahasa = {settings['prompt_language'].upper()}, "
            f"Membaca Pesan = {'Aktif' if settings['enable_read_message'] else 'Tidak'}, "
            f"Delay Membaca = {settings['read_delay']} detik, "
            f"Interval = {settings['delay_interval']} detik, "
            f"Slow Mode = {'Aktif' if settings['use_slow_mode'] else 'Tidak'}, "
            f"Reply = {'Ya' if settings['use_reply'] else 'Tidak'}, "
            f"Hapus Pesan = {hapus_str}",
            "INFO"
        )
    
    # Start bot with dashboard
    start_bot_with_dashboard(channel_ids, server_settings, channel_infos)
    
    log_message("Bot sedang berjalan dengan Web Dashboard... Tekan CTRL+C untuk menghentikan.", "INFO")
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        log_message("Menghentikan bot...", "WARNING")
        bot_running = False
        bot_stats['status'] = 'offline'
        update_bot_stats(status='offline')
        log_message("Bot dihentikan!", "SUCCESS")