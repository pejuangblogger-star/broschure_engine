import streamlit as st
from fpdf import FPDF
import os
import qrcode
import requests
import json
from bs4 import BeautifulSoup
import pypdf
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
import tempfile

# --- CONFIG & INIT ---
st.set_page_config(page_title="Ultimate Pro Brochure Engine", layout="wide", page_icon="🚀")

CATALOG_DIR = "katalog_tersimpan"
os.makedirs(CATALOG_DIR, exist_ok=True)

# --- CACHING ENGINE (HEMAT RESOURCE & API) ---
@st.cache_data(show_spinner=False, ttl=3600)
def extract_source_data(url, pdf_path):
    scraped_text = ""
    if url:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.extract()
            scraped_text += "DATA WEBSITE:\n" + soup.get_text(separator=' ', strip=True)[:4000] + "\n\n"
        except Exception as e:
            pass

    if pdf_path and os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as file_pdf:
                pdf_reader = pypdf.PdfReader(file_pdf)
                scraped_text += "DATA KATALOG PDF:\n"
                num_pages = min(8, len(pdf_reader.pages))
                for i in range(num_pages):
                    text = pdf_reader.pages[i].extract_text()
                    if text: scraped_text += text + "\n"
        except Exception as e:
            pass
            
    return scraped_text[:10000]

# --- KELAS PDF CUSTOM ---
class ProBrochure(FPDF):
    def __init__(self, brand_color, brand_name, website_link, logo_path, wa_number):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.brand_color = brand_color
        self.brand_name = brand_name
        self.website_link = website_link
        self.logo_path = logo_path
        self.wa_number = wa_number
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_fill_color(*self.brand_color)
        self.rect(0, 0, 210, 5, 'F')
        if self.logo_path and os.path.exists(self.logo_path):
            self.image(self.logo_path, x=160, y=10, w=40)
        else:
            self.ln(5)
            self.set_font('helvetica', 'B', 24)
            self.set_text_color(*self.brand_color)
            self.cell(0, 10, self.brand_name, align='R')

    def footer(self):
        self.set_y(-25)
        self.set_draw_color(*self.brand_color)
        self.set_line_width(0.5)
        self.line(10, 272, 200, 272)
        self.set_text_color(50, 50, 50)
        self.set_font('helvetica', 'B', 9)
        self.cell(0, 6, f'{self.brand_name.upper()} - SMART EQUIPMENT FOR SMART BUILDERS', align='C', ln=True)
        self.set_font('helvetica', 'I', 8)
        clean_link = self.website_link.replace("https://", "").replace("http://", "").rstrip("/")
        self.cell(0, 4, f'Authorized Representative by Adjie Agung | {clean_link}', align='C', ln=True)


# --- UI DASHBOARD & SESSION STATE INIT ---
st.title("🚀 Ultimate Brochure Engine + Auto Layout")
st.markdown("*Powered by Omni-Extraction JSON AI & FPDF2 Engine*")

