from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, get_flashed_messages, jsonify
)
from flask_mail import Mail, Message as MailMessage

from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required
)

from functools import wraps
from models import (db, Preferences,  User,
                    COMMITMENT_LEVELS, commitment_level_label,
                    CollaborationRequest,
                    ChatRoom, Message,
                    Course, PreferenceCourse,
                    Report, ReportMessage, Block, AlgorithmSettings, seed_algorithm_settings)

from matching import find_ml_matches
from sqlalchemy import func
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
import secrets
import json
import os
import socket

from dotenv import load_dotenv

load_dotenv()



app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "SMART_MATCHMAKER_DATABASE_URI",
    "sqlite:///app.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.jinja_env.filters["commitment_label"] = commitment_level_label
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False


# Mail Configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False

app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")

app.config["PUBLIC_BASE_URL"] = os.environ.get(
    "PUBLIC_BASE_URL",
    "http://127.0.0.1:5000"
)

# Prevent SMTP from hanging forever
socket.setdefaulttimeout(20)
mail = Mail(app)




db.init_app(app)
jwt = JWTManager(app)
app.secret_key = os.environ.get("SECRET_KEY")


@jwt.token_in_blocklist_loader
def check_if_token_blocked(jwt_header, jwt_payload):

    user_id = jwt_payload.get("sub")

    if not user_id:
        return True

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return True

    user = db.session.get(
        User,
        user_id
    )

    # Deleted users should not keep using old tokens either.
    if not user:
        return True

    return user.is_banned


@jwt.revoked_token_loader
def revoked_token_response(
    jwt_header,
    jwt_payload
):

    user_id = jwt_payload.get("sub")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "code": "invalid_session",
            "message": "Invalid session."
        }), 401


    user = db.session.get(
        User,
        user_id
    )

    if user and user.is_banned:

        return jsonify({
            "success": False,
            "code": "account_banned",
            "message": "This account has been banned."
        }), 403


    return jsonify({
        "success": False,
        "code": "invalid_session",
        "message": "This session is no longer valid."
    }), 401

print(Course)
print(PreferenceCourse)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def preferences_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        pref = Preferences.query.filter_by(
            user_id=session.get("user_id")
        ).first()
        if not pref:
            return redirect(url_for("preferences"))
        return view(*args, **kwargs)
    return wrapped


def get_or_create_chat(user1_id, user2_id):
    chat = ChatRoom.query.filter(
        db.or_(
            db.and_(ChatRoom.user1_id == user1_id, ChatRoom.user2_id == user2_id),
            db.and_(ChatRoom.user1_id == user2_id, ChatRoom.user2_id == user1_id)
        )
    ).first()

    if chat:
        return chat

    chat = ChatRoom(user1_id=user1_id, user2_id=user2_id)
    db.session.add(chat)
    db.session.commit()
    return chat


def unread_messages_count(user_id):
    return Message.query.join(ChatRoom).filter(
        Message.sender_id != user_id,
        Message.is_read == False,
        ((ChatRoom.user1_id == user_id) | (ChatRoom.user2_id == user_id))
    ).count()


def is_blocked_between(user1_id, user2_id):
    return Block.query.filter(
        db.or_(
            db.and_(Block.blocker_id == user1_id, Block.blocked_id == user2_id),
            db.and_(Block.blocker_id == user2_id, Block.blocked_id == user1_id)
        )
    ).first() is not None


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/start")
def start():
    # غير مسجل دخول
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = User.query.get(session["user_id"])

    # مسجل دخول ولكن لم يملأ الاستبيان
    if not user.preferences:
        return redirect(url_for("preferences"))

    # مسجل دخول + الاستبيان موجود
    return redirect(url_for("match"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("profile"))



    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        # --- ADMIN CHECK ---
        if (email == os.environ.get("ADMIN_EMAIL")
            and password == os.environ.get("ADMIN_PASSWORD")):
            session.clear()
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        
        if not user:
            flash("This email is not registered or incorrect.", "email_error")
            return redirect(url_for("login"))

        if not check_password_hash(user.password, password):
            flash("Incorrect password or email.", "password_error")
            return redirect(url_for("login"))


        session["user_id"] = user.id
        session["user_first_name"] = user.first_name
        session["user_email"] = user.email
        session["user_role"] = user.role

        return redirect(url_for("profile"))

    return render_template("login.html")


def serialize_academic_info(pref):

    if not pref:
        return None

    country_code = pref.country_code or ""
    stored_phone = pref.phone or ""

    # Website stores country_code + phone together.
    # For Android editing, return only the local phone part.
    if (
        country_code
        and stored_phone.startswith(country_code)
    ):
        phone = stored_phone[len(country_code):]
    else:
        phone = stored_phone

    return {
        "age": pref.age,
        "gender": pref.gender,
        "country_code": country_code,
        "phone": phone,

        "gpa": pref.gpa,
        "program": pref.program,
        "semester": pref.semester,
        "academic_year": pref.academic_year,
        "commitment_level": pref.commitment_level,

        "courses": [
            {
                "course_id": pc.course_id,
                "code": pc.course.code,
                "name": pc.course.name,
                "academic_year": pc.course.academic_year,
                "program": pc.course.program,
                "cross_section": pc.cross_section,
                "section": pc.section
            }
            for pc in pref.courses
        ]
    }


@app.route("/api/register", methods=["POST"])
def api_register():

    data = request.get_json(silent=True) or {}

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # Required fields
    if not first_name:
        return jsonify({
            "success": False,
            "message": "First name is required."
        }), 400

    if not last_name:
        return jsonify({
            "success": False,
            "message": "Last name is required."
        }), 400

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required."
        }), 400

    if not password:
        return jsonify({
            "success": False,
            "message": "Password is required."
        }), 400

    # Same minimum we used in Project I
    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters."
        }), 400


    # Duplicate email
    existing_user = User.query.filter(
        db.func.lower(User.email) == email
    ).first()

    if existing_user:
        return jsonify({
            "success": False,
            "message": "An account with this email already exists."
        }), 409

    # Create account
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=generate_password_hash(password)
    )

    db.session.add(user)

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Could not create account."
        }), 500

    # Automatically log in
    access_token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "success": True,
        "message": "Account created successfully.",
        "access_token": access_token,

        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "has_preferences": False
        }
    }), 201

@app.route("/api/login", methods=["POST"])
def api_login():

    data = request.get_json(
        silent=True
    ) or {}

    email = (
        data.get("email") or ""
    ).strip().lower()

    password = (
        data.get("password") or ""
    )

    # Required fields
    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    # Find user
    user = User.query.filter(
        func.lower(User.email) == email
    ).first()

    # Invalid credentials
    if not user or not check_password_hash(
        user.password,
        password
    ):
        return jsonify({
            "success": False,
            "message": "Invalid email or password."
        }), 401

    # Banned account
    if user.is_banned:
        return jsonify({
        "success": False,
        "code": "account_banned",
        "message": "This account has been banned."
    }), 403

    # Create Android authentication token
    access_token = create_access_token(
        identity=str(user.id)
    )

    return jsonify({
        "success": True,
        "access_token": access_token,
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "has_preferences": user.preferences is not None
        }
    }), 200



