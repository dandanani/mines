from flask import Flask, render_template, redirect, request, jsonify, session, url_for, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(days=7)

# MySQL Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'your_password'
app.config['MYSQL_DB'] = 'MinesweeperApp'
mysql = MySQL(app)

# Game state variables
game_data = {
    "bet_amount": 0,
    "num_mines": 0,
    "board": [],
    "rows": 5,
    "cols": 5,
    "selected_cells": [],
    "game_active": False,
}

# Authentication Middleware
def login_required(func):
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials!", "danger")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        mobile_number = request.form["mobile_number"]
        otp = random.randint(1000, 9999)

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s OR mobile_number = %s", (username, mobile_number))
        if cursor.fetchone():
            flash("Username or Mobile Number already exists!")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password, mobile_number, otp) VALUES (%s, %s, %s, %s)",
            (username, hashed_password, mobile_number, otp),
        )
        mysql.connection.commit()
        cursor.close()

        flash(f"Registration successful! Your OTP is {otp} (for demo purposes only).")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/")
@login_required
def index():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT money FROM users WHERE id = %s", (session['user_id'],))
    user_data = cursor.fetchone()
    money = user_data[0] if user_data else 0
    return render_template("index.html", money=money)

@app.route("/start_game", methods=["POST"])
@login_required
def start_game():
    data = request.json
    bet_amount = data.get("bet_amount")
    num_mines = data.get("num_mines")

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT money FROM users WHERE id = %s", (session['user_id'],))
    money = cursor.fetchone()[0]

    if bet_amount > money:
        return jsonify({"error": "Not enough money!"}), 400

    # Deduct money & create board
    cursor.execute("UPDATE users SET money = money - %s WHERE id = %s", (bet_amount, session['user_id']))
    mysql.connection.commit()

    board = generate_board(game_data["rows"], game_data["cols"], num_mines)
    game_data.update({
        "bet_amount": bet_amount,
        "num_mines": num_mines,
        "board": board,
        "selected_cells": [],
        "game_active": True,
    })

    return jsonify({
        "message": "Game started!",
        "board": board,
        "money": money - bet_amount
    })

@app.route("/click_cell", methods=["POST"])
@login_required
def click_cell():
    if not game_data["game_active"]:
        return jsonify({"error": "No active game!"}), 400

    data = request.json
    row, col = int(data.get("row")), int(data.get("col"))

    if (row, col) in game_data["selected_cells"]:
        return jsonify({"error": "Cell already selected!"}), 400

    game_data["selected_cells"].append((row, col))

    result = "safe" if game_data["board"][row][col] != "mine" else "mine"

    return jsonify({"result": result})

@app.route("/submit_selection", methods=["POST"])
@login_required
def submit_selection():
    if not game_data["game_active"]:
        return jsonify({"error": "No active game!"}), 400

    data = request.json
    selected_cells = [(int(row), int(col)) for row, col in data.get("selected_cells", [])]

    # Check if user clicked a mine
    for row, col in selected_cells:
        if game_data["board"][row][col] == "mine":
            game_data["game_active"] = False
            return jsonify({
                "result": "lost",
                "money": 0,
                "revealed_board": reveal_board()
            })

    # Calculate winnings
    total_safe_cells = game_data["rows"] * game_data["cols"] - game_data["num_mines"]
    correct_clicks = len(selected_cells)
    multiplier = correct_clicks / total_safe_cells
    winnings = round(game_data["bet_amount"] * (1 + multiplier))

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE users SET money = money + %s WHERE id = %s", (winnings, session['user_id']))
    mysql.connection.commit()

    cursor.execute("SELECT money FROM users WHERE id = %s", (session['user_id'],))
    new_balance = cursor.fetchone()[0]

    game_data["game_active"] = False

    return jsonify({
        "result": "won",
        "money": winnings,
        "new_balance": new_balance,
        "board": game_data["board"]
    })


def generate_board(rows, cols, num_mines):
    board = [["star" for _ in range(cols)] for _ in range(rows)]
    for _ in range(num_mines):
        while True:
            r, c = random.randint(0, rows - 1), random.randint(0, cols - 1)
            if board[r][c] != "mine":
                board[r][c] = "mine"
                break
    return board

def reveal_board():
    return [[cell if cell == "mine" else "safe" for cell in row] for row in game_data["board"]]

if __name__ == "__main__":
    app.run(debug=True)
