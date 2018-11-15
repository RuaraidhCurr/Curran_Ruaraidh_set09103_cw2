from flask import Flask, request, render_template, url_for, g, flash, redirect, session
from flask_mail import Mail, Message
from logging import FileHandler, WARNING
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
import sqlite3 as sql
import time, datetime

app = Flask(__name__)
file_handler = FileHandler("./static/errorlog.txt")
file_handler.setLevel(WARNING)

app.config.from_pyfile("config.cfg")
mail = Mail(app)
s = URLSafeTimedSerializer(app.config["SECRET_KEY"])


# app.logger.addHandler(file_handler)

# # ERROR LOG TEST
# @app.route("/errortest/")
# def errortest():
#     return 1 / 0

DATABASE = "cw2.db"

# Helper Functions
def get_db():
    db = getattr(g, 'db', None)
    if db is None:
        db = g._database = sql.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def verified_login(useremail, password):
    db = get_db()
    cur = db.cursor()
    find_user = ("select * from users")
    cur.execute(find_user)
    logdata = cur.fetchall()
    for x in logdata:
        y = x[1]
        p = x[2]
        z = s.loads(y, salt="emailConfirm")
        if z == useremail and p == password:
            logdata = 1
        else:
            logdata = None
    if logdata:
        return False
    else:
        return True

def new_user(useremail):
    db = get_db()
    userData = None
    cur = db.cursor()
    findUser = ("select useremail from users")
    cur.execute(findUser)
    data = cur.fetchall()
    for x in data:
        y = x[0]
        z = s.loads(y, salt="emailConfirm")
        if z == useremail:
            userData = 1
            break
    if userData:
        return True    
    else:
        return False

@app.route("/")
@app.route("/start/")
@app.route("/main/")
def route():
    if "useremail" in session:
        return redirect(url_for('home'))
    else:
        flash("Please Log in or register new user account")
        return redirect(url_for("login"))

# create account url
@app.route("/registeruser/")
@app.route("/newuser/")
@app.route("/createnewuser/")
@app.route("/register/")
def register():
    db = get_db()
    cur = db.cursor()
    find_user = ("select * from users")
    cur.execute(find_user)
    logdata = cur.fetchall()
    return render_template("register.html")

@app.route("/registeruser", methods=["GET", "POST"])
def registeruser():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        useremail = request.form["useremail"]
        password = request.form["password"]
        verPassword = request.form["verPassword"] 
        nameCombo = request.form["nameCombo"]
        nameCombo = nameCombo.split(" ")
        firstname = nameCombo[0]
        lastname = nameCombo[-1]
        token = s.dumps(useremail, salt="emailConfirm")
        if password == verPassword:
            if new_user(useremail):
                flash("account using that email has allready been made")
                print("failed")
                # redirects user to the login page
                return redirect(url_for("register"))
            else:
                cur.execute(
                    "INSERT INTO users (useremail, password, firstname, lastname) values (?,?,?,?)", (token, password, firstname, lastname))
                db.commit()
                print("success")
                msg = Message("Email Confimation", sender="cwtwoemail@gmail.com", recipients=[useremail])
                link = url_for("emailconfirm", token=token, _external=True)
                msg.body = "Welcome {}! Please click the link to verify your email! {}".format(firstname, link)
                mail.send(msg)
                flash("New User account Registered! Please verify email or Log-in")
            return redirect(url_for("login"))
        else:
            flash("passwords did not match, Please try again")
            return redirect("register")

    else:
        flash("Please Log in or register new user account")
    return redirect(url_for("login"))

@app.route("/emailconfirm/<token>")
def emailconfirm(token):
    db = get_db()
    cur = db.cursor()
    try:
        useremail = s.loads(token, salt="emailConfirm", max_age=3600)
    except SignatureExpired:
        cur.execute("DELETE FROM users WHERE useremail =?", [token])
        db.commit()
        return "<h1> The token is expired</h1>"
    cur.execute("UPDATE users SET confirmedemail = 1 WHERE useremail =?", [token])
    db.commit()
    flash("Email verified")
    return redirect(url_for("home"))