@app.route(
    "/api/academic-info",
    methods=["GET", "PUT"]
)
@jwt_required()
def api_academic_info():

    user_id = int(get_jwt_identity())

    pref = Preferences.query.filter_by(
        user_id=user_id
    ).first()

    # GET
    if request.method == "GET":

        courses = Course.query.order_by(
            Course.academic_year.asc(),
            Course.code.asc()
        ).all()

        return jsonify({
            "success": True,

            "has_preferences":
                pref is not None,

            "preferences":
                serialize_academic_info(pref),

            "courses": [
                {
                    "id": course.id,
                    "code": course.code,
                    "name": course.name,
                    "academic_year":
                        course.academic_year,
                    "program":
                        course.program
                }
                for course in courses
            ]
        }), 200


    # PUT - create or update
    data = request.get_json(
        silent=True
    ) or {}

    age = data.get("age")
    gender = (
        data.get("gender") or ""
    ).strip()

    country_code = (
        data.get("country_code") or ""
    ).strip()

    phone = (
        data.get("phone") or ""
    ).strip()

    gpa = data.get("gpa")

    program = (
        data.get("program") or ""
    ).strip()

    semester = (
        data.get("semester") or ""
    ).strip()

    academic_year = data.get("academic_year")

    commitment_level = data.get("commitment_level")

    selected_courses = data.get("courses") or []

    # Basic validation
    if (
        age is None
        or not gender
        or not phone
        or gpa is None
        or not program
        or not semester
        or academic_year is None
        or commitment_level is None
    ):
        return jsonify({
            "success": False,
            "message":
                "All required academic information must be provided."
        }), 400


    try:
        age = int(age)
        gpa = float(gpa)
        academic_year = int(
            academic_year
        )
        commitment_level = int(
            commitment_level
        )

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message":
                "Invalid numeric values."
        }), 400


    if not 0 <= gpa <= 4:
        return jsonify({
            "success": False,
            "message":
                "GPA must be between 0 and 4."
        }), 400


    if not 1 <= commitment_level <= 5:
        return jsonify({
            "success": False,
            "message":
                "Commitment level must be between 1 and 5."
        }), 400


    if not isinstance(
        selected_courses,
        list
    ):
        return jsonify({
            "success": False,
            "message":
                "Courses must be a list."
        }), 400


    # Create or update Preferences
    if not pref:

        pref = Preferences(
            user_id=user_id
        )

        db.session.add(pref)


    pref.age = age
    pref.gender = gender

    pref.country_code = country_code

    pref.phone = country_code + phone

    pref.gpa = gpa
    pref.program = program
    pref.semester = semester

    pref.academic_year = academic_year

    pref.commitment_level = commitment_level


    # Replace selected courses

    pref.courses.clear()

    seen_course_ids = set()

    for item in selected_courses:

        try:
            course_id = int(
                item.get("course_id")
            )
        except (
            AttributeError,
            TypeError,
            ValueError
        ):
            db.session.rollback()

            return jsonify({
                "success": False,
                "message":
                    "Invalid course data."
            }), 400


        # Avoid duplicates
        if course_id in seen_course_ids:
            continue

        seen_course_ids.add(
            course_id
        )


        course = db.session.get(
            Course,
            course_id
        )

        if not course:
            db.session.rollback()

            return jsonify({
                "success": False,
                "message":
                    f"Course {course_id} does not exist."
            }), 400


        cross_section = bool(
            item.get(
                "cross_section",
                False
            )
        )

        section = (
            item.get("section") or ""
        ).strip()

        if cross_section:

            section = None

        elif not section:

            db.session.rollback()

            return jsonify({
                "success": False,
                "message":
                    f"Section is required for course {course.code}."
            }), 400


        preference_course = PreferenceCourse(
                course=course,
                cross_section=cross_section,
                section=section
            )

        pref.courses.append(
            preference_course
        )


    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message":
                "Could not save academic information."
        }), 500


    return jsonify({
        "success": True,
        "message":
            "Academic information saved successfully.",

        "has_preferences": True,

        "preferences":
            serialize_academic_info(pref)
    }), 200


@app.route("/api/matches", methods=["GET"])
@jwt_required()
def api_matches():
    """Return the website's hybrid-ML matches as JSON for Android."""

    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "The authentication token is invalid."
        }), 401

    user = db.session.get(User, user_id)

    if user is None:
        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    if user.is_banned:
        return jsonify({
            "success": False,
            "message": "This account is restricted."
        }), 403

    if user.preferences is None:
        return jsonify({
            "success": False,
            "message": "Please complete your preferences first."
        }), 409

    matches = find_ml_matches(
        user.preferences,
        Preferences.query.all()
    )

    related_requests = CollaborationRequest.query.filter(
        (CollaborationRequest.sender_id == user.id) |
        (CollaborationRequest.receiver_id == user.id)
    ).all()

    relation_map = {}
    for collaboration_request in related_requests:
        other_user_id = (
            collaboration_request.receiver_id
            if collaboration_request.sender_id == user.id
            else collaboration_request.sender_id
        )
        relation_map[other_user_id] = collaboration_request

    result = []

    for preference, probability in matches:
        if is_blocked_between(user.id, preference.user_id):
            continue

        collaboration_request = relation_map.get(preference.user_id)

        result.append({
            "user_id": preference.user.id,
            "first_name": preference.user.first_name,
            "last_name": preference.user.last_name,
            "program": preference.program,
            "semester": preference.semester,
            "academic_year": preference.academic_year,
            "commitment_level": preference.commitment_level,
            "compatibility_probability": probability,
            "compatibility_percent": round(probability * 100, 1),
            "request": None if collaboration_request is None else {
                "id": collaboration_request.id,
                "status": collaboration_request.status,
                "direction": (
                    "outgoing"
                    if collaboration_request.sender_id == user.id
                    else "incoming"
                )
            },
            "courses": [
                {
                    "code": preference_course.course.code,
                    "name": preference_course.course.name,
                    "section": preference_course.section,
                    "cross_section": preference_course.cross_section
                }
                for preference_course in preference.courses
            ]
        })

    return jsonify({
        "success": True,
        "count": len(result),
        "matches": result
    }), 200


