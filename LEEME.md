# MuseDouble — backend y estudio local

Esta carpeta contiene la nueva implementación con **Next.js 16.4.3**, **FastAPI
0.162.0** y **PostgreSQL 18.4**. El trabajo actual se desarrolla únicamente en
`musedouble_local`. La consola de Next.js permite utilizar y
comprobar el backend; no representa la migración de toda la portada pública.

El VPS y el repositorio GitHub no se actualizan al cambiar estos archivos.

## Abrir el proyecto

Desde PowerShell:

```powershell
cd musedouble_local
.\START-LOCAL.ps1
```

El script instala las dependencias fijadas, prepara PostgreSQL local, aplica
las migraciones y los permisos, e inicia los procesos en segundo plano. Con las
dependencias ya instaladas se puede utilizar `-SkipInstall`.

Incluye Node 24 LTS portátil dentro de `storage/tools/node`, descargado de la
fuente oficial y verificado por SHA-256. No sustituye Node global. Para ejecutar
comandos npm manualmente con el mismo runtime:

```powershell
$env:Path = (Join-Path $PWD 'storage/tools/node') + [IO.Path]::PathSeparator + $env:Path
```

| Parte | Dirección local |
| --- | --- |
| Estudio | <http://127.0.0.1:3001/> |
| Administrador | <http://127.0.0.1:3001/control-musedouble/> |
| API | <http://127.0.0.1:8010/api/v1/> |
| Documentación OpenAPI, solo entorno local | <http://127.0.0.1:8010/docs> |
| Estado básico de API y base | <http://127.0.0.1:8010/health> |
| Entrega de objetos mediante enlaces firmados | `127.0.0.1:9011` |
| PostgreSQL aislado del proyecto | `127.0.0.1:55432` |
| Redis 8.10.3 (cola ARQ, límites y progreso) | `127.0.0.1:6380`, dentro de WSL; URL y contraseña en `MUSE_REDIS_URL` de `.env`; claves con prefijo `musedouble:` |

La cuenta local importada conserva el usuario **jhon** y su contraseña previa.
No hay una contraseña de acceso escrita en el código ni en esta documentación.
La importación asignó 100 créditos locales de prueba al administrador una sola
vez; no representan dinero ni una compra. Nuevas cuentas requieren autorización
de generación y asignación de créditos desde el administrador.

Para detener la API, el servidor de objetos, el worker y Next.js:

```powershell
.\STOP-LOCAL.ps1
```

PostgreSQL queda activo. Estos scripts no detienen las instalaciones de
PostgreSQL que ya existían como servicios de Windows. Los registros y los PID
de los procesos locales están en `storage/runtime/`.

## Mapa de archivos

```text
musedouble_local/
├── LEEME.md                  Cómo instalar, abrir y comprobar el proyecto
├── app/
│   ├── main.py               API, límites de cuerpo y respuestas de error
│   ├── config.py             Configuración privada desde el entorno y .env
│   ├── db.py, models.py      Conexiones, modelos y acciones tras commit
│   ├── colas.py              Entrega a la cola ARQ y publicación de progreso
│   ├── redis_client.py       Cliente Redis con prefijo propio
│   ├── security.py           Sesiones, CSRF, contraseñas, cifrado y límites (Redis)
│   ├── usuarios/             Registro, login, logout y cambio de contraseña
│   ├── creditos/             Saldo derivado del libro de movimientos
│   ├── trabajos/             Trabajos, catálogo, contratos y WebSocket de progreso
│   ├── archivos/             Referencias, objetos privados y URLs firmadas
│   ├── admin/                Usuarios, modelos, workflows y servidores
│   └── comfy.py              Transporte privado hacia ComfyUI
├── workers/
│   ├── arq_worker.py         Proceso ARQ: ejecuta trabajos y barre la cola
│   ├── comfy_worker.py       Reclamo, despacho, progreso y recuperación
│   └── object_server.py      Descarga de resultados con firma y caducidad
├── web/                      Next.js, React y TypeScript
│   ├── app/                  Estudio, administrador, 404 y estilos
│   ├── components/           Formularios y vistas conectadas a la API
│   └── generated/api.d.ts    Tipos generados desde OpenAPI
├── database/                 Migraciones Alembic; no contiene registros reales
├── scripts/                  Instalación, respaldo y verificación
├── tests/                    Pruebas aisladas sobre PostgreSQL, Redis y ComfyUI simulado
├── workflows/                JSON API actuales (las versiones previas viven en storage/objects/workflows)
├── storage/                  Archivos y datos locales privados, excluidos de Git
├── pyproject.toml, uv.lock    Dependencias Python
└── web/package-lock.json     Dependencias de la consola web
```

