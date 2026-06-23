import json, requests
from flask import Blueprint, request, jsonify, current_app
from database import db, Order, Product, ProductSize
from auth_utils import admin_required, jwt_required

printful_bp = Blueprint("printful", __name__)

def _headers():
    key = current_app.config.get("PRINTFUL_API_KEY", "")
    if not key:
        return None
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

def _get(path):
    h = _headers()
    if not h: return None, "PRINTFUL_API_KEY not set"
    r = requests.get(f"{current_app.config['PRINTFUL_BASE_URL']}{path}", headers=h, timeout=10)
    if r.status_code != 200: return None, r.json().get("error", {}).get("message", "Error")
    return r.json().get("result"), None

def _post(path, payload):
    h = _headers()
    if not h: return None, "PRINTFUL_API_KEY not set"
    r = requests.post(f"{current_app.config['PRINTFUL_BASE_URL']}{path}", headers=h, json=payload, timeout=15)
    d = r.json()
    if r.status_code not in (200, 201): return None, d.get("error", {}).get("message", "Error")
    return d.get("result"), None

@printful_bp.route("/products", methods=["GET"])
@admin_required
def pf_products(current_user):
    result, err = _get("/store/products")
    if err: return jsonify({"error": err}), 502
    return jsonify(result), 200

@printful_bp.route("/sync", methods=["POST"])
@admin_required
def pf_sync(current_user):
    result, err = _get("/store/products")
    if err: return jsonify({"error": err}), 502
    synced = 0
    for item in result:
        pf_id  = item["id"]
        detail, derr = _get(f"/store/products/{pf_id}")
        if derr or not detail: continue
        sync_product = detail.get("sync_product", {})
        variants     = detail.get("sync_variants", [])
        p = Product.query.filter_by(printful_id=pf_id).first()
        if not p:
            name = sync_product.get("name", "HOV Product")
            cat  = next((c for kw,c in [("hoodie","hoodies"),("tee","tees"),
                                         ("cap","caps"),("track","tracksuits")] if kw in name.lower()), "hoodies")
            p = Product(name=name, category=cat, price=0, printful_id=pf_id)
            db.session.add(p)
            db.session.flush()
        if variants:
            p.price = float(variants[0].get("retail_price") or 0)
        for v in variants:
            option = next((o["value"] for o in v.get("options", []) if o["id"] == "size"), None)
            if not option: continue
            size = option.upper()
            row  = ProductSize.query.filter_by(product_id=p.id, size=size).first()
            if not row:
                db.session.add(ProductSize(product_id=p.id, size=size, stock=10))
        synced += 1
    db.session.commit()
    return jsonify({"message": f"Synced {synced} products from Printful"}), 200

@printful_bp.route("/order/<int:order_id>", methods=["POST"])
@admin_required
def submit_to_printful(current_user, order_id):
    order   = Order.query.get_or_404(order_id)
    address = json.loads(order.shipping_address or "{}")
    if not address:
        return jsonify({"error": "Order has no shipping address"}), 400
    pf_items = [{"sync_variant_id": i.product.printful_id, "quantity": i.quantity}
                for i in order.items if i.product and i.product.printful_id]
    if not pf_items:
        return jsonify({"error": "No Printful-linked items in this order"}), 400
    payload = {
        "recipient": {
            "name": address.get("name", ""),
            "address1": address.get("address1", ""),
            "city": address.get("city", ""),
            "state_code": address.get("province", ""),
            "country_code": address.get("country", "ZA"),
            "zip": address.get("postal_code", ""),
            "email": order.user.email if order.user else "",
        },
        "items": pf_items,
        "retail_costs": {"total": str(order.total)},
    }
    result, err = _post("/orders", payload)
    if err: return jsonify({"error": err}), 502
    order.printful_order_id = str(result.get("id"))
    order.status = "Processing"
    db.session.commit()
    return jsonify({"message": "Submitted to Printful",
                    "printful_order_id": order.printful_order_id}), 200

@printful_bp.route("/order/<int:order_id>", methods=["GET"])
@jwt_required
def printful_status(current_user, order_id):
    order = Order.query.get_or_404(order_id)
    if not order.printful_order_id:
        return jsonify({"error": "Not submitted to Printful yet"}), 404
    result, err = _get(f"/orders/{order.printful_order_id}")
    if err: return jsonify({"error": err}), 502
    return jsonify(result), 200

@printful_bp.route("/webhook", methods=["POST"])
def printful_webhook():
    data  = request.get_json(silent=True) or {}
    event = data.get("type", "")
    if event == "shipment_sent":
        pf_oid = str(data.get("data", {}).get("order", {}).get("id", ""))
        order  = Order.query.filter_by(printful_order_id=pf_oid).first()
        if order:
            order.status = "Shipped"
            db.session.commit()
    return jsonify({"received": True}), 200