@app.route(
    "/api/requests/<int:receiver_id>",
    methods=["POST"]
)
@jwt_required()
def api_send_request(receiver_id):

    sender_id = int(get_jwt_identity())

    # Cannot send request to yourself
    if sender_id == receiver_id:
        return jsonify({
            "success": False,
            "message": "You cannot send a request to yourself."
        }), 400

    # Make sure receiver exists
    receiver = db.session.get(
        User,
        receiver_id
    )

    if not receiver:
        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    # Check blocking
    if is_blocked_between(
        sender_id,
        receiver_id
    ):
        return jsonify({
            "success": False,
            "message": "You cannot send a request to this user."
        }), 403

    # Check if a relationship already exists
    existing = CollaborationRequest.query.filter(
        db.or_(
            db.and_(
                CollaborationRequest.sender_id == sender_id,
                CollaborationRequest.receiver_id == receiver_id
            ),
            db.and_(
                CollaborationRequest.sender_id == receiver_id,
                CollaborationRequest.receiver_id == sender_id
            )
        )
    ).first()

    if existing:
        return jsonify({
            "success": False,
            "message": "A collaboration request already exists.",
            "request_id": existing.id,
            "status": existing.status
        }), 409

    collaboration_request = CollaborationRequest(
        sender_id=sender_id,
        receiver_id=receiver_id
    )

    db.session.add(
        collaboration_request
    )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Collaboration request sent.",
        "request": {
            "id": collaboration_request.id,
            "sender_id": collaboration_request.sender_id,
            "receiver_id": collaboration_request.receiver_id,
            "status": collaboration_request.status
        }
    }), 201



@app.route(
    "/api/requests/<int:request_id>",
    methods=["DELETE"]
)
@jwt_required()
def api_cancel_request(request_id):

    user_id = int(get_jwt_identity())

    collaboration_request = db.session.get(
        CollaborationRequest,
        request_id
    )

    if not collaboration_request:
        return jsonify({
            "success": False,
            "message": "Collaboration request not found."
        }), 404

    # Only the sender can cancel the request
    if collaboration_request.sender_id != user_id:
        return jsonify({
            "success": False,
            "message": "You are not allowed to cancel this request."
        }), 403

    # Only pending requests can be cancelled
    if collaboration_request.status != "pending":
        return jsonify({
            "success": False,
            "message": "Only pending requests can be cancelled."
        }), 400

    db.session.delete(
        collaboration_request
    )

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Collaboration request cancelled."
    }), 200


@app.route("/api/requests", methods=["GET"])
@jwt_required()
def api_get_requests():

    user_id = int(get_jwt_identity())

    requests_list = CollaborationRequest.query.filter(
        (CollaborationRequest.sender_id == user_id) |
        (CollaborationRequest.receiver_id == user_id)
    ).order_by(
        CollaborationRequest.created_at.desc()
    ).all()

    result = []

    for req in requests_list:

        if req.sender_id == user_id:
            direction = "outgoing"
            other_user_id = req.receiver_id
        else:
            direction = "incoming"
            other_user_id = req.sender_id

        if is_blocked_between(
            user_id,
            other_user_id
        ):
            continue

        other_user = db.session.get(
            User,
            other_user_id
        )

        if not other_user:
            continue

        result.append({
            "id": req.id,
            "status": req.status,
            "direction": direction,

            "other_user": {
                "id": other_user.id,
                "first_name": other_user.first_name,
                "last_name": other_user.last_name
            },

            "created_at": (
                req.created_at.isoformat()
                if req.created_at
                else None
            )
        })

    counts = {
        "all": len(result),
        "pending": sum(
            1 for req in result
            if req["status"] == "pending"
        ),
        "accepted": sum(
            1 for req in result
            if req["status"] == "accepted"
        ),
        "rejected": sum(
            1 for req in result
            if req["status"] == "rejected"
        )
    }

    return jsonify({
        "success": True,
        "counts": counts,
        "requests": result
    }), 200




@app.route(
    "/api/requests/<int:request_id>/accept",
    methods=["POST"]
)
@jwt_required()
def api_accept_request(request_id):

    user_id = int(get_jwt_identity())

    req = db.session.get(
        CollaborationRequest,
        request_id
    )

    if not req:
        return jsonify({
            "success": False,
            "message": "Collaboration request not found."
        }), 404

    if req.receiver_id != user_id:
        return jsonify({
            "success": False,
            "message": "You are not allowed to accept this request."
        }), 403

    if req.status != "pending":
        return jsonify({
            "success": False,
            "message": "Only pending requests can be accepted."
        }), 400

    req.status = "accepted"

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Collaboration request accepted."
    }), 200


@app.route(
    "/api/requests/<int:request_id>/reject",
    methods=["POST"]
)
@jwt_required()
def api_reject_request(request_id):

    user_id = int(get_jwt_identity())

    req = db.session.get(
        CollaborationRequest,
        request_id
    )

    if not req:
        return jsonify({
            "success": False,
            "message": "Collaboration request not found."
        }), 404

    if req.receiver_id != user_id:
        return jsonify({
            "success": False,
            "message": "You are not allowed to reject this request."
        }), 403

    if req.status != "pending":
        return jsonify({
            "success": False,
            "message": "Only pending requests can be rejected."
        }), 400

    req.status = "rejected"

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Collaboration request rejected."
    }), 200


@app.route(
    "/api/requests/<int:request_id>/chat",
    methods=["POST"]
)
@jwt_required()
def api_open_chat(request_id):

    user_id = int(get_jwt_identity())

    req = db.session.get(
        CollaborationRequest,
        request_id
    )

    if not req:
        return jsonify({
            "success": False,
            "message": "Collaboration request not found."
        }), 404

    # User must belong to the collaboration request
    if user_id not in [
        req.sender_id,
        req.receiver_id
    ]:
        return jsonify({
            "success": False,
            "message": "You are not allowed to access this chat."
        }), 403

    # Chat becomes available only after acceptance
    if req.status != "accepted":
        return jsonify({
            "success": False,
            "message": "Chat is available only after the request is accepted."
        }), 400

    other_user_id = (
        req.receiver_id
        if req.sender_id == user_id
        else req.sender_id
    )

    if is_blocked_between(
        user_id,
        other_user_id
    ):
        return jsonify({
            "success": False,
            "message": "This chat is unavailable."
        }), 403

    chat = get_or_create_chat(
        req.sender_id,
        req.receiver_id
    )

    other_user = db.session.get(
        User,
        other_user_id
    )

    return jsonify({
        "success": True,
        "chat": {
            "id": chat.id,
            "other_user": {
                "id": other_user.id,
                "first_name": other_user.first_name,
                "last_name": other_user.last_name
            }
        }
    }), 200

@app.route(
    "/api/chats/<int:chat_id>/messages",
    methods=["GET"]
)
@jwt_required()
def api_get_chat_messages(chat_id):

    user_id = int(get_jwt_identity())

    chat = db.session.get(
        ChatRoom,
        chat_id
    )

    if not chat:
        return jsonify({
            "success": False,
            "message": "Chat not found."
        }), 404

    # User must belong to this chat
    if user_id not in [
        chat.user1_id,
        chat.user2_id
    ]:
        return jsonify({
            "success": False,
            "message": "You are not allowed to access this chat."
        }), 403

    other_user_id = (
        chat.user2_id
        if chat.user1_id == user_id
        else chat.user1_id
    )

    if is_blocked_between(
        user_id,
        other_user_id
    ):
        return jsonify({
            "success": False,
            "message": "This chat is unavailable."
        }), 403

    messages = Message.query.filter_by(
        chat_id=chat.id
    ).order_by(
        Message.created_at.asc()
    ).all()

    # Mark received messages as read
    Message.query.filter(
        Message.chat_id == chat.id,
        Message.sender_id != user_id,
        Message.is_read == False
    ).update({
        "is_read": True
    })

    db.session.commit()

    return jsonify({
        "success": True,
        "messages": [
            {
                "id": msg.id,
                "content": msg.content,
                "sender_id": msg.sender_id,
                "is_mine": msg.sender_id == user_id,
                "created_at": (
                    msg.created_at.isoformat()
                    if msg.created_at
                    else None
                ),
                "time": (
                    msg.created_at.strftime("%H:%M")
                    if msg.created_at
                    else ""
                )
            }
            for msg in messages
        ]
    }), 200

