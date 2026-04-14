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
@st.cache_data(show_spinner=False, ttl=3600) # Cache 1 jam
def extract_source_data(url, pdf_path):
    """Fungsi ini hanya akan jalan sekali untuk data yang sama. Sangat hemat resource."""
    scraped_text = ""
    # Ekstraksi Web
    if url:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            # Hapus script dan style agar bersih
            for script in soup(["script", "style"]):
                script.extract()
            scraped_text += "DATA WEBSITE:\n" + soup.get_text(separator=' ', strip=True)[:4000] + "\n\n"
        except Exception as e:
            st.warning(f"Gagal scrape web: {e}")

    # Ekstraksi PDF
    if pdf_path and os.path.exists(pdf_path):
        try:
            with open(pdf_path, "rb") as file_pdf:
                pdf_reader = pypdf.PdfReader(file_pdf)
                scraped_text += "DATA KATALOG PDF:\n"
                num_pages = min(8, len(pdf_reader.pages)) # Batasi 8 halaman awal untuk hemat token API
                for i in range(num_pages):
                    text = pdf_reader.pages[i].extract_text()
                    if text: scraped_text += text + "\n"
        except Exception as e:
            st.warning(f"Gagal ekstrak PDF: {e}")
            
    return scraped_text[:10000] # Hard limit token

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
        self.cell(0, 4, f'Authorized Representative | {clean_link}', align='C', ln=True)


# --- UI DASHBOARD ---
st.title("🚀 Ultimate Brochure Engine + Auto Layout")
st.markdown("*Powered by Gemini 1.5 Flash JSON Mode & FPDF2 Engine*")

col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.subheader("1. Visual & Identitas")
    brand = st.selectbox("Pilih Merek", ["AIMIX", "TATSUO"])
    
    default_link = "https://aimix-self-loading-mixer.netlify.app/" if brand == "AIMIX" else "https://tatsuosales-id.netlify.app/#/"
    default_model = "SELF LOADING MIXER" if brand == "AIMIX" else "WHEEL CRAWLER EXCAVATOR JP80-9"

    logo_file = st.file_uploader("Upload Logo Brand (PNG Transparan)", type=['png', 'jpg', 'jpeg'])
    foto = st.file_uploader("Upload Foto Unit Utama (Wajib)", type=['png', 'jpg', 'jpeg'])
    
    st.markdown("---")
    model = st.text_input("Tipe Unit", default_model)
    headline = st.text_input("Headline Utama", "TANGGUH DISEGALA MEDAN")
    
    c_sp1, c_sp2, c_sp3 = st.columns(3)
    spec_engine = c_sp1.text_input("Engine / Power", "Yanmar 4TNV98")
    spec_cap = c_sp2.text_input("Hydraulic Sys", "Rexroth")
    spec_weight = c_sp3.text_input("Bobot Unit", "9600kg")

    b_col1, b_col2, b_col3 = st.columns(3)
    badge1 = b_col1.text_input("Badge 1", "GARANSI 1 TAHUN")
    badge2 = b_col2.text_input("Badge 2", "FREE ONGKIR JABODETABEK")
    badge3 = b_col3.text_input("Badge 3", "READY STOCK")

with col2:
    st.subheader("2. AI Copywriter & Database")
    
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
        
    wa_num = st.text_input("Nomor WhatsApp", "6281230857759")
    
    # --- AI GENERATOR (JSON STRICT MODE) ---
    if st.button("✨ Tarik Data & Buat Copywriting (AI Engine)", type="primary"):
        if not ref_link and not pdf_path_to_read:
            st.error("Masukkan Link Website atau Katalog PDF.")
        else:
            with st.spinner("Mengakses Deep Data & Menjalankan LLM..."):
                try:
                    # Ambil data pake cache
                    raw_data = extract_source_data(ref_link, pdf_path_to_read)
                    
                    # Setup Gemini SDK
                    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                    llm = genai.GenerativeModel('gemini-1.5-flash', 
                                                generation_config={"response_mime_type": "application/json"})
                    
                    prompt = f"""
                    Anda adalah Copywriter Alat Berat profesional.
                    Analisis spesifikasi teknis berikut dan buat 4 poin keunggulan utama (selling points).
                    Fokus pada performa, efisiensi, kekuatan, atau garansi.
                    Bahasa: Indonesia, maskulin, teknis, persuasif.
                    
                    KEMBALIKAN OUTPUT STRICT DALAM FORMAT JSON SEPERTI INI:
                    [
                      {{"judul": "JUDUL FITUR SINGKAT", "deskripsi": "Penjelasan maksimal 2 kalimat yang menjual."}},
                      ... (total 4 objek)
                    ]
                    
                    Data Spesifikasi:
                    {raw_data}
                    """
                    
                    response = llm.generate_content(prompt)
                    ai_json_data = json.loads(response.text) # Aman karena mode MIME type
                    
                    # Konversi JSON ke format UI Text Area agar bisa diedit manual oleh user
                    text_output = ""
                    for item in ai_json_data:
                        text_output += f"{item.get('judul', 'Fitur')} | {item.get('deskripsi', 'Deskripsi')}\n"
                    
                    st.session_state['ai_result'] = text_output.strip()
                    st.success("✅ Struktur Copywriting berhasil di-generate!")
                    
                except Exception as e:
                    st.error(f"AI Engine Error: {e}")

    ai_raw_text = st.session_state.get('ai_result', "JUDUL 1 | Deskripsi 1...\nJUDUL 2 | Deskripsi 2...")
    final_copy = st.text_area("Hasil Copywriting (Bisa Diedit. Format: JUDUL | Deskripsi)", ai_raw_text, height=150)

