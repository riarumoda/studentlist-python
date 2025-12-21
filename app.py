# Impor deps yang diperlukan
from flask import Flask, render_template, request, redirect, url_for, flash, make_response, session, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

# Load environment variables dari .env file
load_dotenv()

# Variabel Global
app = Flask(__name__)

# Apply environment variables
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SESSION_PERMANENT'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'

# Inisialisasi database dan login manager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = "strong"
login_manager.login_view = 'login'

# Model student
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f'<Student {self.name}>'

# Model User untuk autentikasi
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Model untuk login
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

############################
# Start Routes
############################
# Route utama - add login required
@app.route('/')
@login_required
def index():
    # Menggunakan query builder daripada pull secara raw
    students = Student.query.all()
    response = make_response(render_template('index.html', students=students))
    # Mencegah browser menampilkan halaman index dari cache setelah logout
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

# Route add student
@app.route('/add', methods=['POST'])
@login_required
def add_student():
    # Ambil data dari form dengan sanitasi dasar
    name = request.form.get('name', '').strip()
    grade = request.form.get('grade', '').strip()
    
    # Validasi tipe data usia
    try:
        age_input = request.form.get('age')
        if not age_input:
            flash("Usia tidak boleh kosong!")
            return redirect(url_for('index'))
            
        age = int(age_input)
    except (ValueError, TypeError):
        flash("Input usia harus berupa angka!")
        return redirect(url_for('index'))

    # Simpan menggunakan ORM
    try:
        new_student = Student(name=name, age=age, grade=grade)
        db.session.add(new_student)
        db.session.commit()
        flash(f"Siswa {name} berhasil ditambahkan!")
    except Exception as e:
        db.session.rollback()
        flash("Gagal menambahkan data ke database.")
        
    return redirect(url_for('index'))

# Route delete student
@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_student(id):
    student = db.session.get(Student, id)
    if student:
        db.session.delete(student)
        db.session.commit()
    return redirect(url_for('index'))

# Route edit student
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    student = db.session.get(Student, id)
    if not student:
        abort(404)

    if request.method == 'POST':
        student.name = request.form.get('name', '').strip()
        student.grade = request.form.get('grade', '').strip()
        try:
            student.age = int(request.form.get('age'))
        except (ValueError, TypeError):
            flash("Usia harus berupa angka!")
            return render_template('edit.html', student=student)

        db.session.commit()
        flash("Data berhasil diperbarui!")
        return redirect(url_for('index'))
    
    return render_template('edit.html', student=student)

# Route login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Username atau password salah.')
    return render_template('login.html')

# Route logout
@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('session', path='/', domain=None)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    flash('Anda telah berhasil keluar.')
    return response

# Route signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(username=request.form['username'], password=hashed_pw)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Akun berhasil dibuat!')
            return redirect(url_for('login'))
        except:
            flash('Username sudah ada.')
    return render_template('signup.html')
############################
# End Routes
############################

# Main executor
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)