@app.route(
    "/api/chats/<int:chat_id>/messages",
    methods=["POST"]
)
@jwt_required()
def api_send_chat_message(chat_id):

    user_id = int(get_jwt_identity())

    chat = db.session.get(
        ChatRoom,
        chat_id
    )

    if not chat:
        return jsonify({
            "success": False,
            "message": "Chat not found."
        }), 404

    if user_id not in [
        chat.user1_id,
        chat.user2_id
    ]:
        return jsonify({
            "success": False,
            "message": "You are not allowed to access this chat."
        }), 403

    other_user_id = (
        chat.user2_id
        if chat.user1_id == user_id
        else chat.user1_id
    )

    if is_blocked_between(
        user_id,
        other_user_id
    ):
        return jsonify({
            "success": False,
            "message": "This chat is unavailable."
        }), 403

    data = request.get_json(
        silent=True
    ) or {}

    content = (
        data.get("content") or ""
    ).strip()

    if not content:
        return jsonify({
            "success": False,
            "message": "Message cannot be empty."
        }), 400

    message = Message(
        chat_id=chat.id,
        sender_id=user_id,
        content=content
    )

    chat.last_activity = db.func.now()

    db.session.add(message)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": {
            "id": message.id,
            "content": message.content,
            "sender_id": message.sender_id,
            "is_mine": True,
            "created_at": (
                message.created_at.isoformat()
                if message.created_at
                else None
            ),
            "time": (
                message.created_at.strftime("%H:%M")
                if message.created_at
                else ""
            )
        }
    }), 201



@app.route("/api/chats", methods=["GET"])
@jwt_required()
def api_get_chats():

    user_id = int(get_jwt_identity())

    chats = ChatRoom.query.filter(
        (ChatRoom.user1_id == user_id) |
        (ChatRoom.user2_id == user_id)
    ).order_by(
        ChatRoom.last_activity.desc()
    ).all()

    result = []

    for chat in chats:

        other_user_id = (
            chat.user2_id
            if chat.user1_id == user_id
            else chat.user1_id
        )

        if is_blocked_between(
            user_id,
            other_user_id
        ):
            continue

        other_user = db.session.get(
            User,
            other_user_id
        )

        if not other_user:
            continue

        last_message = Message.query.filter_by(
            chat_id=chat.id
        ).order_by(
            Message.created_at.desc()
        ).first()

        unread_count = Message.query.filter(
            Message.chat_id == chat.id,
            Message.sender_id != user_id,
            Message.is_read == False
        ).count()

        result.append({
            "id": chat.id,

            "other_user": {
                "id": other_user.id,
                "first_name": other_user.first_name,
                "last_name": other_user.last_name
            },

            "last_message": (
                last_message.content
                if last_message
                else None
            ),

            "last_message_time": (
                last_message.created_at.isoformat()
                if last_message and last_message.created_at
                else None
            ),

            "unread_count": unread_count
        })

    return jsonify({
        "success": True,
        "count": len(result),
        "chats": result
    }), 200


@app.route(
    "/api/account-status",
    methods=["GET"]
)
@jwt_required(
    skip_revocation_check=True
)
def api_account_status():

    user_id = int(
        get_jwt_identity()
    )

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        return jsonify({
            "success": False,
            "exists": False,
            "is_banned": False
        }), 404


    return jsonify({
        "success": True,
        "exists": True,
        "is_banned": user.is_banned
    }), 200

@app.route("/api/account", methods=["DELETE"])
@jwt_required()
def api_delete_account():

    user_id = int(get_jwt_identity())

    user = db.session.get(User, user_id)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    data = request.get_json(silent=True) or {}

    password = data.get("password") or ""

    if not password:
        return jsonify({
            "success": False,
            "message": "Password is required."
        }), 400

    # Verify password
    if not check_password_hash(
        user.password,
        password
    ):
        return jsonify({
            "success": False,
            "message": "Incorrect password."
        }), 401


    try:

        # Collaboration requests
        CollaborationRequest.query.filter(
            (CollaborationRequest.sender_id == user_id) |
            (CollaborationRequest.receiver_id == user_id)
        ).delete(
            synchronize_session=False
        )


        # Blocks
        Block.query.filter(
            (Block.blocker_id == user_id) |
            (Block.blocked_id == user_id)
        ).delete(
            synchronize_session=False
        )


        # Reports + ReportMessage rows
        report_ids = [
            report.id
            for report in Report.query.filter(
                (Report.reporter_id == user_id) |
                (Report.reported_user_id == user_id)
            ).all()
        ]

        if report_ids:

            ReportMessage.query.filter(
                ReportMessage.report_id.in_(
                    report_ids
                )
            ).delete(
                synchronize_session=False
            )

            Report.query.filter(
                Report.id.in_(report_ids)
            ).delete(
                synchronize_session=False
            )


        # Chats + messages
        chats = ChatRoom.query.filter(
            (ChatRoom.user1_id == user_id) |
            (ChatRoom.user2_id == user_id)
        ).all()

        for chat in chats:

            Message.query.filter_by(
                chat_id=chat.id
            ).delete(
                synchronize_session=False
            )

            db.session.delete(chat)


        # Preferences are removed through the existing
        # User -> Preferences delete-orphan cascade.
        db.session.delete(user)

        db.session.commit()


    except Exception:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Could not delete account."
        }), 500


    return jsonify({
        "success": True,
        "message": "Account deleted permanently."
    }), 200


@app.route("/api/forgot-password", methods=["POST"])
def api_forgot_password():

    data = request.get_json(silent=True) or {}

    email = (
        data.get("email") or ""
    ).strip().lower()

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required."
        }), 400


    user = User.query.filter(
        db.func.lower(User.email) == email
    ).first()


    # Always return the same public response,
    # whether the email exists or not.

    # This prevents people from using the API
    # to discover registered email addresses.
    if user:

        token = secrets.token_urlsafe(32)

        user.reset_token = token

        user.reset_token_expiration = (
            datetime.utcnow() +
            timedelta(minutes=30)
        )

        db.session.commit()

        reset_path = url_for(
            "reset_password",
            token=token
        )

        reset_link = (
            app.config["PUBLIC_BASE_URL"].rstrip("/")
            + reset_path
        )


        msg = MailMessage(
            subject="إعادة تعيين كلمة المرور",
            recipients=[user.email],
            sender=app.config["MAIL_USERNAME"]
        )

        msg.body = (
            "لقد تم طلب إعادة تعيين كلمة المرور "
            "لحسابك في Smart Academic Matchmaker.\n\n"
            "اضغط على الرابط التالي لإعادة تعيين كلمة المرور:\n"
            f"{reset_link}\n\n"
            "صلاحية هذا الرابط 30 دقيقة."
        )


        try:

            print("ABOUT TO SEND RESET EMAIL")

            mail.send(msg)

            print(
                "RESET EMAIL SENT TO:",
                user.email
            )

        except Exception as e:

            print(
                "RESET EMAIL ERROR:",
                repr(e)
            )


        



    return jsonify({
        "success": True,
        "message":
            "If this email is registered, a password reset link will be sent."
    }), 200


