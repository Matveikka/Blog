from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import re

app = Flask(__name__)

first_request = True


@app.before_request
def before_first_request():
    global first_request
    if first_request:
        init_db()
        first_request = False


def generate_slug(title):
    slug = re.sub(r'[^a-zA-Z0-9-]', '-', title.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')
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


@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()
    return render_template('home.html', posts=posts)


@app.route('/<string:post_slug>', strict_slashes=False)
def get_post(post_slug):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE slug = ?', (post_slug,)).fetchone()
    conn.close()
    return render_template('details.html', post=post)


@app.route('/new', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        rezume = request.form['rezume']
        info = request.form['info']
        created_at = request.form['created_at']
        slug = generate_slug(title)
        conn = get_db_connection()
        conn.execute('INSERT INTO posts (title, rezume, info, created_at, slug) VALUES (?, ?, ?, ?, ?)',
                     (title, rezume, info, created_at, slug))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    return render_template('add_post.html')


@app.route('/delete/<string:post_slug>', methods=['POST'])
def delete_post(post_slug):
    conn = get_db_connection()
    post = conn.execute('DELETE FROM posts WHERE slug = ?', (post_slug,))
    conn.commit()
    conn.close()
    return render_template('after_delete.html', post=post)


if __name__ == '__main__':
    app.run()
