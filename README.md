# Lumen Óptica

Aplicación web para administrar un catálogo de anteojos y recibir pedidos de compra. Está construida con Python, Flask y SQLite.

## Requisitos

- Python 3.10 o superior.
- Flask (`pip install -r requirements.txt`).

## Iniciar en Windows PowerShell

```powershell
pip install -r requirements.txt
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "elegir-una-clave-segura"
$env:SECRET_KEY = "reemplazar-por-una-clave-larga-y-aleatoria"
python app.py
```

Abrí `http://127.0.0.1:5000`. El primer inicio crea una base SQLite, una empresa y dos anteojos de muestra. Para entrar al panel, abrí `/admin`. Si no definís variables de entorno, las credenciales de demostración son `admin` / `admin123`; cambialas antes de publicar la aplicación.

El archivo `catalogo.db` se crea en la carpeta del proyecto. Las imágenes cargadas por administración se guardan en `static/uploads/` (límite de 8 MB; JPG, PNG, WEBP o GIF).

## Uso

- Desde **Empresas** y **Marcas**, organizá el catálogo. En **Nuevo anteojo**, elegí empresa, marca y tipo, y completá nombre, imagen, precio y stock. Los productos destacados rotan en la portada.
- Configurá el nombre, la frase de portada y el número del vendedor en **Datos de tienda**. El teléfono debe incluir el código de país y área, solo con dígitos.
- El comprador filtra el catálogo, agrega cantidades al pedido, informa nombre y asigna porcentajes a uno o varios medios de pago. Los porcentajes deben sumar 100.
- Al confirmar, se registra un código único, se reserva stock y se abre WhatsApp con el mensaje dirigido al vendedor. Ese mismo código aparece en **Pedidos**. El público no tiene un historial de compras.
- En administración se pueden ajustar cantidades y estado del pedido. Cancelar devuelve el stock; reactivar reserva nuevamente las unidades disponibles.

La aplicación es una base funcional para desarrollo local. Antes de publicarla en internet, usá HTTPS, configurá una clave secreta y credenciales robustas, y desplegala detrás de un servidor WSGI de producción.