Los datos de la implementación PHP anterior (`musedouble.sqlite`, `jobs/`,
`results/` y `sessions/`) ya se importaron y se borraron de esta carpeta el
06/11/2026 por decisión del propietario; el original activo sigue en el VPS. La
nueva aplicación trabaja con PostgreSQL y `storage/objects/`.

## Instalación en una carpeta nueva

Requisitos: Windows, Python 3.12 o 3.13, `uv`, Node.js compatible con Next.js 16,
npm y los binarios de PostgreSQL 18. El arranque actual busca PostgreSQL en
`C:/Program Files/PostgreSQL/18/bin`; se puede definir `MUSE_PG_BIN` si está en
otra ubicación. El entorno se probó con Python 3.12 y Node.js 25.

```powershell
uv sync --locked
uv run python scripts/setup_local.py
uv run alembic upgrade head
uv run python scripts/grant_database.py
```

`setup_local.py` crea un clúster de desarrollo independiente, vinculado a
loopback, dentro de `storage/runtime/postgres`. No mueve ni reutiliza los
directorios de datos de los servicios PostgreSQL existentes. Esa carpeta es
estado de ejecución privado, no código del esquema ni contenido publicable.

Los datos del sistema PHP anterior ya se importaron a PostgreSQL y el importador
se eliminó junto con el SQLite de origen. En una instalación nueva se crea la cuenta
administradora por línea de comandos:

```powershell
uv run python scripts/create_admin.py --username jhon
```

La contraseña se introduce de forma interactiva. Este comando no sobrescribe
una cuenta existente. Después instalar las dependencias de `web/` con
`npm.cmd ci`, e iniciar con `START-LOCAL.ps1`.

## Redis (cola, límites y progreso)

Redis corre dentro de WSL y no sustituye ni toca el servicio Redis de Windows,
que es la versión 3.0 y no recibe parches. Para instalarlo en una carpeta nueva
(requiere una distribución WSL con `gcc` y `make`; no usa `sudo`):

```powershell
.\scripts\setup-redis-wsl.ps1
```

El script descarga el código oficial de Redis, comprueba su SHA-256 contra el
repositorio oficial de hashes, compila solo el núcleo en `~/musedouble-redis`
(WSL), genera una contraseña propia y guarda `MUSE_REDIS_URL` en `.env`. Es
idempotente. `START-LOCAL.ps1` inicia Redis y `STOP-LOCAL.ps1` lo apaga.
Configuración: puerto 6380 solo en loopback, `maxmemory-policy noeviction` y AOF.
ARQ 0.28.0 exige `redis-py<6`, por eso se fija redis-py 5.3.1. En Windows ARQ no
puede manejar señales: `STOP-LOCAL.ps1` termina el worker sin esperar y los
trabajos en curso se recuperan por el vencimiento de su latido.

## Configuración privada y permisos

`.env` se genera localmente con secretos aleatorios. `.env.example` es solo un
mapa de variables; sus valores de ejemplo no son credenciales utilizables.

- `MUSE_DATABASE_URL`: conexión de la API mediante `musedouble_app`.
- `MUSE_MIGRATION_DATABASE_URL`: conexión del propietario para migraciones y
  herramientas CLI; la API no la utiliza para atender solicitudes.
- `MUSE_ENCRYPTION_KEY`: clave Fernet para URLs y tokens de ComfyUI en reposo.
- `MUSE_SIGNING_KEY`: firma de enlaces temporales de descarga.
- `MUSE_ALLOWED_GPU_HOSTS`: lista explícita de hosts que pueden configurarse.
- `MUSE_WEB_ORIGIN`, `MUSE_API_ORIGIN`, `MUSE_OBJECT_ORIGIN`: orígenes locales.
- `MUSE_STORAGE`: carpeta de almacenamiento privado.

La API usa una cuenta PostgreSQL sin superusuario, sin creación de bases ni
roles y sin propiedad del esquema. Los permisos sobre tablas se otorgan
explícitamente; `PUBLIC` no recibe acceso a datos. Las solicitudes comprueban
siempre el usuario y la propiedad del recurso. Un trabajo o archivo ajeno
devuelve 404 incluso para otra cuenta administradora.

Las cookies son `HttpOnly`, `SameSite=Lax`, con caducidad y revocación en
servidor. `Secure=false` corresponde al HTTP de loopback de este entorno local.
Login y cambio de contraseña rotan la sesión; las escrituras por cookie
requieren CSRF. Login, registro, cargas, generación y conexiones de progreso tienen
límites de tasa en ventana deslizante dentro de Redis. Si Redis no responde, la API
responde 503 y no acepta trabajos. Las respuestas de error no incluyen parámetros SQL, claves ni
URLs privadas.

