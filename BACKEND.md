# MuseDouble backend

Implementación en PHP sin framework. Conserva la web original y conecta
Image generation y Reference image a ComfyUI. Administración: `/control-musedouble/`.

## Arrancar

Ejecutar `START-LOCAL.ps1` y abrir http://127.0.0.1:8087/control-musedouble/.
La cuenta de prueba solicitada usa el identificador `jhon`. La contraseña se
introdujo durante la instalación y solo se guarda su hash en la base de datos.

Requisitos: PHP 8.3 o posterior con PDO SQLite, cURL, mbstring, fileinfo y sesiones.
La instalación actual utiliza SQLite; no utiliza ni modifica la base MySQL
entregada anteriormente. No requiere Composer ni Node en producción.

Los datos locales están en `C:/CODIGOS/webs/musedouble-private/`, fuera del sitio:

- `musedouble.sqlite`: usuarios, modelos, configuración, trabajos y resultados.
- `workflows/`: originales JSON versionados por SHA-256.
- `jobs/`: snapshot privado exacto enviado a ComfyUI y bloqueos de importación.
- `results/`: imágenes originales, servidas mediante sesión y propietario.
- `sessions/`: sesiones privadas.

Para otra instalación, definir `MUSEDOUBLE_DATA_DIR` con una ruta privada fuera
del document root. Ejecutar `scripts/install.php <carpeta-de-workflows>` por CLI
con `MUSEDOUBLE_ADMIN_PASSWORD` en el entorno para crear el primer administrador.
El instalador no cambia contraseñas de cuentas existentes. No hay instalador web.
El administrador puede cambiar su contraseña desde Account.

## Panel y estudio

- ComfyUI: URL y token Bearer opcional, prueba de conexión y listado de LoRAs.
- Models: nombre público, prompt del personaje, prompt de ojos y hasta seis
  LoRAs con intensidad. Se pueden ocultar sin perder resultados históricos.
- Workflows: subida de JSON API para cada uno de los dos apartados. Se valida
  antes de reemplazarlo; el original queda preservado sin modificar sus bytes.
- Generation settings: máximo de una o dos imágenes y lista de formatos.
- Studio access: activar/desactivar cuentas y autorizar generación a miembros.
- Account: cambio de contraseña comprobando la actual.
- El usuario puede registrarse con contraseña; generar requiere aprobación
  manual. El administrador tiene acceso a generación desde su propia sesión.
- Los resultados persisten tras recargar, pueden abrirse y descargarse sin
  conversión. Cada usuario solo puede acceder a sus propios resultados.

ComfyUI configurado localmente: la URL indicada por el propietario. Las pruebas
usan dos perfiles importados del archivo de modelos de Fansla: Aiko Tanaka y
Amara Dlamini. Se pueden modificar u ocultar en Models. No se modificó Fansla.
`scripts/import-models.php <archivo-presets> [cantidad]` permite importar más
perfiles por CLI sin sobrescribir los existentes.

## Contrato ComfyUI

Se buscan nodos únicamente por `title` o `_meta.title`. Los identificadores del
grafo solo se conservan para conexiones y para localizar la salida por el título
`FINAL_IMAGE`; no hay números de nodos codificados en la lógica.

Ambos apartados aplican `SELECT_CHARACTER` (seis LoRAs), `CHARACTER_PROMPT`,
`EYE_PROMPT`, `USER_PROMPT`, `SEED` y `BATCH_SIZE`. Se limpian las ranuras de
personaje que no se utilizan; otros LoRAs internos permanecen intactos.

Image generation envía la etiqueta a `ASPECT_RATIOS.aspect_ratio` cuando existe.
El propio nodo determina las dimensiones. Solo si no existe se utilizan
`HORIZONTAL_RES.value` y `VERTICAL_RES.value` con la tabla del administrador.

Reference image sube el archivo a `/upload/image` y aplica el nombre devuelto a
`LOAD_IMAGE.image`, además de `REFERENCE_STRENGTH.value`. El formato se deriva
de la imagen de referencia. Se valida tipo real, tamaño y dimensiones del archivo.

