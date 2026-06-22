import json
from flask import Blueprint, request, jsonify
from database import db, Order, OrderItem, CartItem, ProductSize, PromoCode
from auth_utils import jwt_required

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/checkout", methods=["POST"])
@jwt_required
def checkout(current_user):
    body       = request.get_json(silent=True) or {}
    promo_code = str(body.get("promo_code", "")).upper().strip()
    address    = body.get("shipping_address", {})
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({"error": "Your cart is empty"}), 400
    order_item_data = []
    subtotal = 0.0
    for ci in cart_items:
        size_row = ProductSize.query.filter_by(product_id=ci.product_id, size=ci.size).first()
        if not size_row or size_row.stock < ci.quantity:
            return jsonify({"error": f"{ci.product.name} ({ci.size}) has insufficient stock",
                            "available": size_row.stock if size_row else 0}), 400
        subtotal += ci.quantity * ci.product.price
        order_item_data.append({"product_id": ci.product_id, "size": ci.size,
                                 "quantity": ci.quantity, "unit_price": ci.product.price,
                                 "size_row": size_row})
    discount = 0.0
    promo_applied = ""
    if promo_code:
        promo = PromoCode.query.filter_by(code=promo_code, active=True).first()
        if not promo:
            return jsonify({"error": "Invalid or expired promo code"}), 400
        discount = round(subtotal * promo.discount / 100, 2)
        promo_applied = promo.code
    after_discount = subtotal - discount
    shipping = 0.0 if after_discount >= 500 else 50.0
    total    = round(after_discount + shipping, 2)
    order = Order(user_id=current_user.id, subtotal=round(subtotal, 2),
                  discount=discount, shipping=shipping, total=total,
                  promo_code=promo_applied, status="Pending",
                  shipping_address=json.dumps(address))
    db.session.add(order)
    db.session.flush()
    for d in order_item_data:
        db.session.add(OrderItem(order_id=order.id, product_id=d["product_id"],
                                  size=d["size"], quantity=d["quantity"],
                                  unit_price=d["unit_price"]))
        d["size_row"].stock -= d["quantity"]
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"message": "Order placed!", "order": order.to_dict()}), 201

@orders_bp.route("/", methods=["GET"])
@jwt_required
def order_history(current_user):
    orders = Order.query.filter_by(user_id=current_user.id)\
                        .order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders]), 200

@orders_bp.route("/<int:order_id>", methods=["GET"])
@jwt_required
def get_order(current_user, order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order.to_dict()), 200
