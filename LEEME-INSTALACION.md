# Instalación de MuseDouble

La versión actual incluye backend PHP, administrador, usuarios y generación con
ComfyUI. El código está en la raíz del repositorio; no existe una carpeta `dist/`.

Sigue [README.md](README.md) para clonar, instalar desde cero, configurar tu
servidor ComfyUI y descargar actualizaciones con Git.

Para publicar en un hosting, consulta [BACKEND.md](BACKEND.md#publicar-el-backend)
y adapta los ejemplos de `deployment/`. Se necesita PHP con PDO SQLite y una
carpeta privada fuera de la raíz pública. Un servidor estático de Python no
puede ejecutar la API.

El repositorio no contiene bases, cuentas de producción, contraseñas, sesiones,
modelos de IA ni imágenes generadas de usuarios. Los workflows API se incluyen
en `workflows/`; instala sus nodos y modelos en tu propio ComfyUI.

Las notas del antiguo prototipo en `ENGINEERING-HANDOFF.md` y la publicación
estática en `PUBLICACION.md` son históricas. El alcance vigente está en README.
