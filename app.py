from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "silverconnect-secret-2025")

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["silverconnect"]
volunteers_col = db["volunteers"]
users_col = db["users"]
chats_col = db["chats"]
chat_messages_col = db["chat_messages"]

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if "user_id" not in session:
        return None
    role = session.get("role")
    if role == "volunteer":
        v = volunteers_col.find_one({"_id": ObjectId(session["user_id"])})
        if v:
            v["_id"] = str(v["_id"])
            v["role"] = "volunteer"
        return v
    else:
        u = users_col.find_one({"_id": ObjectId(session["user_id"])})
        if u:
            u["_id"] = str(u["_id"])
            u["role"] = "user"
        return u

@app.route("/")
def home():
    volunteers = list(volunteers_col.find({}, {"password": 0}))
    for v in volunteers:
        v["_id"] = str(v["_id"])
    current_user = get_current_user()
    return render_template("index.html", volunteers=volunteers, current_user=current_user)

@app.route("/about")
def about():
    current_user = get_current_user()
    return render_template("about.html", current_user=current_user)

@app.route("/helpers")
def helpers():
    neighborhood = request.args.get("neighborhood", "")
    skill = request.args.get("skill", "")
    query = {}
    if neighborhood:
        query["neighborhood"] = {"$regex": neighborhood, "$options": "i"}
    if skill:
        query["skills"] = {"$in": [skill]}
    volunteers = list(volunteers_col.find(query, {"password": 0}))
    for v in volunteers:
        v["_id"] = str(v["_id"])
    neighborhoods = volunteers_col.distinct("neighborhood")
    all_skills = ["Smartphones", "Wi-Fi Setup", "Video Calls", "Email", "Tablets", "Social Media", "Online Banking", "Streaming"]
    current_user = get_current_user()
    return render_template("helpers.html", volunteers=volunteers, neighborhoods=neighborhoods,
                           all_skills=all_skills, selected_neighborhood=neighborhood,
                           selected_skill=skill, current_user=current_user)

@app.route("/contact")
def contact():
    volunteers = list(volunteers_col.find({}, {"_id": 1, "name": 1, "neighborhood": 1}))
    for v in volunteers:
        v["_id"] = str(v["_id"])
    preselect = request.args.get("volunteer", "")
    current_user = get_current_user()
    return render_template("contact.html", volunteers=volunteers, preselect=preselect, current_user=current_user)

# AUTH PAGES 

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("profile"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "user")
        if role == "volunteer":
            user = volunteers_col.find_one({"email": email})
            if user and check_password_hash(user.get("password", ""), password):
                session["user_id"] = str(user["_id"])
                session["role"] = "volunteer"
                session["name"] = user["name"]
                return redirect(url_for("profile"))
            else:
                error = "Invalid email or password for volunteer account."
        else:
            user = users_col.find_one({"email": email})
            if user and check_password_hash(user.get("password", ""), password):
                session["user_id"] = str(user["_id"])
                session["role"] = "user"
                session["name"] = user["name"]
                return redirect(url_for("profile"))
            else:
                error = "Invalid email or password for user account."
    return render_template("login.html", error=error)

@app.route("/register/user", methods=["GET", "POST"])
def register_user():
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not email or not password:
            error = "Please fill in all required fields."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif users_col.find_one({"email": email}):
            error = "An account with this email already exists."
        else:
            user = {
                "name": name,
                "email": email,
                "phone": phone,
                "password": generate_password_hash(password),
                "bio": "",
                "neighborhood": "",
                "created_at": datetime.utcnow().isoformat(),
                "last_active": datetime.utcnow().isoformat()
            }
            result = users_col.insert_one(user)
            session["user_id"] = str(result.inserted_id)
            session["role"] = "user"
            session["name"] = name
            return redirect(url_for("profile"))
    return render_template("register_user.html", error=error)

@app.route("/register/volunteer", methods=["GET", "POST"])
def register_volunteer():
    error = None
    all_skills = ["Smartphones", "Wi-Fi Setup", "Video Calls", "Email", "Tablets", "Social Media", "Online Banking", "Streaming"]
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        neighborhood = request.form.get("neighborhood", "").strip()
        availability = request.form.get("availability", "").strip()
        bio = request.form.get("bio", "").strip()
        skills = request.form.getlist("skills")
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not email or not neighborhood or not password:
            error = "Please fill in all required fields."
        elif password != confirm:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif volunteers_col.find_one({"email": email}):
            error = "A volunteer account with this email already exists."
        else:
            volunteer = {
                "name": name,
                "email": email,
                "phone": phone,
                "neighborhood": neighborhood,
                "availability": availability,
                "bio": bio,
                "skills": skills,
                "password": generate_password_hash(password),
                "active": True,
                "created_at": datetime.utcnow().isoformat()
            }
            result = volunteers_col.insert_one(volunteer)
            session["user_id"] = str(result.inserted_id)
            session["role"] = "volunteer"
            session["name"] = name
            return redirect(url_for("profile"))
    return render_template("register_volunteer.html", error=error, all_skills=all_skills)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/profile")
