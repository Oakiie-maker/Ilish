import re
import bcrypt
from flask import Blueprint, request, jsonify
from database import db, User
from auth_utils import create_tokens, decode_token, jwt_required
import jwt

auth_bp = Blueprint("auth", __name__)
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
EMAIL_RE    = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

@auth_bp.route("/register", methods=["POST"])
def register():
    data     = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    email    = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    errors   = {}
    if not USERNAME_RE.match(username):
        errors["username"] = "3-20 characters, letters/numbers/_ only"
    if not EMAIL_RE.match(email):
        errors["email"] = "Enter a valid email address"
    if len(password) < 8:
        errors["password"] = "Password must be at least 8 characters"
    elif not re.search(r"[0-9]", password):
        errors["password"] = "Password must include at least one number"
    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 422
    if User.query.filter_by(username=username.lower()).first():
        return jsonify({"error": "Username already taken"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409
    pw_hash  = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    is_admin = User.query.count() == 0
    user     = User(username=username.lower(), email=email, password=pw_hash, is_admin=is_admin)
    db.session.add(user)
    db.session.commit()
    tokens = create_tokens(user.id, user.username, user.is_admin)
    return jsonify({"message": "Account created", "user": user.to_dict(), **tokens}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data     = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip().lower()
    password = str(data.get("password", ""))
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
        return jsonify({"error": "Invalid credentials"}), 401
    tokens = create_tokens(user.id, user.username, user.is_admin)
    return jsonify({"message": "Login successful", "user": user.to_dict(), **tokens}), 200

@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    data  = request.get_json(silent=True) or {}
    token = data.get("refresh_token", "")
    if not token:
        return jsonify({"error": "Refresh token required"}), 400
    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Not a refresh token")
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token expired, please login again"}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({"error": f"Invalid token: {e}"}), 401
    user = User.query.get(payload["sub"])
    if not user:
        return jsonify({"error": "User not found"}), 401
    return jsonify(create_tokens(user.id, user.username, user.is_admin)), 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required
def me(current_user):
    return jsonify({"user": current_user.to_dict()}), 200

@auth_bp.route("/logout", methods=["POST"])
@jwt_required
def logout(current_user):
    return jsonify({"message": "Logged out. Stay dripped."}), 200
