import jwt
import functools
from datetime import datetime, timezone, timedelta
from flask import request, jsonify, current_app
from database import User

def create_tokens(user_id, username, is_admin):
    now = datetime.now(timezone.utc)
    secret = current_app.config["JWT_SECRET_KEY"]
    access = jwt.encode({"sub": str(user_id), "username": username, "is_admin": is_admin,
                          "iat": now, "exp": now + timedelta(hours=24), "type": "access"},
                         secret, algorithm="HS256")
    refresh = jwt.encode({"sub": str(user_id), "iat": now,
                           "exp": now + timedelta(days=30), "type": "refresh"},
                          secret, algorithm="HS256")
    return {"access_token": access, "refresh_token": refresh, "token_type": "Bearer"}

def decode_token(token):
    return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])

def _get_token():
    auth = request.headers.get("Authorization", "")
    return auth[7:] if auth.startswith("Bearer ") else None

def jwt_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        token = _get_token()
        if not token:
            return jsonify({"error": "Authorization token required"}), 401
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                raise jwt.InvalidTokenError("Not an access token")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {e}"}), 401
        user = User.query.get(int(payload["sub"]))
        if not user:
            return jsonify({"error": "User not found"}), 401
        kwargs["current_user"] = user
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        token = _get_token()
        if not token:
            return jsonify({"error": "Authorization token required"}), 401
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                raise jwt.InvalidTokenError("Not an access token")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {e}"}), 401
        user = User.query.get(int(payload["sub"]))
        if not user:
            return jsonify({"error": "User not found"}), 401
        if not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        kwargs["current_user"] = user
        return f(*args, **kwargs)
    return wrapper

def optional_jwt(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        token = _get_token()
        user = None
        if token:
            try:
                payload = decode_token(token)
                if payload.get("type") == "access":
                    user = User.query.get(int(payload["sub"]))
            except Exception:
                pass
        kwargs["current_user"] = user
        return f(*args, **kwargs)
    return wrapper