@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/profile")
@login_required
def profile():

    user = User.query.get(session["user_id"])
    preferences = user.preferences   # or however you get it

    delete_error = False

    flashes = get_flashed_messages(with_categories=True)
    for category, message in flashes:
        if category == "delete_error":
            delete_error = True

    return render_template(
        "profile.html",
        user=user,
        preferences=preferences,
        delete_error=delete_error
    )


@app.route("/api/profile", methods=["GET", "PUT"])
@jwt_required()
def api_profile():

    user_id = int(get_jwt_identity())

    user = db.session.get(User, user_id)

    if not user:
        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404

    pref = user.preferences

    # GET

    if request.method == "GET":

        academic_info = None

        if pref:

            academic_info = {
                "gender": pref.gender,
                "program": pref.program,
                "semester": pref.semester,
                "academic_year": pref.academic_year,
                "gpa": pref.gpa,
                "commitment_level": pref.commitment_level,

                "courses": [
                    {
                        "code": pc.course.code,
                        "name": pc.course.name,
                        "cross_section": pc.cross_section,
                        "section": pc.section
                    }
                    for pc in pref.courses
                ]
            }

        return jsonify({
            "success": True,

            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email
            },

            "has_preferences": pref is not None,

            "academic_info": academic_info
        }), 200


    # PUT
    data = request.get_json(
        silent=True
    ) or {}

    first_name = (
        data.get("first_name") or ""
    ).strip()

    last_name = (
        data.get("last_name") or ""
    ).strip()


    if not first_name:

        return jsonify({
            "success": False,
            "message": "First name is required."
        }), 400


    if not last_name:

        return jsonify({
            "success": False,
            "message": "Last name is required."
        }), 400


    if len(first_name) > 50:

        return jsonify({
            "success": False,
            "message": "First name is too long."
        }), 400


    if len(last_name) > 50:

        return jsonify({
            "success": False,
            "message": "Last name is too long."
        }), 400


    user.first_name = first_name
    user.last_name = last_name


    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Could not update profile."
        }), 500


    return jsonify({
        "success": True,

        "message":
            "Profile updated successfully.",

        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email
        }
    }), 200




@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if len(password) < 8:
            flash("Password must at least contain 8 characters long.", "password_error")
            return redirect(url_for("register"))

        if password != confirm_password:
            return render_template(
                "register.html",
                error="كلمتا المرور غير متطابقتين"
            )

        existing = User.query.filter_by(email=email).first()
        if existing:
            return render_template(
                "register.html",
                error="البريد الإلكتروني مستخدم مسبقاً"
            )

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        # AUTO LOGIN
        session["user_id"] = user.id
        session["user_first_name"] = user.first_name
        session["user_email"] = user.email
        session["user_role"] = user.role

        return redirect(url_for("home"))

    return render_template("register.html")


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiration = datetime.utcnow() + timedelta(minutes=30)
            db.session.commit()

            reset_link = url_for('reset_password', token=token, _external=True)

            mail = Mail(app)
            # Send Email To Reset Password
            msg = MailMessage("إعادة تعيين كلمة المرور",
                          recipients=[email])
            msg.body = f"اضغط على الرابط لإعادة التعيين:\n{reset_link}"
            try:
                mail.send(msg)
                print("Email sent successfully.")
            except Exception as e:
                print("Email failed:", e)


        flash("إذا كان البريد موجوداً، سيتم إرسال رابط إعادة التعيين.")
        return redirect(url_for('login'))
    return render_template('forgot_password.html')



@app.route(
    "/reset-password/<token>",
    methods=["GET", "POST"]
)
def reset_password(token):

    user = User.query.filter_by(
        reset_token=token
    ).first()

    if (
        not user
        or user.reset_token_expiration is None
        or user.reset_token_expiration < datetime.utcnow()
    ):
        flash(
            "الرابط غير صالح أو منتهي الصلاحية."
        )

        return redirect(
            url_for("login")
        )


    if request.method == "POST":

        new_password = (
            request.form.get("password")
            or ""
        )

        if len(new_password) < 8:

            flash(
                "يجب أن تتكون كلمة المرور من 8 محارف على الأقل."
            )

            return render_template(
                "reset_password.html"
            )


        user.password = generate_password_hash(
            new_password
        )

        user.reset_token = None
        user.reset_token_expiration = None

        db.session.commit()


        flash(
            "تم تغيير كلمة المرور بنجاح."
        )

        return redirect(
            url_for("login")
        )

    # This handles opening the link from the email.
    return render_template(
        "reset_password.html"
    )


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():

    user_id = session.get("user_id")
    user = User.query.get(user_id)

    # ALWAYS define existing here
    existing = Preferences.query.filter_by(user_id=user_id).first()

    all_courses = Course.query.all()
    print (all_courses)
    courses_map = {}

    if request.method == "POST":
        print("==== FORM DATA ====")
        print(request.form)
        print("COURSES LIST:", request.form.getlist("courses[]"))
        print("===================")


        if existing:
            pref = existing
        else:
            pref = Preferences(user_id=user_id)
            db.session.add(pref)

        # -------- Personal Info --------
        age_raw = request.form.get("age")
        if not age_raw:
            flash("يرجى تعبئة جميع الحقول المطلوبة", "danger")
            return redirect(url_for("preferences"))

        pref.age = int(age_raw)
        pref.gender = request.form["gender"]

        pref.country_code = request.form["country_code"]
        pref.phone = request.form["country_code"] + request.form["phone"]

        # -------- Academic Info --------
        gpa_raw = request.form.get("gpa")

        if not gpa_raw:
            flash("يرجى تعبئة جميع الحقول المطلوبة", "danger")
            return redirect(url_for("preferences"))
        pref.gpa = float(gpa_raw)

        pref.program = request.form["program"]
        pref.semester = request.form["semester"]

        year_raw = request.form.get("academic_year")
        pref.academic_year = int(year_raw) if year_raw else None

        commitment_raw = request.form.get("commitment_level")
        if not commitment_raw:
            flash("يرجى اختيار مستوى الالتزام", "danger")
            return redirect(url_for("preferences"))

        pref.commitment_level = int(commitment_raw)

        # -------- Courses --------
        pref.courses.clear()
        selected_codes = request.form.getlist("courses[]")
        print("Selected:", selected_codes)


        print("Pref ID BEFORE LOOP:", pref.id)
        for code in selected_codes:

            course = Course.query.filter_by(code=code).first()
            print("Course lookup result:", course)
            print("Appending course:", code)
            if not course:
                continue
            
            cross_section = bool(int(request.form.get(f"cross_section[{code}]", 0)))
            section = request.form.get(f"section[{code}]") if not cross_section else None

            pc = PreferenceCourse(
                course=course,
                cross_section=cross_section,
                section=section
            )

            pref.courses.append(pc)
        print("Courses attached:", pref.courses)
        db.session.commit()

        print("FORM DATA:", request.form)
        print("SELECTED:", request.form.getlist("courses[]"))
        print(request.form.getlist("courses[]"))

        flash("تم حفظ التفضيلات بنجاح", "success")
        return redirect(url_for("profile"))

    return render_template(
        "preferences.html",
        user=user,
        courses=all_courses,
        courses_map=courses_map,
        preferences=existing
    )



