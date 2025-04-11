from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def init_db():
    with sqlite3.connect('expenses.db') as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                category TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS budget (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total REAL NOT NULL
            )
        ''')

@app.route('/')
def index():
    with sqlite3.connect('expenses.db') as conn:
        expenses = conn.execute('SELECT * FROM expenses ORDER BY date DESC').fetchall()
        total_spent = conn.execute('SELECT SUM(amount) FROM expenses WHERE amount > 0').fetchone()[0] or 0
        categories = conn.execute('SELECT category, SUM(amount) FROM expenses WHERE amount > 0 GROUP BY category').fetchall()
        budget_row = conn.execute('SELECT total FROM budget WHERE id = 1').fetchone()
        budget = budget_row[0] if budget_row else 0
        remaining = budget - total_spent
        labels = [c[0] for c in categories]
        data = [c[1] for c in categories]
    return render_template('index.html', expenses=expenses, total_spent=total_spent, remaining=remaining, budget=budget, labels=labels, data=data)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        title = request.form['title']
        amount = float(request.form['amount'])
        date = request.form['date']
        category = request.form['category']
        with sqlite3.connect('expenses.db') as conn:
            conn.execute('INSERT INTO expenses (title, amount, date, category) VALUES (?, ?, ?, ?)',
                         (title, amount, date, category))
        return redirect('/')
    return render_template('add.html')

@app.route('/set-budget', methods=['POST'])
def set_budget():
    total = float(request.form['total'])
    with sqlite3.connect('expenses.db') as conn:
        conn.execute('INSERT OR REPLACE INTO budget (id, total) VALUES (1, ?)', (total,))
    return redirect('/')

@app.route('/add_credit', methods=['POST'])
def add_credit():
    amount = float(request.form['amount'])
    with sqlite3.connect('expenses.db') as conn:
        conn.execute('INSERT INTO expenses (title, amount, date, category) VALUES (?, ?, DATE("now"), ?)',
                     ('Credit', -amount, 'Income'))
    return redirect('/')

@app.route('/delete/<int:id>')
def delete_expense(id):
    with sqlite3.connect('expenses.db') as conn:
        conn.execute('DELETE FROM expenses WHERE id = ?', (id,))
    return redirect('/')

@app.route('/clear')
def clear_all():
    with sqlite3.connect('expenses.db') as conn:
        conn.execute('DELETE FROM expenses')
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