#Log in screen
@app.route("/login", methods=["GET", "POST"])
def login():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        print(request.form["useremail"], request.form["password"])
        # Checks to see if the sucessful login params were met
        if verified_login(request.form["useremail"], request.form["password"]):
            # stores flash message for sucseful login
            flash("Login Succseful")
            sessioninfo = ("select user_id, useremail, firstname, lastname, profilepic, confirmedemail from users")
            cur.execute(sessioninfo)
            logdata = cur.fetchall()
            firstname = None
            lastname = None
            for x in logdata:
                y = x[1]
                z = s.loads(y, salt="emailConfirm")
                if z == request.form["useremail"]:
                    user_id = x[0]
                    user_id = int(user_id)
                    firstname = x[2]
                    lastname = x[3]
                    profilepic = x[4]
                    confirmedemail = x[5]
            # stores useremail in useremail session
            session["user_id"] = user_id
            session["useremail"] = request.form["useremail"]
            session["firstname"] = str(firstname)
            session["lastname"] = str(lastname)
            session["profilepic"] = None
            session["confirmedemail"] = confirmedemail
            defaultpp = "static/media/default.png"
            if profilepic == None:
                session["profilepic"] = defaultpp
            else:
                session["profilepic"] = str(profilepic)

            print("login sucssful")
            return redirect(url_for("home"))
        else:
            print("invalid details")
            flash("Invalid useremail and/or passwords")
    return render_template("login.html")

@app.route("/main/logout/")
@app.route("/home/logout/")
@app.route("/logout")
def logout():
    # deletes the session
    session.pop("useremail", None)
    session.pop("user_id", None)
    # redirects to login
    return redirect(url_for("login"))

@app.route("/Home/")
@app.route("/home")
def home():
    # print(session["firstname"], session["lastname"], session["user_id"], session["profilepic"], session["confirmedemail"])
    return render_template("home.html")

@app.route("/profile/")
@app.route("/userProfile/")
@app.route("/Profile/")
@app.route("/Userprofile/")
@app.route("/userprofile/")
def userprofile():
    db = get_db()
    cur = db.cursor()
    if "useremail" in session:
        cur.execute("SELECT facebooklink, twitterlink, instagramlink, githublink, userblurb FROM users WHERE user_id =?", [session["user_id"]])
        linkdata = cur.fetchone()
        print(linkdata[0])
        facebooklink = linkdata[0]
        twitterlink = linkdata[1]
        instagramlink = linkdata[2]
        githublink = linkdata[3]
        blurb = linkdata[4]
        return render_template("userprofile.html", 
        profilepicurl=session["profilepic"],
        firstname=session["firstname"],
        lastname=session["lastname"],
        useremail=session["useremail"],
        blurb = blurb,
        facebooklink = facebooklink,
        twitterlink = twitterlink,
        instagramlink = instagramlink,
        githublink = githublink)
    else:
        flash("Please Log in or register new user account")
        return redirect(url_for("login"))

@app.route("/profilepic/")
@app.route("/profilepicupload/")
@app.route("/ProfilePic/")
@app.route("/Profilepic/")
@app.route("/profilePic/")
def profilepic():
    db = get_db()
    cur = db.cursor()
    if "useremail" in session:
        cur.execute("SELECT confirmedemail FROM users WHERE user_id = ?", [session["user_id"]])
        verified = cur.fetchone()
        verified = verified[0]
        print(verified)
        if verified == 0:
            flash("Please verify email to update profile picture")
            print("not verified")
            return redirect(url_for("userprofile"))
        else:
            return render_template("ppupload.html")
    else:
        flash("Please Log in or register new user account")
        return redirect(url_for("login"))

