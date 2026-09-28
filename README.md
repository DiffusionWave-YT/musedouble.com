# MuseDouble

Web y estudio de generación de imágenes con PHP sin framework y ComfyUI.
Incluye frontend, API, administrador, workflows, pruebas y ejemplos de Nginx/PHP-FPM.

## Qué funciona

- Registro e inicio de sesión reales, permisos y aprobación manual de generación.
- Administrador personalizado en `/control-musedouble/`.
- Image generation y Reference image, con selector de modelos por nombre.
- Configuración de ComfyUI, LoRAs y subida de workflows desde el administrador.
- Galería persistente y descarga de originales accesibles solo a su propietario.

Pagos, entrenamiento, verificación de identidad/email, contratos, soporte,
All in one y Photo to prompt todavía no están conectados. El precio mostrado
en el frontend no implica un sistema de cobros activo.

## Requisitos

- PHP 8.3 o posterior con `pdo_sqlite`, `curl`, `mbstring`, `fileinfo` y sesiones.
- Un servidor ComfyUI para generar imágenes. Debe tener los nodos personalizados,
  modelos y LoRAs requeridos por los workflows elegidos.
- Git. Python 3 solo es necesario para ejecutar las pruebas HTTP.

No requiere Composer, npm ni compilación del frontend. La base es SQLite.

## Instalar localmente en Windows

```powershell
git clone https://github.com/DiffusionWave-YT/musedouble.com.git
cd musedouble.com
$env:MUSEDOUBLE_DATA_DIR = Join-Path (Split-Path $PWD -Parent) 'musedouble-private'
$adminPassword = Read-Host 'Nueva contraseña del administrador (mínimo 10 caracteres)' -AsSecureString
$env:MUSEDOUBLE_ADMIN_PASSWORD = [System.Net.NetworkCredential]::new('', $adminPassword).Password
try {
    php scripts/install.php workflows
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo completar la instalación' }
} finally {
    Remove-Item Env:MUSEDOUBLE_ADMIN_PASSWORD -ErrorAction SilentlyContinue
}
.\START-LOCAL.ps1
```

Abrir <http://127.0.0.1:8087/control-musedouble/>. El usuario inicial es `jhon`
y la contraseña es la que acabas de introducir. No se incluye ninguna cuenta
ni contraseña del servidor publicado. El instalador conserva la contraseña
de un administrador existente.

En el administrador:

1. En **ComfyUI**, configurar la URL de tu servidor y el token si lo requiere.
2. En **Models**, crear los perfiles con sus nombres, prompts y LoRAs disponibles.
3. En **Workflows**, revisar los dos JSON instalados o subir tus versiones API.
4. Abrir el estudio y generar; usar **Studio access** para aprobar otros usuarios.

Los workflows incluidos preservan los grafos utilizados por la integración.
Los archivos de modelos, LoRAs y nodos de ComfyUI se instalan aparte; un clon
del repositorio no proporciona acceso al servidor ni a los modelos de producción.

## Datos privados

`MUSEDOUBLE_DATA_DIR` debe apuntar a una carpeta fuera de la raíz pública.
Contiene SQLite, configuración privada, workflows activos, sesiones y resultados.
Si no se define, se usa `musedouble-private` junto a la carpeta del proyecto.
La aplicación rechaza almacenar estos datos dentro de la raíz pública.

El repositorio excluye credenciales, bases, sesiones, imágenes generadas, informes
locales y respaldos. `assets/` contiene los recursos visuales del frontend.
Las variables se leen del entorno del proceso; no hay cargador automático de `.env`.

## Descargar actualizaciones

Desde tu copia local:

```powershell
git pull --ff-only origin main
```

Conserva primero tus cambios locales mediante un commit o stash. El comando
actualiza el código; no reemplaza la base ni los resultados privados. No vuelvas
a importar workflows sobre una configuración personalizada sin revisarlos.

Publicar cambios en GitHub **no despliega automáticamente al VPS**. Para producción,
hacer un respaldo privado, revisar los cambios y publicar solo los archivos
indicados en [BACKEND.md](BACKEND.md#publicar-el-backend). Las configuraciones de
`deployment/` son ejemplos del dominio original: adaptar rutas, usuario, IP,
certificados y socket PHP. No exponer `.git`, documentación, pruebas ni workflows
fuente por HTTP. Mantener las reglas de acceso y PHP indicadas.

## Pruebas sin consumir GPU

```powershell
php tests/workflow.php
$testPassword = Read-Host 'Contraseña temporal de pruebas (mínimo 10 caracteres)' -AsSecureString
$env:MUSEDOUBLE_ADMIN_PASSWORD = [System.Net.NetworkCredential]::new('', $testPassword).Password
try {
    python tests/integration.py workflows
} finally {
    Remove-Item Env:MUSEDOUBLE_ADMIN_PASSWORD -ErrorAction SilentlyContinue
}
```

La prueba HTTP utiliza una base aislada y un ComfyUI simulado. Las pruebas de
workflow verifican el contrato por títulos y que `FINAL_IMAGE` no cambia.
Las pruebas reales de GPU se realizan aparte desde el estudio configurado.

## Documentación

- [BACKEND.md](BACKEND.md): arquitectura, seguridad, contratos y publicación.
- [LEEME-INSTALACION.md](LEEME-INSTALACION.md): orientación de instalación.
- [ENGINEERING-HANDOFF.md](ENGINEERING-HANDOFF.md): notas históricas del prototipo.
- [PUBLICACION.md](PUBLICACION.md): registro histórico de la publicación estática.
