from flask import Blueprint, request, jsonify
from database import db, WishlistItem, Product
from auth_utils import jwt_required

wishlist_bp = Blueprint("wishlist", __name__)

@wishlist_bp.route("/", methods=["GET"])
@jwt_required
def get_wishlist(current_user):
    items = WishlistItem.query.filter_by(user_id=current_user.id).all()
    return jsonify([i.to_dict() for i in items]), 200

@wishlist_bp.route("/toggle", methods=["POST"])
@jwt_required
def toggle_wish(current_user):
    product_id = (request.get_json(silent=True) or {}).get("product_id")
    if not product_id:
        return jsonify({"error": "product_id required"}), 400
    product = Product.query.filter_by(id=product_id, active=True).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404
    existing = WishlistItem.query.filter_by(user_id=current_user.id,
                                             product_id=product_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"message": "Removed from wishlist", "wishlisted": False}), 200
    db.session.add(WishlistItem(user_id=current_user.id, product_id=product_id))
    db.session.commit()
    return jsonify({"message": "Added to wishlist", "wishlisted": True}), 200

@wishlist_bp.route("/<int:item_id>", methods=["DELETE"])
@jwt_required
def remove_wish(current_user, item_id):
    item = WishlistItem.query.filter_by(id=item_id, user_id=current_user.id).first()
    if not item:
        return jsonify({"error": "Wishlist item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Removed from wishlist"}), 200