No publicar esta raíz como un directorio estático. `.env`, SQLite, `storage/`,
respaldos, sesiones y datos de usuario están excluidos mediante `.gitignore`.
No copiar secretos a `NEXT_PUBLIC_*`, al código de cliente ni a documentación.

## Trabajos, créditos y resultados

```text
Next.js → FastAPI → PostgreSQL (trabajo y cargo, una transacción)
                         ↓ tras el commit
                    Redis (ARQ: solo el identificador)
                         ↓
              worker ARQ → ComfyUI → objetos privados
                         ↓ progreso (Redis pub/sub)
              FastAPI /api/v1/jobs/stream → navegador
```

`POST /jobs` valida los parámetros, bloquea la fila del usuario, comprueba el
saldo y el límite de trabajos activos, registra el cargo y crea el trabajo en
una transacción. Una clave `Idempotency-Key` evita cobrar dos veces un reenvío.
El saldo se obtiene sumando `credit_ledger`; no se modifica un contador manual.

La API escribe el trabajo en PostgreSQL y solo después, con el commit confirmado,
envía su identificador a Redis. Si ese envío falla, el trabajo queda `queued` y el
barrido del worker lo vuelve a encolar tras `MUSE_REQUEUE_AFTER_SECONDS`. Redis
no decide nada: el worker reclama el trabajo y la GPU con `FOR UPDATE SKIP LOCKED`
en PostgreSQL, así que un mensaje duplicado o tardío se ignora. Guarda una copia
del grafo, versión, modo, parámetros, modelo y coste de cada trabajo. Editar un
workflow o modelo no cambia lo que ya se encoló. El progreso llega al navegador
por `/api/v1/jobs/stream` (WebSocket, con sesión y origen comprobados); la consulta
`GET /jobs/{id}` sigue siendo la fuente definitiva. Al terminar, los objetos
propios y PostgreSQL son la fuente de verdad.

Arranque del worker: `uv run python -m arq workers.arq_worker.WorkerSettings`
(lo hace `START-LOCAL.ps1`). Concurrencia: `MUSE_WORKER_CONCURRENCY`. Al detener
el worker con `STOP-LOCAL.ps1` no hay apagado ordenado en Windows.

Estados: `queued → running → succeeded | failed | canceled`. Los fallos y las
cancelaciones reembolsan mediante movimientos únicos. Los latidos permiten
recuperar un worker caído con intentos acotados. Un envío ambiguo a ComfyUI no
se repite a ciegas: se intenta reconciliar y, si no se puede asegurar su estado,
el servidor queda fuera de reparto para revisión.

En una GPU compartida no se envía una interrupción global que pueda afectar
trabajos de otras webs. Si una cancelación afecta a un trabajo ya ejecutándose,
puede esperar su finalización. El indicador de servidor exclusivo debe reflejar
que realmente esté dedicado a esta web.

Los resultados se descargan desde el proceso de objetos del puerto 9011, con
enlaces firmados que duran 300 segundos. La API solo emite el enlace después
de comprobar la propiedad; los bytes de resultado no se sirven a través de la
API principal. No hay una ruta pública de listado de objetos.

Valores iniciales: hasta 2 trabajos activos por usuario, 1 o 2 imágenes por
envío, 20 MB por referencia, 40 megapíxeles por imagen y 32 MB por resultado.
Las referencias requieren autorización de generación y tienen un límite de
200 MB por usuario en una ventana de 24 horas, configurable por entorno.
La cola y los tiempos máximos se configuran en `app/config.py` y variables de
entorno. Los límites de cantidad y formatos del estudio se administran en
**Workflows**. No hay eliminación automática de resultados de usuarios.

## Workflows y modelos

En **Servidores**, guardar la conexión, probarla y habilitar las herramientas
correspondientes. Las URLs y tokens se cifran y no se devuelven a la consola:
el administrador recibe una máscara. La revisión de compatibilidad identifica
nodos u opciones que falten en el ComfyUI seleccionado, sin ejecutar una imagen.

En **Modelos**, configurar el nombre público, los prompts y hasta 6 LoRAs. Los
modelos de IA, LoRAs y nodos personalizados se instalan en ComfyUI, no mediante
esta aplicación.

Los workflows actualizados instalados el 26/10/2026 son:

| Apartado | Archivo | Versión instalada | SHA-256 |
| --- | --- | --- | --- |
| Crear imagen | `workflows/IMG_GEN_API.json` | 2 | `29122f538551b38feccc4bc323a1e57dcbe6b546a4e91ca3bd195e85221682c4` |
| Usar referencia | `workflows/IMG_REFERENCE_GEN_API.json` | 2 | `5f7d632d2b4222eb031cdc01ce3c082bb5065d77f2b9508040a3f27fdca2a361` |