@login_required
def profile():
    current_user = get_current_user()
    if not current_user:
        session.clear()
        return redirect(url_for("login"))
    if current_user["role"] == "volunteer":
        my_chats = list(chats_col.find({"volunteer_id": session["user_id"]}).sort("last_message_at", -1))
        for c in my_chats:
            c["_id"] = str(c["_id"])
            u = users_col.find_one({"_id": ObjectId(c["user_id"])})
            c["user_name"] = u["name"] if u else "User"
        return render_template("profile_volunteer.html", current_user=current_user, chats=my_chats)
    else:
        my_chats = list(chats_col.find({"user_id": session["user_id"]}).sort("last_message_at", -1))
        for c in my_chats:
            c["_id"] = str(c["_id"])
            v = volunteers_col.find_one({"_id": ObjectId(c["volunteer_id"])})
            c["volunteer_name"] = v["name"] if v else "Volunteer"
            c["volunteer_neighborhood"] = v["neighborhood"] if v else ""
        return render_template("profile_user.html", current_user=current_user, chats=my_chats)

@app.route("/profile/edit", methods=["POST"])
@login_required
def edit_profile():
    data = request.json or {}
    role = session.get("role")
    if role == "volunteer":
        update = {}
        for field in ["name", "phone", "neighborhood", "availability", "bio"]:
            if field in data:
                update[field] = data[field]
        if "skills" in data:
            update["skills"] = data["skills"]
        volunteers_col.update_one({"_id": ObjectId(session["user_id"])}, {"$set": update})
        if "name" in update:
            session["name"] = update["name"]
    else:
        update = {}
        for field in ["name", "phone", "neighborhood", "bio"]:
            if field in data:
                update[field] = data[field]
        users_col.update_one({"_id": ObjectId(session["user_id"])}, {"$set": update})
        if "name" in update:
            session["name"] = update["name"]
    return jsonify({"success": True})


@app.route("/chat/<volunteer_id>")
@login_required
def chat(volunteer_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login"))
    if current_user["role"] == "volunteer":
        return redirect(url_for("profile"))
    v = volunteers_col.find_one({"_id": ObjectId(volunteer_id)}, {"password": 0})
    if not v:
        return redirect(url_for("helpers"))
    v["_id"] = str(v["_id"])
    user_id = session["user_id"]
    existing_chat = chats_col.find_one({"user_id": user_id, "volunteer_id": volunteer_id})
    if not existing_chat:
        new_chat = {
            "user_id": user_id,
            "volunteer_id": volunteer_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_message_at": datetime.utcnow().isoformat()
        }
        result = chats_col.insert_one(new_chat)
        chat_id = str(result.inserted_id)
    else:
        chat_id = str(existing_chat["_id"])
    messages = list(chat_messages_col.find({"chat_id": chat_id}).sort("sent_at", 1))
    for m in messages:
        m["_id"] = str(m["_id"])
    return render_template("chat.html", volunteer=v, current_user=current_user,
                           chat_id=chat_id, messages=messages)

@app.route("/chat/room/<chat_id>")
@login_required
def chat_room(chat_id):
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for("login"))
    chat = chats_col.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        return redirect(url_for("profile"))
    uid = session["user_id"]
    role = session.get("role")
    if role == "volunteer" and chat["volunteer_id"] != uid:
        return redirect(url_for("profile"))
    if role == "user" and chat["user_id"] != uid:
        return redirect(url_for("profile"))
    if role == "volunteer":
        u = users_col.find_one({"_id": ObjectId(chat["user_id"])})
        other_name = u["name"] if u else "User"
        other = {"name": other_name, "role": "user"}
    else:
        v = volunteers_col.find_one({"_id": ObjectId(chat["volunteer_id"])}, {"password": 0})
        v["_id"] = str(v["_id"])
        other_name = v["name"] if v else "Volunteer"
        other = v
        other["role"] = "volunteer"
    messages = list(chat_messages_col.find({"chat_id": chat_id}).sort("sent_at", 1))
    for m in messages:
        m["_id"] = str(m["_id"])
    return render_template("chat.html", volunteer=other, current_user=current_user,
                           chat_id=chat_id, messages=messages)

@app.route("/api/chats/<chat_id>/messages")
@login_required
def get_chat_messages(chat_id):
    msgs = list(chat_messages_col.find({"chat_id": chat_id}).sort("sent_at", 1))
    for m in msgs:
        m["_id"] = str(m["_id"])
    return jsonify(msgs)


@app.route("/api/contact", methods=["POST"])
def save_contact_message():
    data = request.json
    required = ["name", "email", "subject", "message"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400
    general_col = db["general_messages"]
    msg = {
        "name": data["name"].strip(),
        "email": data["email"].strip().lower(),
        "type": data.get("type", "General"),
        "subject": data["subject"].strip(),
        "message": data["message"].strip(),
        "sent_at": datetime.utcnow().isoformat(),
        "read": False
    }
    general_col.insert_one(msg)
    return jsonify({"success": True}), 201


@socketio.on("join")
def on_join(data):
    chat_id = data.get("chat_id")
    if not chat_id:
        return
    join_room(chat_id)
    emit("status", {"msg": "Connected to chat."}, room=chat_id)

@socketio.on("leave")
def on_leave(data):
    chat_id = data.get("chat_id")
    if chat_id:
        leave_room(chat_id)

@socketio.on("send_message")
def handle_message(data):
    chat_id = data.get("chat_id")
    sender_id = data.get("sender_id")
    sender_name = data.get("sender_name")
    sender_role = data.get("sender_role")
    text = data.get("text", "").strip()
    if not chat_id or not text:
        return
    msg = {
        "chat_id": chat_id,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "sender_role": sender_role,
        "text": text,
        "sent_at": datetime.utcnow().isoformat()
    }
    chat_messages_col.insert_one(msg)
    msg["_id"] = str(msg["_id"])
    chats_col.update_one({"_id": ObjectId(chat_id)}, {"$set": {"last_message_at": msg["sent_at"]}})
    emit("new_message", msg, room=chat_id)

if __name__ == "__main__":
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
