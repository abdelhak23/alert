"""
AlertPro — Python Flask Backend
================================
Provides a REST API for managing products and order requests.
The frontend HTML files communicate with this backend via fetch().

Run:
    pip install flask flask-cors pillow
    python app.py

API available at: http://localhost:5000
"""

import os
import json
import uuid
import base64
import datetime
from io import BytesIO

from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS
from PIL import Image

# ── CONFIG ──────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR  = os.path.join(BASE_DIR, '..', 'frontend')
DATA_FILE   = os.path.join(BASE_DIR, 'data', 'products.json')
ORDERS_FILE = os.path.join(BASE_DIR, 'data', 'orders.json')
IMAGES_DIR  = os.path.join(BASE_DIR, 'data', 'images')
ADMIN_USER  = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS  = os.environ.get('ADMIN_PASS', 'admin123')
IMAGE_MAX_W = 800      # max width for uploaded images (px)
IMAGE_QUALITY = 82     # JPEG quality (0-100)

# ── INIT ─────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*"}})

os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)


# ── HELPERS ──────────────────────────────────────────────────────────────────
def load_products():
    if not os.path.exists(DATA_FILE):
        return _default_products()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_products(products):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


def load_orders():
    if not os.path.exists(ORDERS_FILE):
        return []
    with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_orders(orders):
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)


def next_id(items):
    return max((i['id'] for i in items), default=0) + 1


def process_image(b64_data: str) -> str:
    """
    Accepts a base64 data-URL, resizes to max IMAGE_MAX_W px wide,
    saves as JPEG on disk, returns the public URL path.
    """
    if not b64_data:
        return ''
    # Strip data-URL prefix if present
    if ',' in b64_data:
        b64_data = b64_data.split(',', 1)[1]

    raw = base64.b64decode(b64_data)
    img = Image.open(BytesIO(raw)).convert('RGB')

    w, h = img.size
    if w > IMAGE_MAX_W:
        h = int(h * IMAGE_MAX_W / w)
        w = IMAGE_MAX_W
        img = img.resize((w, h), Image.LANCZOS)

    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(IMAGES_DIR, filename)
    img.save(filepath, 'JPEG', quality=IMAGE_QUALITY)
    return f"/api/images/{filename}"


def check_auth():
    data = request.get_json(silent=True) or {}
    u = data.get('username') or request.args.get('username', '')
    p = data.get('password') or request.args.get('password', '')
    return u == ADMIN_USER and p == ADMIN_PASS


# ── SERVE FRONTEND ────────────────────────────────────────────────────────────
@app.route('/')
def serve_store():
    return send_from_directory(STATIC_DIR, 'store.html')


@app.route('/admin')
@app.route('/admin.html')
def serve_admin():
    return send_from_directory(STATIC_DIR, 'admin.html')


# ── AUTH ──────────────────────────────────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        return jsonify({'ok': True, 'message': 'Login successful'})
    return jsonify({'ok': False, 'message': 'Invalid credentials'}), 401


# ── PRODUCTS (public read) ────────────────────────────────────────────────────
@app.route('/api/products', methods=['GET'])
def api_get_products():
    products = load_products()
    category = request.args.get('category')
    if category:
        products = [p for p in products if p.get('category') == category]
    return jsonify(products)


@app.route('/api/products/<int:pid>', methods=['GET'])
def api_get_product(pid):
    products = load_products()
    product = next((p for p in products if p['id'] == pid), None)
    if not product:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(product)


# ── PRODUCTS (admin write) ────────────────────────────────────────────────────
@app.route('/api/products', methods=['POST'])
def api_create_product():
    data = request.get_json(silent=True) or {}
    if data.get('username') != ADMIN_USER or data.get('password') != ADMIN_PASS:
        return jsonify({'error': 'Unauthorized'}), 401

    required = ['name', 'category', 'price', 'desc']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    products = load_products()
    image_url = ''
    if data.get('image'):
        try:
            image_url = process_image(data['image'])
        except Exception as e:
            return jsonify({'error': f'Image processing failed: {e}'}), 400

    product = {
        'id':       next_id(products),
        'name':     data['name'],
        'category': data['category'],
        'price':    float(data['price']),
        'oldPrice': float(data['oldPrice']) if data.get('oldPrice') else None,
        'badge':    data.get('badge', ''),
        'desc':     data['desc'],
        'image':    image_url,
        'createdAt': datetime.datetime.utcnow().isoformat() + 'Z',
    }
    products.append(product)
    save_products(products)
    return jsonify(product), 201


