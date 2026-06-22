import hashlib, urllib.parse, requests
from flask import Blueprint, request, jsonify, current_app
from database import db, Order, ProductSize
from auth_utils import jwt_required

payfast_bp = Blueprint("payfast", __name__)

PAYFAST_IPS = {"197.97.145.144","197.97.145.145","197.97.145.146","197.97.145.147",
               "41.74.179.194","41.74.179.195","41.74.179.196","41.74.179.197"}

def _signature(data, passphrase=""):
    filtered  = {k: v for k, v in data.items() if k != "signature" and v != ""}
    param_str = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted(filtered.items()))
    if passphrase:
        param_str += f"&passphrase={urllib.parse.quote_plus(passphrase)}"
    return hashlib.md5(param_str.encode()).hexdigest()

def _verify_itn(data):
    cfg = current_app.config
    if _signature(data, cfg.get("PAYFAST_PASSPHRASE","")) != data.get("signature"):
        return False, "Signature mismatch"
    if not cfg.get("PAYFAST_SANDBOX"):
        ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
        if ip not in PAYFAST_IPS:
            return False, f"Invalid IP: {ip}"
    order_id = data.get("m_payment_id")
    if order_id:
        order = Order.query.get(int(order_id))
        if order and abs(float(data.get("amount_gross", 0)) - order.total) > 0.01:
            return False, "Amount mismatch"
    try:
        url = "https://sandbox.payfast.co.za/eng/query/validate" if cfg.get("PAYFAST_SANDBOX") \
              else "https://www.payfast.co.za/eng/query/validate"
        r = requests.post(url, data=urllib.parse.urlencode(data),
                          headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=10)
        if "VALID" not in r.text:
            return False, "PayFast validation failed"
    except Exception as e:
        return False, str(e)
    return True, "ok"

@payfast_bp.route("/initiate/<int:order_id>", methods=["POST"])
@jwt_required
def initiate(current_user, order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
    if not order: return jsonify({"error": "Order not found"}), 404
    if order.pf_payment_status == "COMPLETE": return jsonify({"error": "Already paid"}), 400
    cfg = current_app.config
    data = {
        "merchant_id":      cfg["PAYFAST_MERCHANT_ID"],
        "merchant_key":     cfg["PAYFAST_MERCHANT_KEY"],
        "return_url":       cfg["PAYFAST_RETURN_URL"],
        "cancel_url":       cfg["PAYFAST_CANCEL_URL"],
        "notify_url":       cfg["PAYFAST_NOTIFY_URL"],
        "name_first":       current_user.username,
        "email_address":    current_user.email,
        "m_payment_id":     str(order.id),
        "amount":           f"{order.total:.2f}",
        "item_name":        f"ILISH Order #{order.id}",
        "item_description": f"HOV Collection Zero — {len(order.items)} item(s)",
    }
    data["signature"] = _signature(data, cfg.get("PAYFAST_PASSPHRASE",""))
    return jsonify({"payfast_url": cfg["PAYFAST_URL"], "payment_data": data}), 200

@payfast_bp.route("/notify", methods=["POST"])
def notify():
    data = request.form.to_dict()
    valid, reason = _verify_itn(data)
    if not valid:
        current_app.logger.warning(f"[PayFast ITN] Invalid: {reason}")
        return "Invalid", 400
    order_id  = data.get("m_payment_id")
    pf_status = data.get("payment_status")
    if order_id:
        order = Order.query.get(int(order_id))
        if order:
            order.pf_payment_id     = data.get("pf_payment_id")
            order.pf_payment_status = pf_status
            if pf_status == "COMPLETE":
                order.status = "Processing"
            elif pf_status in ("FAILED", "CANCELLED"):
                order.status = "Cancelled"
                for item in order.items:
                    sz = ProductSize.query.filter_by(product_id=item.product_id, size=item.size).first()
                    if sz: sz.stock += item.quantity
            db.session.commit()
    return "OK", 200

@payfast_bp.route("/return", methods=["GET"])
def pf_return():
    return jsonify({"message": "Payment successful! Welcome to the HOV movement."}), 200

@payfast_bp.route("/cancel", methods=["GET"])
def pf_cancel():
    return jsonify({"message": "Payment cancelled. Your order is saved."}), 200
