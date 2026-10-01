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
        self.client = application.app.test_client()
        self.client.get("/")
        with self.client.session_transaction() as browser_session:
            browser_session["csrf_token"] = "test-csrf-token"

    def tearDown(self):
        application.DATABASE = self.original_database
        self.database_path.unlink(missing_ok=True)

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
                "username": "admin",
                "password": "admin123",
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


if __name__ == "__main__":
    unittest.main()