Se preservan los bytes originales y las versiones previas. La resolución de
entradas se hace por `title` o `_meta.title`, nunca por IDs numéricos.
`FINAL_IMAGE` se conserva intacto. Los usuarios envían un `workflow_id` conocido
y parámetros; solo el administrador o una herramienta CLI pueden instalar un
grafo API. El formato del editor (`nodes`/`links`) se rechaza al subir.

La instalación CLI de un JSON propio también valida el contrato:

```powershell
uv run python scripts/install_workflow.py generate <ruta-al-JSON-API>
uv run python scripts/install_workflow.py reference <ruta-al-JSON-API>
```

En Windows, el transporte utiliza cURL con la validación TLS del sistema para
las peticiones HTTP de ComfyUI; no se desactiva la verificación de certificados.
Un fallo del WebSocket no impide verificar el resultado mediante historial.

## API disponible

Estas rutas llevan el prefijo `/api/v1`:

| Grupo | Rutas principales |
| --- | --- |
| Sesiones | `GET /auth/session`; `POST /auth/register`, `/auth/login`, `/auth/logout`, `/auth/password` |
| Estudio | `GET /catalog`; `POST /uploads`; `POST /jobs`; `GET /jobs`, `/jobs/{id}`; `POST /jobs/{id}/cancel` |
| Resultados | `GET /outputs/{id}/url`; parámetro `download=true` para descarga |
| Créditos propios | `GET /credits` |
| Administración | `/admin/overview`, `/admin/users`, `/admin/models`, `/admin/workflows`, `/admin/gpus`, `/admin/settings`, `/admin/audit` |

El historial se pagina; las cuentas de miembro no pueden usar rutas de
administración. OpenAPI contiene los contratos completos. Para regenerar los
tipos TypeScript después de cambiar la API:

```powershell
uv run python scripts/export_openapi.py
cd web
npm.cmd run generate:types
```

## Verificaciones

```powershell
uv run pytest --junitxml=storage/pytest-results.xml
uv run alembic check
uv run python scripts/check_contrast.py
uv run pip-audit --local
cd web
npm.cmd run typecheck
npm.cmd run build
```

Las pruebas de cola usan Redis real con un prefijo distinto para cada prueba y
requieren un servidor Redis soportado accesible en `MUSE_REDIS_URL`. Las pruebas de
base usan esquemas PostgreSQL temporales. Ambos usan un ComfyUI simulado para
comprobar éxito, referencia, permisos entre usuarios, saldo concurrente,
idempotencia, reembolsos, cancelación, recuperación, sesiones, CSRF, límites y
contratos con IDs de nodos cambiados. No consumen GPU ni cambian los registros
del estudio local. `storage/pytest-results.xml` conserva el resultado concreto;
`storage/contrast.json` contiene las mediciones de 40 pares de colores de ambos
temas. El 26/10/2026 pasaron 21 pruebas automáticas y las dos pruebas reales con
los workflows actualizados: texto (319.273 bytes) y referencia (372.385 bytes).
Los originales y los trabajos quedaron guardados. El informe completo está en
`storage/validation/report.json`. También se revisan login, galería tras recarga,
temas y 404 en el navegador antes de cerrar la entrega.

## Respaldos y restauración

```powershell
uv run python scripts/backup_local.py
uv run python scripts/verify_restore.py
```

El respaldo PostgreSQL usa formato custom y queda en `storage/backups/`.
`verify_restore.py` restaura en una base temporal con nombre propio, compara
cantidades de las tablas principales y elimina únicamente esa base de prueba.
El respaldo crea además un archivo `.objects.tar.gz` con los objetos inmutables
y un manifiesto `.objects.json` con sus hashes. La restauración comprueba también
los bytes y hashes de los originales recuperados. El informe está en
`storage/restore-verification.json`. Conservar las claves privadas de `.env` y
la configuración del clúster por separado y bajo acceso privado para recuperar
el cifrado de las conexiones. Un dump de PostgreSQL por sí solo no contiene
los objetos ni esas claves.

## Alcance actual

Implementado: usuarios y permisos, administrador, catálogo/modelos, carga de
referencias, workflows versionados, cola, workers, créditos manuales,
reembolsos, galería privada, enlaces firmados, auditoría y configuración local.

No están integrados cobros, recuperación por email, verificación de identidad,
entrenamiento de modelos, contratos, soporte comercial, All in one ni Photo to
prompt. No hay infraestructura de producción ni una garantía de 100.000
usuarios simultáneos. Ese dimensionamiento requiere mediciones y trabajo
separado.
