from io import BytesIO
import pathlib
import tempfile
import unittest

import app as application


class StorefrontTests(unittest.TestCase):
    def setUp(self):
        self.original_database = application.DATABASE
        self.database_path = pathlib.Path(tempfile.mktemp(suffix=".sqlite"))
        application.DATABASE = self.database_path
        application.initialize_database()
        application.app.config["TESTING"] = True
        self.uploads_before = set(application.UPLOAD_DIR.iterdir())
        self.client = application.app.test_client()
        self.client.get("/")
        with self.client.session_transaction() as browser_session:
            browser_session["csrf_token"] = "test-csrf-token"

    def tearDown(self):
        application.DATABASE = self.original_database
        self.database_path.unlink(missing_ok=True)
        for uploaded_file in set(application.UPLOAD_DIR.iterdir()) - self.uploads_before:
            uploaded_file.unlink(missing_ok=True)

    def test_order_reserves_stock_and_appears_in_admin(self):
        response = self.client.post(
            "/order",
            json={
                "buyer_name": "Comprador de prueba",
                "items": [{"id": 1, "quantity": 2}],
                "payments": [
                    {"method": "Efectivo", "percent": 60},
                    {"method": "Transferencia", "percent": 40},
                ],
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )

        self.assertEqual(response.status_code, 200)
        order_id = response.json["order_id"]
        with application.connect_db() as db:
            stock = db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0]
        self.assertEqual(stock, 6)
        self.assertIn(order_id, response.json["whatsapp_url"])
        self.assertNotIn(order_id.encode(), self.client.get("/").data)

        login = self.client.post(
            "/admin",
            data={
                "username": "Mati77",
                "password": "Matata77",
                "csrf_token": "test-csrf-token",
            },
        )
        self.assertEqual(login.status_code, 302)
        admin_orders = self.client.get("/admin/panel?tab=pedidos")
        self.assertEqual(admin_orders.status_code, 200)
        self.assertIn(order_id.encode(), admin_orders.data)

        with self.client.session_transaction() as browser_session:
            admin_csrf = browser_session["csrf_token"]
        with application.connect_db() as db:
            item_id = db.execute(
                "SELECT id FROM order_items WHERE order_id = ?", (order_id,)
            ).fetchone()[0]
        updated = self.client.post(
            f"/admin/orders/{order_id}",
            data={
                "csrf_token": admin_csrf,
                f"quantity_{item_id}": "3",
                "status": "Confirmada",
            },
        )
        self.assertEqual(updated.status_code, 302)
        with application.connect_db() as db:
            stock = db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0]
        self.assertEqual(stock, 5)

        with self.client.session_transaction() as browser_session:
            admin_csrf = browser_session["csrf_token"]
        cancelled = self.client.post(
            f"/admin/orders/{order_id}",
            data={
                "csrf_token": admin_csrf,
                f"quantity_{item_id}": "3",
                "status": "Cancelada",
            },
        )
        self.assertEqual(cancelled.status_code, 302)
        with application.connect_db() as db:
            stock = db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0]
        self.assertEqual(stock, 8)

        with self.client.session_transaction() as browser_session:
            admin_csrf = browser_session["csrf_token"]
        reactivated = self.client.post(
            f"/admin/orders/{order_id}",
            data={
                "csrf_token": admin_csrf,
                f"quantity_{item_id}": "3",
                "status": "Pendiente",
            },
        )
        self.assertEqual(reactivated.status_code, 302)
        with application.connect_db() as db:
            stock = db.execute("SELECT stock FROM products WHERE id = 1").fetchone()[0]
        self.assertEqual(stock, 5)

    def test_payment_percentages_must_total_one_hundred(self):
        response = self.client.post(
            "/order",
            json={
                "buyer_name": "Comprador de prueba",
                "items": [{"id": 1, "quantity": 1}],
                "payments": [{"method": "Efectivo", "percent": 90}],
            },
            headers={"X-CSRF-Token": "test-csrf-token"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("100%", response.json["error"])

    def test_admin_can_customize_cover_slide_and_contact(self):
        with self.client.session_transaction() as browser_session:
            browser_session["admin"] = True
            browser_session["csrf_token"] = "admin-csrf-token"
        cover_editor = self.client.get("/admin/panel?tab=portada")
        contact_editor = self.client.get("/admin/panel?tab=contacto")
        self.assertEqual(cover_editor.status_code, 200)
        self.assertEqual(contact_editor.status_code, 200)
        self.assertIn("Diapositivas rotativas".encode(), cover_editor.data)
        self.assertIn("Contacto y redes".encode(), contact_editor.data)

        cover = self.client.post(
            "/admin/settings",
            data={
                "csrf_token": "admin-csrf-token",
                "section": "portada",
                "store_name": "Mati Visual",
                "store_tagline": "Diseño para cada mirada",
                "theme_primary": "#205544",
                "theme_secondary": "#c94f32",
                "theme_paper": "#f5f2e9",
                "theme_sun": "#e7b842",
            },
        )
        self.assertEqual(cover.status_code, 302)

        contact = self.client.post(
            "/admin/settings",
            data={
                "csrf_token": "admin-csrf-token",
                "section": "contacto",
                "contact_name": "Matías",
                "contact_phone": "+54 9 11 1234-5678",
                "contact_email": "hola@example.com",
                "contact_address": "Buenos Aires",
                "whatsapp": "5491112345678",
                "instagram": "@matioptica",
            },
        )
        self.assertEqual(contact.status_code, 302)

        slide = self.client.post(
            "/admin/slides",
            data={
                "csrf_token": "admin-csrf-token",
                "title": "Nueva colección",
                "subtitle": "Hechos para mirar distinto",
                "sort_order": "1",
                "active": "on",
                "image": (BytesIO(b"test image"), "cover.png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(slide.status_code, 302)

        public_page = self.client.get("/")
        self.assertEqual(public_page.status_code, 200)
        self.assertIn("Diseño para cada mirada".encode(), public_page.data)
        self.assertIn("Nueva colección".encode(), public_page.data)
        self.assertIn("Matías".encode(), public_page.data)
        self.assertIn(b"https://www.instagram.com/matioptica", public_page.data)
        self.assertIn(b"--forest: #205544", public_page.data)


if __name__ == "__main__":
    unittest.main()