@app.route("/ppupload/", methods=["GET", "POST"])
def ppupload():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        f = request.files["profilepic"]
        name = f.filename
        # user_id = session["user_id"]
        f.save("static/media/{}".format(name))
        furl = str("static/media/{}".format(name))
        cur.execute(
            "UPDATE users SET profilepic = ? WHERE user_id =?", [furl, session["user_id"]])
        db.commit()
        cur.execute(
            "SELECT profilepic FROM users WHERE user_id =?", [session["user_id"]]
        )
        picurl = cur.fetchone()
        session["profilepic"] = str(picurl[0])
        flash("Profile Picutre Updated!")
        return redirect (url_for("home"))
    else:
        return redirect (url_for("userprofile"))

@app.route("/editprofile/")
def editprofile():
    db = get_db()
    cur = db.cursor()
    if "useremail" in session:
        cur.execute("SELECT facebooklink, twitterlink, instagramlink, githublink, userblurb FROM users WHERE user_id =?", [session["user_id"]])
        data = cur.fetchone()
        facebooklink = data[0]
        twitterlink = data[1]
        instagramlink = data[2]
        githublink = data[3]
        blurb = data[4]
        return render_template("editprofile.html",
        profilepicurl = session["profilepic"], 
        firstname=session["firstname"],
        lastname=session["lastname"],
        useremail=session["useremail"],
        blurb = blurb,
        facebooklink= facebooklink,
        twitterlink = twitterlink,
        instagramlink = instagramlink,
        githublink = githublink)
    else:
        flash("Please Log in or register new user account")
        return redirect(url_for("login"))

@app.route("/updateprofile", methods=["GET", "POST"])
def updateprofile():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        nameCombo = request.form["nameCombo"]
        nameCombo = nameCombo.split(" ")
        firstname = nameCombo[0]
        lastname = nameCombo[-1]
        facebooklink = request.form["facebooklink"]
        twitterlink = request.form["twitterlink"]
        instagramlink = request.form["instagramlink"]
        githublink = request.form["githublink"]
        blurb = request.form["blurb"]
        cur.execute("UPDATE users SET"
                    " firstname = ?,"
                    " lastname = ?,"
                    " facebooklink = ?,"
                    " twitterlink = ?,"
                    " instagramlink = ?,"
                    " githublink = ?,"
                    " userblurb = ?"
                    " WHERE user_id =?",
                    [firstname, lastname, facebooklink, twitterlink, instagramlink, githublink, blurb, session["user_id"]])
        db.commit()
        flash("User details updated")
        session["firstname"] = firstname
        session["lastname"] = lastname
        return redirect(url_for("userprofile"))
    else:
        return redirect(url_for('editprofile'))

@app.route("/changepass")
def changepass():
    if "useremail" in session:
        return render_template("changepass.html")
    else:
        flash("Please log in and try again")
        return redirect(url_for('login'))

@app.route("/changepassword/", methods=["GET","POST"])
def changepassword():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        oldpass = request.form["oldpass"]
        password = request.form["password"]
        verpassword = request.form["verpassword"]
        cur.execute("SELECT password FROM users WHERE user_id = ?", [session["user_id"]])
        veroldpass = cur.fetchone()
        veroldpass = veroldpass[0]
        print(password)
        print(verpassword)
        print(oldpass)
        print(veroldpass)
        if oldpass == veroldpass and password == verpassword:
            cur.execute("UPDATE users SET password = ? WHERE user_id = ?", [verpassword, session["user_id"]])
            db.commit()
            flash("Password Updated!")
            return redirect(url_for('userprofile'))
        else:
            flash("passwords did not match, please try again")
            print(flash)
            return redirect(url_for('changepass'))
    else:
        return redirect(url_for('home'))

