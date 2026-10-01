import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
DATABASE = BASE_DIR / "catalogo.db"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
PAYMENT_METHODS = {"Efectivo", "Transferencia", "Cheque"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cambia-esta-clave-antes-de-publicar")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get("ADMIN_PASSWORD", "admin123"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with connect_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                UNIQUE(company_id, name)
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                image TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL CHECK(price >= 0),
                stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
                company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
                brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
                kind TEXT NOT NULL CHECK(kind IN ('Sol', 'Receta')),
                description TEXT NOT NULL DEFAULT '',
                featured INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                buyer_name TEXT NOT NULL,
                buyer_phone TEXT NOT NULL DEFAULT '',
                total REAL NOT NULL,
                payment_breakdown TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pendiente'
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
                product_name TEXT NOT NULL,
                unit_price REAL NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0)
            );
            """
        )
        defaults = {
            "store_name": "LUMEN ÓPTICA",
            "store_tagline": "Una nueva forma de mirar.",
            "whatsapp": "",
        }
        db.executemany(
            "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)", defaults.items()
        )
        if db.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 0:
            company_id = db.execute(
                "INSERT INTO companies(name, description) VALUES (?, ?)",
                ("Casa Matiz", "Selección independiente para todos los días."),
            ).lastrowid
            brand_id = db.execute(
                "INSERT INTO brands(company_id, name) VALUES (?, ?)",
                (company_id, "Norte"),
            ).lastrowid
            db.executemany(
                """INSERT INTO products
                   (name, image, price, stock, company_id, brand_id, kind, description, featured)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        "Marea 02",
                        "https://images.unsplash.com/photo-1511499767150-a48a237f0083?auto=format&fit=crop&w=1000&q=85",
                        78500,
                        8,
                        company_id,
                        brand_id,
                        "Sol",
                        "Acetato translúcido y líneas suaves.",
                        1,
                    ),
                    (
                        "Línea 01",
                        "https://images.unsplash.com/photo-1574258495973-f010dfbb5371?auto=format&fit=crop&w=1000&q=85",
                        69200,
                        4,
                        company_id,
                        brand_id,
                        "Receta",
                        "Un clásico liviano para todos los días.",
                        1,
                    ),
                ],
            )


def get_settings():
    with connect_db() as db:
        return {row["key"]: row["value"] for row in db.execute("SELECT key, value FROM settings")}


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


@app.context_processor
def inject_template_helpers():
    return {"csrf_token": csrf_token, "settings": get_settings()}


app.jinja_env.filters["from_json"] = json.loads


@app.before_request
def protect_forms():
    if request.method == "POST":
        submitted = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        expected = session.get("csrf_token", "")
        if not submitted or not secrets.compare_digest(submitted, expected):
            if request.is_json:
                return jsonify(error="La sesión venció. Actualizá la página e intentá de nuevo."), 400
            return "Solicitud inválida. Actualizá la página e intentá de nuevo.", 400


def admin_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


@app.get("/")
def storefront():
    with connect_db() as db:
        companies = [dict(row) for row in db.execute("SELECT * FROM companies ORDER BY name").fetchall()]
        brands = [dict(row) for row in db.execute(
            "SELECT brands.*, companies.name AS company_name FROM brands JOIN companies ON companies.id = brands.company_id ORDER BY brands.name"
        ).fetchall()]
        products = [dict(row) for row in db.execute(
            """SELECT products.*, companies.name AS company_name, brands.name AS brand_name
               FROM products JOIN companies ON companies.id = products.company_id
               JOIN brands ON brands.id = products.brand_id ORDER BY products.id DESC"""
        ).fetchall()]
        featured = [dict(row) for row in db.execute(
            """SELECT products.*, companies.name AS company_name, brands.name AS brand_name
               FROM products JOIN companies ON companies.id = products.company_id
               JOIN brands ON brands.id = products.brand_id
               WHERE products.featured = 1 ORDER BY products.id DESC"""
        ).fetchall()]
    return render_template(
        "index.html", companies=companies, brands=brands, products=products, featured=featured
    )