@app.route("/match")
@login_required
def match():

    user = User.query.get(session["user_id"])

    if not user.preferences:
        flash(
            "يرجى تعبئة استبيان التفضيلات أولاً",
            "warning"
        )
        return redirect(url_for("preferences"))

    all_prefs = Preferences.query.all()

    # Project II hybrid matcher:
    # rule-based eligibility + ML ranking
    matches = find_ml_matches(
        user.preferences,
        all_prefs
    )

    # Remove blocked users
    filtered_matches = []

    for pref, probability in matches:

        if not is_blocked_between(
            user.id,
            pref.user_id
        ):
            filtered_matches.append(
                (pref, probability)
            )

    matches = filtered_matches

    user_id = user.id

    # All collaboration requests related to this user
    all_requests = CollaborationRequest.query.filter(
        (CollaborationRequest.sender_id == user_id) |
        (CollaborationRequest.receiver_id == user_id)
    ).all()

    relation_map = {}

    for req in all_requests:

        if req.sender_id == user_id:
            other_id = req.receiver_id
        else:
            other_id = req.sender_id

        relation_map[other_id] = req

    return render_template(
        "match_results.html",
        matches=matches,
        relation_map=relation_map
    )




@app.route("/requests")
@login_required
def requests():
    user_id = session["user_id"]
    status_filter = request.args.get("status")

    base_query = CollaborationRequest.query.filter(
        (CollaborationRequest.sender_id == user_id) |
        (CollaborationRequest.receiver_id == user_id)
    )

    # counts
    counts = {
        "all": base_query.count(),
        "pending": base_query.filter_by(status="pending").count(),
        "accepted": base_query.filter_by(status="accepted").count(),
        "rejected": base_query.filter_by(status="rejected").count()
    }

    # filtered results
    if status_filter in ["pending", "accepted", "rejected"]:
        requests_list = base_query.filter_by(
            status=status_filter
        ).order_by(CollaborationRequest.created_at.desc()).all()
    else:
        requests_list = base_query.order_by(
            CollaborationRequest.created_at.desc()
        ).all()

    filtered_requests = []
    for req in requests_list:
        other_id = req.receiver_id if req.sender_id == user_id else req.sender_id
        if not is_blocked_between(user_id, other_id):
            filtered_requests.append(req)

    requests_list = filtered_requests

    return render_template(
        "requests.html",
        requests=requests_list,
        counts=counts,
        current_filter=status_filter
    )





@app.route("/request/<int:receiver_id>")
@login_required
def send_request(receiver_id):
    sender_id = session["user_id"]


    # Check blocking
    if is_blocked_between(sender_id, receiver_id):
        flash("لا يمكنك إرسال طلب لهذا المستخدم", "danger")
        return redirect(url_for("match"))
    

    if sender_id == receiver_id:
        flash("لا يمكنك إرسال طلب لنفسك", "danger")
        return redirect(url_for("match"))

    existing = CollaborationRequest.query.filter_by(
        sender_id=sender_id,
        receiver_id=receiver_id
    ).first()

    if existing:
        flash("تم إرسال طلب مسبقاً", "warning")
        return redirect(url_for("match"))

    req = CollaborationRequest(
        sender_id=sender_id,
        receiver_id=receiver_id
    )

    db.session.add(req)
    db.session.commit()

    flash("تم إرسال طلب التعاون بنجاح", "success")
    return redirect(url_for("match"))

# Cancel Sent Request while it's pending
@app.route("/requests/<int:receiver_id>/cancel")
@login_required
def cancel_request(receiver_id):
    sender_id = session["user_id"]


    req = CollaborationRequest.query.filter_by(
        sender_id=sender_id,
        receiver_id=receiver_id,
        status="pending"
    ).first()

    if not req:
        flash("لا يوجد طلب قابل للإلغاء", "warning")
        return redirect(url_for("match"))

    db.session.delete(req)
    db.session.commit()

    flash("تم إلغاء طلب التعاون", "info")
    return redirect(url_for("match"))


# Accepting Invitations
@app.route("/requests/<int:request_id>/accept")
@login_required
def accept_request(request_id):
    user_id = session["user_id"]

    req = CollaborationRequest.query.get_or_404(request_id)

    # تأكد أن الطلب موجه لهذا المستخدم
    if req.receiver_id != user_id:
        flash("غير مصرح لك", "danger")
        return redirect(url_for("requests"))

    req.status = "accepted"
    db.session.commit()

    flash("تم قبول طلب التعاون", "success")
    return redirect(url_for("requests"))

 # Rejecting Invitations
@app.route("/requests/<int:request_id>/reject")
@login_required
def reject_request(request_id):
    user_id = session["user_id"]

    req = CollaborationRequest.query.get_or_404(request_id)

    if req.receiver_id != user_id:
        flash("غير مصرح لك", "danger")
        return redirect(url_for("requests"))

    req.status = "rejected"
    db.session.commit()

    flash("تم رفض الطلب", "info")
    return redirect(url_for("requests"))


@app.route("/chat/<int:request_id>")
@login_required
def open_chat(request_id):
    req = CollaborationRequest.query.get_or_404(request_id)

    user_id = session["user_id"]

    # تأكد أن المستخدم طرف في الطلب
    if user_id not in [req.sender_id, req.receiver_id]:
        flash("غير مصرح لك", "danger")
        return redirect(url_for("requests"))

    if req.status != "accepted":
        flash("الدردشة متاحة فقط بعد قبول الطلب", "warning")
        return redirect(url_for("requests"))

    other_id = req.receiver_id if req.sender_id == user_id else req.sender_id

    if is_blocked_between(user_id, other_id):
        flash("لا يمكنك فتح الدردشة مع هذا المستخدم", "danger")
        return redirect(url_for("requests"))

    chat = get_or_create_chat(req.sender_id, req.receiver_id)
    return redirect(url_for("chat_room", chat_id=chat.id))


