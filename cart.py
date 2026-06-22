from flask import Blueprint, request, jsonify
from database import db, CartItem, Product, ProductSize
from auth_utils import jwt_required

cart_bp = Blueprint("cart", __name__)

@cart_bp.route("/", methods=["GET"])
@jwt_required
def get_cart(current_user):
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    data  = [i.to_dict() for i in items]
    total = sum(i["product"]["price"] * i["quantity"] for i in data)
    return jsonify({"items": data, "subtotal": round(total, 2)}), 200

@cart_bp.route("/add", methods=["POST"])
@jwt_required
def add_to_cart(current_user):
    body       = request.get_json(silent=True) or {}
    product_id = body.get("product_id")
    size       = str(body.get("size", "")).upper()
    qty        = int(body.get("quantity", 1))
    if not product_id or not size:
        return jsonify({"error": "product_id and size required"}), 400
    product  = Product.query.filter_by(id=product_id, active=True).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404
    size_row = ProductSize.query.filter_by(product_id=product_id, size=size).first()
    if not size_row:
        return jsonify({"error": f"Size {size} not available"}), 400
    if size_row.stock < qty:
        return jsonify({"error": f"Only {size_row.stock} left in size {size}"}), 400
    existing = CartItem.query.filter_by(user_id=current_user.id,
                                        product_id=product_id, size=size).first()
    if existing:
        new_qty = existing.quantity + qty
        if new_qty > size_row.stock:
            return jsonify({"error": f"Only {size_row.stock} available in {size}"}), 400
        existing.quantity = new_qty
    else:
        db.session.add(CartItem(user_id=current_user.id,
                                product_id=product_id, size=size, quantity=qty))
    db.session.commit()
    return jsonify({"message": f"{product.name} ({size}) added to bag"}), 200

@cart_bp.route("/<int:item_id>", methods=["PATCH"])
@jwt_required
def update_cart_item(current_user, item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return jsonify({"error": "Cart item not found"}), 404
    qty = int((request.get_json(silent=True) or {}).get("quantity", item.quantity))
    if qty < 1:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Item removed"}), 200
    size_row = ProductSize.query.filter_by(product_id=item.product_id, size=item.size).first()
    if size_row and qty > size_row.stock:
        return jsonify({"error": f"Only {size_row.stock} in stock"}), 400
    item.quantity = qty
    db.session.commit()
    return jsonify({"message": "Cart updated"}), 200

@cart_bp.route("/<int:item_id>", methods=["DELETE"])
@jwt_required
def remove_cart_item(current_user, item_id):
    item = CartItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return jsonify({"error": "Cart item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item removed"}), 200

@cart_bp.route("/clear", methods=["DELETE"])
@jwt_required
def clear_cart(current_user):
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"message": "Cart cleared"}), 200