@app.post("/order")
def create_order():
    payload = request.get_json(silent=True) or {}
    buyer_name = str(payload.get("buyer_name", "")).strip()[:100]
    buyer_phone = str(payload.get("buyer_phone", "")).strip()[:40]
    items = payload.get("items")
    payments = payload.get("payments")
    if not buyer_name or not isinstance(items, list) or not items:
        return jsonify(error="Ingresá tu nombre y agregá al menos un anteojo."), 400
    if not isinstance(payments, list) or not payments:
        return jsonify(error="Elegí cómo querés pagar."), 400
    normalized_payments = []
    for payment in payments:
        try:
            method = str(payment["method"])
            percent = int(payment["percent"])
        except (KeyError, TypeError, ValueError):
            return jsonify(error="Revisá los porcentajes de pago."), 400
        if method not in PAYMENT_METHODS or not 1 <= percent <= 100:
            return jsonify(error="Los métodos de pago o porcentajes no son válidos."), 400
        normalized_payments.append({"method": method, "percent": percent})
    if len({payment["method"] for payment in normalized_payments}) != len(normalized_payments):
        return jsonify(error="Cada método de pago se puede agregar una sola vez."), 400
    if sum(payment["percent"] for payment in normalized_payments) != 100:
        return jsonify(error="Los porcentajes de pago deben sumar 100%."), 400

    quantities = {}
    try:
        for item in items:
            product_id, quantity = int(item["id"]), int(item["quantity"])
            if quantity < 1 or quantity > 99:
                raise ValueError
            quantities[product_id] = quantities.get(product_id, 0) + quantity
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Hay cantidades de productos inválidas."), 400

    order_id = f"OC-{secrets.token_hex(3).upper()}"
    try:
        with connect_db() as db:
            db.execute("BEGIN IMMEDIATE")
            saved_items = []
            total = 0
            for product_id, quantity in quantities.items():
                product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
                if not product or quantity > product["stock"]:
                    raise ValueError("Uno de los anteojos ya no tiene esa cantidad disponible.")
                line_total = product["price"] * quantity
                total += line_total
                saved_items.append((product, quantity))
            db.execute(
                "INSERT INTO orders(id, created_at, buyer_name, buyer_phone, total, payment_breakdown) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    order_id,
                    datetime.now().strftime("%d/%m/%Y %H:%M"),
                    buyer_name,
                    buyer_phone,
                    total,
                    json.dumps(normalized_payments, ensure_ascii=False),
                ),
            )
            for product, quantity in saved_items:
                db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product["id"]))
                db.execute(
                    "INSERT INTO order_items(order_id, product_id, product_name, unit_price, quantity) VALUES (?, ?, ?, ?, ?)",
                    (order_id, product["id"], product["name"], product["price"], quantity),
                )
    except ValueError as error:
        return jsonify(error=str(error)), 409

    settings = get_settings()
    whatsapp_number = "".join(char for char in settings.get("whatsapp", "") if char.isdigit())
    message = quote(f"Hola! Me interesa comprar, mi orden de compra es: {order_id}")
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={message}" if whatsapp_number else f"https://wa.me/?text={message}"
    return jsonify(order_id=order_id, whatsapp_url=whatsapp_url)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if session.get("admin"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = os.environ.get("ADMIN_USERNAME", "admin")
        if request.form.get("username", "") == username and check_password_hash(
            ADMIN_PASSWORD_HASH, request.form.get("password", "")
        ):
            session.clear()
            session["admin"] = True
            csrf_token()
            return redirect(url_for("admin_dashboard"))
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.get("/admin/panel")
@admin_required
def admin_dashboard():
    tab = request.args.get("tab", "productos")
    with connect_db() as db:
        products = [dict(row) for row in db.execute(
            """SELECT products.*, brands.name AS brand_name, companies.name AS company_name
               FROM products JOIN brands ON brands.id = products.brand_id
               JOIN companies ON companies.id = products.company_id ORDER BY products.id DESC"""
        ).fetchall()]
        companies = [dict(row) for row in db.execute("SELECT * FROM companies ORDER BY name").fetchall()]
        brands = [dict(row) for row in db.execute(
            "SELECT brands.*, companies.name AS company_name FROM brands JOIN companies ON companies.id = brands.company_id ORDER BY brands.name"
        ).fetchall()]
        orders = [dict(row) for row in db.execute("SELECT * FROM orders ORDER BY rowid DESC").fetchall()]
        order_items = {}
        for order in orders:
            order_items[order["id"]] = [dict(row) for row in db.execute(
                "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order["id"],)
            ).fetchall()]
    return render_template(
        "admin.html",
        tab=tab,
        products=products,
        companies=companies,
        brands=brands,
        orders=orders,
        order_items=order_items,
    )


def save_uploaded_image(file):
    if not file or not file.filename:
        return ""
    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Usá una imagen PNG, JPG, WEBP o GIF.")
    stored_name = f"{uuid4().hex}.{extension}"
    file.save(UPLOAD_DIR / stored_name)
    return stored_name


@app.post("/admin/products")
@admin_required
def save_product():
    product_id = request.form.get("product_id", "").strip()
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    try:
        company_id = int(request.form.get("company_id", ""))
        brand_id = int(request.form.get("brand_id", ""))
        price = float(request.form.get("price", ""))
        stock = int(request.form.get("stock", ""))
        if not name or price < 0 or stock < 0:
            raise ValueError
    except ValueError:
        flash("Completá nombre, precio, stock, empresa y marca con datos válidos.", "error")
        return redirect(url_for("admin_dashboard", tab="productos"))
    with connect_db() as db:
        valid_brand = db.execute(
            "SELECT id FROM brands WHERE id = ? AND company_id = ?", (brand_id, company_id)
        ).fetchone()
        if not valid_brand:
            flash("La marca debe pertenecer a la empresa seleccionada.", "error")
            return redirect(url_for("admin_dashboard", tab="productos"))
        existing = db.execute("SELECT image FROM products WHERE id = ?", (product_id,)).fetchone() if product_id else None
        if product_id and not existing:
            flash("No se encontró el anteojo para editar.", "error")
            return redirect(url_for("admin_dashboard", tab="productos"))
        try:
            uploaded = save_uploaded_image(request.files.get("image"))
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("admin_dashboard", tab="productos"))
        image = uploaded or (existing["image"] if existing else "")
        values = (
            name,
            image,
            price,
            stock,
            company_id,
            brand_id,
            request.form.get("kind", "Sol") if request.form.get("kind") in {"Sol", "Receta"} else "Sol",
            description,
            int(request.form.get("featured") == "on"),
        )
        if product_id:
            db.execute(
                """UPDATE products SET name=?, image=?, price=?, stock=?, company_id=?, brand_id=?, kind=?, description=?, featured=? WHERE id=?""",
                (*values, product_id),
            )
            flash("Anteojo actualizado.", "success")
        else:
            db.execute(
                """INSERT INTO products(name, image, price, stock, company_id, brand_id, kind, description, featured)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                values,
            )
            flash("Anteojo creado.", "success")
    return redirect(url_for("admin_dashboard", tab="productos"))


@app.post("/admin/products/<int:product_id>/delete")
@admin_required
def delete_product(product_id):
    with connect_db() as db:
        db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    flash("Anteojo eliminado del catálogo.", "success")
    return redirect(url_for("admin_dashboard", tab="productos"))


@app.post("/admin/companies")
@admin_required
def save_company():
    company_id = request.form.get("company_id", "").strip()
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if not name:
        flash("El nombre de la empresa es obligatorio.", "error")
    else:
        with connect_db() as db:
            if company_id:
                db.execute("UPDATE companies SET name = ?, description = ? WHERE id = ?", (name, description, company_id))
            else:
                db.execute("INSERT INTO companies(name, description) VALUES (?, ?)", (name, description))
        flash("Empresa guardada.", "success")
    return redirect(url_for("admin_dashboard", tab="empresas"))


@app.post("/admin/companies/<int:company_id>/delete")
@admin_required
def delete_company(company_id):
    with connect_db() as db:
        db.execute("DELETE FROM companies WHERE id = ?", (company_id,))
    flash("Empresa y sus marcas quitadas del catálogo.", "success")
    return redirect(url_for("admin_dashboard", tab="empresas"))


@app.post("/admin/brands")
@admin_required
def save_brand():
    brand_id = request.form.get("brand_id", "").strip()
    name = request.form.get("name", "").strip()
    try:
        company_id = int(request.form.get("company_id", ""))
    except ValueError:
        company_id = 0
    if not name or not company_id:
        flash("Indicá el nombre de la marca y su empresa.", "error")
    else:
        with connect_db() as db:
            if brand_id:
                db.execute("UPDATE brands SET company_id = ?, name = ? WHERE id = ?", (company_id, name, brand_id))
                db.execute("UPDATE products SET company_id = ? WHERE brand_id = ?", (company_id, brand_id))
            else:
                db.execute("INSERT INTO brands(company_id, name) VALUES (?, ?)", (company_id, name))
        flash("Marca guardada.", "success")
    return redirect(url_for("admin_dashboard", tab="marcas"))


@app.post("/admin/brands/<int:brand_id>/delete")
@admin_required
def delete_brand(brand_id):
    with connect_db() as db:
        db.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
    flash("Marca quitada del catálogo.", "success")
    return redirect(url_for("admin_dashboard", tab="marcas"))


@app.post("/admin/settings")
@admin_required
def save_settings():
    values = {
        "store_name": request.form.get("store_name", "").strip()[:80],
        "store_tagline": request.form.get("store_tagline", "").strip()[:160],
        "whatsapp": request.form.get("whatsapp", "").strip()[:30],
    }
    with connect_db() as db:
        db.executemany("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", values.items())
    flash("Datos de la tienda guardados.", "success")
    return redirect(url_for("admin_dashboard", tab="ajustes"))


@app.post("/admin/orders/<order_id>")
@admin_required
def update_order(order_id):
    try:
        with connect_db() as db:
            db.execute("BEGIN IMMEDIATE")
            order = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            if not order:
                raise ValueError("No se encontró el pedido.")
            items = db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
            status = request.form.get("status", "Pendiente")
            if status not in {"Pendiente", "Confirmada", "Entregada", "Cancelada"}:
                status = "Pendiente"
            was_cancelled = order["status"] == "Cancelada"
            is_cancelled = status == "Cancelada"
            new_total = 0
            for item in items:
                quantity = int(request.form.get(f"quantity_{item['id']}", item["quantity"]))
                if not 1 <= quantity <= 99:
                    raise ValueError("Cada cantidad debe estar entre 1 y 99.")
                difference = quantity - item["quantity"]
                if item["product_id"] and was_cancelled != is_cancelled:
                    inventory_change = -quantity if was_cancelled else item["quantity"]
                    product = db.execute("SELECT stock FROM products WHERE id = ?", (item["product_id"],)).fetchone()
                    if inventory_change < 0 and (not product or product["stock"] < -inventory_change):
                        raise ValueError(f"No hay stock suficiente para reactivar {item['product_name']}.")
                    db.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (inventory_change, item["product_id"]))
                elif item["product_id"] and difference and not was_cancelled:
                    product = db.execute("SELECT stock FROM products WHERE id = ?", (item["product_id"],)).fetchone()
                    if difference > 0 and (not product or product["stock"] < difference):
                        raise ValueError(f"No hay stock suficiente para aumentar {item['product_name']}.")
                    db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (difference, item["product_id"]))
                db.execute("UPDATE order_items SET quantity = ? WHERE id = ?", (quantity, item["id"]))
                new_total += item["unit_price"] * quantity
            db.execute("UPDATE orders SET total = ?, status = ? WHERE id = ?", (new_total, status, order_id))
        flash("Pedido actualizado y stock sincronizado.", "success")
    except (ValueError, sqlite3.Error) as error:
        flash(str(error) or "No se pudo actualizar el pedido.", "error")
    return redirect(url_for("admin_dashboard", tab="pedidos"))


initialize_database()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")