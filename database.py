from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(40), unique=True, nullable=False, index=True)
    email      = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password   = db.Column(db.String(256), nullable=False)
    is_admin   = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cart_items = db.relationship("CartItem",     backref="user", lazy=True, cascade="all, delete-orphan")
    wish_items = db.relationship("WishlistItem", backref="user", lazy=True, cascade="all, delete-orphan")
    orders     = db.relationship("Order",        backref="user", lazy=True)

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email,
                "is_admin": self.is_admin, "created_at": self.created_at.isoformat()}

class Product(db.Model):
    __tablename__ = "products"
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(120), nullable=False)
    category     = db.Column(db.String(40), nullable=False)
    price        = db.Column(db.Float, nullable=False)
    collection   = db.Column(db.String(80), default="Collection Zero")
    description  = db.Column(db.Text, default="")
    badge        = db.Column(db.String(40), default="")
    active       = db.Column(db.Boolean, default=True)
    printful_id  = db.Column(db.Integer, nullable=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    sizes        = db.relationship("ProductSize", backref="product", lazy=True, cascade="all, delete-orphan")
    order_items  = db.relationship("OrderItem",   backref="product", lazy=True)

    def stock_dict(self):
        return {s.size: s.stock for s in self.sizes}

    def to_dict(self):
        return {"id": self.id, "name": self.name, "category": self.category,
                "price": self.price, "collection": self.collection,
                "description": self.description, "badge": self.badge,
                "active": self.active, "stock": self.stock_dict(),
                "printful_id": self.printful_id}

class ProductSize(db.Model):
    __tablename__ = "product_sizes"
    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    size       = db.Column(db.String(8), nullable=False)
    stock      = db.Column(db.Integer, default=0)

class CartItem(db.Model):
    __tablename__ = "cart_items"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    size       = db.Column(db.String(8), nullable=False)
    quantity   = db.Column(db.Integer, default=1)
    added_at   = db.Column(db.DateTime, default=datetime.utcnow)
    product    = db.relationship("Product")

    def to_dict(self):
        return {"id": self.id, "product": self.product.to_dict(),
                "size": self.size, "quantity": self.quantity}

class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    added_at   = db.Column(db.DateTime, default=datetime.utcnow)
    product    = db.relationship("Product")

    def to_dict(self):
        return {"id": self.id, "product": self.product.to_dict()}

class Order(db.Model):
    __tablename__ = "orders"
    id                = db.Column(db.Integer, primary_key=True)
    user_id           = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subtotal          = db.Column(db.Float, nullable=False)
    discount          = db.Column(db.Float, default=0.0)
    shipping          = db.Column(db.Float, default=0.0)
    total             = db.Column(db.Float, nullable=False)
    promo_code        = db.Column(db.String(40), default="")
    status            = db.Column(db.String(40), default="Pending")
    pf_payment_id     = db.Column(db.String(120), nullable=True)
    pf_payment_status = db.Column(db.String(40), nullable=True)
    printful_order_id = db.Column(db.String(80), nullable=True)
    shipping_address  = db.Column(db.Text, default="{}")
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items             = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id, "subtotal": self.subtotal,
                "discount": self.discount, "shipping": self.shipping, "total": self.total,
                "promo_code": self.promo_code, "status": self.status,
                "pf_payment_id": self.pf_payment_id,
                "printful_order_id": self.printful_order_id,
                "shipping_address": json.loads(self.shipping_address or "{}"),
                "items": [i.to_dict() for i in self.items],
                "created_at": self.created_at.isoformat()}

class OrderItem(db.Model):
    __tablename__ = "order_items"
    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    size       = db.Column(db.String(8), nullable=False)
    quantity   = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {"product_id": self.product_id,
                "name": self.product.name if self.product else "",
                "size": self.size, "quantity": self.quantity,
                "unit_price": self.unit_price,
                "line_total": round(self.unit_price * self.quantity, 2)}

class PromoCode(db.Model):
    __tablename__ = "promo_codes"
    id         = db.Column(db.Integer, primary_key=True)
    code       = db.Column(db.String(40), unique=True, nullable=False, index=True)
    discount   = db.Column(db.Float, nullable=False)
    active     = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "code": self.code,
                "discount": self.discount, "active": self.active}

def init_db():
    db.create_all()
    _seed_products()
    _seed_promos()

def _seed_products():
    if Product.query.count() > 0:
        return
    seed = [
        ("Shadow Hoodie",       "hoodies",    499, "Oversized heavyweight hoodie. Embroidered HOV logo.",      "New",  {"S":8,"M":12,"L":10,"XL":6,"XXL":3}),
        ("Panel Hoodie",        "hoodies",    549, "Bold panel construction. Premium heavyweight cotton.",      "New",  {"S":5,"M":10,"L":8,"XL":5,"XXL":2}),
        ("Tribal Hoodie",       "hoodies",    549, "Tribal detail embroidery. Distressed washes.",              "",     {"S":6,"M":10,"L":9,"XL":4,"XXL":0}),
        ("Paint Splatter Tee",  "tees",       299, "Oversized premium cotton. Paint splatter screen print.",    "New",  {"S":15,"M":20,"L":18,"XL":10,"XXL":5}),
        ("Shadow Logo Tee",     "tees",       299, "Clean oversized cut. Shadow HOV logo print.",               "",     {"S":12,"M":18,"L":15,"XL":8,"XXL":4}),
        ("Tribal Tee",          "tees",       329, "Tribal graphic print. Premium cotton blend.",               "",     {"S":10,"M":15,"L":12,"XL":7,"XXL":3}),
        ("Distressed Cap",      "caps",       199, "Structured 6-panel. Distressed finish. Embroidered logo.",  "New",  {"S":0,"M":20,"L":20,"XL":0,"XXL":0}),
        ("Tribal Cap",          "caps",       199, "Tribal patch detail. Premium materials.",                   "",     {"S":0,"M":15,"L":15,"XL":0,"XXL":0}),
        ("Patch Cap",           "caps",       219, "Embroidered patches. Distressed brim. Limited run.",        "",     {"S":0,"M":10,"L":10,"XL":0,"XXL":0}),
        ("Panel Tracksuit",     "tracksuits", 899, "Matching jacket & pants. Panel construction.",              "New",  {"S":4,"M":8,"L":6,"XL":4,"XXL":2}),
        ("Destroyed Tracksuit", "tracksuits", 949, "Distressed detailing. Premium fabric. Matching set.",       "",     {"S":3,"M":6,"L":5,"XL":3,"XXL":1}),
        ("Tribal Tracksuit",    "tracksuits", 949, "Tribal embroidery throughout. Heavyweight fabric.",         "",     {"S":3,"M":5,"L":4,"XL":2,"XXL":0}),
    ]
    for name, cat, price, desc, badge, stock in seed:
        p = Product(name=name, category=cat, price=price, description=desc, badge=badge)
        db.session.add(p)
        db.session.flush()
        for sz, qty in stock.items():
            db.session.add(ProductSize(product_id=p.id, size=sz, stock=qty))
    db.session.commit()
    print("[ILISH] Products seeded")

def _seed_promos():
    if PromoCode.query.count() > 0:
        return
    db.session.add_all([
        PromoCode(code="HOV20",   discount=20, active=True),
        PromoCode(code="DRIP10",  discount=10, active=True),
        PromoCode(code="ILISH15", discount=15, active=True),
    ])
    db.session.commit()
    print("[ILISH] Promo codes seeded")