@app.route('/api/products/<int:pid>', methods=['PUT'])
def api_update_product(pid):
    data = request.get_json(silent=True) or {}
    if data.get('username') != ADMIN_USER or data.get('password') != ADMIN_PASS:
        return jsonify({'error': 'Unauthorized'}), 401

    products = load_products()
    idx = next((i for i, p in enumerate(products) if p['id'] == pid), None)
    if idx is None:
        return jsonify({'error': 'Not found'}), 404

    p = products[idx]

    # Handle image: new base64 → process; empty string → remove; omitted → keep existing
    if 'image' in data:
        if data['image'] and not data['image'].startswith('/api/'):
            # New base64 upload — delete old file first
            _delete_image_file(p.get('image', ''))
            try:
                p['image'] = process_image(data['image'])
            except Exception as e:
                return jsonify({'error': f'Image processing failed: {e}'}), 400
        elif data['image'] == '':
            _delete_image_file(p.get('image', ''))
            p['image'] = ''
        # else: data['image'] is already a /api/images/... URL — keep it

    for field in ['name', 'category', 'badge', 'desc']:
        if field in data:
            p[field] = data[field]
    if 'price' in data:
        p['price'] = float(data['price'])
    if 'oldPrice' in data:
        p['oldPrice'] = float(data['oldPrice']) if data['oldPrice'] else None

    p['updatedAt'] = datetime.datetime.utcnow().isoformat() + 'Z'
    products[idx] = p
    save_products(products)
    return jsonify(p)


@app.route('/api/products/<int:pid>', methods=['DELETE'])
def api_delete_product(pid):
    data = request.get_json(silent=True) or {}
    if data.get('username') != ADMIN_USER or data.get('password') != ADMIN_PASS:
        return jsonify({'error': 'Unauthorized'}), 401

    products = load_products()
    product = next((p for p in products if p['id'] == pid), None)
    if not product:
        return jsonify({'error': 'Not found'}), 404

    _delete_image_file(product.get('image', ''))
    products = [p for p in products if p['id'] != pid]
    save_products(products)
    return jsonify({'ok': True, 'deleted': pid})


def _delete_image_file(url: str):
    if not url or not url.startswith('/api/images/'):
        return
    filename = url.split('/')[-1]
    filepath = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)


# ── IMAGES ────────────────────────────────────────────────────────────────────
@app.route('/api/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)


# ── ORDERS ────────────────────────────────────────────────────────────────────
@app.route('/api/orders', methods=['POST'])
def api_create_order():
    data = request.get_json(silent=True) or {}
    required = ['name', 'phone', 'message']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'Missing field: {field}'}), 400

    orders = load_orders()
    order = {
        'id':        next_id(orders),
        'name':      data['name'],
        'phone':     data['phone'],
        'email':     data.get('email', ''),
        'city':      data.get('city', ''),
        'message':   data['message'],
        'status':    'new',
        'createdAt': datetime.datetime.utcnow().isoformat() + 'Z',
    }
    orders.append(order)
    save_orders(orders)
    print(f"[ORDER] #{order['id']} from {order['name']} ({order['phone']})")
    return jsonify({'ok': True, 'orderId': order['id']}), 201


@app.route('/api/orders', methods=['GET'])
def api_get_orders():
    if request.args.get('username') != ADMIN_USER or request.args.get('password') != ADMIN_PASS:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(load_orders())


@app.route('/api/orders/<int:oid>', methods=['PUT'])
def api_update_order(oid):
    data = request.get_json(silent=True) or {}
    if data.get('username') != ADMIN_USER or data.get('password') != ADMIN_PASS:
        return jsonify({'error': 'Unauthorized'}), 401

    orders = load_orders()
    idx = next((i for i, o in enumerate(orders) if o['id'] == oid), None)
    if idx is None:
        return jsonify({'error': 'Not found'}), 404

    if 'status' in data:
        orders[idx]['status'] = data['status']
    save_orders(orders)
    return jsonify(orders[idx])


# ── DEFAULT PRODUCTS ──────────────────────────────────────────────────────────
def _default_products():
    """No default products — admin uploads all products via the admin panel."""
    save_products([])
    return []


# ── RUN ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 50)
    print("  AlertPro Backend")
    print("  Store  → http://localhost:5000")
    print("  Admin  → http://localhost:5000/admin")
    print("  API    → http://localhost:5000/api/products")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
