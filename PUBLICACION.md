# Publicación de MuseDouble

> Registro de la publicación estática del 23/09/2026. Para el nuevo backend,
> consultar `BACKEND.md`. El ZIP inicial no incluye el backend.

Esta versión conserva la interfaz entregada. `index.php` sirve el HTML original,
sin framework, dependencias ni conexión a base de datos.

## Archivos públicos

Subir únicamente `index.php`, `index.html`, los archivos `.css` y `.js` de la raíz,
y la carpeta `assets/` completa. No subir documentos de entrega, credenciales,
copias de seguridad ni herramientas locales.

`entrega/musedouble-php.zip` contiene exclusivamente esos 35 archivos públicos.
Extraer su contenido en la carpeta pública; no publicar el ZIP ni `entrega/`.

Configurar el hosting para usar `index.php` como documento inicial. Las rutas
usan fragmentos (`#signup`, `#dashboard`); no necesitan reescritura de URL.

## Comprobar localmente

Desde esta carpeta, ejecutar:

```powershell
php -S 127.0.0.1:8080
```

Abrir http://127.0.0.1:8080/index.php.

## Alcance

La publicación muestra la web tal como fue entregada. No implementa cuentas
reales, sesiones, almacenamiento de fotos, generación, pagos ni soporte.
El registro actual es temporal y se pierde al recargar. La base de datos no es
necesaria para esta publicación visual; sus credenciales no deben estar en
archivos públicos ni en JavaScript.

Antes de subir: confirmar host SSH, puerto y carpeta pública; inspeccionar la
instalación existente y guardar una copia de cualquier archivo que se reemplace.
Después: verificar los archivos subidos y la web por HTTPS.

## Configuración del servidor comprobada el 23 de septiembre de 2026

- SSH: `musedouble.com`, puerto `22`, usuario `musedouble`.
- Carpeta pública: `/home/musedouble/public_html/musedouble.com`.
- Nginx tiene configurado HTTPS para este dominio, pero no un manejador PHP.
- La cuenta no dispone de permisos sudo. El proveedor debe habilitar PHP antes
  de publicar `index.php`; de lo contrario podría servirse como un archivo.
- La entrega original también funciona directamente con `index.html`. Para
  esta publicación se utilizan los 34 archivos originales públicos, sin PHP.
- El acceso por HTTP continúa mostrando Fans.la: el proveedor debe revisar el
  bloque del dominio en el puerto 80 y su redirección a HTTPS.
- El informe `entrega/publicacion-verificada.json`, cuando exista, identifica
  la copia de seguridad y las huellas SHA-256 de los archivos publicados.
