from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime, timedelta
app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('spor_salonu.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def ana_sayfa():
    try:
        conn = get_db_connection()
        paketler = conn.execute('SELECT * FROM paketler').fetchall()
        conn.close()
        return render_template('index.html', paketler=paketler)
    except Exception as e:
        return f"Ana Sayfa Hatası: {e}"

@app.route('/login-secim')
def login_secim():
    return render_template('login_secim.html')

@app.route('/login/<tur>', methods=['GET', 'POST'])
def login_sayfasi(tur):
    if request.method == 'POST':
        kullanici = request.form.get('username')
        sifre = request.form.get('password')
        if tur == 'yonetici' and kullanici == 'Datariders' and sifre == '1234':
            return redirect(url_for('yonetim_merkezi'))
        return "<h2>Giris Basarisiz! Bilgileri kontrol edin.</h2>"
    return render_template('login.html', tur=tur)

@app.route('/yonetim-merkezi')
def yonetim_merkezi():
    return render_template('datariders_panel.html')


@app.route('/yonetim-merkezi/uyeler')
def uyeler_sayfasi():
    try:
        conn = get_db_connection()
        uyeler = conn.execute('SELECT * FROM Uyeler').fetchall()
        uye_verileri = []

        for uye in uyeler:
            kiralamalar = conn.execute('SELECT * FROM SahaKiralama WHERE Uye_Id = ?', (uye['Id'],)).fetchall()
            uye_verileri.append({
                'detay': uye,
                'kiralamalar': kiralamalar
            })

        conn.close()
        return render_template('uye_listesi.html', uyeler_listesi=uye_verileri)
    except Exception as e:
        return f"Üye Listesi Hatası: {e}"

@app.route('/yonetim-merkezi/dersler')
def ders_yonetimi():
    conn = get_db_connection()
    dersler = conn.execute('SELECT * FROM Dersler').fetchall()
    conn.close()
    return render_template('ders_yonetimi.html', dersler=dersler)

@app.route('/yonetim-merkezi/ders-ekle', methods=['POST'])
def ders_ekle():
    try:
        conn = get_db_connection()
        conn.execute('''INSERT INTO Dersler (Ders_Adi, Hoca_Adi, Ucret, Ders_Tarihi, Ders_Saati, Kontenjan) 
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (request.form.get('ders_adi'), request.form.get('hoca_adi'),
                      request.form.get('ucret'), request.form.get('tarih'),
                      request.form.get('saat'), request.form.get('kontenjan')))
        conn.commit()
        conn.close()
        return redirect(url_for('ders_yonetimi'))
    except Exception as e:
        return f"Ders Ekleme Hatası: {e}"

@app.route('/yonetim-merkezi/ders-sil/<int:id>')
def ders_sil(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM Dersler WHERE Id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('ders_yonetimi'))

@app.route('/yonetim-merkezi/uye-sil/<int:id>')
def uye_sil(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM SahaKiralama WHERE Uye_Id = ?', (id,))
        conn.execute('DELETE FROM Uyeler WHERE Id = ?', (id,))

        conn.commit()
        conn.close()
        return redirect(url_for('uyeler_sayfasi'))
    except Exception as e:
        return f"Üye Silme Hatası: {e}"


@app.route('/yonetim-merkezi/odemeler')
def odemeler_paneli():
    try:
        conn = get_db_connection()
        uyeler = conn.execute('SELECT * FROM Uyeler').fetchall()
        paketler_raw = conn.execute('SELECT * FROM paketler').fetchall()
        paket_fiyatlari = {}
        for p in paketler_raw:
            p_adi = p['PaketAdi'] if 'PaketAdi' in p.keys() else p['paket_adi']
            p_fiyat = p['Fiyat'] if 'Fiyat' in p.keys() else p['fiyat']
            paket_fiyatlari[p_adi] = p_fiyat

        odeme_listesi = []
        for u in uyeler:
            p_ucreti = paket_fiyatlari.get(u['Secili_Paket'], 0)
            ders_toplam = conn.execute('''
                SELECT SUM(d.Ucret) as toplam 
                FROM DersKayitlari dk 
                JOIN Dersler d ON dk.Ders_Id = d.Id 
                WHERE dk.Uye_Id = ?
            ''', (u['Id'],)).fetchone()['toplam'] or 0

            odeme_listesi.append({
                'Ad_Soyad': f"{u['Isim']} {u['Soyisim']}",
                'Paket': u['Secili_Paket'],
                'Paket_Ucret': p_ucreti,
                'Ders_Ucret': ders_toplam,
                'Toplam': p_ucreti + ders_toplam,
                'Durum': u['Odeme_Durumu']
            })

        conn.close()
        return render_template('odemeler.html', odemeler=odeme_listesi)
    except Exception as e:
        return f"Ödeme Paneli Hatası: {str(e)}"
@app.route('/uye-kayit', methods=['GET', 'POST'])
def uye_kayit():
    if request.method == 'POST':
        isim, soyisim, telefon, paket, sifre = request.form.get('isim'), request.form.get('soyisim'), request.form.get('telefon'), request.form.get('secili_paket'), request.form.get('sifre')
        baslangic = datetime.now().strftime('%Y-%m-%d')
        ay_sayisi = 3 if "3" in paket else (6 if "6" in paket else 12)
        bitis = (datetime.now() + timedelta(days=ay_sayisi * 30)).strftime('%Y-%m-%d')
        try:
            conn = get_db_connection()
            if conn.execute('SELECT * FROM Uyeler WHERE Telefon = ?', (telefon,)).fetchone():
                conn.close()
                return render_template('kayit.html', hata="Bu numara kayıtlı!")
            conn.execute('''INSERT INTO Uyeler (Isim, Soyisim, Telefon, Sifre, Secili_Paket, Baslangic_Tarihi, Bitis_Tarihi, Alinan_Ders) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (isim, soyisim, telefon, sifre, paket, baslangic, bitis, "Yok"))
            conn.commit(); conn.close()
            return "<div style='text-align:center; margin-top:50px;'><h2>Kayıt Başarılı!</h2><a href='/login-secim'>Giriş Yap</a></div>"
        except Exception as e: return f"Kayıt Hatası: {str(e)}"
    return render_template('kayit.html')

@app.route('/login/uye', methods=['POST'])
def uye_giris_yap():
    telefon = request.form.get('username')
    sifre = request.form.get('password')
    conn = get_db_connection()
    uye = conn.execute('SELECT * FROM Uyeler WHERE Telefon = ? AND Sifre = ?', (telefon, sifre)).fetchone()
    conn.close()
    if uye:
        return redirect(url_for('uye_paneli_ac', id=uye['Id']))
    return "<h2>Hatalı telefon veya şifre!</h2><a href='/login-secim'>Geri Dön</a>"


@app.route('/uye-paneli/<int:id>')
def uye_paneli_ac(id):
    try:
        conn = get_db_connection()
        uye = conn.execute('SELECT * FROM Uyeler WHERE Id = ?', (id,)).fetchone()
        kiralamalar = conn.execute('SELECT * FROM SahaKiralama WHERE Uye_Id = ?', (id,)).fetchall()
        kayitli_dersler = conn.execute('''
            SELECT dk.Id as Kayit_Id, d.Ders_Adi, d.Hoca_Adi, d.Ders_Saati, d.Ders_Tarihi, d.Ucret 
            FROM DersKayitlari dk
            JOIN Dersler d ON dk.Ders_Id = d.Id
            WHERE dk.Uye_Id = ?
        ''', (id,)).fetchall()

        conn.close()
        return render_template('uye_paneli.html',
                               uye=uye,
                               kiralamalar=kiralamalar,
                               kayitli_dersler=kayitli_dersler)
    except Exception as e:
        return f"Panel yüklenirken hata oluştu: {e}"

@app.route('/uye-paneli/iptal/<int:id>')
def uye_kendi_iptal(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM SahaKiralama WHERE Uye_Id = ?', (id,))
        conn.execute('DELETE FROM Uyeler WHERE Id = ?', (id,))

        conn.commit()
        conn.close()
        return "<h2>Üyeliğiniz ve tüm randevularınız başarıyla silindi.</h2><a href='/'>Ana Sayfaya Dön</a>"
    except Exception as e:
        return f"İptal Hatası: {e}"

SAATLER = ["09:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00", "13:00 - 14:00", "14:00 - 15:00", "15:00 - 16:00", "17:00 - 18:00", "18:00 - 19:00", "19:00 - 20:00"]


@app.route('/uye-paneli/saha-kirala/<int:uye_id>', methods=['GET', 'POST'])
def saha_kirala(uye_id):
    conn = get_db_connection()
    bugun = datetime.now().strftime('%Y-%m-%d')
    secilen_tarih = request.args.get('tarih', bugun)
    secilen_saha = request.args.get('saha_tipi', 'Futbol')
    dolu_kayitlar = conn.execute('SELECT Saat FROM SahaKiralama WHERE Tarih = ? AND Saha_Tipi = ?',
                                 (secilen_tarih, secilen_saha)).fetchall()
    dolu_saat_listesi = [k['Saat'] for k in dolu_kayitlar]

    if request.method == 'POST':
        saha = request.form.get('saha_tipi')
        tarih = request.form.get('tarih')
        saat = request.form.get('saat')
        dolu = conn.execute('SELECT * FROM SahaKiralama WHERE Saha_Tipi = ? AND Tarih = ? AND Saat = ?',
                            (saha, tarih, saat)).fetchone()

        if dolu:
            conn.close()
            return "<h2>Bu saatte saha dolu!</h2>"

        conn.execute('INSERT INTO SahaKiralama (Uye_Id, Saha_Tipi, Tarih, Saat) VALUES (?, ?, ?, ?)',
                     (uye_id, saha, tarih, saat))
        conn.commit()
        conn.close()
        return redirect(url_for('uye_paneli_ac', id=uye_id))

    conn.close()
    return render_template('saha_kirala.html',
                           uye_id=uye_id,
                           saatler=SAATLER,
                           dolu_saatler=dolu_saat_listesi,
                           bugun=bugun,
                           secilen_tarih=secilen_tarih,
                           secilen_saha=secilen_saha)

@app.route('/kiralama-iptal/<int:kira_id>/<int:uye_id>')
def kiralama_iptal(kira_id, uye_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM SahaKiralama WHERE Id = ?', (kira_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('uye_paneli_ac', id=uye_id))
    except Exception as e:
        return f"İptal işlemi sırasında hata oluştu: {e}"


@app.route('/uye-paneli/ders-kayit/<int:uye_id>', methods=['GET', 'POST'])
def ders_kayit(uye_id):
    conn = get_db_connection()

    if request.method == 'POST':
        ders_id = request.form.get('ders_id')
        ders = conn.execute('SELECT * FROM Dersler WHERE Id = ?', (ders_id,)).fetchone()
        mevcut_kayit = conn.execute('SELECT COUNT(*) as sayi FROM DersKayitlari WHERE Ders_Id = ?',
                                    (ders_id,)).fetchone()

        if mevcut_kayit['sayi'] >= ders['Kontenjan']:
            conn.close()
            return "<h2>Kontenjan dolu!</h2><a href='javascript:history.back()'>Geri Dön</a>"

        zaten_kayitli = conn.execute('SELECT * FROM DersKayitlari WHERE Uye_Id = ? AND Ders_Id = ?',
                                     (uye_id, ders_id)).fetchone()
        if zaten_kayitli:
            conn.close()
            return "<h2>Zaten kayıtlısınız!</h2><a href='javascript:history.back()'>Geri Dön</a>"

        conn.execute('INSERT INTO DersKayitlari (Uye_Id, Ders_Id) VALUES (?, ?)', (uye_id, ders_id))
        conn.commit()
        conn.close()
        return redirect(url_for('uye_paneli_ac', id=uye_id))

    # --- GET SORGUSU (Burayı çok dikkatli kopyala) ---
    dersler = conn.execute('''
        SELECT 
            Id, 
            Ders_Adi, 
            Hoca_Adi, 
            Ders_Tarihi, 
            Ders_Saati, 
            Kontenjan, 
            Ucret,
            (SELECT COUNT(*) FROM DersKayitlari dk WHERE dk.Ders_Id = Dersler.Id) as Doluluk 
        FROM Dersler
    ''').fetchall()

    conn.close()
    return render_template('ders_kayit.html', dersler=dersler, uye_id=uye_id)

@app.route('/ders-iptal/<int:kayit_id>/<int:uye_id>')
def ders_iptal(kayit_id, uye_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM DersKayitlari WHERE Id = ?', (kayit_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('uye_paneli_ac', id=uye_id))
@app.route('/logout')
def logout():
    return redirect(url_for('ana_sayfa'))


@app.route('/uye-paneli/odeme/<int:id>')
def odeme_sayfasi(id):
    try:
        conn = get_db_connection()
        uye = conn.execute('SELECT * FROM Uyeler WHERE Id = ?', (id,)).fetchone()
        paket = conn.execute('SELECT * FROM paketler WHERE PaketAdi = ?', (uye['Secili_Paket'],)).fetchone()
        paket_fiyat = paket['Fiyat'] if paket else 0
        ders_toplam = conn.execute('''
            SELECT SUM(d.Ucret) as toplam 
            FROM DersKayitlari dk 
            JOIN Dersler d ON dk.Ders_Id = d.Id 
            WHERE dk.Uye_Id = ?
        ''', (id,)).fetchone()['toplam'] or 0

        conn.close()

        toplam_tutar = paket_fiyat + ders_toplam
        return render_template('odeme_yap.html', uye=uye, toplam=toplam_tutar)

    except Exception as e:
        return f"Ödeme Sayfası Hatası: {e}"


@app.route('/uye-paneli/odeme-tamamla/<int:id>', methods=['POST'])
def odeme_tamamla(id):
    try:
        conn = get_db_connection()
        conn.execute('UPDATE Uyeler SET Odeme_Durumu = "Ödendi" WHERE Id = ?', (id,))
        conn.commit()
        conn.close()
        return f"""
        <div style="text-align:center; margin-top:50px; font-family:sans-serif; background:#f4f7f6; padding:40px;">
            <div style="background:white; display:inline-block; padding:30px; border-radius:15px; box-shadow:0 5px 15px rgba(0,0,0,0.1);">
                <h2 style="color: #28a745;">✅ Ödeme Başarıyla Alındı!</h2>
                <p style="color:#555;">Üyeliğiniz aktifleşti. Keyifli sporlar dileriz.</p>
                <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
                <a href="/uye-paneli/{id}" style="text-decoration:none; background:#1a73e8; color:white; padding:10px 20px; border-radius:5px; font-weight:bold;">Panelime Dön</a>
            </div>
        </div>
        """
    except Exception as e:
        return f"Ödeme İşlenirken Hata Oluştu: {e}"

if __name__ == '__main__':
    app.run(debug=True)