from flask import Blueprint, request, jsonify
from database import db, Product
from auth_utils import optional_jwt

products_bp = Blueprint("products", __name__)

@products_bp.route("/", methods=["GET"])
@optional_jwt
def list_products(current_user):
    category = request.args.get("category", "").lower()
    q        = request.args.get("q", "").lower()
    query    = Product.query.filter_by(active=True)
    if category and category != "all":
        query = query.filter_by(category=category)
    if q:
        query = query.filter(db.or_(Product.name.ilike(f"%{q}%"),
                                    Product.description.ilike(f"%{q}%")))
    return jsonify([p.to_dict() for p in query.order_by(Product.id).all()]), 200

@products_bp.route("/<int:product_id>", methods=["GET"])
def get_product(product_id):
    p = Product.query.filter_by(id=product_id, active=True).first_or_404()
    return jsonify(p.to_dict()), 200
