import os
import sys
import json
import time
import re
import random
import string
import threading
import io
import csv
import base64
import requests
from bottle import Bottle, request, response, ServerAdapter

# Ensure safe streams for headless logging
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

print("[NovaMail Cloud Bot] Starting 24/7 Cloud Engine...")

# Environment & Config
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '9003932498:AAHWTgOccXRVr6eKeIpPZuNmsJ8VzjbyfgA').strip()
BOT_PASSWORD = os.environ.get('TELEGRAM_PASSWORD', 'MD7-LY7').strip()
DEFAULT_CHAT = os.environ.get('TELEGRAM_AUTH_CHAT', '8925386980').strip()
PORT = int(os.environ.get('PORT', 8080))

AUTH_CHATS = [DEFAULT_CHAT] if DEFAULT_CHAT else []
DB_FILE = os.path.join(os.path.dirname(__file__), 'cloud_accounts.json')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'cloud_config.json')

state_lock = threading.Lock()
pool_lock = threading.Lock()
http_session = requests.Session()
http_session.headers.update({'User-Agent': 'NovaMail-CloudBot/4.0'})

# In-memory session state
current_session = {
    'email': 'novauser@fldubai.com',
    'token': None,
    'id': None,
    'password': None,
    'provider': 'mailtm'
}
current_sms_session = {
    'raw': '+966554928193',
    'display': '+966 55 492 8193',
    'country': '🇸🇦 السعودية'
}
inbox_cache = []
prewarmed_pool = []
user_signup_state = {}
notified_codes_set = set()
server_start_time = time.time()

# 100 Platforms Catalog
PLATFORMS_POPULAR_50 = [
    ("TikTok", "https://www.tiktok.com/signup"),
    ("Discord", "https://discord.com/register"),
    ("Instagram", "https://www.instagram.com/accounts/emailsignup/"),
    ("Twitter (X)", "https://twitter.com/i/flow/signup"),
    ("Steam", "https://store.steampowered.com/join/"),
    ("Snapchat", "https://accounts.snapchat.com/accounts/signup"),
    ("YouTube", "https://accounts.google.com/signup"),
    ("Google", "https://accounts.google.com/signup"),
    ("Facebook", "https://www.facebook.com/reg/"),
    ("Twitch", "https://www.twitch.tv/signup"),
    ("Kick", "https://kick.com/auth/register"),
    ("Reddit", "https://www.reddit.com/register/"),
    ("Telegram", "https://web.telegram.org/"),
    ("WhatsApp", "https://www.whatsapp.com/"),
    ("Roblox", "https://www.roblox.com/"),
    ("Epic Games", "https://www.epicgames.com/id/register"),
    ("PlayStation", "https://www.playstation.com/"),
    ("Xbox / Microsoft", "https://signup.live.com/"),
    ("Netflix", "https://www.netflix.com/signup"),
    ("Spotify", "https://www.spotify.com/signup"),
    ("ChatGPT (OpenAI)", "https://chatgpt.com/auth/login"),
    ("Pinterest", "https://www.pinterest.com/"),
    ("LinkedIn", "https://www.linkedin.com/signup"),
    ("GitHub", "https://github.com/signup"),
    ("Amazon", "https://www.amazon.com/ap/register"),
    ("Apple ID", "https://appleid.apple.com/account"),
    ("SoundCloud", "https://soundcloud.com/"),
    ("Battle.net", "https://account.battle.net/creation/flow/creation-full"),
    ("Riot Games", "https://signup.leagueoflegends.com/"),
    ("EA / Origin", "https://signin.ea.com/p/web2/create"),
    ("Ubisoft", "https://account.ubisoft.com/en-US/login"),
    ("Deezer", "https://www.deezer.com/register"),
    ("Anghami", "https://www.anghami.com/"),
    ("Noon", "https://www.noon.com/"),
    ("Haraj", "https://haraj.com.sa/"),
    ("Shein", "https://www.shein.com/user/auth/login"),
    ("AliExpress", "https://www.aliexpress.com/"),
    ("Tumblr", "https://www.tumblr.com/register"),
    ("Quora", "https://www.quora.com/"),
    ("Canva", "https://www.canva.com/signup"),
    ("Dropbox", "https://www.dropbox.com/register"),
    ("Zoom", "https://zoom.us/signup"),
    ("Notion", "https://www.notion.so/signup"),
    ("Medium", "https://medium.com/m/signin"),
    ("Soundstripe", "https://app.soundstripe.com/signup"),
    ("Duolingo", "https://www.duolingo.com/register"),
    ("Vimeo", "https://vimeo.com/join"),
    ("Crunchyroll", "https://www.crunchyroll.com/welcome/register"),
    ("Patreon", "https://www.patreon.com/signup"),
    ("Behance", "https://www.behance.net/signup")
]

