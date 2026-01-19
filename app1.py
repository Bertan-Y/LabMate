import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import datetime
import json
import os
import shutil
import threading
import sys

# --- SİSTEM SABİTLERİ VE YOL AYARLARI ---
APP_NAME = "LabMate"
APP_VERSION = "V0.1"
DEV_NAME = "Bertan Yurteri"
DEV_MAIL = "bertanyurteri1069@gmail.com"

# PyInstaller ile derlendiğinde dosya yollarını doğru bulmak için:
if getattr(sys, 'frozen', False):
    APP_PATH = os.path.dirname(sys.executable)
else:
    APP_PATH = os.path.dirname(os.path.abspath(__file__))

VERI_DOSYASI = os.path.join(APP_PATH, "lab_verileri.json")
AYAR_DOSYASI = os.path.join(APP_PATH, "ayarlar.json")
TOKEN_FILE = os.path.join(APP_PATH, "token.json")
CREDENTIALS_FILE = os.path.join(APP_PATH, "credentials.json")

# --- GOOGLE DRIVE KÜTÜPHANE KONTROLÜ ---
DRIVE_MEVCUT = False
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    DRIVE_MEVCUT = True
except ImportError:
    pass

# --- VERİ YÖNETİMİ ---
def ayarlari_yukle():
    varsayilan = {
        "yedek_klasoru": "", 
        "otomatik_yedekle": True, 
        "siklik": "Anlık",
        "drive_api_aktif": False
    }
    if not os.path.exists(AYAR_DOSYASI): return varsayilan
    try:
        with open(AYAR_DOSYASI, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in varsayilan.items():
                if k not in data: data[k] = v
            return data
    except: return varsayilan

def ayarlari_kaydet_dosyaya(ayarlar):
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(ayarlar, f, ensure_ascii=False, indent=4)

def verileri_yukle():
    if not os.path.exists(VERI_DOSYASI): return []
    try:
        with open(VERI_DOSYASI, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Veri yapısını onar (Migration)
            for p in data:
                if "lab_defteri" not in p: p["lab_defteri"] = []
                if "prosedur_listesi" not in p: p["prosedur_listesi"] = []
                if "dosyalar" not in p: p["dosyalar"] = []
            return data
    except: return []

def verileri_kaydet(veriler):
    with open(VERI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(veriler, f, ensure_ascii=False, indent=4)

# --- GOOGLE DRIVE & YEDEKLEME MOTORU ---
def google_giris_yap(log_cb, zorla_giris=False):
    """Google hesabına giriş yapar ve token.json oluşturur"""
    if not DRIVE_MEVCUT:
        msg = "Google Drive kütüphaneleri bulunamadı.\nLütfen terminalde şu komutu çalıştırın:\npip install google-api-python-client google-auth-oauthlib"
        log_cb("HATA: " + msg)
        messagebox.showerror("Kütüphane Hatası", msg)
        return False
    
    # Kullanıcı butona bastıysa eski token'ı silip temiz giriş yapalım
    if zorla_giris and os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
        except:
            pass

    creds = None
    if os.path.exists(TOKEN_FILE):
        try: creds = Credentials.from_authorized_user_file(TOKEN_FILE, ['https://www.googleapis.com/auth/drive.file'])
        except: os.remove(TOKEN_FILE)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try: creds.refresh(Request())
            except: creds = None
        
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                msg = f"'{CREDENTIALS_FILE}' dosyası bulunamadı!\nBu dosyayı programın yanına (veya dist/LabMate klasörüne) koymalısınız."
                log_cb("HATA: " + msg)
                messagebox.showerror("Dosya Eksik", msg)
                return False
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, ['https://www.googleapis.com/auth/drive.file'])
                # Tarayıcıyı açmaya çalışır
                creds = flow.run_local_server(port=0)
                with open(TOKEN_FILE, 'w') as token: token.write(creds.to_json())
            except Exception as e:
                msg = f"Giriş sırasında hata oluştu:\n{str(e)}\n\nLütfen varsayılan tarayıcınızı kontrol edin."
                log_cb(f"Giriş Hatası: {e}")
                messagebox.showerror("Giriş Hatası", msg)
                return False
    return True

def drive_upload(dosya_yolu, log_cb):
    """Dosyayı Google Drive'a yükler"""
    if not DRIVE_MEVCUT: return
    
    if not os.path.exists(TOKEN_FILE):
        log_cb("UYARI: Drive token yok, ayarlardan giriş yapın.")
        return

    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, ['https://www.googleapis.com/auth/drive.file'])
        service = build('drive', 'v3', credentials=creds)
        
        tarih = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        meta = {'name': f"LabMate_Yedek_{tarih}.json"}
        media = MediaFileUpload(dosya_yolu, mimetype='application/json')
        
        log_cb("Google Drive'a yükleniyor...")
        dosya = service.files().create(body=meta, media_body=media, fields='id').execute()
        log_cb(f"BAŞARILI: Drive'a yüklendi. ID: {dosya.get('id')}")
    except Exception as e:
        log_cb(f"Drive Upload Hatası: {e}")

def yedekleme_baslat(ayarlar, log_cb):
    """Otomatik yedekleme sürecini yönetir"""
    if not ayarlar.get("otomatik_yedekle"): return

    # 1. Google Drive API Yedekleme
    if ayarlar.get("drive_api_aktif"):
        drive_upload(VERI_DOSYASI, log_cb)

    # 2. Yerel Klasör Yedekleme
    if ayarlar.get("yedek_klasoru"):
        hedef = ayarlar["yedek_klasoru"]
        if os.path.exists(hedef):
            try:
                tarih = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                shutil.copy2(VERI_DOSYASI, os.path.join(hedef, f"LabMate_Yedek_{tarih}.json"))
                # Temizlik (Son 5 dosya kalsın)
                dosyalar = sorted([os.path.join(hedef, f) for f in os.listdir(hedef) if f.startswith("LabMate_Yedek_")], key=os.path.getmtime)
                while len(dosyalar) > 5: os.remove(dosyalar.pop(0))
                log_cb(f"Klasöre Yedeklendi: {hedef}")
            except Exception as e:
                log_cb(f"Klasör Hatası: {e}")

# --- ANA UYGULAMA ---
class LabMateApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1100x750")
        
        self.projeler = verileri_yukle()
        self.ayarlar = ayarlari_yukle()
        self.log_gecmisi = []

        # Ekran Yönetimi için Ana Konteyner
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        # Global Tıklama (Açık menüleri kapatmak için)
        self.root.bind("<Button-1>", self.global_sol_tik)

        # İlk Açılış
        self.ekran_ana_sayfa()

    def log_ekle(self, mesaj):
        zaman = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_gecmisi.append(f"[{zaman}] {mesaj}")

    def veri_degisti(self):
        verileri_kaydet(self.projeler)
        if self.ayarlar.get("siklik") == "Anlık":
            threading.Thread(target=yedekleme_baslat, args=(self.ayarlar, self.log_ekle), daemon=True).start()

    def global_sol_tik(self, event):
        # Sağ tık menülerini kapat
        try:
            if hasattr(self, 'menu_proje'): self.menu_proje.unpost()
            # Alt framelerdeki menüler için referans kontrolü zor olabilir, 
            # widget focus değişimi genelde yeterlidir.
        except: pass

    # --- SAYFA 1: ANA SAYFA (PROJE LİSTESİ) ---
    def ekran_ana_sayfa(self):
        for widget in self.container.winfo_children(): widget.destroy()

        # Toolbar
        toolbar = tk.Frame(self.container, bd=1, relief=tk.RAISED, bg="#f0f0f0", height=50)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(toolbar, text="+ Yeni Proje", bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"), 
                  command=self.yeni_proje).pack(side="left", padx=10, pady=10)
        
        tk.Button(toolbar, text="Yardım ❓", command=self.popup_yardim).pack(side="right", padx=5)
        tk.Button(toolbar, text="Ayarlar ⚙️", command=self.popup_ayarlar).pack(side="right", padx=5)

        # Liste
        columns = ("ad", "baslangic", "kisi")
        self.tree = ttk.Treeview(self.container, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("ad", text="Proje Adı"); self.tree.column("ad", width=300)
        self.tree.heading("baslangic", text="Başlangıç Tarihi"); self.tree.column("baslangic", width=150)
        self.tree.heading("kisi", text="Araştırmacılar"); self.tree.column("kisi", width=400)
        
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)
        
        sb = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb.set); sb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self.projeye_gir)
        
        self.menu_proje = tk.Menu(self.root, tearoff=0)
        self.menu_proje.add_command(label="Projeyi Sil 🗑️", command=self.proje_sil)
        self.tree.bind("<Button-3>", self.sag_tik_proje)

        self.listeyi_doldur()

    def listeyi_doldur(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for p in self.projeler:
            self.tree.insert("", "end", values=(p["ad"], p["baslangic"], p["arastirmacilar"]))

    def yeni_proje(self):
        ad = simpledialog.askstring("Yeni Proje", "Proje Adı:")
        if ad:
            self.projeler.append({
                "id": len(self.projeler)+1, "ad": ad, "arastirmacilar": "Ben", 
                "baslangic": datetime.datetime.now().strftime("%Y-%m-%d"), 
                "lab_defteri": [], "prosedur_listesi": [], "dosyalar": []
            })
            self.veri_degisti(); self.listeyi_doldur()

    def sag_tik_proje(self, event):
        item = self.tree.identify_row(event.y)
        if item: self.tree.selection_set(item); self.menu_proje.post(event.x_root, event.y_root)

    def proje_sil(self):
        sel = self.tree.selection()
        if not sel: return
        ad = self.tree.item(sel)['values'][0]
        if messagebox.askyesno("Onay", f"'{ad}' projesi ve tüm verileri KALICI OLARAK silinecek.\nOnaylıyor musunuz?"):
            self.projeler = [p for p in self.projeler if p['ad'] != ad]
            self.veri_degisti(); self.listeyi_doldur()

    def projeye_gir(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        ad = self.tree.item(sel)['values'][0]
        proje = next((p for p in self.projeler if p['ad'] == ad), None)
        if proje: self.ekran_proje_detay(proje)

    # --- SAYFA 2: PROJE DETAYLARI ---
    def ekran_proje_detay(self, proje):
        for widget in self.container.winfo_children(): widget.destroy()

        nav_bar = tk.Frame(self.container, bg="#ddd", height=40)
        nav_bar.pack(fill="x", side="top")

        btn_geri = tk.Button(nav_bar, text="← Geri Dön", font=("Arial", 10, "bold"), 
                             bg="#555", fg="white", command=self.ekran_ana_sayfa)
        btn_geri.pack(side="left", padx=10, pady=5)
        lbl_baslik = tk.Label(nav_bar, text=f"Proje: {proje['ad']}", font=("Arial", 12, "bold"), bg="#ddd")
        lbl_baslik.pack(side="left", padx=20)

        detay_frame = ProjeDetayFrame(self.container, proje, self.veri_degisti, self.root)
        detay_frame.pack(fill="both", expand=True)

    # --- POPUP PENCERELER ---
    def popup_yardim(self):
        win = tk.Toplevel(self.root)
        win.title("LabMate Yardım")
        win.geometry("600x500")
        st = scrolledtext.ScrolledText(win, width=70, height=25, font=("Consolas", 10))
        st.pack(padx=10, pady=10, fill="both", expand=True)
        text = """
LABMATE KULLANIM KILAVUZU
=========================
1. PROJE YÖNETİMİ
-----------------
- "+ Yeni Proje" ile proje oluşturun.
- Çift tıklayarak detaya girin.
- Sağ tıklayarak projeyi silebilirsiniz.

2. LAB DEFTERİ & PROSEDÜRLER
----------------------------
- Not eklerken "Kimler" listesinden seçim yapabilirsiniz.
- Prosedürlere malzeme ve talimat ekleyebilirsiniz.
- Sağ tık menüsü ile hatalı kayıtları silebilirsiniz.

3. YEDEKLEME
------------
- Ayarlardan bir Klasör seçerek yerel yedekleme yapın (USB, OneDrive).
- "Google Drive API" kullanmak için "credentials.json" dosyasını indirip
  programın yanına koyun ve Ayarlardan giriş yapın.
"""
        st.insert("end", text); st.config(state="disabled")

    def popup_ayarlar(self):
        win = tk.Toplevel(self.root)
        win.title("Ayarlar")
        win.geometry("500x550")

        # Üst Kısım: Yedekleme Ayarları
        lf_yedek = ttk.LabelFrame(win, text="Yedekleme Ayarları")
        lf_yedek.pack(fill="x", padx=10, pady=10)

        # 1. Klasör Seçimi
        ttk.Label(lf_yedek, text="Yerel Yedek Klasörü:", font=("Arial", 9, "bold")).pack(anchor="w", padx=10)
        f_klasor = ttk.Frame(lf_yedek)
        f_klasor.pack(fill="x", padx=10, pady=2)
        lbl_klasor = ttk.Label(f_klasor, text=self.ayarlar.get("yedek_klasoru", "Seçilmedi"), relief="sunken")
        lbl_klasor.pack(side="left", fill="x", expand=True)
        def sec():
            d = filedialog.askdirectory()
            if d: lbl_klasor.config(text=d)
        ttk.Button(f_klasor, text="Seç", command=sec).pack(side="right", padx=5)

        # 2. Drive API
        ttk.Separator(lf_yedek, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(lf_yedek, text="Google Drive API:", font=("Arial", 9, "bold")).pack(anchor="w", padx=10)
        
        var_drive = tk.BooleanVar(value=self.ayarlar.get("drive_api_aktif", False))
        chk_drive = ttk.Checkbutton(lf_yedek, text="Drive API Aktif Et", variable=var_drive)
        chk_drive.pack(anchor="w", padx=10)

        def giris_yap():
            # Butona basınca zorla_giris=True göndererek eski token'ı sildiriyoruz
            if google_giris_yap(self.log_ekle, zorla_giris=True):
                messagebox.showinfo("Başarılı", "Google hesabına bağlanıldı.")
                var_drive.set(True)
            else:
                var_drive.set(False)
        
        ttk.Button(lf_yedek, text="Google ile Giriş Yap (Bağlan)", command=giris_yap).pack(anchor="w", padx=10, pady=5)
        
        # 3. Sıklık
        ttk.Separator(lf_yedek, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(lf_yedek, text="Yedekleme Sıklığı:").pack(anchor="w", padx=10)
        cmb = ttk.Combobox(lf_yedek, values=["Anlık", "Kapatırken"], state="readonly")
        cmb.set(self.ayarlar.get("siklik", "Anlık"))
        cmb.pack(fill="x", padx=10, pady=5)

        def kaydet():
            self.ayarlar["yedek_klasoru"] = lbl_klasor.cget("text") if lbl_klasor.cget("text") != "Seçilmedi" else ""
            self.ayarlar["siklik"] = cmb.get()
            self.ayarlar["drive_api_aktif"] = var_drive.get()
            ayarlari_kaydet_dosyaya(self.ayarlar)
            messagebox.showinfo("Tamam", "Ayarlar kaydedildi.")
            win.destroy()
        
        ttk.Button(win, text="AYARLARI KAYDET", command=kaydet).pack(pady=10)

        # Alt Kısım: Geliştirici Bilgileri (En altta)
        # Spacer
        ttk.Frame(win).pack(fill="both", expand=True)
        
        ttk.Separator(win, orient="horizontal").pack(fill="x")
        
        f_footer = tk.Frame(win, bg="#f0f0f0")
        f_footer.pack(fill="x", side="bottom")
        
        lbl_dev = tk.Label(f_footer, text=f"Geliştirici: {DEV_NAME}", bg="#f0f0f0", font=("Arial", 9))
        lbl_dev.pack(pady=(10,2))
        
        lbl_mail = tk.Label(f_footer, text=f"İletişim: {DEV_MAIL}", bg="#f0f0f0", fg="blue", cursor="hand2")
        lbl_mail.pack(pady=2)
        
        lbl_ver = tk.Label(f_footer, text=f"Versiyon: {APP_VERSION}", bg="#f0f0f0", font=("Arial", 8, "bold"), fg="#555")
        lbl_ver.pack(pady=(2, 10))


# --- PROJE DETAY PANELİ (FRAME) ---
class ProjeDetayFrame(ttk.Frame):
    def __init__(self, parent, proje, kaydet_cb, root_ref):
        super().__init__(parent)
        self.proje = proje; self.kaydet_cb = kaydet_cb; self.root_ref = root_ref

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_genel = ttk.Frame(self.nb); self.nb.add(self.tab_genel, text="Genel Bilgiler")
        self.tab_defter = ttk.Frame(self.nb); self.nb.add(self.tab_defter, text="Lab Defteri")
        self.tab_pros = ttk.Frame(self.nb); self.nb.add(self.tab_pros, text="Prosedürler")
        self.tab_dosya = ttk.Frame(self.nb); self.nb.add(self.tab_dosya, text="Dosyalar")

        self.setup_genel(); self.setup_defter(); self.setup_prosedur(); self.setup_dosyalar()

    def setup_genel(self):
        f = ttk.Frame(self.tab_genel); f.pack(fill="x", padx=30, pady=30)
        ttk.Label(f, text=f"Proje Adı: {self.proje['ad']}", font=("Arial", 16, "bold")).pack(pady=10)
        f_kisi = ttk.Frame(f); f_kisi.pack(fill="x", pady=5)
        ttk.Label(f_kisi, text="Araştırmacılar:", font="bold").pack(side="left")
        self.lbl_kisi = ttk.Label(f_kisi, text=self.proje['arastirmacilar'])
        self.lbl_kisi.pack(side="left", padx=10)
        tk.Button(f_kisi, text="+", command=self.kisi_ekle).pack(side="left")

    def kisi_ekle(self):
        yeni = simpledialog.askstring("Ekle", "Yeni araştırmacı adı:")
        if yeni:
            mevcut = self.proje['arastirmacilar']
            if yeni not in mevcut:
                self.proje['arastirmacilar'] = mevcut + ", " + yeni
                self.lbl_kisi.config(text=self.proje['arastirmacilar']); self.kaydet_cb()

    def setup_defter(self):
        top = ttk.Frame(self.tab_defter); top.pack(fill="x", padx=10, pady=10)
        self.ent_ara_def = ttk.Entry(top); self.ent_ara_def.pack(side="left", fill="x", expand=True)
        tk.Button(top, text="Ara", command=lambda: self.defter_listele(self.ent_ara_def.get())).pack(side="left", padx=5)
        tk.Button(top, text="+ Not Ekle", bg="#4CAF50", fg="white", command=self.popup_not_ekle).pack(side="right")
        self.tree_def = ttk.Treeview(self.tab_defter, columns=("tarih", "kimler", "ozet"), show="headings")
        self.tree_def.heading("tarih", text="Tarih"); self.tree_def.column("tarih", width=120)
        self.tree_def.heading("kimler", text="Kimler"); self.tree_def.column("kimler", width=150)
        self.tree_def.heading("ozet", text="İçerik"); self.tree_def.column("ozet", width=500)
        self.tree_def.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.menu_def = tk.Menu(self.root_ref, tearoff=0)
        self.menu_def.add_command(label="Sil 🗑️", command=self.not_sil)
        self.tree_def.bind("<Button-3>", lambda e: self.sag_tik(e, self.tree_def, self.menu_def))
        self.tree_def.bind("<Double-1>", self.not_oku)
        
        # Menü kapatma işlemini global event ile çözüyoruz, ama burada da manuel unpost deneyebiliriz
        self.defter_listele()

    def popup_not_ekle(self):
        win = tk.Toplevel(self); win.title("Not Ekle"); win.geometry("400x500")
        ttk.Label(win, text="Tarih:").pack(pady=5)
        ent_tarih = ttk.Entry(win); ent_tarih.pack(fill="x", padx=20)
        ent_tarih.insert(0, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        ttk.Label(win, text="Kimler (Çoklu Seçim):").pack(pady=5)
        lb_kisiler = tk.Listbox(win, selectmode="multiple", height=5)
        lb_kisiler.pack(fill="x", padx=20)
        for k in self.proje['arastirmacilar'].split(','): lb_kisiler.insert("end", k.strip())
        
        ttk.Label(win, text="İçerik:").pack(pady=5)
        txt = scrolledtext.ScrolledText(win, height=10); txt.pack(fill="both", expand=True, padx=20, pady=5)
        
        def kaydet():
            secilen = [lb_kisiler.get(i) for i in lb_kisiler.curselection()]
            kimler = ", ".join(secilen) if secilen else "Belirtilmedi"
            self.proje["lab_defteri"].insert(0, {"tarih": ent_tarih.get(), "kimler": kimler, "icerik": txt.get("1.0", "end").strip()})
            self.kaydet_cb(); self.defter_listele(); win.destroy()
        ttk.Button(win, text="Kaydet", command=kaydet).pack(pady=10)

    def not_sil(self):
        sel = self.tree_def.selection()
        if not sel: return
        vals = self.tree_def.item(sel)['values']
        if messagebox.askyesno("Sil", "Bu not kalıcı olarak silinecek. Onaylıyor musunuz?"):
            self.proje["lab_defteri"] = [n for n in self.proje["lab_defteri"] if not (n['tarih'] == vals[0] and n['kimler'] == vals[1])]
            self.kaydet_cb(); self.defter_listele()

    def defter_listele(self, filtre=""):
        for i in self.tree_def.get_children(): self.tree_def.delete(i)
        for n in self.proje["lab_defteri"]:
            if filtre.lower() in n['icerik'].lower(): self.tree_def.insert("", "end", values=(n['tarih'], n['kimler'], n['icerik'][:80]))

    def not_oku(self, event):
        sel = self.tree_def.selection(); 
        if not sel: return
        vals = self.tree_def.item(sel)['values']
        tam = next((n['icerik'] for n in self.proje["lab_defteri"] if n['tarih'] == vals[0]), "")
        messagebox.showinfo("Not", f"Tarih: {vals[0]}\nKimler: {vals[1]}\n\n{tam}")

    def setup_prosedur(self):
        top = ttk.Frame(self.tab_pros); top.pack(fill="x", padx=10, pady=10)
        self.ent_ara_pros = ttk.Entry(top); self.ent_ara_pros.pack(side="left", fill="x", expand=True)
        tk.Button(top, text="Ara", command=lambda: self.pros_listele(self.ent_ara_pros.get())).pack(side="left", padx=5)
        tk.Button(top, text="+ Ekle", bg="#2196F3", fg="white", command=self.popup_pros_editor).pack(side="right")
        self.tree_pros = ttk.Treeview(self.tab_pros, columns=("ad", "tarih"), show="headings")
        self.tree_pros.heading("ad", text="Ad"); self.tree_pros.column("ad", width=300)
        self.tree_pros.heading("tarih", text="Tarih"); self.tree_pros.column("tarih", width=150)
        self.tree_pros.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.menu_pros = tk.Menu(self.root_ref, tearoff=0)
        self.menu_pros.add_command(label="Sil 🗑️", command=self.pros_sil)
        self.tree_pros.bind("<Button-3>", lambda e: self.sag_tik(e, self.tree_pros, self.menu_pros))
        self.tree_pros.bind("<Double-1>", self.pros_duzenle)
        self.pros_listele()

    def popup_pros_editor(self, veri=None, index=None):
        win = tk.Toplevel(self); win.title("Prosedür"); win.geometry("600x600")
        ttk.Label(win, text="Ad:").pack(pady=5); ent_ad = ttk.Entry(win); ent_ad.pack(fill="x", padx=20)
        if veri: ent_ad.insert(0, veri['ad'])
        lbl_malz = ttk.Label(win, text="Malzemeler:", font="bold"); lbl_malz.pack(pady=(10,5), anchor="w", padx=20)
        f_malz = ttk.Frame(win); f_malz.pack(fill="x", padx=20); entries = []
        def satir(d=""): e = ttk.Entry(f_malz); e.pack(fill="x", pady=2); entries.append(e)
        if d: e.insert(0, d)
        tk.Button(win, text="+ Satır", command=lambda: satir()).pack(anchor="w", padx=20)
        if veri and 'malzemeler' in veri: 
            for m in veri['malzemeler']: satir(m)
        else: satir()
        ttk.Label(win, text="Talimatlar:").pack(pady=(10,5))
        txt = scrolledtext.ScrolledText(win, height=10); txt.pack(fill="both", expand=True, padx=20, pady=5)
        if veri: txt.insert("1.0", veri.get("icerik", ""))
        def kaydet():
            yeni = {"ad": ent_ad.get(), "malzemeler": [e.get() for e in entries if e.get().strip()], "icerik": txt.get("1.0", "end").strip(), "son_guncelleme": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
            if index is not None: self.proje["prosedur_listesi"][index] = yeni
            else: self.proje["prosedur_listesi"].append(yeni)
            self.kaydet_cb(); self.pros_listele(); win.destroy()
        ttk.Button(win, text="Kaydet", command=kaydet).pack(pady=10)

    def pros_sil(self):
        sel = self.tree_pros.selection()
        if not sel: return
        ad = self.tree_pros.item(sel)['values'][0]
        if messagebox.askyesno("Sil", "Silinsin mi?"):
            self.proje["prosedur_listesi"] = [p for p in self.proje["prosedur_listesi"] if p['ad'] != ad]
            self.kaydet_cb(); self.pros_listele()

    def pros_listele(self, filtre=""):
        for i in self.tree_pros.get_children(): self.tree_pros.delete(i)
        for p in self.proje["prosedur_listesi"]:
            if filtre.lower() in p['ad'].lower(): self.tree_pros.insert("", "end", values=(p['ad'], p.get('son_guncelleme', '-')))

    def pros_duzenle(self, event):
        sel = self.tree_pros.selection(); 
        if not sel: return
        ad = self.tree_pros.item(sel)['values'][0]
        for i, p in enumerate(self.proje["prosedur_listesi"]):
            if p['ad'] == ad: self.popup_pros_editor(p, i); break

    def setup_dosyalar(self):
        lb = tk.Listbox(self.tab_dosya); lb.pack(fill="both", expand=True, padx=10, pady=10)
        for d in self.proje["dosyalar"]: lb.insert("end", d)
        def ekle():
            f = filedialog.askopenfilename()
            if f: self.proje["dosyalar"].append(f); lb.insert("end", f); self.kaydet_cb()
        tk.Button(self.tab_dosya, text="Dosya Ekle", command=ekle).pack(pady=5)

    def sag_tik(self, event, tree, menu):
        item = tree.identify_row(event.y)
        if item: tree.selection_set(item); menu.post(event.x_root, event.y_root)

if __name__ == "__main__":
    root = tk.Tk()
    app = LabMateApp(root)
    root.mainloop()