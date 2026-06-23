import csv, io
from datetime import datetime
from flask import Blueprint, request, jsonify, Response
from database import db, Product, ProductSize, Order, User, PromoCode
from auth_utils import admin_required

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/stats", methods=["GET"])
@admin_required
def stats(current_user):
    orders  = Order.query.all()
    revenue = sum(o.total for o in orders)
    return jsonify({"total_orders": len(orders), "revenue": round(revenue, 2),
                    "total_products": Product.query.filter_by(active=True).count(),
                    "total_users": User.query.count(),
                    "pending_orders": sum(1 for o in orders if o.status == "Pending")}), 200

@admin_bp.route("/products", methods=["GET"])
@admin_required
def list_all_products(current_user):
    return jsonify([p.to_dict() for p in Product.query.order_by(Product.id).all()]), 200

@admin_bp.route("/products", methods=["POST"])
@admin_required
def create_product(current_user):
    body  = request.get_json(silent=True) or {}
    name  = str(body.get("name", "")).strip()
    cat   = str(body.get("category", "")).lower().strip()
    price = body.get("price")
    if not name or not cat or price is None:
        return jsonify({"error": "name, category, price required"}), 400
    p = Product(name=name, category=cat, price=float(price),
                description=str(body.get("description", "")),
                collection=str(body.get("collection", "Collection Zero")),
                badge=str(body.get("badge", "")))
    db.session.add(p)
    db.session.flush()
    for sz, qty in (body.get("stock") or {}).items():
        db.session.add(ProductSize(product_id=p.id, size=sz.upper(), stock=int(qty)))
    db.session.commit()
    return jsonify({"message": "Product created", "product": p.to_dict()}), 201

@admin_bp.route("/products/<int:pid>", methods=["PATCH"])
@admin_required
def update_product(current_user, pid):
    p    = Product.query.get_or_404(pid)
    body = request.get_json(silent=True) or {}
    for field in ["name", "category", "price", "description", "collection", "badge", "active"]:
        if field in body:
            setattr(p, field, body[field])
    if "stock" in body:
        for sz, qty in body["stock"].items():
            row = ProductSize.query.filter_by(product_id=pid, size=sz.upper()).first()
            if row:
                row.stock = int(qty)
            else:
                db.session.add(ProductSize(product_id=pid, size=sz.upper(), stock=int(qty)))
    db.session.commit()
    return jsonify({"message": "Product updated", "product": p.to_dict()}), 200

@admin_bp.route("/products/<int:pid>", methods=["DELETE"])
@admin_required
def delete_product(current_user, pid):
    p = Product.query.get_or_404(pid)
    p.active = False
    db.session.commit()
    return jsonify({"message": "Product removed"}), 200

@admin_bp.route("/orders", methods=["GET"])
@admin_required
def list_orders(current_user):
    return jsonify([o.to_dict() for o in Order.query.order_by(Order.created_at.desc()).all()]), 200

@admin_bp.route("/orders/<int:oid>", methods=["PATCH"])
@admin_required
def update_order(current_user, oid):
    order  = Order.query.get_or_404(oid)
    status = (request.get_json(silent=True) or {}).get("status")
    valid  = {"Pending","Processing","Shipped","Delivered","Cancelled","Refunded"}
    if status not in valid:
        return jsonify({"error": f"Status must be one of: {', '.join(valid)}"}), 400
    order.status = status
    db.session.commit()
    return jsonify({"message": f"Order #{oid} → {status}", "order": order.to_dict()}), 200

@admin_bp.route("/orders/export", methods=["GET"])
@admin_required
def export_csv(current_user):
    orders = Order.query.order_by(Order.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order ID","User","Items","Subtotal","Discount","Shipping",
                     "Total","Promo","Status","PayFast ID","Printful ID","Date"])
    for o in orders:
        items_str = "; ".join(f"{i.product.name if i.product else '?'} x{i.quantity} ({i.size})"
                               for i in o.items)
        writer.writerow([f"ORD-{o.id:06d}",
                         o.user.username if o.user else o.user_id,
                         items_str, o.subtotal, o.discount, o.shipping, o.total,
                         o.promo_code or "", o.status,
                         o.pf_payment_id or "", o.printful_order_id or "",
                         o.created_at.strftime("%Y-%m-%d %H:%M")])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":
                             f"attachment; filename=ilish-orders-{datetime.utcnow().strftime('%Y%m%d')}.csv"})

@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users(current_user):
    return jsonify([u.to_dict() for u in User.query.order_by(User.created_at.desc()).all()]), 200

@admin_bp.route("/promos", methods=["GET"])
@admin_required
def list_promos(current_user):
    return jsonify([p.to_dict() for p in PromoCode.query.all()]), 200

@admin_bp.route("/promos", methods=["POST"])
@admin_required
def create_promo(current_user):
    body     = request.get_json(silent=True) or {}
    code     = str(body.get("code", "")).upper().strip()
    discount = body.get("discount")
    if not code or discount is None:
        return jsonify({"error": "code and discount required"}), 400
    if not (1 <= float(discount) <= 100):
        return jsonify({"error": "Discount must be 1-100"}), 400
    if PromoCode.query.filter_by(code=code).first():
        return jsonify({"error": "Code already exists"}), 409
    p = PromoCode(code=code, discount=float(discount))
    db.session.add(p)
    db.session.commit()
    return jsonify({"message": f"{code} created", "promo": p.to_dict()}), 201

@admin_bp.route("/promos/<int:pid>", methods=["PATCH"])
@admin_required
def update_promo(current_user, pid):
    p    = PromoCode.query.get_or_404(pid)
    body = request.get_json(silent=True) or {}
    if "active"   in body: p.active   = bool(body["active"])
    if "discount" in body: p.discount = float(body["discount"])
    db.session.commit()
    return jsonify({"message": "Promo updated", "promo": p.to_dict()}), 200

@admin_bp.route("/promos/<int:pid>", methods=["DELETE"])
@admin_required
def delete_promo(current_user, pid):
    p = PromoCode.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"message": "Promo deleted"}), 200
