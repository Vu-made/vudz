import sqlite3
from flask import Flask, render_template, request, send_file, Response, session, redirect, url_for , jsonify
import os , json 

app = Flask(__name__)

# Đọc secret key từ file
app.secret_key = os.environ.get("SECRET_KEY","hoangvudangghetxautinh")


dbfile = "meta.db"

# Tạo bảng nếu chưa có
with sqlite3.connect("account.db") as conn:
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tai_khoan ( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            avatar BLOB,
            full_name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            interest TEXT DEFAULT '',
            address TEXT DEFAULT '',
            date TEXT DEFAULT '',
            target TEXT DEFAULT ''
        )
    ''')

with sqlite3.connect ( dbfile ) as conn : 
    conn.execute('''
        CREATE TABLE IF NOT EXISTS meta(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_exercise TEXT DEFAULT '',
            exercise TEXT DEFAULT '',
            testcase TEXT DEFAULT ''
        )
    ''')

# =========================== LOGIC ===============================

def create_account(username, password, avatar, full_name, email, phone):
    try:
        with sqlite3.connect("account.db") as conn:
            conn.execute("""
                INSERT INTO tai_khoan 
                (username, password, avatar, full_name, email, phone) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, password, avatar, full_name, email, phone))
            print("✅ Thêm tài khoản thành công")
    except sqlite3.IntegrityError:
        print("❌ Tài khoản đã tồn tại")

def get_profile_html(is_logged_in):
    if not is_logged_in:
        return '''
            <div id="nav-profile"><a href="/login">Đăng nhập</a></div>
        '''
    else:
        return f'''
           <div id="nav-profile"><a href="/profile">Tài khoản</a></div>
        '''

def push_exercise ( exercise , testcase , code_exercise ) : 
    with sqlite3 .connect ( dbfile ) as conn :
        conn.execute("""
            INSERT INTO meta ( code_exercise , exercise , testcase )
            VALUES ( ? , ? , ? )
        """ , (code_exercise , exercise , testcase) )
    
def get_exercise( code ) : 
    with sqlite3.connect(dbfile) as conn : 
        cursor = conn.execute("SELECT * FROM meta WHERE code_exercise=?" , (code,) ) 
        row = cursor.fetchall() 
        return row

# ========================== ROUTES ===============================

@app.route('/')
def home():
    problems = ''
    with sqlite3.connect(dbfile) as conn : 
        row = conn.execute('SELECT * FROM meta').fetchall()
        # print ( row[2] )
        for i in range ( len ( row ) - 1 , -1 , -1 ) :
            data = json.loads( row[i][2] )
            q = f'''
                <tr>
                  <td>{ row[i][1] }</td>
                  <td>{ data["titles"] }</td>
                  <td><button class="view-button" onclick="window.location.href='/render_exercise/{row[i][1]}'">Xem</button></td>
                </tr>
            '''
            problems += q 

    return render_template("home.html",
        username=session.get("username"),
        user_id=session.get("user_id"),
        profile=get_profile_html("username" in session),
        problem_list=problems
    )

@app.route('/register')
def register_page():
    return render_template("register.html")

@app.route("/submit", methods=["POST"])
def login_and_register():
    action = request.form.get("action")
    return login() if action == "login" else register()

@app.route('/login')
def login_page():
    return render_template("login.html", error=None, username="", password="")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/avatar")
def get_avatar():
    if "user_id" not in session:
        return "Không có tài khoản", 404
    with sqlite3.connect("account.db") as conn:
        cursor = conn.execute("SELECT avatar FROM tai_khoan WHERE id=?", (session["user_id"],))
        row = cursor.fetchone()
        if row and row[0]:
            return Response(row[0], mimetype="image/jpeg")
        return "Không có ảnh", 404

@app.route('/profile')
def get_profile() :
     with sqlite3.connect("account.db") as conn:
            cursor = conn.execute("""
                SELECT full_name, email, interest, address, date, target 
                FROM tai_khoan WHERE id=?
            """, (session.get("user_id"),))
            row = cursor.fetchone()
            if row:
                full_name, email, interest, address, date, target = row
                return render_template (
                    "profile.html" , 
                    full_name=full_name,
                    interest=interest,
                    email=email,
                    address=address,
                    date=date,
                    target=target
                )

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect(url_for("login_page"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        interest = request.form.get("interest", "")
        address = request.form.get("address", "")
        date = request.form.get("date", "")
        target = request.form.get("target", "")
        avatar = request.files.get("avatar")

        with sqlite3.connect("account.db") as conn:
            if avatar and avatar.filename:
                conn.execute("""
                    UPDATE tai_khoan SET
                        full_name=?, email=?, phone=?, interest=?,
                        address=?, date=?, target=?, avatar=?
                    WHERE id=?
                """, (full_name, email, phone, interest, address, date, target, avatar.read(), session["user_id"]))
            else:
                conn.execute("""
                    UPDATE tai_khoan SET
                        full_name=?, email=?, phone=?, interest=?,
                        address=?, date=?, target=?
                    WHERE id=?
                """, (full_name, email, phone, interest, address, date, target, session["user_id"]))

        return redirect(url_for("home"))

    with sqlite3.connect("account.db") as conn:
        cursor = conn.execute("""
            SELECT full_name, email, phone, interest, address, date, target 
            FROM tai_khoan WHERE id=?
        """, (session["user_id"],))
        row = cursor.fetchone()

    if row:
        return render_template("edit_profile.html",
            full_name=row[0], email=row[1], phone=row[2],
            interest=row[3], address=row[4], date=row[5], target=row[6]
        )

    return "Không tìm thấy tài khoản", 404

@app.route('/create-exercise')
def create_exercise():
    return render_template ( "create_exercise.html" )

@app.route('/render_exercise/<id>')
def render_exercise( id ) :
    return render_template ("render_exercise.html" , id=id )

@app.route('/api/render_exercise', methods=['POST'])
def get_info_exercise() :
    code_exercise = request.get_json().get('id',None)
    # print ( code_exercise )
    with sqlite3.connect(dbfile) as conn : 
        row = conn.execute("SELECT exercise FROM meta WHERE code_exercise=?" , (code_exercise,)).fetchall()
        return jsonify ( json.loads(row[0][0]) )

@app.route('/api/submit_exercise', methods=['POST'])
def handle_submission():
    data = request.get_json()

    code_exercise = data.get("new_id","")
    titles = data.get("titles", [])
    bodies = data.get("bodies", [])
    examples = data.get("examples", [])
    time_limit = data.get("timeLimit", "")
    point = data.get("point","")
    tests = data.get("tests", {})

    exercise = {
         "titles" : titles,
         "bodies" : bodies,
         "examples" : examples,
         "time_limit" : time_limit,
         "point" : point,
         "author" : session["username"]
    }

    testcase = {
        "time_limit" : time_limit,
        "point" : point,
        "tests" : tests
    }


    push_exercise (
        json.dumps(exercise,ensure_ascii=False),
        json.dumps (testcase , ensure_ascii=False),
        code_exercise
    )
    # Bạn có thể xử lý lưu dữ liệu tại đây

    # print ( json.dumps(testcase, indent=4, ensure_ascii=False))

    return jsonify({"message": "Đã nhận bài tập!"})



# ====================== FORM HANDLING ============================

def login():
    data = {
        "username": request.form.get("username"),
        "password": request.form.get("password"),
        "remember": request.form.get("remember")
    }
    with sqlite3.connect("account.db") as conn:
        cursor = conn.execute("SELECT * FROM tai_khoan WHERE username=?", (data["username"],))
        user = cursor.fetchone()

    if user:
        if user[2] == data["password"]:
            session["username"] = data["username"]
            session["user_id"] = user[0]
            if not data["remember"]:
                session.permanent = False
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Sai mật khẩu", **data)
    else:
        return render_template("login.html", error="Tài khoản chưa tồn tại", **data)

def register():
    data = {
        "username": request.form.get("username"),
        "password": request.form.get("password"),
        "confirm_password": request.form.get("confirm_password"),
        "full_name": request.form.get("fullname", ""),
        "email": request.form.get("email", ""),
        "phone": request.form.get("phone", ""),
        "avatar": request.files.get("avatar")
    }

    if data["password"] != data["confirm_password"]:
        return render_template("register.html", error="Mật khẩu không khớp!", **data)

    with sqlite3.connect("account.db") as conn:
        cursor = conn.execute("SELECT * FROM tai_khoan WHERE username=?", (data["username"],))
        if cursor.fetchone():
            return render_template("register.html", error="Người dùng này đã tồn tại!", **data)

    avatar_data = data["avatar"].read() if data["avatar"] else open("./access/avatar.jpg", "rb").read()

    create_account(
        data["username"],
        data["password"],
        avatar_data,
        data["full_name"],
        data["email"],
        data["phone"]
    )
    return render_template("login.html", error="Tạo tài khoản thành công! Mời bạn đăng nhập", username=data["username"], password="")

# ======================== MAIN ==================================

if __name__ == "__main__":
    # print ( get_exercise("mbsxq5a99jclpda7f"))
    if not os.path.exists("./access/avatar.jpg"):
        print("⚠️ File avatar.jpg không tồn tại!")
    app.run(debug=True, port=5000)
