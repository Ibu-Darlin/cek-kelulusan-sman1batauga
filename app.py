from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, send_from_directory
import sqlite3
from fpdf import FPDF
import io, os

app = Flask(__name__)
app.secret_key = "rahasia_sekolah_sman1batauga"

DB_PATH = 'kelulusan.db'
LOGO_PATH = os.path.join(app.root_path, 'static', 'logo.jpg') if True else None

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS siswa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nisn TEXT UNIQUE NOT NULL,
        nama TEXT NOT NULL,
        nilai REAL NOT NULL,
        status TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()

init_db()

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'sma1batauga'

@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username','').strip()
        p = request.form.get('password','').strip()
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session['admin'] = True
            flash('Login berhasil.','success')
            return redirect(url_for('admin'))
        flash('Username atau password salah.','danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash('Anda telah logout.','info')
    return redirect(url_for('login'))

def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('admin'):
            flash('Harus login sebagai admin.','danger')
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapper

@app.route('/admin')
@admin_required
def admin():
    conn = get_db_connection()
    siswa = conn.execute('SELECT * FROM siswa ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin.html', siswa=siswa)

@app.route('/tambah', methods=['POST'])
@admin_required
def tambah():
    nisn = request.form.get('nisn','').strip()
    nama = request.form.get('nama','').strip()
    try:
        nilai = float(request.form.get('nilai',0))
    except:
        nilai = 0.0
    status = request.form.get('status','Tidak Lulus')
    if not nisn or not nama:
        flash('NISN dan Nama wajib diisi.','danger')
        return redirect(url_for('admin'))
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO siswa (nisn, nama, nilai, status) VALUES (?,?,?,?)', (nisn, nama, nilai, status))
        conn.commit()
        flash('Data siswa ditambahkan.','success')
    except Exception as e:
        flash('Gagal menambahkan: ' + str(e),'danger')
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/hapus/<int:id>')
@admin_required
def hapus(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM siswa WHERE id=?', (id,))
    conn.commit()
    conn.close()
    flash('Data siswa dihapus.','warning')
    return redirect(url_for('admin'))

@app.route('/ubah/<int:id>', methods=['POST'])
@admin_required
def ubah(id):
    nisn = request.form.get('nisn','').strip()
    nama = request.form.get('nama','').strip()
    try:
        nilai = float(request.form.get('nilai',0))
    except:
        nilai = 0.0
    status = request.form.get('status','Tidak Lulus')
    conn = get_db_connection()
    try:
        conn.execute('UPDATE siswa SET nisn=?, nama=?, nilai=?, status=? WHERE id=?', (nisn, nama, nilai, status, id))
        conn.commit()
        flash('Data siswa diperbarui.','success')
    except Exception as e:
        flash('Gagal mengubah: ' + str(e),'danger')
    finally:
        conn.close()
    return redirect(url_for('admin'))

@app.route('/export_pdf_all')
@admin_required
def export_pdf_all():
    conn = get_db_connection()
    siswa = conn.execute('SELECT * FROM siswa ORDER BY nama').fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try:
            pdf.image(LOGO_PATH, x=10, y=8, w=25)
        except: pass
    pdf.set_font('Arial','B',14)
    pdf.cell(0, 10, 'DAFTAR KELULUSAN SMAN 1 BATAUGA', ln=True, align='C')
    pdf.ln(4)
    pdf.set_font('Arial','',11)
    for row in siswa:
        pdf.cell(0, 8, "{nisn} - {nama} - Nilai: {nilai} - Status: {status}".format(nisn=row['nisn'], nama=row['nama'], nilai=row['nilai'], status=row['status']), ln=True)
    pdf.ln(8)
    pdf.cell(0, 8, 'Mengetahui,', ln=True)
    pdf.ln(12)
    pdf.cell(0, 8, 'Drs. La Ode Kepala, M.Pd', ln=True)
    output = io.BytesIO(pdf.output(dest='S').encode('latin1'))
    return send_file(output, as_attachment=True, download_name='kelulusan_all.pdf', mimetype='application/pdf')

@app.route('/export_pdf/<nisn>')
@admin_required
def export_pdf_single(nisn):
    conn = get_db_connection()
    siswa = conn.execute('SELECT * FROM siswa WHERE nisn=?', (nisn,)).fetchone()
    conn.close()
    if not siswa:
        flash('Data tidak ditemukan.','danger')
        return redirect(url_for('admin'))

    pdf = FPDF()
    pdf.add_page()
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        try:
            pdf.image(LOGO_PATH, x=10, y=8, w=25)
        except: pass
    pdf.set_font('Arial','B',14)
    pdf.cell(0, 10, 'SURAT KETERANGAN HASIL', ln=True, align='C')
    pdf.ln(6)
    pdf.set_font('Arial','',12)
    pdf.cell(0,8, "Nama: {0}".format(siswa['nama']), ln=True)
    pdf.cell(0,8, "NISN: {0}".format(siswa['nisn']), ln=True)
    pdf.cell(0,8, "Nilai Akhir: {0}".format(siswa['nilai']), ln=True)
    pdf.cell(0,8, "Status: {0}".format(siswa['status']), ln=True)
    pdf.ln(12)
    pdf.cell(0,8,'Mengetahui,', ln=True)
    pdf.ln(18)
    pdf.cell(0,8,'Drs. La Ode Kepala, M.Pd', ln=True)
    output = io.BytesIO(pdf.output(dest='S').encode('latin1'))
    return send_file(output, as_attachment=True, download_name='kelulusan_'+nisn+'.pdf', mimetype='application/pdf')

@app.route('/', methods=['GET','POST'])
def siswa_view():
    hasil = None
    notfound = False
    if request.method == 'POST':
        nisn = request.form.get('nisn','').strip()
        conn = get_db_connection()
        hasil = conn.execute('SELECT * FROM siswa WHERE nisn=?', (nisn,)).fetchone()
        conn.close()
        if not hasil:
            notfound = True
    return render_template('siswa.html', hasil=hasil, notfound=notfound, logo_exists=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
