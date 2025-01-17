from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3
import re
from flask_login import current_user, LoginManager, UserMixin, login_user
from flask_bcrypt import Bcrypt


app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = 'secret_key'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
first_request = True


@app.before_request
def before_first_request():
    global first_request
    if first_request:
        init_db()
        init_superuser()
        first_request = False


class User(UserMixin):
    def __init__(self, id, username, is_superuser):
        self.id = id
        self.username = username
        self.is_superuser = is_superuser


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return User(user['id'], user['username'], user['is_superuser']) if user else None


def get_user_by_id(user_id):
    conn = get_db_connection()
    user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    close_db_connection(conn)
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['is_superuser'])
    return None


def generate_slug(title):
    slug = re.sub(r'[^a-zA-Zа-яА-Я0-9-]', '-', title.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
    conn = get_db_connection()
    cursor = conn.cursor()
    original_slug = slug
    count = cursor.execute('SELECT COUNT(*) FROM posts WHERE slug = ?', (slug,)).fetchone()[0]
    i = 1
    while count > 0:
        slug = f"{original_slug}-{i}"
        count = cursor.execute('SELECT COUNT(*) FROM posts WHERE slug = ?', (slug,)).fetchone()[0]
        i += 1
    close_db_connection(conn)
    return slug


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def close_db_connection(conn):
    conn.close()


def init_db():
    conn = get_db_connection()
    conn.execute(
        'CREATE TABLE IF NOT EXISTS posts ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'title TEXT NOT NULL, '
        'rezume TEXT NOT NULL, '
        'info TEXT NOT NULL, '
        'created_at DATETIME DEFAULT CURRENT_TIMESTAMP, '
        'slug TEXT UNIQUE NOT NULL)')
    conn.close()


def init_superuser():
    conn = get_db_connection()
    conn.execute(
        'CREATE TABLE IF NOT EXISTS users ('
        'id INTEGER PRIMARY KEY AUTOINCREMENT, '
        'username TEXT NOT NULL UNIQUE, '
        'password TEXT NOT NULL, '
        'is_superuser BOOLEAN NOT NULL DEFAULT 0)')
    if not conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone():
        password = '12345'
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        conn.execute('INSERT INTO users (username, password, is_superuser) VALUES (?, ?, ?)',
                     ('admin', hashed_password, 1))
    conn.commit()
    conn.close()


@app.route('/home_page')
def all_posts():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts ORDER BY created_at DESC').fetchall()
    conn.close()
    is_superuser = current_user.is_superuser if current_user.is_authenticated else False
    return render_template('home.html', posts=posts, is_superuser=is_superuser)


@app.route('/posts/<slug>', strict_slashes=False)
def get_post(slug):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE slug = ?', (slug,)).fetchone()
    conn.close()
    return render_template('details.html', post=post)


@app.route('/new_post', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        rezume = request.form['rezume']
        info = request.form['info']
        created_at = datetime.now().isoformat()
        slug = generate_slug(title)
        conn = get_db_connection()
        conn.execute('INSERT INTO posts (title, rezume, info, created_at, slug) VALUES (?, ?, ?, ?, ?)',
                     (title, rezume, info, created_at, slug))
        conn.commit()
        conn.close()
        return redirect(url_for('all_posts'))
    return render_template('add_post.html')


@app.post('/posts/<slug>/delete')
def delete_post(slug: str):
    conn = get_db_connection()
    post = conn.execute('SELECT title, info, created_at FROM posts WHERE slug = ? ', (slug,)).fetchone()
    title = post['title']
    conn.execute('DELETE FROM posts WHERE slug = ?', (slug,))
    conn.commit()
    conn.close()
    return redirect(url_for('after_delete', title=title))


@app.get('/posts/deleted/<title>')
def after_delete(title: str):
    return render_template('after_delete.html', title=title)


@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        existing_user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if existing_user:
            flash('Пользователь с таким именем уже существует.')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            conn.execute('INSERT INTO users (username, password, is_superuser) VALUES (?, ?, ?)',
                         (username, hashed_password, 0))
            conn.commit()
            return redirect(url_for('login'))
        conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and bcrypt.check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['is_superuser'])
            login_user(user_obj)
            return redirect(url_for('all_posts'))
        else:
            flash('Неверное имя пользователя или пароль!')
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
