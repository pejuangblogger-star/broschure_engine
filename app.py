import streamlit as st
from fpdf import FPDF
import os, uuid, json, hashlib, requests
from bs4 import BeautifulSoup
import fitz
import datetime

st.set_page_config(page_title="Brochure SaaS AI PRO", layout="wide")

# ======================
# FILE SETUP
# ======================
USER_DB = "users.json"
HISTORY_DB = "history.json"
CATALOG_DIR = "katalog_tersimpan"
os.makedirs(CATALOG_DIR, exist_ok=True)

# ======================
# UTIL
# ======================
def safe_remove(p):
    try:
        if p and os.path.exists(p):
            os.remove(p)
    except:
        pass

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_json(p):
    if not os.path.exists(p):
        return {}
    with open(p,"r") as f:
        return json.load(f)

def save_json(p,d):
    with open(p,"w") as f:
        json.dump(d,f)

# ======================
# AUTH
# ======================
users = load_json(USER_DB)

if "user" not in st.session_state:
    menu = st.radio("Menu",["Login","Register"])
    u = st.text_input("Username")
    p = st.text_input("Password",type="password")

    if menu=="Register" and st.button("Daftar"):
        users[u]=hash_pw(p)
        save_json(USER_DB,users)
        st.success("Akun dibuat")

    if menu=="Login" and st.button("Login"):
        if u in users and users[u]==hash_pw(p):
            st.session_state["user"]=u
            st.session_state["usage"]=0
            st.session_state["day"]=str(datetime.date.today())
            st.rerun()
        else:
            st.error("Login gagal")

    st.stop()

user = st.session_state["user"]

# ======================
# RESET LIMIT
# ======================
today = str(datetime.date.today())
if st.session_state.get("day") != today:
    st.session_state["usage"] = 0
    st.session_state["day"] = today

st.success(f"Login: {user} | Usage: {st.session_state['usage']}/10")

if st.button("Logout"):
    del st.session_state["user"]
    st.rerun()

# ======================
# API
# ======================
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("API KEY belum diset")
    st.stop()

API_KEY = st.secrets["GOOGLE_API_KEY"]

# ======================
# AUTO SWITCH AI
# ======================
def ai_generate_auto(prompt):
    models = [
        "gemini-2.5-flash",
        "gemini-3-flash",
        "gemini-flash-latest"
    ]

    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={API_KEY}"
            payload = {"contents":[{"parts":[{"text":prompt}]}]}
            r = requests.post(url, json=payload, timeout=15)

            if r.status_code == 200:
                return r.json()['candidates'][0]['content']['parts'][0]['text'], model
        except:
            continue

    return None, None

# ======================
# CACHE
# ======================
@st.cache_data
def scrape(url):
    try:
        soup = BeautifulSoup(requests.get(url).text,'html.parser')
        return " ".join([t.get_text() for t in soup.find_all(['p','li','h1','h2'])])[:4000]
    except:
        return ""

@st.cache_data
def read_pdf(path):
    try:
        doc = fitz.open(path)
        return "".join([p.get_text() for p in doc[:10]])[:8000]
    except:
        return ""

# ======================
# PDF CLASS (UPDATED FOOTER)
# ======================
class Brosur(FPDF):
    def __init__(self, brand_color, brand_name, website_link):
        super().__init__()
        self.brand_color = brand_color
        self.brand_name = brand_name
        self.website_link = website_link

    def header(self):
        self.set_fill_color(*self.brand_color)
        self.rect(0, 0, 210, 4, 'F')

    def footer(self):
        self.set_y(-25)
        self.set_draw_color(*self.brand_color)
        self.line(10, 272, 200, 272)
        
        self.set_text_color(50, 50, 50)
        self.set_font('Helvetica', 'B', 9)
        self.cell(0, 6, f'{self.brand_name} - SMART EQUIPMENT FOR SMART BUILDERS', align='C', ln=True)
        
        self.set_font('Helvetica', 'I', 8)
        clean_link = self.website_link.replace("https://", "").replace("http://", "").rstrip("/")
        self.cell(0, 4, f'Authorized Representative: Adjie Agung | {clean_link}', align='C', ln=True)

# ======================
# UI
# ======================
st.title("🚀 Brochure SaaS AUTO AI PRO")

col1,col2 = st.columns([1,1.2])

with col1:
    brand = st.selectbox("Brand",["AIMIX","TATSUO"])
    foto = st.file_uploader("Foto Unit",type=['png','jpg'])

    model = st.text_input("Model","JP60-8")
    headline = st.text_input("Headline","KERJA CEPAT & HEMAT")

    s1 = st.text_input("Engine","Yanmar")
    s2 = st.text_input("Hydraulic","Rexroth")
    s3 = st.text_input("Bobot","5800kg")

with col2:
    link = st.text_input("Website")
    pdf_file = st.file_uploader("PDF",type=['pdf'])
    wa = st.text_input("WhatsApp","628123456789")

    if st.button("✨ Generate AI"):
        if st.session_state["usage"] >= 10:
            st.warning("Limit habis")
            st.stop()

        web = scrape(link) if link else ""
        pdf = ""

        if pdf_file:
            path = os.path.join(CATALOG_DIR,pdf_file.name)
            with open(path,"wb") as f:
                f.write(pdf_file.getbuffer())
            pdf = read_pdf(path)

        prompt = f"""
        Buat 4 keunggulan alat berat.
        Fokus tenaga, efisiensi, durability.

        Format:
        JUDUL | Deskripsi

        Data:
        {web} {pdf}
        """

        hasil, model_used = ai_generate_auto(prompt)

        if not hasil:
            hasil = """TENAGA KUAT | Mesin tangguh
EFISIENSI TINGGI | Hemat bahan bakar
STRUKTUR KOKOH | Tahan medan berat
SIAP KERJA | Ready stock"""
            model_used = "fallback"

        st.success(f"Model: {model_used}")

        st.session_state["copy"] = hasil
        st.session_state["usage"] += 1

    copy = st.text_area("Copywriting", st.session_state.get("copy",""), height=150)