@app.route("/chat/room/<int:chat_id>", methods=["GET", "POST"])
@login_required
def chat_room(chat_id):
    chat = ChatRoom.query.get_or_404(chat_id)
    user_id = session["user_id"]

    if user_id not in [chat.user1_id, chat.user2_id]:
        flash("غير مصرح", "danger")
        return redirect(url_for("home"))

    other_user = chat.user2 if chat.user1_id == user_id else chat.user1

    if is_blocked_between(user_id, other_user.id):
        flash("تم حظر هذه المحادثة", "danger")
        return redirect(url_for("chats"))

    if request.method == "POST":
        if is_blocked_between(user_id, other_user.id):
            return redirect(url_for("chat_room", chat_id=chat.id))
        
        content = request.form["message"].strip()
        if content:
            msg = Message(
                chat_id=chat.id,
                sender_id=user_id,
                content=content
            )
            chat.last_activity = db.func.now()
            db.session.add(msg)
            db.session.commit()
            return redirect(url_for("chat_room", chat_id=chat.id))

    messages = Message.query.filter_by(
        chat_id=chat.id
    ).order_by(Message.created_at.asc()).all()

    Message.query.filter(
        Message.chat_id == chat.id,
        Message.sender_id != user_id,
        Message.is_read == False
    ).update({"is_read": True})

    db.session.commit()

    return render_template(
        "chat_room.html",
        chat=chat,
        other_user=other_user,
        messages=messages
    )


@app.route("/chats")
@login_required
def chats():
    user_id = session["user_id"]



    chats = ChatRoom.query.filter(
        (ChatRoom.user1_id == user_id) |
        (ChatRoom.user2_id == user_id)
    ).order_by(ChatRoom.last_activity.desc()).all()

    filtered_chats = []
    for chat in chats:
        other_id = chat.user2_id if chat.user1_id == user_id else chat.user1_id
        if not is_blocked_between(user_id, other_id):
            filtered_chats.append(chat)

    chats = filtered_chats

    unread_counts = {}

    for chat in chats:
        count = Message.query.filter(
            Message.chat_id == chat.id,
            Message.sender_id != user_id,
            Message.is_read == False
        ).count()
        unread_counts[chat.id] = count

    return render_template(
        "chats.html",
        chats=chats,
        unread_counts=unread_counts
    )

@app.route("/api/chat/<int:chat_id>/messages")
@login_required
def api_chat_messages(chat_id):
    chat = ChatRoom.query.get_or_404(chat_id)
    user_id = session["user_id"]

    if user_id not in [chat.user1_id, chat.user2_id]:
        return {"error": "unauthorized"}, 403

    messages = Message.query.filter_by(
        chat_id=chat.id
    ).order_by(Message.created_at.asc()).all()

    data = []
    for msg in messages:
        data.append({
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender_id,
            "time": msg.created_at.strftime("%H:%M")
        })

    return {"messages": data}


@app.route("/api/reports", methods=["POST"])
@jwt_required()
def api_submit_report():

    reporter_id = int(get_jwt_identity())

    data = request.get_json(silent=True) or {}

    reported_user_id = data.get("reported_user_id")
    reason = (data.get("reason") or "").strip()
    message_ids = data.get("message_ids") or []

    # Validate reported user
    try:
        reported_user_id = int(reported_user_id)
    except (TypeError, ValueError):
        return jsonify({
            "success": False,
            "message": "Invalid reported user."
        }), 400

    if reporter_id == reported_user_id:
        return jsonify({
            "success": False,
            "message": "You cannot report yourself."
        }), 400

    reported_user = db.session.get(
        User,
        reported_user_id
    )

    if not reported_user:
        return jsonify({
            "success": False,
            "message": "Reported user not found."
        }), 404


    # Validate reason

    if not reason:
        return jsonify({
            "success": False,
            "message": "Report reason is required."
        }), 400

    if len(reason) > 1000:
        return jsonify({
            "success": False,
            "message": "Report reason is too long."
        }), 400


    # Validate message selection

    if not isinstance(message_ids, list):
        return jsonify({
            "success": False,
            "message": "Message IDs must be a list."
        }), 400

    if not message_ids:
        return jsonify({
            "success": False,
            "message": "Select at least one message."
        }), 400


    valid_messages = []

    for message_id in message_ids:

        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "message": "Invalid message ID."
            }), 400

        message = db.session.get(
            Message,
            message_id
        )

        if not message:
            return jsonify({
                "success": False,
                "message": f"Message {message_id} was not found."
            }), 404


        chat = db.session.get(
            ChatRoom,
            message.chat_id
        )

        if not chat:
            return jsonify({
                "success": False,
                "message": "Chat not found."
            }), 404


        participants = {
            chat.user1_id,
            chat.user2_id
        }

        expected_participants = {
            reporter_id,
            reported_user_id
        }

        if participants != expected_participants:
            return jsonify({
                "success": False,
                "message": "One or more selected messages are not from this conversation."
            }), 403


        # A report should reference messages written by
        # the person being reported.
        if message.sender_id != reported_user_id:
            return jsonify({
                "success": False,
                "message": "Only messages sent by the reported user can be selected."
            }), 400

        valid_messages.append(message)


    # Create report
    report = Report(
        reporter_id=reporter_id,
        reported_user_id=reported_user_id,
        reason=reason
    )

    db.session.add(report)
    db.session.flush()


    for message in valid_messages:

        db.session.add(
            ReportMessage(
                report_id=report.id,
                message_id=message.id
            )
        )


    try:
        db.session.commit()

    except Exception:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Could not submit report."
        }), 500


    return jsonify({
        "success": True,
        "message": "Report submitted successfully.",
        "report": {
            "id": report.id,
            "reported_user_id": reported_user_id,
            "message_count": len(valid_messages),
            "status": report.status
        }
    }), 201


@app.route("/submit_report", methods=["POST"])
@login_required
def submit_report():

    report = Report(
        reporter_id=session["user_id"],
        reported_user_id=request.form["reported_user_id"],
        reason=request.form["reason"]
    )

    db.session.add(report)
    db.session.flush()  # get report.id

    messages = json.loads(request.form["messages"])

    for msg_id in messages:
        db.session.add(
            ReportMessage(report_id=report.id, message_id=msg_id)
        )

    db.session.commit()

    return render_template("report_success.html",
                           reported_user_id=request.form["reported_user_id"])



@app.route(
    "/api/users/<int:user_id>/block",
    methods=["POST"]
)
@jwt_required()
def api_block_user(user_id):

    current_user_id = int(
        get_jwt_identity()
    )

    # Cannot block yourself

    if current_user_id == user_id:

        return jsonify({
            "success": False,
            "message": "You cannot block yourself."
        }), 400


    blocked_user = db.session.get(
        User,
        user_id
    )

    if not blocked_user:

        return jsonify({
            "success": False,
            "message": "User not found."
        }), 404


    # Already blocked?

    existing = Block.query.filter_by(
        blocker_id=current_user_id,
        blocked_id=user_id
    ).first()

    if existing:

        return jsonify({
            "success": False,
            "message": "This user is already blocked."
        }), 409


    # Create block

    block = Block(
        blocker_id=current_user_id,
        blocked_id=user_id
    )

    db.session.add(block)


    # Remove pending collaboration requests
    # between these two users
    CollaborationRequest.query.filter(
        (
            (
                CollaborationRequest.sender_id ==
                    current_user_id
            )
            &
            (
                CollaborationRequest.receiver_id ==
                    user_id
            )
        )
        |
        (
            (
                CollaborationRequest.sender_id ==
                    user_id
            )
            &
            (
                CollaborationRequest.receiver_id ==
                    current_user_id
            )
        )
    ).filter(
        CollaborationRequest.status ==
            "pending"
    ).delete(
        synchronize_session=False
    )


    try:

        db.session.commit()

    except Exception:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Could not block user."
        }), 500


    return jsonify({
        "success": True,
        "message": "User blocked successfully.",
        "blocked_user_id": user_id
    }), 200


