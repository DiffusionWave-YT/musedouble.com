# Activación del backend de Musedouble

> Instrucciones históricas de la release 20260926T035422Z, activada y verificada
> el 26/09/2026. La semilla y la carpeta privada citadas no se distribuyen en Git.
> Para una instalación nueva, crear una base propia siguiendo README.md.

La versión preparada está en `/home/musedouble/releases/20260926T035422Z/`.
No se ha modificado el sitio público. La carpeta de la versión y su semilla
son privadas; no deben usarse como document root ni exponerse por HTTP.

El proveedor, con permisos de administrador, debe:

1. Habilitar `pdo_sqlite` para PHP 8.3 (CLI y FPM); validar también curl,
   mbstring y fileinfo. Actualmente SQLite está en el PHP CLI 7.4, pero no 8.3.
2. Guardar una copia privada de la configuración actual de Nginx y de cualquier
   pool FPM que vaya a reemplazar. Se preparó un respaldo del sitio público.
3. Crear `/home/musedouble/private-backend` con propietario musedouble y modo
   0700. Solo en una instalación nueva, copiar allí `seed/musedouble.sqlite` y
   `seed/workflows/`. Si ya existe una base, NO sobrescribirla: respaldar y migrar.
   Crear jobs/, results/ y sessions/ con propietario musedouble y modo 0700.
4. Revisar e instalar `config/musedouble-pool.conf` como
   `/etc/php/8.3/fpm/pool.d/musedouble.conf`; comprobar `php-fpm8.3 -t` y recargar
   php8.3-fpm. Verificar la creación de `/run/php/php-musedouble.sock`.
5. Revisar e instalar `config/musedouble-vhost.conf` reemplazando únicamente
   `/etc/nginx/sites-available/musedouble.conf`. Verificar primero `nginx -t`.
   Corregir cualquier error antes de recargar Nginx; no modificar otros dominios.
6. Activar primero esas reglas mientras continúa la versión estática. Confirmar
   que la nueva regla PHP está activa antes de copiar código PHP al document root.
7. Copiar el contenido de `public/` a
   `/home/musedouble/public_html/musedouble.com/`, manteniendo el propietario
   musedouble, directorios 0755 y archivos 0644. Copiar index.html al final.
   No copiar seed/, config/,
   manifests, archivos comprimidos o documentación a la carpeta pública.
8. Verificar `/api.php?action=session` como JSON, login en
   `https://musedouble.com/control-musedouble/`, redirección HTTP a HTTPS,
   404 de backend/bootstrap.php y pruebas de generación desde el VPS.

La cuenta inicial solicitada es jhon. Solo se transfirió su hash de contraseña;
no se incluyen sesiones ni imágenes o trabajos de las pruebas locales.

Si se requiere rollback, usar el respaldo privado del sitio y de la configuración
realizado antes del cambio. Conservar la base privada para no perder nuevos datos.