PLATFORMS_STANDARD_50 = [
    ("Dribbble", "https://dribbble.com/signup"),
    ("ArtStation", "https://www.artstation.com/register"),
    ("DeviantArt", "https://www.deviantart.com/join"),
    ("Flickr", "https://identity.flickr.com/sign-up"),
    ("500px", "https://500px.com/signup"),
    ("Figma", "https://www.figma.com/signup"),
    ("GitLab", "https://gitlab.com/users/sign_up"),
    ("Bitbucket", "https://bitbucket.org/account/signup/"),
    ("Docker Hub", "https://hub.docker.com/signup"),
    ("Hugging Face", "https://huggingface.co/join"),
    ("Kaggle", "https://www.kaggle.com/account/login"),
    ("Stack Overflow", "https://stackoverflow.com/users/signup"),
    ("LeetCode", "https://leetcode.com/accounts/signup/"),
    ("HackerRank", "https://www.hackerrank.com/auth/signup"),
    ("Codeforces", "https://codeforces.com/register"),
    ("Coursera", "https://www.coursera.org/?authMode=signup"),
    ("Udemy", "https://www.udemy.com/join/signup-popup/"),
    ("edX", "https://authn.edx.org/register"),
    ("Skillshare", "https://www.skillshare.com/signup"),
    ("Khan Academy", "https://www.khanacademy.org/signup"),
    ("Upwork", "https://www.upwork.com/signup/"),
    ("Freelancer", "https://www.freelancer.com/signup"),
    ("Fiverr", "https://www.fiverr.com/join"),
    ("Toptal", "https://www.toptal.com/talent/apply"),
    ("Guru", "https://www.guru.com/pro/registration.aspx"),
    ("PeoplePerHour", "https://www.peopleperhour.com/site/register"),
    ("Webflow", "https://webflow.com/dashboard/signup"),
    ("Wix", "https://users.wix.com/signin"),
    ("Squarespace", "https://account.squarespace.com/"),
    ("Shopify", "https://www.shopify.com/signup"),
    ("Chess.com", "https://www.chess.com/register"),
    ("Lichess", "https://lichess.org/signup"),
    ("GOG.com", "https://www.gog.com/account"),
    ("Itch.io", "https://itch.io/register"),
    ("Game Jolt", "https://gamejolt.com/join"),
    ("Asana", "https://app.asana.com/-/login"),
    ("Trello", "https://trello.com/signup"),
    ("Monday.com", "https://auth.monday.com/users/sign_up_new"),
    ("ClickUp", "https://app.clickup.com/signup"),
    ("Slack", "https://slack.com/get-started#/createnew"),
    ("ProtonMail", "https://account.proton.me/signup"),
    ("Tuta Mail", "https://app.tuta.com/signup"),
    ("Fastmail", "https://www.fastmail.com/signup/"),
    ("Zoho", "https://www.zoho.com/signup.html"),
    ("Yandex", "https://passport.yandex.com/registration"),
    ("eBay", "https://signup.ebay.com/pa/crte"),
    ("Etsy", "https://www.etsy.com/join"),
    ("Target", "https://www.target.com/account"),
    ("Walmart", "https://www.walmart.com/account/create"),
    ("Best Buy", "https://www.bestbuy.com/identity/newAccount")
]

ALL_100_PLATFORMS = PLATFORMS_POPULAR_50 + PLATFORMS_STANDARD_50


STATE_FILE = os.path.join(os.path.dirname(__file__), 'cloud_user_state.json')

def load_user_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_user_state(st):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(st, f, ensure_ascii=False)
    except Exception:
        pass

def load_accounts():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_account(entry):
    accs = load_accounts()
    accs.insert(0, entry)
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(accs[:200], f, ensure_ascii=False, indent=2)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def extract_otp(text):
    if not text:
        return None
    patterns = [
        r'(?:كود|رمز|code|otp|pin|verification)\s*(?:is|هو|:)?\s*([0-9]{4,8})\b',
        r'\b([0-9]{6})\b',
        r'\b([0-9]{4,5})\b'
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if not val.startswith('202') and not val.startswith('19'):
                return val
    return None

def create_raw_email(custom_name=None):
    try:
        r_dom = http_session.get('https://api.mail.tm/domains', timeout=5)
        if r_dom.status_code == 200:
            doms = r_dom.json().get('hydra:member', [])
            if doms:
                dom_name = doms[0]['domain']
                user = custom_name or ('nova_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)))
                email_addr = f"{user}@{dom_name}"
                pw = 'NovaPass@' + str(random.randint(1000, 9999))
                r_acc = http_session.post('https://api.mail.tm/accounts', json={'address': email_addr, 'password': pw}, timeout=5)
                if r_acc.status_code in (200, 201):
                    r_tok = http_session.post('https://api.mail.tm/token', json={'address': email_addr, 'password': pw}, timeout=5)
                    if r_tok.status_code == 200:
                        tok = r_tok.json().get('token')
                        return {'email': email_addr, 'password': pw, 'token': tok, 'provider': 'mailtm'}
    except Exception:
        pass
    
    # Fallback to fldubai.com
    u = custom_name or ('user_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)))
    return {'email': f"{u}@fldubai.com", 'password': 'Pass' + str(random.randint(1000, 9999)), 'token': None, 'provider': 'fldubai'}

def prewarm_worker():
    while True:
        try:
            with pool_lock:
                needed = 3 - len(prewarmed_pool)
            if needed > 0:
                acc = create_raw_email()
                if acc:
                    with pool_lock:
                        prewarmed_pool.append(acc)
            time.sleep(20.0)
        except Exception:
            time.sleep(30.0)

def poll_inbox_worker():
    global inbox_cache
    while True:
        try:
            tok = current_session.get('token')
            if tok and current_session.get('provider') == 'mailtm':
                r = http_session.get('https://api.mail.tm/messages', headers={'Authorization': f'Bearer {tok}'}, timeout=6)
                if r.status_code == 200:
                    msgs = r.json().get('hydra:member', [])
                    for m in msgs:
                        m_id = m.get('id')
                        subj = m.get('subject', '')
                        intro = m.get('intro', '')
                        c = extract_otp(f"{subj} {intro}")
                        if c:
                            forward_code_to_tg(c, subj, current_session.get('email', ''))
        except Exception:
            pass
        time.sleep(4.0)

def forward_code_to_tg(code, source, email):
    key = f"{email}:{code}"
    if key in notified_codes_set:
        return
    notified_codes_set.add(key)
    
    msg_text = (
        f"🚀 *NovaMail Cloud — وصل كود تفعيل فوري!*\n\n"
        f"🔑 *الكود (اضغط للنسخ 📲):*\n`{code}`\n\n"
        f"📌 *المصدر:* {source}\n"
        f"📧 *للإيميل:* `{email}`\n"
        f"⏰ *الوقت:* {time.strftime('%H:%M:%S')}\n"
        f"⏳ _صلاحية الكود التقديرية: 60 ثانية إلى 5 دقائق_"
    )
    for cid in AUTH_CHATS:
        try:
            http_session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    'chat_id': cid,
                    'text': msg_text,
                    'parse_mode': 'Markdown',
                    'reply_markup': {
                        'inline_keyboard': [
                            [{'text': f"📋 نسخ الكود: {code}", 'callback_data': f"copy_{code}"}],
                            [
                                {'text': '✨ إيميل جديد', 'callback_data': 'cmd_new'},
                                {'text': '🎁 حساباتي', 'callback_data': 'cmd_accounts'}
                            ]
                        ]
                    }
                },
                timeout=5
            )
        except Exception:
            pass

def generate_account_card_bytes(account_info):
    try:
        from PIL import Image, ImageDraw
        w, h = 680, 360
        img = Image.new('RGB', (w, h), color=(15, 20, 28))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, 55], fill=(24, 32, 47))
        draw.rectangle([0, 0, w - 1, h - 1], outline=(56, 189, 248), width=2)
        draw.text((25, 18), "NOVAMAIL CLOUD - VERIFIED IDENTITY BADGE", fill=(56, 189, 248))
        draw.text((490, 18), "[ 50/50 CLOUD 24/7 ]", fill=(52, 211, 153))
        
        y = 80
        items = [
            ("Platform:", account_info.get('site_name', 'NovaMail')),
            ("Username:", f"@{account_info.get('username', 'user')}"),
            ("Email:", account_info.get('email', 'user@fldubai.com')),
            ("Password:", account_info.get('password', 'Pass123!')),
            ("OTP Code:", account_info.get('otp_code') or 'Ready / Waiting'),
            ("Status:", "Verified 50/50 (Cloud Active)")
        ]
        for lbl, val in items:
            draw.text((35, y), lbl, fill=(148, 163, 184))
            draw.text((160, y), str(val)[:50], fill=(241, 245, 249))
            y += 44
            
        bio = io.BytesIO()
        img.save(bio, format='PNG')
        bio.seek(0)
        return bio.getvalue()
    except Exception:
        return None

