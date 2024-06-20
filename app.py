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
    conn = pymysql.connect(db="db_hotel", user="root", passwd="", host="localhost", port=3306, autocommit=True)
    cursor = conn.cursor()

# Function to close the database connection
def closeDb():
    global conn, cursor
    cursor.close()
    conn.close()
    
# Jika login sebagai Customer akan Routing ke /hotel
@application.route('/hotel')
def hotel():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('hotel.html')

    
# Jika login sebagai pegawai hotel akan Routing ke /index
@application.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    openDb()
    container = []
    sql = "SELECT * FROM orders ORDER BY ID DESC;"
    cursor.execute(sql)
    results = cursor.fetchall()
    for data in results:
        container.append(data)
    closeDb()
    return render_template('index.html', container=container)

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
            if user[3] == 'customer':  # Assuming user type is stored in the 4th column
                return redirect(url_for('hotel'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Tidak sesuai a username atau password')
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
            flash('Password tidak cocok')
            return redirect(url_for('register'))
        
        openDb()
        cursor.execute('INSERT INTO user (username, password, role) VALUES (%s, %s, %s)', (username, password, 'customer'))
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

# Function to generate Invoice
def generate_invoice():
    openDb()
    current_year = datetime.datetime.now().year
    current_month = datetime.datetime.now().month
    year_str = str(current_year).zfill(2)
    current_month_str = str(current_month).zfill(2)
    base_invoice_without_number = f"H-{year_str}{current_month_str}"
    cursor.execute("SELECT invoice FROM kamar WHERE invoice LIKE %s ORDER BY invoice DESC LIMIT 1", (f"{base_invoice_without_number}%",))
    last_invoice = cursor.fetchone()
    if last_invoice:
        last_number = int(last_invoice[0].split("-")[-1])
        next_number = last_number + 1
        next_invoice = f"H-{str(next_number).zfill(3)}"
    else:
        next_number = 1
        next_invoice = f"{base_invoice_without_number}{str(next_number).zfill(3)}"
    closeDb()
    return next_invoice

# Function to handle room booking
@application.route('/order', methods=['GET', 'POST'])
def order():
    if 'username' not in session:
        return redirect(url_for('login'))

    generated_invoice = generate_invoice()
    tipe_ruangan = {
        "1": 1000000,
        "2": 2000000,
        "3": 3000000,
        "4": 4000000,
        "5": 5000000
    }
    fasilitas = {
        "kolam_renang": 50000,
        "gym": 100000,
        "breakfast": 250000,
        "spa": 400000
    }

    if request.method == 'POST':
        invoice = request.form['invoice']
        nama_tamu = request.form['nama_tamu']
        room_type = request.form['room_type']
        jumlah_tamu_dewasa = int(request.form['jumlah_tamu_dewasa'])
        jumlah_tamu_anak = int(request.form['jumlah_tamu_anak'])
        tambahan = request.form.getlist('fasilitas')

        # Calculate total cost
        room_price = tipe_ruangan[room_type]
        fasilitas_cost = sum(fasilitas[facility] for facility in tambahan)
        guests_cost = (jumlah_tamu_dewasa * 250000) + (jumlah_tamu_anak * 50000)
        total_biaya = room_price + fasilitas_cost + guests_cost

        openDb()
        sql = "INSERT INTO orders (invoice, id, nama_tamu, room_type, jumlah_tamu_dewasa, jumlah_tamu_anak_lansia, fasilitas, total_harga, status, create_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        val = (invoice, nama_tamu, room_type, jumlah_tamu_dewasa, jumlah_tamu_anak, ",".join(tambahan), total_biaya)
        cursor.execute(sql, val)
        conn.commit()
        closeDb()
        return redirect(url_for('index'))
    else:
        return render_template('order.html', invoice=generated_invoice, tipe_ruangan=tipe_ruangan, fasilitas=fasilitas)
    
@application.route('/hapus/<invoice>', methods=['GET', 'POST'])
def hapus(invoice):
    if 'username' not in session:
        return redirect(url_for('login'))

    openDb()
    cursor.execute('DELETE FROM kamar WHERE invoice=%s', (invoice,))
    path_to_photo = os.path.join(application.root_path, '/web_hotel/crud/static/foto', f'{invoice}.jpg')
    if os.path.exists(path_to_photo):
        os.remove(path_to_photo)
    conn.commit()
    closeDb()
    return redirect(url_for('index'))

# Function to fetch room data as JSON
@application.route('/get_room_data/<invoice>', methods=['GET'])
def get_room_data(invoice):
    connection = pymysql.connect(host='localhost', user='root', password='', db='db_hotel', charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM kamar WHERE invoice = %s"
            cursor.execute(sql, (invoice,))
            room_data = cursor.fetchone()
            return jsonify(room_data)
    except Exception as e:
        return jsonify({'error': 'Terjadi kesalahan saat mengambil data'}), 500
    finally:
        connection.close()

# Main program
if __name__ == '__main__':
    application.run(debug=True)
