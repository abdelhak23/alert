# AlertPro — Safety Equipment Store

A complete store website for safety & protection equipment with a Python/Flask backend.

---

## Project Structure

```
alertpro/
├── backend/
│   ├── app.py              ← Flask API server
│   ├── requirements.txt    ← Python dependencies
│   └── data/               ← Created automatically on first run
│       ├── products.json
│       ├── orders.json
│       └── images/         ← Uploaded product images saved here
├── frontend/
│   ├── store.html          ← Public store page
│   └── admin.html          ← Admin panel (password protected)
└── README.md
```

---

## Setup & Run

### 1. Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the server

```bash
python app.py
```

### 3. Open in browser

| Page   | URL                          |
|--------|------------------------------|
| Store  | http://localhost:5000        |
| Admin  | http://localhost:5000/admin  |

---

## Admin Login

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

To change credentials, set environment variables before running:

```bash
ADMIN_USER=myuser ADMIN_PASS=mysecretpass python app.py
```

---

## REST API Endpoints

### Products (public)
| Method | Endpoint                  | Description            |
|--------|---------------------------|------------------------|
| GET    | `/api/products`           | List all products      |
| GET    | `/api/products?category=gloves` | Filter by category |
| GET    | `/api/products/<id>`      | Get single product     |

### Products (admin — requires username + password in JSON body)
| Method | Endpoint                  | Description            |
|--------|---------------------------|------------------------|
| POST   | `/api/products`           | Create product         |
| PUT    | `/api/products/<id>`      | Update product         |
| DELETE | `/api/products/<id>`      | Delete product         |

### Orders
| Method | Endpoint        | Description              |
|--------|-----------------|--------------------------|
| POST   | `/api/orders`   | Submit an order request  |
| GET    | `/api/orders`   | List orders (admin only) |
| PUT    | `/api/orders/<id>` | Update order status   |

### Images
| Method | Endpoint              | Description          |
|--------|-----------------------|----------------------|
| GET    | `/api/images/<file>`  | Serve a product image |

---

## How Product Images Work

1. In the **Admin Panel**, click a product → Edit → upload an image.
2. The image is sent as base64 to `/api/products` (POST or PUT).
3. The backend resizes it to max 800px wide and saves it as a JPEG in `backend/data/images/`.
4. The product record stores the URL `/api/images/<filename>`.
5. The store page fetches products from `/api/products` and displays the images.

---

## Notes

- The frontend HTML files call `http://localhost:5000/api/...` automatically when served by Flask.
- For production, replace Flask's dev server with **gunicorn**:
  ```bash
  pip install gunicorn
  gunicorn -w 4 -b 0.0.0.0:5000 app:app
  ```
- All data is stored as JSON files in `backend/data/` — no database needed.
