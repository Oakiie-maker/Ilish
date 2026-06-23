
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, send_file
from flask_cors import CORS
from database import db, init_db
from routes.auth import auth_bp
from routes.products import products_bp
from routes.cart import cart_bp
from routes.wishlist import wishlist_bp
from routes.orders import orders_bp
from routes.admin import admin_bp
from routes.printful import printful_bp
from routes.payfast import payfast_bp
import os

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "ilish-secret-2026")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///ilish.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "ilish-jwt-2026")
    app.config["PRINTFUL_API_KEY"] = os.getenv("PRINTFUL_API_KEY", "1ZXtq5kS2WJl4l7n1r39tl4sFD6TEEAkd8BxHpFw")
    app.config["PRINTFUL_BASE_URL"] = "https://api.printful.com"
    app.config["PAYFAST_MERCHANT_ID"] = os.getenv("PAYFAST_MERCHANT_ID", "")
    app.config["PAYFAST_MERCHANT_KEY"] = os.getenv("PAYFAST_MERCHANT_KEY", "")
    app.config["PAYFAST_PASSPHRASE"] = os.getenv("PAYFAST_PASSPHRASE", "")
    app.config["PAYFAST_SANDBOX"] = True
    app.config["PAYFAST_URL"] = "https://sandbox.payfast.co.za/eng/process"
    app.config["PAYFAST_NOTIFY_URL"] = ""
    app.config["PAYFAST_RETURN_URL"] = ""
    app.config["PAYFAST_CANCEL_URL"] = ""
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)
    app.register_blueprint(auth_bp,     url_prefix="/api/auth")
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(cart_bp,     url_prefix="/api/cart")
    app.register_blueprint(wishlist_bp, url_prefix="/api/wishlist")
    app.register_blueprint(orders_bp,   url_prefix="/api/orders")
    app.register_blueprint(admin_bp,    url_prefix="/api/admin")
    app.register_blueprint(printful_bp, url_prefix="/api/printful")
    app.register_blueprint(payfast_bp,  url_prefix="/api/payfast")
    with app.app_context():
        init_db()
    @app.route("/")
    def index():
        return open("ilish.html").read()
    @app.route("/api/health")
    def health():
        return {"status": "ok", "app": "ILISH API", "version": "1.0.0"}
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