st.markdown("---")

# --- CORE RENDER ENGINE ---
if st.button("🌟 RENDER ULTIMATE BROCHURE", use_container_width=True, type="primary"):
    if not foto:
        st.warning("⚠️ Unit utama wajib diupload untuk merender brosur.")
    else:
        with st.spinner("Merender PDF High-Res & Mencegah Tabrakan Layout..."):
            b_color = (0, 82, 155) if brand == "AIMIX" else (204, 0, 0)
            
            # GARBAGE COLLECTION SYSTEM (Memastikan tidak ada file nyangkut)
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
                        alpha = img.split()[3].point(lambda p: p * 0.08) # Transparansi 8%
                        img.putalpha(alpha)
                        
                        wm_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                        img.save(wm_temp, format="PNG")
                        wm_temp.close()
                        temp_files_to_clean.append(wm_temp.name)
                        
                        pdf.image(wm_temp.name, x=35, y=90, w=140)
                    except Exception as e:
                        pass # Lewati jika gagal render watermark

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
                
                # 4. TYPOGRAPHY & SPECS
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
                        pdf.cell(5, 8, "", align='C') # Spasi
                pdf.ln(12)
                
                # 6. COPYWRITING INJECTOR
                lines = final_copy.strip().split('\n')
                for line in lines:
                    if '|' in line:
                        judul, deskripsi = line.split('|', 1)
                        pdf.set_fill_color(*b_color)
                        pdf.ellipse(10, pdf.get_y() + 1.5, 3, 3, 'F') # Bullet point dinamis
                        
                        pdf.set_xy(16, pdf.get_y())
                        pdf.set_font('helvetica', 'B', 11)
                        pdf.set_text_color(*b_color)
                        pdf.cell(0, 6, judul.strip().upper(), ln=True)
                        
                        pdf.set_xy(16, pdf.get_y())
                        pdf.set_font('helvetica', '', 10)
                        pdf.set_text_color(50, 50, 50)
                        pdf.multi_cell(0, 5, deskripsi.strip())
                        pdf.ln(3)

                # 7. ANTI-COLLISION ENGINE (FOOTER WA)
                # Jika Y saat ini sudah melebihi 245, paksa pindah halaman atau margin aman
                safe_y = max(pdf.get_y() + 5, 245) 
                
                pdf.set_xy(10, safe_y)
                pdf.set_font('helvetica', 'B', 12)
                pdf.set_text_color(20, 20, 20)
                pdf.cell(50, 6, "HUBUNGI SALES KAMI:", ln=True)
                
                pdf.set_font('helvetica', 'B', 16)
                pdf.set_text_color(*b_color)
                wa_clean = ''.join(filter(str.isdigit, wa_num))
                pdf.cell(50, 8, f"WhatsApp: +{wa_clean}", link=f"https://wa.me/{wa_clean}", ln=True)

                # --- EXPORT DATA ---
                pdf_bytes = bytes(pdf.output(dest='S'))
                
                # Konversi PDF ke PNG via PyMuPDF (fitz)
                doc = fitz.open("pdf", pdf_bytes)
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=300)
                png_bytes = pix.tobytes("png")
                doc.close()

                st.success("🎉 Engine berhasil merender mahakarya secara sempurna!")
                
                # DOWNLOAD BUTTONS
                dl_col1, dl_col2 = st.columns(2)
                dl_col1.download_button("⬇️ Download High-Res PDF", data=pdf_bytes, file_name=f"Brosur_{brand}_{model}.pdf", mime="application/pdf", use_container_width=True)
                dl_col2.download_button("🖼️ Download Gambar (PNG)", data=png_bytes, file_name=f"Brosur_{brand}_{model}.png", mime="image/png", use_container_width=True)

            except Exception as e:
                st.error(f"Gagal saat proses render: {e}")
                
            finally:
                # GARBAGE COLLECTOR: Selalu hapus file temporary untuk menjaga server tetap sehat
                for f_path in temp_files_to_clean:
                    if os.path.exists(f_path):
                        try:
                            os.remove(f_path)
                        except:
                            pass