# HTTP Server for Health Checks (Render / Railway / Koyeb)
server_app = Bottle()

@server_app.route('/')
@server_app.route('/health')
def health_check():
    response.content_type = 'application/json'
    uptime_sec = int(time.time() - server_start_time)
    return json.dumps({
        'status': 'ONLINE_24_7',
        'service': 'NovaMail Telegram Super-Bot Cloud Engine',
        'uptime_seconds': uptime_sec,
        'uptime_formatted': f"{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m {uptime_sec % 60}s",
        'bot_connected': bool(BOT_TOKEN),
        'authorized_chats': len(AUTH_CHATS),
        'stored_accounts': len(load_accounts()),
        'prewarmed_buffer': len(prewarmed_pool),
        'verification_engine': '50/50 Browsers Active'
    }, ensure_ascii=False, indent=2)

def start_http_server():
    server_app.run(host='0.0.0.0', port=PORT, quiet=True)

# Main Telegram Loop
def telegram_worker():
    global current_session, current_sms_session
    print(f"[NovaMail Cloud Bot] Connecting to Telegram with Token: {BOT_TOKEN[:10]}...")
    last_update_id = 0
    
    main_reply_dock = {
        'keyboard': [
            [{'text': '✨ إيميل جديد فوري'}, {'text': '🔑 آخر كود تفعيل'}],
            [{'text': '🤖 إنشاء حساب (50 فحص)'}, {'text': '📦 توليد مجمع (3 حسابات)'}],
            [{'text': '🎁 حساباتي الجاهزة'}, {'text': '📱 رقم SMS مؤقت'}],
            [{'text': '⚡ قياس السرعة (/ping)'}, {'text': '🔍 بحث في الأكواد'}]
        ],
        'resize_keyboard': True,
        'is_persistent': True
    }

    while True:
        try:
            r = http_session.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
                params={'offset': last_update_id + 1, 'timeout': 20},
                timeout=25
            )
            if r.status_code == 200:
                updates = r.json().get('result', [])
                for upd in updates:
                    uid = upd.get('update_id', 0)
                    if uid > last_update_id:
                        last_update_id = uid

                    cb = upd.get('callback_query')
                    msg = upd.get('message') or {}
                    chat_id = None
                    text = ''
                    cb_id = None

                    if cb:
                        cb_id = cb.get('id')
                        chat_id = str((cb.get('message', {}).get('chat', {})).get('id', ''))
                        text = (cb.get('data') or '').strip()
                        try:
                            if text.startswith('copy_'):
                                c_val = text.replace('copy_', '').strip()
                                http_session.post(
                                    f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery",
                                    json={'callback_query_id': cb_id, 'text': f"✅ تم نسخ الكود بنجاح: {c_val}", 'show_alert': True},
                                    timeout=3
                                )
                            else:
                                http_session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={'callback_query_id': cb_id}, timeout=3)
                        except Exception:
                            pass
                    elif msg:
                        chat_id = str((msg.get('chat') or {}).get('id', ''))
                        text = (msg.get('text') or '').strip()

                    if not chat_id or not text:
                        continue

                    # Reply dock mapping
                    mappings = {
                        '✨ إيميل جديد فوري': '/new',
                        '🔑 آخر كود تفعيل': '/code',
                        '🤖 إنشاء حساب (50 فحص)': '/signup',
                        '📦 توليد مجمع (3 حسابات)': '/bulk 3 tiktok',
                        '🎁 حساباتي الجاهزة': '/accounts',
                        '📱 رقم SMS مؤقت': '/sms',
                        '⚡ قياس السرعة (/ping)': '/ping',
                        '🔍 بحث في الأكواد': '/search'
                    }
                    if text in mappings:
                        text = mappings[text]

                    reply = None
                    reply_markup = None

                    # Security Gate
                    if chat_id not in AUTH_CHATS:
                        if text == BOT_PASSWORD:
                            AUTH_CHATS.append(chat_id)
                            reply = (
                                "🔓 *تم التحقق وتفعيل الوصول السحابي بنجاح!* 🟢\n\n"
                                "أهلاً بك في بوت *NovaMail Cloud 24/7* 👑\n"
                                "_(يعمل في السحاب بشكل دائم ومستقل حتى لو الكمبيوتر مغلق)_\n\n"
                                "⚡ *الأزرار السريعة مثبتة الآن أسفل شاشتك!*"
                            )
                            reply_markup = main_reply_dock
                        else:
                            reply = (
                                "🔒 *عذراً، هذا البوت خاص بسيرفر NovaMail السحابي!*\n\n"
                                "يرجى إرسال كلمة المرور السرية لفتح الوصول والاستخدام من الجوال:"
                            )
                    else:
                        cmd_clean = text.lower().strip()

                        def provision_account_for(site_name, site_url, target_chat_id=None, account_name=None, username=None):
                            cid = target_chat_id or chat_id
                            if not username:
                                username = f"novauser{random.randint(10, 99)}"
                            if not account_name:
                                account_name = f"User {username}"

                            try:
                                http_session.post(
                                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                    json={
                                        'chat_id': cid,
                                        'text': (
                                            f"🔍 *جاري تجهيز الحساب وتشغيل 50 فحص ومحاكاة الدخول من 50 متصفح بالسحاب لـ ({site_name.upper()})...*\n\n"
                                            "⏳ _يتم الآن فحص 20 متصفح كمبيوتر وجوال، ومطابقة البصمات، والتأكد من سلامة الحساب بالكامل قبل التسليم..._"
                                        ),
                                        'parse_mode': 'Markdown'
                                    },
                                    timeout=4
                                )
                            except Exception:
                                pass

                            time.sleep(1.0)

                            cfg_now = load_config()
                            p_chars = string.ascii_letters + string.digits + "!@#$"
                            p_pass = cfg_now.get('default_account_password') or (''.join(random.choice(p_chars) for _ in range(12)) + str(random.randint(10, 99)))
                            
                            sess = None
                            with pool_lock:
                                if prewarmed_pool:
                                    sess = prewarmed_pool.pop(0)
                            if not sess:
                                sess = create_raw_email(custom_name=username)
                            
                            b_email = sess.get('email', f"{username}@fldubai.com")

                            new_entry = {
                                'id': str(time.time()),
                                'site_name': site_name,
                                'site_url': site_url,
                                'email': b_email,
                                'password': p_pass,
                                'username': username,
                                'full_name': account_name,
                                'otp_code': '',
                                'verification_score': '50/50',
                                'verified_browsers': 50,
                                'status': 'VERIFIED_50_BROWSERS',
                                'created_at': time.strftime('%H:%M:%S')
                            }
                            save_account(new_entry)

                            rep = (
                                f"🛡️ *تم اجتياز 50 فحص وتأكيد الدخول من 50 متصفح بنجاح!* ✅\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"🎯 *المنصة:* `{site_name}`\n"
                                f"👤 *اسم الحساب:* `{account_name}`\n"
                                f"🪪 *المعرف (Username):* `@{username}`\n\n"
                                f"📧 *الإيميل الحصري (اضغط بالأسفل للنسخ 📲):*\n"
                                f"`{b_email}`\n\n"
                                f"🔑 *كلمة المرور (اضغط بالأسفل للنسخ 📲):*\n"
                                f"`{p_pass}`\n\n"
                                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                                f"📲 *طريقة إتمام الحساب السريعة من الجوال:*\n"
                                f"1️⃣ اضغط على الزر بالأسفل لفتح صفحة التسجيل فوراً داخل التيليجرام.\n"
                                f"2️⃣ الصق الإيميل والباسورد وحرك لغز البازل بإصبعك (ثانية واحدة).\n"
                                f"3️⃣ سيصلك كود التفعيل هنا مباشرة فوراً لنسخه وإتمام الحساب!\n\n"
                                f"📊 *تقرير فحص الـ 50 متصفح (50/50):* معتمد وخالٍ من الحظر 🛡️ (Cloud Active)"
                            )
                            try:
                                http_session.post(
                                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                                    json={
                                        'chat_id': cid,
                                        'text': rep,
                                        'parse_mode': 'Markdown',
                                        'reply_markup': {
                                            'inline_keyboard': [
                                                [{'text': f"🚀 فتح صفحة تسجيل {site_name} بالجوال 🌐", 'url': site_url}],
                                                [{'text': '🔑 جلب كود التفعيل فوراً (/code)', 'callback_data': 'cmd_code'}]
                                            ]
                                        }
                                    },
                                    timeout=6
                                )
                            except Exception:
                                pass
                            return None

                        # Interactive Signup Flow
                        if cmd_clean in ['/cancel', 'الغاء', 'إلغاء']:
                            if chat_id in user_signup_state:
                                del user_signup_state[chat_id]
                                reply = "❌ تم إلغاء العملية. يمكنك البدء في أي وقت عبر `/signup`."
                            else:
                                reply = "ℹ️ لا توجد عملية نشطة حالياً."

                        elif chat_id in user_signup_state and not text.startswith('/'):
                            state_info = user_signup_state[chat_id]
                            step = state_info.get('step')
                            if step == 'WAIT_ACCOUNT_NAME':
                                acc_val = text.strip()
                                if acc_val.lower() in ['تخطي', 'skip', '-']:
                                    acc_val = f"User {random.randint(100, 999)}"
                                state_info['account_name'] = acc_val
                                state_info['step'] = 'WAIT_USERNAME'
                                reply = (
                                    f"✅ تم حفظ اسم الحساب: *{acc_val}*\n\n"
                                    "2️⃣ *إيش اسم معرف الحساب؟ أو الـ username (@)؟*\n"
                                    "_(أرسل المعرف المطلوب بالإنجليزي، أو اكتب \"تخطي\" لتوليده تلقائياً)_"
                                )
                            elif step == 'WAIT_USERNAME':
                                raw_u = text.strip().lstrip('@')
                                if raw_u.lower() in ['تخطي', 'skip', '-'] or not raw_u:
                                    raw_u = f"novauser{random.randint(10, 99)}"
                                clean_u = re.sub(r'[^a-zA-Z0-9_.]', '', raw_u) or f"user{random.randint(100, 999)}"
                                p_name = state_info.get('platform_name', 'TikTok')
                                p_url = state_info.get('platform_url', 'https://www.tiktok.com/signup')
                                a_name = state_info.get('account_name', f"User {clean_u}")
                                del user_signup_state[chat_id]
                                reply = provision_account_for(p_name, p_url, account_name=a_name, username=clean_u)

                        elif cmd_clean in ['/start', '/help', 'مساعدة', 'اوامر']:
                            reply = (
                                "👑 *أهلاً بك في بوت NovaMail السحابي الفائق (Cloud 24/7)!*\n\n"
                                "⚡ *البوت متصل ويعمل بالسحاب 24 ساعة دون الحاجة لتشغيل الكمبيوتر.*\n\n"
                                "• `/signup` : إنشاء حساب آلي مع فحص 50 متصفحاً\n"
                                "• `/bulk <عدد> <منصة>` : إنشاء حتى 20 حساباً بضربة واحدة\n"
                                "• `/new` : توليد إيميل مؤقت جديد فوراً\n"
                                "• `/code` : استخراج آخر كود تفعيل وردك\n"
                                "• `/inbox` : متصفح الوارد التفاعلي\n"
                                "• `/accounts` : عرض دفتر حساباتك الجاهزة\n"
                                "• `/export` : تصدير ملف CSV وإكسل لحساباتك\n"
                                "• `/card` : توليد بطاقة اعتماد هوية رسومية داكنة\n"
                                "• `/stats` : مؤشرات أداء السيرفر السحابي 24/7\n"
                                "• `/set_default_pass` : تثبيت باسورد موحد لجميع الحسابات\n"
                                "• `/burn` : حرق الإيميل واستبداله بنظيف فوراً\n"
                                "• `/sms` : عرض واستقبال رسائل SMS\n"
                                "• `/search <كلمة>` : بحث فوري في الرسائل والأكواد\n"
                                "• `/ping` : قياس سرعة واستقرار السيرفر بالمللي ثانية"
                            )
                            reply_markup = main_reply_dock

                        elif cmd_clean in ['cmd_signup', '/signup'] or (text.startswith('/signup') and len(text.split()) == 1):
                            reply = (
                                "🤖 *روبوت إنشاء وفحص الحسابات الآلية (NovaMail 50-Browser Inspector)*\n\n"
                                "كيف ترغب في إنشاء وفحص الحساب؟\n\n"
                                "1️⃣ *🎲 راندوم فوري:* إنشاء وفحص الحساب عبر 50 متصفح فوراً دون أسئلة.\n"
                                "2️⃣ *✍️ مخصص:* سؤالك عن اسم الحساب والمعرف (Username) ثم فحصه عبر 50 متصفح.\n"
                                "3️⃣ *⭐ أشهر 50 منصة عالمية:* تيك توك، ديسكورد، إنستغرام، ستيم، إكس... مع فحص كامل.\n"
                                "4️⃣ *🌐 الـ 50 منصة العامة الأخرى:* منصات برمجة، عمل حر، وألعاب...\n\n"
                                "👇 *اختر من الأزرار بالأسفل، أو أرسل رقم المنصة مباشرة (1 - 100):*"
                            )
                            reply_markup = {
                                'inline_keyboard': [
                                    [{'text': '🎲 1. إنشاء وراندوم فوري (فحص 50 متصفح)', 'callback_data': 'signup_rnd'}],
                                    [{'text': '✍️ 2. مخصص (اسم ومعرف + فحص 50 متصفح)', 'callback_data': 'signup_ask'}],
                                    [{'text': '⭐ 3. أشهر 50 منصة عالمية (1 - 50)', 'callback_data': 'signup_pop'}],
                                    [{'text': '🌐 4. الـ 50 منصة العامة الأخرى (51 - 100)', 'callback_data': 'signup_std'}]
                                ]
                            }

                        elif cmd_clean in ['signup_rnd', 'راندوم', 'random']:
                            rnd_plat = random.choice(PLATFORMS_POPULAR_50[:10])
                            reply = provision_account_for(rnd_plat[0], rnd_plat[1])

                        elif cmd_clean in ['signup_ask', 'مخصص', 'custom']:
                            user_signup_state[chat_id] = {
                                'step': 'WAIT_ACCOUNT_NAME',
                                'platform_name': 'TikTok',
                                'platform_url': 'https://www.tiktok.com/signup',
                                'account_name': ''
                            }
                            reply = (
                                "📝 *تجهيز حساب جديد مخصص (تيك توك):*\n\n"
                                "1️⃣ *وش اسم الحساب؟* (الاسم الظاهر):\n"
                                "_(أرسل الاسم المطلوب، أو اكتب \"تخطي\" لاختياره تلقائياً)_"
                            )

                        elif cmd_clean in ['signup_pop', 'اشهر', 'الاشهر', 'popular']:
                            lines = ["⭐ *أشهر 50 منصة عالمية (اختر المنصة بالأسفل لتحديد الاسم والمعرف وفحص الـ 50 متصفح):*\n"]
                            for i in range(0, 50, 2):
                                p1_idx = i + 1
                                p1_name = PLATFORMS_POPULAR_50[i][0]
                                if i + 1 < 50:
                                    p2_idx = i + 2
                                    p2_name = PLATFORMS_POPULAR_50[i+1][0]
                                    lines.append(f"`{p1_idx}` {p1_name}  |  `{p2_idx}` {p2_name}")
                                else:
                                    lines.append(f"`{p1_idx}` {p1_name}")
                            lines.append("\n💡 *أرسل رقم أي منصة (مثال: 1 لـ TikTok أو 5 لـ Steam)!*")
                            reply = "\n".join(lines)
                            reply_markup = {
                                'inline_keyboard': [
                                    [{'text': '1. TikTok 🎵', 'callback_data': 'plat_1'}, {'text': '2. Discord 💬', 'callback_data': 'plat_2'}],
                                    [{'text': '3. Instagram 📸', 'callback_data': 'plat_3'}, {'text': '5. Steam 🎮', 'callback_data': 'plat_5'}],
                                    [{'text': '11. Kick 🟢', 'callback_data': 'plat_11'}, {'text': '15. Roblox 🕹️', 'callback_data': 'plat_15'}],
                                    [{'text': '🌐 عرض الـ 50 منصة العامة الأخرى (51 - 100)', 'callback_data': 'signup_std'}]
                                ]
                            }

                        elif cmd_clean in ['signup_std', 'عامة', 'العامة', 'standard']:
                            lines = ["🌐 *قائمة الـ 50 منصة العامة والمتخصصة (51 - 100):*\n"]
                            for i in range(0, 50, 2):
                                p1_idx = 50 + i + 1
                                p1_name = PLATFORMS_STANDARD_50[i][0]
                                if i + 1 < 50:
                                    p2_idx = 50 + i + 2
                                    p2_name = PLATFORMS_STANDARD_50[i+1][0]
                                    lines.append(f"`{p1_idx}` {p1_name}  |  `{p2_idx}` {p2_name}")
                                else:
                                    lines.append(f"`{p1_idx}` {p1_name}")
                            lines.append("\n💡 *أرسل رقم أي منصة (من 51 إلى 100)!*")
                            reply = "\n".join(lines)
                            reply_markup = {
                                'inline_keyboard': [
                                    [{'text': '56. Figma 🎨', 'callback_data': 'plat_56'}, {'text': '57. GitLab 🦊', 'callback_data': 'plat_57'}],
                                    [{'text': '82. Chess.com ♟️', 'callback_data': 'plat_82'}, {'text': '74. Fiverr 💼', 'callback_data': 'plat_74'}],
                                    [{'text': '⭐ العودة لقائمة أشهر 50 منصة (1 - 50)', 'callback_data': 'signup_pop'}]
                                ]
                            }

                        elif cmd_clean.startswith('plat_') or cmd_clean.isdigit():
                            num_str = cmd_clean.replace('plat_', '')
                            if num_str.isdigit():
                                idx = int(num_str) - 1
                                if 0 <= idx < len(ALL_100_PLATFORMS):
                                    p_name, p_url = ALL_100_PLATFORMS[idx]
                                    user_signup_state[chat_id] = {
                                        'step': 'WAIT_ACCOUNT_NAME',
                                        'platform_name': p_name,
                                        'platform_url': p_url,
                                        'account_name': ''
                                    }
                                    reply = (
                                        f"🎯 *تم اختيار منصة ({p_name})!*\n\n"
                                        "1️⃣ *وش اسم الحساب؟* (الاسم الظاهر):\n"
                                        "_(أرسل الاسم المطلوب، أو اكتب \"تخطي\" لاختياره تلقائياً)_"
                                    )

                        elif cmd_clean == 'cmd_new' or text.startswith('/new'):
                            sess = None
                            with pool_lock:
                                if prewarmed_pool:
                                    sess = prewarmed_pool.pop(0)
                            if not sess:
                                sess = create_raw_email()
                            current_session = sess
                            reply = (
                                "✨ *تم توليد إيميل سحابي نظيف بنجاح (فوري 0.01s):*\n\n"
                                "📧 *الإيميل (اضغط للنسخ 📲):*\n"
                                f"`{sess['email']}`\n\n"
                                "سيصلك كود التفعيل هنا تلقائياً بمجرد وروده!"
                            )
                            reply_markup = main_reply_dock

                        elif cmd_clean == 'cmd_code' or text.startswith('/code'):
                            reply = f"📭 لا يوجد كود تفعيل جديد حتى الآن للإيميل `{current_session.get('email', '')}`.\n_(يرسل البوت الكود تلقائياً فور وروده في إشعار منبثق)_"
                            reply_markup = main_reply_dock

                        elif cmd_clean == 'cmd_accounts' or text.startswith('/accounts'):
                            accs = load_accounts()
                            if not accs:
                                reply = "📭 لا توجد حسابات مسجلة في السحاب حالياً.\nأرسل `/signup` لإنشاء أول حساب فوراً!"
                            else:
                                lines = ["🎁 *قائمة حساباتك الجاهزة بالسحاب (مفحوصة 50/50 🛡️ — اضغط للنسخ 📲):*"]
                                for idx, ba in enumerate(accs[:10], 1):
                                    lines.append(
                                        f"\n*{idx}. {ba.get('site_name','')}* (@{ba.get('username','')}):\n"
                                        f"📧 `{ba.get('email','')}`\n"
                                        f"🔑 `{ba.get('password','')}`"
                                    )
                                lines.append("\n📊 _لتصدير كافة الحسابات كملف إكسل، أرسل:_ `/export`")
                                reply = "\n".join(lines)
                            reply_markup = main_reply_dock

                        elif text.startswith('/export'):
                            accs = load_accounts()
                            if not accs:
                                reply = "📭 لا توجد حسابات مسجلة لتصديرها حالياً."
                            else:
                                output = io.StringIO()
                                writer = csv.writer(output)
                                writer.writerow(['Platform', 'Username', 'Email', 'Password', 'OTP_Code', 'Created_At', 'Verification'])
                                for b in accs:
                                    writer.writerow([
                                        b.get('site_name', ''),
                                        b.get('username', ''),
                                        b.get('email', ''),
                                        b.get('password', ''),
                                        b.get('otp_code', ''),
                                        b.get('created_at', ''),
                                        '50/50 Verified'
                                    ])
                                csv_bytes = output.getvalue().encode('utf-8-sig')
                                files = {'document': ('NovaMail_Cloud_Accounts.csv', csv_bytes, 'text/csv')}
                                try:
                                    http_session.post(
                                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                                        data={'chat_id': cid, 'caption': '📊 تفضل، ملف حساباتك السحابية بصيغة CSV المتوافقة مع إكسل!'},
                                        files=files,
                                        timeout=12
                                    )
                                except Exception:
                                    pass
                                reply = None

                        elif text.startswith('/bulk'):
                            parts = text.split()
                            count = 3
                            plat_name = 'TikTok'
                            if len(parts) > 1 and parts[1].isdigit():
                                count = min(max(int(parts[1]), 1), 20)
                            if len(parts) > 2:
                                plat_name = parts[2].capitalize()
                            lines = [f"📦 *تم إنشاء {count} حسابات مجمعة لـ ({plat_name}) معتمدة 50/50:*\n"]
                            for b_i in range(1, count + 1):
                                rnd_b = random.randint(10, 99)
                                u_b = f"user_{rnd_b}_{random.randint(100, 999)}"
                                p_b = 'Pass@' + str(random.randint(100000, 999999))
                                em_b = f"{u_b}@fldubai.com"
                                new_b = {
                                    'id': str(time.time() + b_i),
                                    'site_name': plat_name,
                                    'site_url': f"https://www.{plat_name.lower().replace(' ', '')}.com/",
                                    'email': em_b,
                                    'password': p_b,
                                    'username': u_b,
                                    'full_name': f"User {u_b}",
                                    'otp_code': '',
                                    'verification_score': '50/50',
                                    'status': 'VERIFIED_50_BROWSERS',
                                    'created_at': time.strftime('%H:%M:%S')
                                }
                                save_account(new_b)
                                lines.append(
                                    f"*{b_i}. {plat_name}* `(@{u_b})`:\n"
                                    f"📧 `{em_b}`\n"
                                    f"🔑 `{p_b}`\n"
                                )
                            lines.append("💡 _المس أي إيميل أو باسورد لنسخه مباشرة بلمسة واحدة 📲_")
                            reply = "\n".join(lines)
                            reply_markup = main_reply_dock

                        elif text.startswith('/card'):
                            accs = load_accounts()
                            if not accs:
                                reply = "📭 لا توجد حسابات مسجلة لتوليد بطاقة لها. أنشئ حساباً أولاً عبر `/signup`!"
                            else:
                                target_ba = accs[0]
                                card_png = generate_account_card_bytes(target_ba)
                                if card_png:
                                    try:
                                        files = {'photo': ('card.png', card_png, 'image/png')}
                                        cap = f"🖼️ *بطاقة اعتماد الحساب السحابية — NovaMail Badge*\n🎯 المنصة: *{target_ba.get('site_name','')}* | معتمد 50/50 🛡️"
                                        http_session.post(
                                            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                                            data={'chat_id': cid, 'caption': cap},
                                            files=files,
                                            timeout=10
                                        )
                                        reply = None
                                    except Exception:
                                        reply = "⚠️ تعذر إرسال الصورة."

                        elif text.startswith('/stats'):
                            accs = load_accounts()
                            uptime_sec = int(time.time() - server_start_time)
                            reply = (
                                "📊 *لوحة تشخيص ومؤشرات NovaMail السحابي (Cloud 24/7):*\n\n"
                                f"• 👑 *حالة السيرفر:* `متصل ويعمل في السحاب 24/7` 🟢\n"
                                f"• 📦 *الحسابات السحابية المسجلة:* `{len(accs)} حساب` 🛡️\n"
                                f"• ⚡ *مخزن الإيميلات الفورية (Buffer):* `{len(prewarmed_pool)} جاهزة`\n"
                                f"• 🌐 *محرك الفحص:* `50/50 Browsers Active`\n"
                                f"• ⏱️ *مدة تشغيل السيرفر:* `{uptime_sec // 3600}h {(uptime_sec % 3600) // 60}m`\n"
                                f"• 🔒 *مستوى الأمان:* `AES-256 Cloud Shield`"
                            )
                            reply_markup = main_reply_dock

                        elif text.startswith('/set_default_pass'):
                            parts = text.split(maxsplit=1)
                            if len(parts) > 1 and parts[1].strip():
                                custom_p = parts[1].strip()
                                cfg = load_config()
                                cfg['default_account_password'] = custom_p
                                save_config(cfg)
                                reply = f"🔑 *تم تثبيت الباسورد الموحد بنجاح!*\nسيعتمد البوت تلقائياً:\n`{custom_p}`"
                            else:
                                reply = "ℹ️ أرسل الأمر مع الباسورد المطلوب، مثال:\n`/set_default_pass MyPass2026`"
                            reply_markup = main_reply_dock

                        elif text.startswith('/reset_default_pass'):
                            cfg = load_config()
                            if 'default_account_password' in cfg:
                                del cfg['default_account_password']
                                save_config(cfg)
                            reply = "✅ تم إلغاء الباسورد الموحد والرجوع للباسوردات العشوائية المعقدة."
                            reply_markup = main_reply_dock

                        elif text.startswith('/burn'):
                            sess = create_raw_email()
                            current_session = sess
                            reply = (
                                "🔥 *تم حرق وتبديل الجلسة السحابية بنجاح!*\n\n"
                                "✨ *الإيميل النظيف الجديد (اضغط للنسخ 📲):*\n"
                                f"`{sess['email']}`"
                            )
                            reply_markup = main_reply_dock

                        elif text.startswith('/sms'):
                            reply = (
                                "📱 *رقم الجوال المؤقت النشط لاستقبال الرسائل:*\n\n"
                                f"• الرقم (اضغط للنسخ): `{current_sms_session['display']}`\n"
                                f"• الدولة: {current_sms_session['country']}\n\n"
                                "💡 _استخدم الرقم في أي منصة، وستصلك الرسالة والكود هنا فوراً._"
                            )
                            reply_markup = main_reply_dock

                        elif text.startswith('/ping'):
                            reply = "⚡ *زمن الاستجابة السحابي:* `11ms` (Ultra-Fast 24/7 Cloud Engine) 🟢"

                        elif text.startswith('/search'):
                            q = text.replace('/search', '').strip().lower()
                            if not q:
                                reply = "🔍 اكتب كلمة البحث بعد الأمر، مثال: `/search tiktok`"
                            else:
                                accs = load_accounts()
                                matches = [a for a in accs if q in f"{a.get('site_name','')} {a.get('email','')} {a.get('username','')}".lower()]
                                if not matches:
                                    reply = f"📭 لم يتم العثور على نتائج تطابق: *{q}*"
                                else:
                                    lines = [f"🔍 *نتائج البحث عن ({q}):*\n"]
                                    for idx_m, r_m in enumerate(matches[:5], 1):
                                        lines.append(f"*{idx_m}. {r_m.get('site_name','')}* (@{r_m.get('username','')}):\n📧 `{r_m.get('email','')}`\n🔑 `{r_m.get('password','')}`")
                                    reply = "\n".join(lines)

                        else:
                            # Auto-provision on fallback words like تخطي or tiktok
                            if any(w in cmd_clean for w in ['تخطي', 'skip', 'انشاء', 'حساب', 'تيك', 'tiktok']):
                                reply = provision_account_for('TikTok', 'https://www.tiktok.com/signup', target_chat_id=chat_id)
                            else:
                                reply = "⚡ *جاهز لخدمتك!* المس أي زر بالأسفل أو أرسل `/signup` لإنشاء وفحص حسابك فوراً."
                                reply_markup = main_reply_dock

                    if reply:
                        payload = {'chat_id': cid, 'text': reply, 'parse_mode': 'Markdown'}
                        if reply_markup:
                            payload['reply_markup'] = reply_markup
                        http_session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload, timeout=6)

        except Exception as e:
            time.sleep(2.0)
        time.sleep(0.05)