@app.route("/blogpost/")
def blogpost():
    db = get_db()
    cur = db.cursor()
    if "useremail" in session:
        cur.execute("SELECT confirmedemail FROM users WHERE user_id = ?", [session["user_id"]])
        verified = cur.fetchone()
        verified = verified[0]
        if verified == 0:
            print("not verified")
            flash("you need to verify your email before posting")
            return redirect(url_for("home"))
        else:
            print("verified")
            return render_template('blogpost.html')
    else:
        flash("Please log in and try again")
        return redirect(url_for('login'))

@app.route("/uploadpost/", methods=["GET", "POST"])
def uploadpost():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        seconds = time.time()
        auther = session["firstname"] + " " + session["lastname"]
        timestamp = datetime.datetime.fromtimestamp(seconds).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute(
        "INSERT INTO posts (user_id, title, content, auther, timestamp) values (?,?,?,?,?)", (session["user_id"], title, content, auther, timestamp))
        db.commit()
        print("success")
        return (timestamp)
    else:
        return redirect(url_for("home"))

@app.route("/viewallposts/")
def viewallposts():
    db = get_db()
    db.row_factory = sql.Row
    cur = db.cursor()
    cur.execute("SELECT * FROM posts")
    rows = cur.fetchall()
    return render_template("viewallposts.html", rows = rows)

@app.route("/viewpost/<post_num>")
def viewpost(post_num):
    db = get_db()
    cur = db.cursor()
    post_num = int(post_num)
    cur.execute("SELECT * FROM posts WHERE post_num = ?", [post_num])
    postdata = cur.fetchone()
    user_id = None
    if "useremail" in session:
        user_id = session["user_id"]
    else:
        user_id = None
    session["post_num"] = postdata[0]
    return render_template("viewpost.html", postdata=postdata, user_id = user_id)

@app.route("/editpost/")
def editpost():
    if session["post_num"] == None:
        flash("Please edit your own posts")
        return redirect(url_for("viewallposts"))
    else:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM posts WHERE post_num = ?", [session["post_num"]])
        postdata = cur.fetchone()
        print(session["post_num"])
        print(postdata[0])
        return render_template('blogpostedit.html', postdata = postdata)

@app.route("/editblogpost/", methods=["GET", "POST"])
def editblogpost():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        seconds = time.time()
        timestamp = datetime.datetime.fromtimestamp(seconds).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("UPDATE posts SET title = ?, content = ?, timestamp = ?  WHERE post_num = ?", [title, content, timestamp, session["post_num"]])
        db.commit()
        session.pop("post_num", None)
        flash("Post Updated")
        print("post updated")
        return redirect(url_for("viewallposts"))
    else:
        return redirect(url_for('editpost'))

@app.route("/user/<user_id>")
def user(user_id):
    db = get_db()
    cur = db.cursor()
    user_id = int(user_id)
    cur.execute("SELECT * FROM users WHERE user_id = ?", [user_id])
    userdata = cur.fetchone()
    db.row_factory = sql.Row
    cur.execute("SELECT * FROM posts WHERE user_id = ?", [user_id])
    rows = cur.fetchall()
    print(rows)
    return render_template("profiles.html", userdata=userdata, rows=rows)

@app.route("/queryblogs/")
def queryblogs():
    return render_template("queryblogs.html")

@app.route("/querypost/", methods=["GET","POST"])
def querypost():
    db = get_db()
    db.row_factory = sql.Row
    cur = db.cursor()
    if request.method == "POST":
        title = request.form["title"]
        timestamp = request.form["timestamp"]
        auther = request.form["auther"]
        cur.execute("SELECT * FROM posts WHERE (lower(title) IS null or lower(title) LIKE '%' ||?|| '%') AND"
                    "(timestamp IS null or timestamp LIKE '%' ||?|| '%') AND"
                    "(lower(auther) IS NULL or lower(auther) LIKE '%' ||?|| '%')", [title.lower(), timestamp, auther])
        rows = cur.fetchall()
        return render_template("viewallposts.html", rows = rows)