`FINAL_IMAGE` no se modifica. Se recuperan únicamente sus imágenes desde
`/history/{prompt_id}` y `/view`. El límite es 20 MB para referencias, 40
megapíxeles por referencia y 32 MB por resultado. Los errores de ComfyUI aparecen
en el estudio y el administrador; no se sustituyen por imágenes de ejemplo.

La petición tiene un identificador para impedir envíos duplicados por reintento.
Hay hasta dos trabajos pendientes por usuario. El navegador consulta el estado
cada tres segundos; al cerrar todas las pestañas el trabajo continúa en ComfyUI
y se recupera cuando el usuario vuelve. No se ha instalado un worker permanente.
Si se pierde la respuesta a `/prompt`, el trabajo local se marca fallido; antes
de repetirlo conviene revisar la cola remota porque el servidor puede haberlo
aceptado. No se interrumpe ni se vacía la cola global de ComfyUI.

## Comprobaciones

```powershell
php tests/workflow.php
# Definir una contraseña temporal de pruebas en MUSEDOUBLE_ADMIN_PASSWORD.
python tests/integration.py workflows
```

La prueba HTTP utiliza una base aislada y un servidor ComfyUI simulado, sin
gastar GPU. Comprueba sesiones, CSRF, roles, permisos, cargas, validación de
referencias, aislamiento de imágenes y las dos generaciones. Las pruebas de
workflow cambian todos los identificadores del grafo y verifican que solo se
modifican los títulos permitidos y que FINAL_IMAGE permanece intacto.

Además, la validación manual debe comprobar login, guardar modelos, subir un
workflow, generar con el servidor real y revisar Gallery tras recargar.

## Publicar el backend

El backend está activo en https://musedouble.com/ desde la activación del
proveedor, verificada el 26 de septiembre de 2026. El administrador está en
https://musedouble.com/control-musedouble/. Se comprobaron login, conexión
ComfyUI, generación real por texto y referencia, descarga autenticada y Gallery
tras recargar. Los 45 archivos públicos y los dos workflows coinciden con la
release `20260926T035422Z`. La base y los resultados residen fuera del directorio
público en `/home/musedouble/private-backend`.

Evidencia local: `entrega/vps-backend-validacion.json` y
`entrega/vps-gallery-validada.png`. Para futuras publicaciones:

1. El proveedor debe habilitar PHP-FPM y PDO SQLite para este dominio, y revisar
   la redirección HTTP a HTTPS. La cuenta SSH comprobada no tiene sudo.
2. Revisar y adaptar `deployment/nginx-locations.conf` en el bloque HTTPS del
   dominio. Reemplazar el antiguo fallback `/index.php` por las reglas indicadas.
   No tocar los bloques de Fans.la o partners.musedouble.com.
3. Configurar un pool PHP del usuario `musedouble`, con
   `MUSEDOUBLE_DATA_DIR=/home/musedouble/private-backend`, y permisos para escribir
   allí. Ajustar PHP `upload_max_filesize=22M`, `post_max_size=25M`.
4. Respaldar fuera del document root los archivos que se reemplacen. Subir solo
   los HTML, CSS y JS públicos, `assets/`, `index.php`, `api.php`, `backend/*.php`
   y `control-musedouble/index.php`. No subir documentación, scripts, tests,
   `entrega`, bases, credenciales, sesiones, respaldos ni archivos temporales.
5. Instalar la base por CLI desde una carpeta privada o transferir una copia
   consistente de SQLite a la ruta privada. No copiar archivos de sesión local.
6. Validar Nginx antes de recargar; comprobar HTTPS, ejecución PHP, login,
   archivos privados inaccesibles y generación real con el servidor configurado.

La ruta personalizada no reemplaza el login. Los endpoints del administrador
verifican su rol. Las cookies usan HttpOnly, SameSite y Secure bajo HTTPS;
las escrituras requieren CSRF. Hay límite de intentos de autenticación.

## Fuera de este alcance

No están conectados pagos, verificación de email/identidad, entrenamiento,
contratos, soporte, All in one o Photo to prompt. La autorización de generación
es manual y no representa una membresía pagada. No se guardan las fotos del
recorrido antiguo de onboarding. El panel existente de cuenta/membresía se
sustituye por el estado real de acceso, sin saldo ni cobros simulados.