# ======================
# GENERATE PDF
# ======================
from PIL import Image

if st.button("🌟 Generate Brosur Premium"):
    if not foto:
        st.warning("Upload foto dulu")
    else:
        color = (0,82,155) if brand=="AIMIX" else (204,0,0)

        pdf = Brosur(color, brand, link)
        pdf.add_page()

        # ======================
        # QR CODE
        # ======================
        if link:
            import qrcode
            qr = qrcode.make(link)
            qr_path = f"qr_{uuid.uuid4()}.png"
            qr.save(qr_path)
            pdf.image(qr_path, x=12, y=8, w=22)
            safe_remove(qr_path)

        # ======================
        # LOGO
        # ======================
        logo_path = None
        if logo:
            logo_path = f"logo_{uuid.uuid4()}.png"
            with open(logo_path,"wb") as f:
                f.write(logo.getbuffer())
            pdf.image(logo_path, x=160, y=8, w=35)

        # ======================
        # WATERMARK
        # ======================
        if logo_path:
            wm = Image.open(logo_path).convert("RGBA")
            alpha = wm.split()[3]
            alpha = alpha.point(lambda p: p * 0.08)
            wm.putalpha(alpha)

            wm_path = f"wm_{uuid.uuid4()}.png"
            wm.save(wm_path)

            pdf.image(wm_path, x=30, y=90, w=150)
            safe_remove(wm_path)

        # ======================
        # HERO IMAGE
        # ======================
        img_path=f"img_{uuid.uuid4()}.png"
        with open(img_path,"wb") as f:
            f.write(foto.getbuffer())

        pdf.image(img_path, x=35, y=20, w=140)
        safe_remove(img_path)

        # ======================
        # TITLE
        # ======================
        pdf.set_y(115)
        pdf.set_font("Helvetica","B",18)
        pdf.set_text_color(30,30,30)
        pdf.multi_cell(0,10,f"{brand} {model} - {headline}", align="C")

        # ======================
        # SPEC BAR
        # ======================
        pdf.ln(2)
        pdf.set_fill_color(245,245,245)
        pdf.rect(10, pdf.get_y(), 190, 12, 'F')

        pdf.set_y(pdf.get_y()+3)
        pdf.set_font("Helvetica","B",9)
        pdf.set_text_color(80,80,80)

        pdf.cell(63,6,f"ENGINE: {s1.upper()}", align='C')
        pdf.cell(63,6,f"HYDRAULIC: {s2.upper()}", align='C')
        pdf.cell(63,6,f"BOBOT: {s3.upper()}", align='C', ln=True)

        # ======================
        # BADGES
        # ======================
        pdf.ln(5)
        badges = [b for b in [b1,b2,b3] if b.strip()]

        if badges:
            pdf.set_fill_color(*color)
            pdf.set_text_color(255,255,255)
            pdf.set_font("Helvetica","B",10)

            for b in badges:
                pdf.cell(60,8,b.upper(),align='C',fill=True)
                pdf.cell(5,8,"")
            pdf.ln(10)

        # ======================
        # COPY AI
        # ======================
        pdf.set_text_color(50,50,50)

        for line in copy.split("\n"):
            if "|" in line:
                j,d=line.split("|",1)

                # bullet
                pdf.set_fill_color(*color)
                pdf.ellipse(10, pdf.get_y()+2, 3,3,'F')

                pdf.set_xy(16,pdf.get_y())
                pdf.set_font("Helvetica","B",12)
                pdf.set_text_color(*color)
                pdf.cell(0,6,j.strip(),ln=True)

                pdf.set_xy(16,pdf.get_y())
                pdf.set_font("Helvetica","",10)
                pdf.set_text_color(60,60,60)
                pdf.multi_cell(0,5,d.strip())
                pdf.ln(3)

        # ======================
        # CTA WHATSAPP
        # ======================
        pdf.set_y(max(pdf.get_y()+5, 245))

        pdf.set_font("Helvetica","B",12)
        pdf.set_text_color(30,30,30)
        pdf.cell(0,6,"HUBUNGI SALES:",ln=True)

        pdf.set_font("Helvetica","B",16)
        pdf.set_text_color(*color)
        pdf.cell(0,8,f"WhatsApp: {wa}",ln=True, link=f"https://wa.me/{wa}")

        # ======================
        # OUTPUT
        # ======================
        pdf_bytes = pdf.output(dest='S').encode('latin1')

        doc = fitz.open("pdf",pdf_bytes)
        img_bytes = doc[0].get_pixmap(dpi=300).tobytes("png")

        st.download_button("⬇️ PDF PREMIUM",pdf_bytes,"brosur_premium.pdf")
        st.download_button("🖼️ JPG PREMIUM",img_bytes,"brosur_premium.png")

# ======================
# HISTORY
# ======================
st.subheader("📂 Riwayat")

history = load_json(HISTORY_DB)

if user not in history:
    history[user] = []

for h in history[user][-5:]:
    st.write(h)