col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.subheader("1. Visual & Identitas")
    brand = st.selectbox("Pilih Merek", ["AIMIX", "TATSUO"])
    
    default_link = "https://aimix-self-loading-mixer.netlify.app/" if brand == "AIMIX" else "https://tatsuosales-id.netlify.app/#/"
    default_model = "SELF LOADING MIXER" if brand == "AIMIX" else "WHEEL CRAWLER EXCAVATOR JP80-9"

    # INIT SESSION STATE (Nilai Bawaan)
    defaults = {
        'tipe_unit': default_model, 'headline': "TANGGUH DISEGALA MEDAN",
        'engine': "Yanmar 4TNV98", 'hydraulic': "Rexroth", 'bobot': "9600kg",
        'badge1': "GARANSI 1 TAHUN", 'badge2': "FREE ONGKIR", 'badge3': "READY STOCK",
        'ai_copywriting': "BELUM ADA DATA.\nKlik Tarik Data untuk meng-generate dari Katalog/Web."
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    logo_file = st.file_uploader("Upload Logo Brand (PNG Transparan)", type=['png', 'jpg', 'jpeg'])
    foto = st.file_uploader("Upload Foto Unit Utama (Wajib)", type=['png', 'jpg', 'jpeg'])
    
    st.markdown("---")
    
    # 🔴 AREA KOTAK MERAH: MANUAL STATE SYNC (Bypass Streamlit Error)
    # Kita menggunakan `value=` alih-alih `key=` agar AI bisa menimpa data kapan saja tanpa crash.
    
    model = st.text_input("Tipe Unit", value=st.session_state['tipe_unit'])
    st.session_state['tipe_unit'] = model
    
    headline = st.text_input("Headline Utama", value=st.session_state['headline'])
    st.session_state['headline'] = headline
    
    c_sp1, c_sp2, c_sp3 = st.columns(3)
    spec_engine = c_sp1.text_input("Engine / Power", value=st.session_state['engine'])
    st.session_state['engine'] = spec_engine
    
    spec_cap = c_sp2.text_input("Hydraulic Sys", value=st.session_state['hydraulic'])
    st.session_state['hydraulic'] = spec_cap
    
    spec_weight = c_sp3.text_input("Bobot Unit", value=st.session_state['bobot'])
    st.session_state['bobot'] = spec_weight

    b_col1, b_col2, b_col3 = st.columns(3)
    badge1 = b_col1.text_input("Badge 1", value=st.session_state['badge1'])
    st.session_state['badge1'] = badge1
    
    badge2 = b_col2.text_input("Badge 2", value=st.session_state['badge2'])
    st.session_state['badge2'] = badge2
    
    badge3 = b_col3.text_input("Badge 3", value=st.session_state['badge3'])
    st.session_state['badge3'] = badge3

with col2:
    st.subheader("2. AI Omni-Extractor & Database")
    
    ref_link = st.text_input("Link Website Produk", default_link)
    saved_files = [f for f in os.listdir(CATALOG_DIR) if f.endswith('.pdf')]
    pilihan_katalog = st.selectbox("Database Katalog (PDF)", ["-- Upload Baru --"] + saved_files)
    
    pdf_path_to_read = None
    if pilihan_katalog == "-- Upload Baru --":
        pdf_ref = st.file_uploader("Upload Spesifikasi (PDF)", type=['pdf'])
        if pdf_ref:
            pdf_path_to_read = os.path.join(CATALOG_DIR, pdf_ref.name)
            with open(pdf_path_to_read, "wb") as f:
                f.write(pdf_ref.getbuffer())
            st.success("✅ Katalog tersimpan!")
    else:
        pdf_path_to_read = os.path.join(CATALOG_DIR, pilihan_katalog)
        
    wa_num = st.text_input("Nomor WhatsApp", "+6281230857759")
    
    # --- STRATEGI AUTO-SWITCH & OMNI-EXTRACTION ---
    if st.button("✨ Tarik Data & Auto-Fill Brosur (AI Engine)", type="primary"):
        if not ref_link and not pdf_path_to_read:
            st.error("Masukkan Link Website atau Katalog PDF terlebih dahulu.")
        else:
            with st.spinner("Menganalisis Spesifikasi & Menjalankan Auto-Switch Protocol..."):
                raw_data = extract_source_data(ref_link, pdf_path_to_read)
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                
                prompt = f"""
                Anda adalah Insinyur Alat Berat & Copywriter Ahli. Ekstrak data berikut dari spesifikasi.
                Jika data spesifik tidak ada, buat tebakan pintar berdasarkan konteks industri (misal bobot dikira-kira, atau tulis "-").
                
                KEMBALIKAN OUTPUT STRICT DALAM FORMAT JSON BERIKUT:
                {{
                  "tipe_unit": "Nama model/unit utama (misal: JP60-8 Excavator)",
                  "headline": "1 Kalimat marketing bombastis (maks 5 kata)",
                  "engine": "Nama Mesin / Power (misal: Cummins)",
                  "hydraulic": "Tipe Hidrolik",
                  "bobot": "Berat operasional (misal: 6 Ton)",
                  "badge1": "Keunggulan 1 singkat (misal: GARANSI MESIN)",
                  "badge2": "Keunggulan 2 singkat (misal: MUDAH PERAWATAN)",
                  "badge3": "Keunggulan 3 singkat (misal: IRIT BBM)",
                  "copywriting": [
                    {{"judul": "FITUR 1", "deskripsi": "Penjelasan fitur maksimal 3 kalimat."}},
                    {{"judul": "FITUR 2", "deskripsi": "Penjelasan fitur maksimal 3 kalimat."}},
                    {{"judul": "FITUR 3", "deskripsi": "Penjelasan fitur maksimal 3 kalimat."}},
                    {{"judul": "FITUR 4", "deskripsi": "Penjelasan fitur maksimal 3 kalimat."}}
                  ]
                }}
                
                Data Spesifikasi Mentah:
                {raw_data}
                """
                
                # PROTOKOL FAILOVER (Auto-Switch)
                models_to_try = ['gemini-2.5-flash', 'gemini-3-flash', 'gemini-flash-latest']
                ai_json_data = None
                
                for m in models_to_try:
                    try:
                        llm = genai.GenerativeModel(m, generation_config={"response_mime_type": "application/json"})
                        response = llm.generate_content(prompt)
                        ai_json_data = json.loads(response.text)
                        break # Berhasil! Keluar dari loop pencarian
                    except Exception as e:
                        continue # Gagal? Lanjut ke model berikutnya dalam diam
                
                if not ai_json_data:
                    st.error("⚠️ Semua lapis model AI (2.5 -> 3 -> latest) gagal merespons. Periksa API Key / Koneksi Anda.")
                else:
                    # Menimpa Session State dengan Data AI yang baru
                    st.session_state['tipe_unit'] = ai_json_data.get('tipe_unit', st.session_state['tipe_unit']).upper()
                    st.session_state['headline'] = ai_json_data.get('headline', st.session_state['headline']).upper()
                    st.session_state['engine'] = ai_json_data.get('engine', st.session_state['engine'])
                    st.session_state['hydraulic'] = ai_json_data.get('hydraulic', st.session_state['hydraulic'])
                    st.session_state['bobot'] = ai_json_data.get('bobot', st.session_state['bobot'])
                    st.session_state['badge1'] = ai_json_data.get('badge1', st.session_state['badge1']).upper()
                    st.session_state['badge2'] = ai_json_data.get('badge2', st.session_state['badge2']).upper()
                    st.session_state['badge3'] = ai_json_data.get('badge3', st.session_state['badge3']).upper()
                    
                    text_output = ""
                    for item in ai_json_data.get('copywriting', []):
                        text_output += f"{item.get('judul', 'Fitur')} | {item.get('deskripsi', 'Deskripsi')}\n"
                    st.session_state['ai_copywriting'] = text_output.strip()
                    
                    # Memaksa UI untuk memuat ulang layar agar Kotak Merah terisi angka baru
                    st.rerun()

    final_copy = st.text_area("Hasil Copywriting (Format: JUDUL | Deskripsi)", st.session_state['ai_copywriting'], height=150)

st.markdown("---")

# --- CORE RENDER ENGINE ---
if st.button("🌟 RENDER ULTIMATE BROCHURE", use_container_width=True, type="primary"):
    if not foto:
        st.warning("⚠️ Unit utama wajib diupload untuk merender brosur.")
    else:
        with st.spinner("Merender PDF High-Res & Mencegah Tabrakan Layout..."):
            b_color = (0, 82, 155) if brand == "AIMIX" else (204, 0, 0)
            temp_files_to_clean = []
            
            try:
                logo_path = None
                if logo_file:
                    logo_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    logo_temp.write(logo_file.getbuffer())
                    logo_path = logo_temp.name
                    logo_temp.close()
                    temp_files_to_clean.append(logo_path)

                pdf = ProBrochure(brand_color=b_color, brand_name=brand, website_link=ref_link, logo_path=logo_path, wa_number=wa_num)
                pdf.add_page()
                
                # 1. WATERMARK
                if logo_path:
                    try:
                        img = Image.open(logo_path).convert("RGBA")
                        alpha = img.split()[3].point(lambda p: p * 0.08)
                        img.putalpha(alpha)
                        wm_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                        img.save(wm_temp, format="PNG")
                        wm_temp.close()
                        temp_files_to_clean.append(wm_temp.name)
                        pdf.image(wm_temp.name, x=35, y=90, w=140)
                    except: pass

                # 2. QR CODE DI KIRI ATAS
                if ref_link:
                    qr = qrcode.make(ref_link)
                    qr_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                    qr.save(qr_temp, format="PNG")
                    qr_temp.close()
                    temp_files_to_clean.append(qr_temp.name)
                    
                    pdf.image(qr_temp.name, x=15, y=10, w=22, h=22)
                    pdf.set_xy(11, 33)
                    pdf.set_font('helvetica', 'B', 6)
                    pdf.set_text_color(*b_color)
                    pdf.cell(30, 3, "SCAN FOR DETAILS", align='C')

                # 3. FOTO UTAMA
                hero_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                hero_temp.write(foto.getbuffer())
                hero_temp.close()
                temp_files_to_clean.append(hero_temp.name)
                pdf.image(hero_temp.name, x=42, y=20, w=125)
                
                # 4. TYPOGRAPHY & SPECS (Tarik langsung dari UI yang terlihat)
                pdf.set_y(125)
                pdf.set_font('helvetica', 'B', 18) 
                pdf.set_text_color(20, 20, 20)
                pdf.multi_cell(0, 8, f"{brand} {model}\n{headline}", align='C')
                
                pdf.ln(4)
                pdf.set_fill_color(245, 245, 245)
                pdf.rect(10, pdf.get_y(), 190, 12, 'F')
                
                pdf.set_y(pdf.get_y() + 3)
                pdf.set_font('helvetica', 'B', 9)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(63, 6, f"ENGINE: {spec_engine.upper()}", align='C')
                pdf.cell(63, 6, f"HYDRAULIC: {spec_cap.upper()}", align='C')
                pdf.cell(63, 6, f"BOBOT: {spec_weight.upper()}", align='C', ln=True)
                
                # 5. TRUST BADGES
                pdf.ln(5)
                pdf.set_font('helvetica', 'B', 9)
                pdf.set_text_color(255, 255, 255)
                pdf.set_fill_color(*b_color)
                for badge in [badge1, badge2, badge3]:
                    if badge.strip():
                        pdf.cell(60, 8, badge.upper(), align='C', fill=True)
                        pdf.cell(5, 8, "", align='C')
                pdf.ln(12)
                
                # 6. COPYWRITING INJECTOR
                lines = final_copy.strip().split('\n')
                for line in lines:
                    if '|' in line:
                        judul, deskripsi = line.split('|', 1)
                        pdf.set_fill_color(*b_color)
                        pdf.ellipse(10, pdf.get_y() + 1.5, 3, 3, 'F')
                        
                        pdf.set_xy(16, pdf.get_y())
                        pdf.set_font('helvetica', 'B', 11)
                        pdf.set_text_color(*b_color)
                        pdf.cell(0, 6, judul.strip().upper(), ln=True)
                        
                        pdf.set_xy(16, pdf.get_y())
                        pdf.set_font('helvetica', '', 10)
                        pdf.set_text_color(50, 50, 50)
                        pdf.multi_cell(0, 5, deskripsi.strip())
                        pdf.ln(3)

                # 7. FOOTER WA
                safe_y = max(pdf.get_y() + 5, 245) 
                pdf.set_xy(10, safe_y)
                pdf.set_font('helvetica', 'B', 12)
                pdf.set_text_color(20, 20, 20)
                pdf.cell(50, 6, "HUBUNGI SALES KAMI:", ln=True)
                pdf.set_font('helvetica', 'B', 16)
                pdf.set_text_color(*b_color)
                wa_clean = ''.join(filter(str.isdigit, wa_num))
                pdf.cell(50, 8, f"WhatsApp: +{wa_clean}", link=f"https://wa.me/{wa_clean}", ln=True)

                # --- EXPORT ---
                pdf_bytes = bytes(pdf.output(dest='S'))
                
                doc = fitz.open("pdf", pdf_bytes)
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=300)
                png_bytes = pix.tobytes("png")
                doc.close()

                st.success("🎉 Brosur Berhasil Dirender! Model, Spesifikasi & AI Teks telah menyatu.")
                
                dl_col1, dl_col2 = st.columns(2)
                dl_col1.download_button("⬇️ Download High-Res PDF", data=pdf_bytes, file_name=f"Brosur_{brand}_{model}.pdf", mime="application/pdf", use_container_width=True)
                dl_col2.download_button("🖼️ Download Gambar (PNG)", data=png_bytes, file_name=f"Brosur_{brand}_{model}.png", mime="image/png", use_container_width=True)

            except Exception as e:
                st.error(f"Gagal saat proses render: {e}")
            finally:
                for f_path in temp_files_to_clean:
                    if os.path.exists(f_path):
                        try: os.remove(f_path)
                        except: pass
