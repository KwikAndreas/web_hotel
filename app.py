from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql.cursors, os
import datetime
from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

application = Flask(__name__)
application.secret_key = 'your_secret_key'

conn = cursor = None

# Function to connect to the database
def openDb():
    global conn, cursor
    conn = pymysql.connect(db="db_pegawai", user="root", passwd="", host="localhost", port=3306, autocommit=True)
    cursor = conn.cursor()

# Function to close the database connection
def closeDb():
    global conn, cursor
    cursor.close()
    conn.close()

# Function to display the index page
@application.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    openDb()
    container = []
    sql = "SELECT * FROM pegawai ORDER BY NIK DESC;"
    cursor.execute(sql)
    results = cursor.fetchall()
    for data in results:
        container.append(data)
    closeDb()
    return render_template('index.html', container=container)

# Function to generate NIK
def generate_nik():
    openDb()
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month
    year_str = str(current_year).zfill(2)
    current_month_str = str(current_month).zfill(2)
    base_nik_without_number = f"P-{year_str}{current_month_str}"
    cursor.execute("SELECT nik FROM pegawai WHERE nik LIKE %s ORDER BY nik DESC LIMIT 1", (f"{base_nik_without_number}%",))
    last_nik = cursor.fetchone()
    if last_nik:
        last_number = int(last_nik[0].split("-")[-1])
        next_number = last_number + 1
        next_nik = f"P-{str(next_number).zfill(3)}"
    else:
        next_number = 1
        next_nik = f"{base_nik_without_number}{str(next_number).zfill(3)}"
    closeDb()
    return next_nik

@application.route('/tambah', methods=['GET', 'POST'])
def tambah():
    if 'username' not in session:
        return redirect(url_for('login'))

    generated_nik = generate_nik()
    if request.method == 'POST':
        nik = request.form['nik']
        nama = request.form['nama']
        alamat = request.form['alamat']
        tgllahir = request.form['tgllahir']
        jeniskelamin = request.form['jeniskelamin']
        status = request.form['status']
        gaji = request.form['gaji']
        foto = request.form['nik']

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        if 'foto' in request.files:
            foto = request.files['foto']
            if foto.filename != '':
                foto.save(os.path.join(application.config['UPLOAD_FOLDER'], f"{nik}.jpg"))

        openDb()
        sql = "INSERT INTO pegawai (nik, nama, alamat, tgllahir, jeniskelamin, status, gaji, foto) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        val = (nik, nama, alamat, tgllahir, jeniskelamin, status, gaji, foto)
        cursor.execute(sql, val)
        conn.commit()
        closeDb()
        return redirect(url_for('index'))
    else:
        return render_template('tambah.html', nik=generated_nik)

# Function to edit employee data
@application.route('/edit/<nik>', methods=['GET', 'POST'])
def edit(nik):
    if 'username' not in session:
        return redirect(url_for('login'))

    openDb()
    cursor.execute('SELECT * FROM pegawai WHERE nik=%s', (nik))
    data = cursor.fetchone()
    if request.method == 'POST':
        nik = request.form['nik']
        nama = request.form['nama']
        alamat = request.form['alamat']
        tgllahir = request.form['tgllahir']
        jeniskelamin = request.form['jeniskelamin']
        status = request.form['status']
        gaji = request.form['gaji']
        foto = request.form['nik']

        path_to_photo = os.path.join(application.root_path, '/web_pegawai/crud/static/foto', f'{nik}.jpg')
        if os.path.exists(path_to_photo):
            os.remove(path_to_photo)

        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)

        if 'foto' in request.files:
            foto = request.files['foto']
            if foto.filename != '':
                foto.save(os.path.join(application.config['UPLOAD_FOLDER'], f"{nik}.jpg"))
        sql = "UPDATE pegawai SET nama=%s, alamat=%s, tgllahir=%s, jeniskelamin=%s, status=%s, gaji=%s, foto=%s WHERE nik=%s"
        val = (nama, alamat, tgllahir, jeniskelamin, status, gaji, foto, nik)
        cursor.execute(sql, val)
        conn.commit()
        closeDb()
        return redirect(url_for('index'))
    else:
        closeDb()
        return render_template('edit.html', data=data)

# Function to delete an employee
@application.route('/hapus/<nik>', methods=['GET', 'POST'])
def hapus(nik):
    if 'username' not in session:
        return redirect(url_for('login'))

    openDb()
    cursor.execute('DELETE FROM pegawai WHERE nik=%s', (nik,))
    path_to_photo = os.path.join(application.root_path, '/web_pegawai/crud/static/foto', f'{nik}.jpg')
    if os.path.exists(path_to_photo):
        os.remove(path_to_photo)
    conn.commit()
    closeDb()
    return redirect(url_for('index'))

# Function to fetch employee data as JSON
@application.route('/get_employee_data/<nik>', methods=['GET'])
def get_employee_data(nik):
    connection = pymysql.connect(host='localhost', user='root', password='', db='db_pegawai', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM pegawai WHERE nik = %s"
            cursor.execute(sql, (nik,))
            employee_data = cursor.fetchone()
            return jsonify(employee_data)
    except Exception as e:
        return jsonify({'error': 'Terjadi kesalahan saat mengambil data'}), 500
    finally:
        connection.close()

@application.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        openDb()
        cursor.execute('SELECT * FROM user WHERE username=%s AND password=%s', (username, password))
        user = cursor.fetchone()
        closeDb()
        if user:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            return redirect(url_for('login'))
    return render_template('login.html')

# Function to handle user registration
@application.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('register'))
            
        openDb()
        cursor.execute('INSERT INTO user (username, password) VALUES (%s, %s)', (username, password))
        conn.commit()
        closeDb()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

# Function to handle user logout
@application.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Main program
if __name__ == '__main__':
    application.run(debug=True)