@app.route("/chat/<chatnumber>", methods=["GET","POST"])
def chat(chatnumber):
    db = get_db()
    cur = db.cursor()
    chatnumber = int(chatnumber)
    print(chatnumber)
    if request.method == "POST":
        content = request.form["chatcontent"]
        cur.execute("SELECT content FROM chat WHERE chat_num = ?", [chatnumber])
        oldcontent = cur.fetchone()
        oldcontent = oldcontent[0]
        newcontent = oldcontent + "\|/" + session["firstname"] + " " + session["lastname"] + ": " + content
        cur.execute("UPDATE chat SET content = ?", [newcontent])
        db.commit()
        print("success")
        return redirect(url_for('chat', chatnumber = chatnumber))
    if request.method == "GET":
        cur.execute("SELECT * FROM chat WHERE chat_num = ?", [chatnumber])
        chatdata = cur.fetchone()
        user_id1 = int(chatdata[1])
        user_id2 = int(chatdata[2])
        if session["user_id"] == user_id1 or user_id2:
            print("success")
            allmessages = chatdata[3]
            print(allmessages)
            messages = allmessages.split("\|/")
            print(messages)
            return render_template("chat.html", chatdata = chatdata, messages = messages)
        else:
            print("failed")
            return redirect(url_for('home'))


@app.route("/searchpeople/")
def searchpeople():
    return render_template("searchpeople.html")

@app.route("/peoplequery/", methods=["GET","POST"])
def peoplequery():
    db = get_db()
    db.row_factory = sql.Row
    cur = db.cursor()
    if request.method == "POST":
        joinedname = request.form["name"]
        print(joinedname)
        joinedname = joinedname.split(" ")
        firstname = joinedname[0]
        lastname = joinedname[-1]
        cur.execute("SELECT user_id, firstname, lastname, profilepic, userblurb FROM users WHERE (lower(firstname) IS null or lower(firstname) LIKE '%' ||?|| '%') AND"
                    "(lower(lastname) IS null or lower(lastname) LIKE '%' ||?|| '%')", [firstname.lower(), lastname.lower()])
        rows = cur.fetchall()
        print(rows)
        flash("Search results:")
        return render_template("usersearchresults.html", rows = rows)
    else:
        return redirect(url_for('home'))

@app.route("/viewchats/")
def viewchats():
    db = get_db()
    db.row_factory = sql.Row
    cur = db.cursor()
    cur.execute("SELECT chat_num, user1_id, user2_id from chat WHERE user1_id = ? OR user2_id = ?", [session["user_id"], session["user_id"]])
    rows = cur.fetchall()
    print(rows)
    print(session["user_id"])
    return render_template("viewchats.html", rows = rows)

@app.route("/createchat/", methods=["GET","POST"])
def createchat():
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        print("POST")
        user1_id = int(session["user_id"])
        user2_id = request.form["user_id"]
        user2_id = int(user2_id)
        cur.execute("INSERT INTO chat (user1_id, user2_id) values (?,?)", (user1_id, user2_id))
        db.commit()
        print("success")
        cur.execute("SELECT chat_num FROM chat WHERE user1_id = ? AND user2_id = ?", [user1_id, user2_id])
        chatnumber = cur.fetchone()
        chatnumber = chatnumber[0]
        return redirect(url_for('chat', chatnumber = chatnumber))
    else:
        print("failed")
        return redirect(url_for('home'))

# Error pages
@app.errorhandler(404)
def page_not_found(error):
    if "useremail" in session:
        flash("Sorry that page was not found")
        return redirect(url_for('home'))
    else:
        flash("Please log in and try again")
        return redirect(url_for('login'))

if __name__ == "__main__":
    # urandom(12) passkey for sessions and cookies
    app.secret_key = "]\x17\xa7x\xba4[\\\xb9\x12\xae\x85"
    app.run(debug=True)