@app.route("/block/<int:user_id>")
@login_required
def block_user(user_id):

    current_user_id = session["user_id"]

    # prevent blocking yourself
    if current_user_id == user_id:
        flash("لا يمكنك حظر نفسك", "danger")
        return redirect(url_for("home"))

    # check if already blocked
    existing = Block.query.filter_by(
        blocker_id=current_user_id,
        blocked_id=user_id
    ).first()

    if existing:
        flash("تم حظر هذا المستخدم مسبقاً", "info")
        return redirect(url_for("chats"))

    block = Block(
        blocker_id=current_user_id,
        blocked_id=user_id
    )

    db.session.add(block)

    # delete pending collaboration requests
    CollaborationRequest.query.filter(
        (
            (CollaborationRequest.sender_id == current_user_id) &
            (CollaborationRequest.receiver_id == user_id)
        ) |
        (
            (CollaborationRequest.sender_id == user_id) &
            (CollaborationRequest.receiver_id == current_user_id)
        )
    ).delete(synchronize_session=False)

    db.session.commit()

    flash("تم حظر المستخدم بنجاح", "success")
    return redirect(url_for("chats"))


@app.route("/delete_account", methods=["POST"])
@login_required
def delete_account():

    user = User.query.get(session["user_id"])
    password = request.form.get("password")

    # Verify password
    if not check_password_hash(user.password, password):
        flash("incorrect_delete_password", "delete_error")
        return redirect(url_for("profile"))

    user_id = user.id

    # Delete related data manually if no cascade set
    CollaborationRequest.query.filter(
        (CollaborationRequest.sender_id == user_id) |
        (CollaborationRequest.receiver_id == user_id)
    ).delete(synchronize_session=False)

    Block.query.filter(
        (Block.blocker_id == user_id) |
        (Block.blocked_id == user_id)
    ).delete(synchronize_session=False)

    Report.query.filter(
        (Report.reporter_id == user_id) |
        (Report.reported_user_id == user_id)
    ).delete(synchronize_session=False)

    # Delete chat messages
    chats = ChatRoom.query.filter(
        (ChatRoom.user1_id == user_id) |
        (ChatRoom.user2_id == user_id)
    ).all()

    for chat in chats:
        Message.query.filter_by(chat_id=chat.id)\
            .delete(synchronize_session=False)
        db.session.delete(chat)


    # Finally delete user
    db.session.delete(user)

    db.session.commit()

    session.clear()

    flash("Your account has been permanently deleted.", "success")
    return redirect(url_for("home"))



@app.route("/admin")
@admin_required
def admin_dashboard():

    if not session.get("is_admin"):
        return redirect(url_for("login"))

    total_users = User.query.count()
    total_requests = CollaborationRequest.query.count()
    total_reports = Report.query.count()
    banned_users = User.query.filter_by(is_banned=True).count()

    settings = AlgorithmSettings.query.first()

    reports = Report.query.order_by(Report.id.desc()).limit(10).all()
    users = User.query.order_by(User.id.desc()).all()

    weights = {
        "gpa": settings.gpa_weight,
        "commitment": settings.commitment_weight,
        "age": settings.age_weight,
        "year": settings.year_weight,
        "courses": settings.courses_weight,
        "max_courses": settings.max_courses
    }

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_requests=total_requests,
        total_reports=total_reports,
        banned_users=banned_users,
        weights=weights,
        settings=settings,
        reports=reports,
        users=users
    )




@app.route("/admin/update-weights", methods=["POST"])
@admin_required
def update_weights():
    settings = AlgorithmSettings.query.first()

    if not settings:
        seed_algorithm_settings()
        settings = AlgorithmSettings.query.first()

    try:
        settings.gpa_weight = float(request.form.get("gpa_weight", settings.gpa_weight))
        settings.commitment_weight = float(request.form.get("commitment_weight", settings.commitment_weight))
        settings.age_weight = float(request.form.get("age_weight", settings.age_weight))
        settings.year_weight = float(request.form.get("year_weight", settings.year_weight))
        settings.courses_weight = float(request.form.get("courses_weight", settings.courses_weight))
        settings.max_courses = float(request.form.get("max_courses", settings.max_courses))

        db.session.commit()
        flash("تم تحديث الأوزان بنجاح", "success")

    except ValueError:
        flash("قيمة غير صالحة", "danger")

    return redirect(url_for("admin_dashboard"))




@app.route("/admin/delete/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):

    user = User.query.get_or_404(user_id)

    # Delete chat messages
    chats = ChatRoom.query.filter(
        (ChatRoom.user1_id == user_id) |
        (ChatRoom.user2_id == user_id)
    ).all()

    for chat in chats:
        Message.query.filter_by(chat_id=chat.id)\
            .delete(synchronize_session=False)
        db.session.delete(chat)
        

        CollaborationRequest.query.filter(
        (CollaborationRequest.sender_id == user.id) |
        (CollaborationRequest.receiver_id == user.id)
    ).delete()



    db.session.delete(user)
    db.session.commit()

    flash("تم حذف المستخدم نهائياً", "danger")
    return redirect(url_for("admin_dashboard"))



@app.route("/admin/report/ignore/<int:report_id>", methods=["POST"])
@admin_required
def ignore_report(report_id):

    report = Report.query.get_or_404(report_id)

    db.session.delete(report)
    db.session.commit()

    flash("تم تجاهل البلاغ", "info")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/ban/<int:user_id>", methods=["POST"])
@admin_required
def ban_user(user_id):

    user = User.query.get_or_404(user_id)
    user.is_banned = not user.is_banned

    db.session.commit()

    flash("تم تحديث حالة المستخدم", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/banned")
def banned_page():
    return render_template("banned.html")


@app.before_request
def check_ban_status():

    allowed_routes = [
        "login",
        "register",
        "logout",
        "forgot_password",
        "reset_password",
        "banned_page",
        "static"
    ]

    if "user_id" not in session:
        return

    if request.endpoint in allowed_routes:
        return

    user = User.query.get(session["user_id"])

    if user and user.is_banned:
        return redirect(url_for("banned_page"))



@app.context_processor
def inject_unread_messages():    
    if "user_id" not in session:
        return dict(unread_messages=0)

    count = Message.query.join(ChatRoom).filter(
        Message.sender_id != session["user_id"],
        Message.is_read == False,
        (
            (ChatRoom.user1_id == session["user_id"]) |
            (ChatRoom.user2_id == session["user_id"])
        )
    ).count()

    return dict(unread_messages=count)



if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