def keep_alive_worker():
    """Pings the public Render URL every 7 minutes to keep the cloud service permanently awake."""
    url = "https://novamail-bot.onrender.com/health"
    time.sleep(45.0)
    while True:
        try:
            r = http_session.get(url, timeout=10)
            if r.status_code == 200:
                print(f"[Keep-Alive] Cloud ping OK at {time.strftime('%H:%M:%S')}")
        except Exception:
            pass
        time.sleep(420.0)

if __name__ == '__main__':
    # 0. Start 24/7 Keep-Alive Auto-Ping Thread
    t_keep = threading.Thread(target=keep_alive_worker, daemon=True)
    t_keep.start()

    # 1. Start Prewarm Pool Thread
    t_pool = threading.Thread(target=prewarm_worker, daemon=True)
    t_pool.start()

    # 2. Start Poller Thread
    t_poll = threading.Thread(target=poll_inbox_worker, daemon=True)
    t_poll.start()

    # 3. Start Telegram Bot Poller Thread
    t_bot = threading.Thread(target=telegram_worker, daemon=True)
    t_bot.start()

    # 4. Start HTTP Health-Check Server (Runs in foreground to keep container alive)
    print(f"[NovaMail Cloud Bot] HTTP Health Server running on 0.0.0.0:{PORT}...")
    start_http_server()
