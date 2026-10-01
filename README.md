# Lumen Óptica

Aplicación web para administrar un catálogo de anteojos y recibir pedidos de compra. Está construida con Python, Flask y SQLite.

## Requisitos

- Python 3.10 o superior.
- Flask (`pip install -r requirements.txt`).

## Iniciar en Windows PowerShell

```powershell
pip install -r requirements.txt
$env:ADMIN_USERNAME = "Mati77"
$env:ADMIN_PASSWORD = "Matata77"
$env:SECRET_KEY = "reemplazar-por-una-clave-larga-y-aleatoria"
python app.py
```

Abrí `http://127.0.0.1:5000`. El primer inicio crea una base SQLite, una empresa y dos anteojos de muestra. Para entrar al panel, abrí `/admin`. Sin variables de entorno, el usuario y la contraseña iniciales son `Mati77` / `Matata77`.

Si PythonAnywhere ya tiene configuradas `ADMIN_USERNAME` o `ADMIN_PASSWORD`, esas variables prevalecen sobre los valores predeterminados; actualizalas también en la configuración WSGI antes de recargar la aplicación.

El archivo `catalogo.db` se crea en la carpeta del proyecto. Las imágenes cargadas desde el panel se guardan en `static/uploads/` (máximo 8 MB; JPG, PNG, WEBP o GIF). Las tablas y preferencias nuevas se crean sin borrar los datos existentes.

## Administración

- En **Anteojos**, creá y editá productos, imágenes, stock y cuáles aparecen destacados.
- En **Empresas** y **Marcas**, organizá el catálogo.
- En **Portada**, cambiá el nombre, los textos visibles, el logo y los colores. Agregá diapositivas con fotos propias o vinculadas a anteojos, ordenalas y activalas o desactivalas. Si no hay diapositivas propias, se muestran los productos destacados.
- En **Contacto**, configurá nombre, teléfono, WhatsApp, email, dirección y redes sociales. Esos datos aparecen al final de la tienda.
- En **Mensaje WhatsApp**, editá el texto anterior y posterior al código. El código se agrega automáticamente y no se puede modificar.
- En **Pedidos**, ajustá cantidades y estados. Cancelar devuelve las unidades al inventario; reactivar reserva las disponibles.

El índice público no muestra enlaces al panel. La ruta `/admin` sigue disponible para iniciar sesión; las rutas de edición requieren una sesión autenticada.

## Compras

Los compradores pueden filtrar el catálogo, elegir cantidades, combinar métodos de pago y distribuir porcentajes que sumen 100. Al confirmar, se registra un código de pedido, se reserva stock y se prepara un mensaje de WhatsApp para el vendedor. El panel muestra el mismo código; el público no tiene historial de compras.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

Esta aplicación está preparada como base funcional de desarrollo. Antes de publicarla, configurá credenciales y clave secreta robustas, usá HTTPS y desplegala detrás de un servidor WSGI de producción.