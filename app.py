from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'expenses.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(id=user[0], username=user[1], password=user[2])
    return None

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user_id = current_user.id
    db = get_db()
    c = db.cursor()

    if request.method == 'POST':
        budget = request.form.get('budget')
        credit = request.form.get('credit')
        if budget:
            c.execute("UPDATE users SET budget = ? WHERE id = ?", (budget, user_id))
            db.commit()
            flash("Budget updated!")
        elif credit:
            try:
                c.execute("SELECT budget FROM users WHERE id = ?", (user_id,))
                current_budget = c.fetchone()[0]
                new_budget = current_budget + float(credit)
                c.execute("UPDATE users SET budget = ? WHERE id = ?", (new_budget, user_id))
                db.commit()
                flash("Credit added!")
            except Exception as e:
                flash("Error adding credit!")

    # Get data
    c.execute("SELECT budget FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    budget = result[0] if result else 0

    c.execute("SELECT id, amount, category, note, date FROM expenses WHERE user_id = ?", (user_id,))
    expenses = c.fetchall()
    spent = sum([e["amount"] for e in expenses])
    remaining = budget - spent

    # Pie chart data
    pie_data = {}
    for e in expenses:
        category = e["category"]
        pie_data[category] = pie_data.get(category, 0) + e["amount"]

    return render_template('index.html', expenses=expenses, spent=spent, remaining=remaining, budget=budget, pie_data=pie_data)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            category = request.form['category']
            note = request.form['note']
            date = request.form['date']
            user_id = current_user.id
            db = get_db()
            c = db.cursor()
            c.execute("INSERT INTO expenses (user_id, amount, category, note, date) VALUES (?, ?, ?, ?, ?)",
                      (user_id, amount, category, note, date))
            db.commit()
            flash('Expense added!')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error: {e}')
            return redirect(url_for('add'))
    return render_template('add.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            user_obj = User(id=user[0], username=user[1], password=user[2])
            login_user(user_obj)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        try:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, budget) VALUES (?, ?, ?)", (username, password, 0))
            conn.commit()
            conn.close()
            flash('Signup successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists')
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    db = get_db()
    c = db.cursor()

    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        note = request.form['note']
        date = request.form['date']
        c.execute("""UPDATE expenses SET amount=?, category=?, note=?, date=? 
                     WHERE id=? AND user_id=?""", (amount, category, note, date, expense_id, current_user.id))
        db.commit()
        flash('Expense updated!')
        return redirect(url_for('index'))

    # GET method
    c.execute("SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, current_user.id))
    expense = c.fetchone()
    if not expense:
        flash("Expense not found.")
        return redirect(url_for('index'))

    return render_template('edit.html', expense=expense)

@app.route('/delete/<int:expense_id>')
@login_required
def delete_expense(expense_id):
    db = get_db()
    c = db.cursor()
    c.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, current_user.id))
    db.commit()
    flash('Expense deleted!')
    return redirect(url_for('index'))


# Auto-add missing columns
if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                budget REAL DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL NOT NULL,
                category TEXT,
                note TEXT,
                date TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
        conn.close()
    else:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        try: c.execute("ALTER TABLE expenses ADD COLUMN category TEXT")
        except: pass
        try: c.execute("ALTER TABLE expenses ADD COLUMN note TEXT")
        except: pass
        try: c.execute("ALTER TABLE expenses ADD COLUMN date TEXT")
        except: pass
        conn.commit()
        conn.close()

    app.run(debug=True)
