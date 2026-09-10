# 🎓 Triumphare Wiki

Wiki / foro / red social colaborativa para el **Colegio Triumphare**, construida
con Flask. Los estudiantes son los únicos creadores del contenido: esta
plataforma no incluye publicaciones, perfiles ni datos ficticios — solo el
esqueleto funcional y visual, listo para que la comunidad lo llene.

---

## 1. Propuestas de nombre de marca

"triumphare-wiki" era un nombre provisional. Aquí 5 alternativas más
modernas y con personalidad propia para el lanzamiento:

| # | Nombre | Por qué funciona |
|---|--------|-------------------|
| 1 | **Ágora Triumphare** | El ágora era la plaza pública griega de debate: comunica "espacio de discusión abierta" con raíz clásica, coherente con un colegio. |
| 2 | **Triumphare Nexo** | "Nexo" transmite conexión/red social entre estudiantes; corto, fácil de decir y de convertir en dominio. |
| 3 | **Bitácora T** | Evoca un diario de a bordo colectivo ("bitácora"), cercano y menos institucional/frío que "wiki". |
| 4 | **Colmena T** | Metáfora de trabajo colaborativo y comunidad activa; visualmente da pie a un logo de panal muy distintivo. |
| 5 | **Triumphare Campus** | Directo y claro para nuevos usuarios: se entiende de inmediato que es "todo lo del campus" en un solo lugar. |

> Cambiar el nombre visible es tan simple como editar `NOMBRE_INSTITUCION`
> no aplica aquí (ese es el colegio) — el nombre del producto está en
> `templates/base.html`, dentro de `<span class="marca__texto">`.

---

## 2. Identidad visual

Concepto de diseño: **"boletín de campus digital"** — ni una plantilla SaaS
genérica ni un feed de red social anónimo. Los detalles:

- **Paleta**: azul-tinta institucional (`#14213D`) + acento dorado de logro
  académico (`#E8A33D`) + verde bosque para likes/éxito (`#2E8B77`) + ciruela
  para Off-Topic (`#8C5AA8`). Fondo cálido, no blanco puro.
- **Tipografía**: `Literata` (serif, con carácter editorial/académico) para
  títulos, `Work Sans` (sans humanista) para el cuerpo.
- **Estructura visual**: cada tarjeta de publicación lleva una barra de
  color a la izquierda que identifica su categoría (no es decoración: es
  información). Las pestañas de categoría imitan separadores de carpeta.
- **Modo claro/oscuro**: variables CSS en `themes.css`, activadas con
  `data-tema="oscuro"` en `<html>` y persistidas en `localStorage` desde
  `likes.js`.
- Totalmente responsivo (`style.css`, sección `@media`), con foco de
  teclado visible y soporte de `prefers-reduced-motion`.

---

## 3. Arquitectura del proyecto

```
triumphare-wiki/
├── app.py                 # App factory, todas las rutas/vistas
├── config.py              # Configuración por entorno (lee .env)
├── extensions.py          # db, login_manager, csrf, migrate (sin imports circulares)
├── models.py               # User, Category, Post, Comment, Like + gamificación
├── forms.py                # Formularios Flask-WTF con validación y CSRF
├── requirements.txt
├── .env.example             # Plantilla de variables de entorno
├── .gitignore
├── instance/                 # Base de datos SQLite (NO se versiona)
├── static/
│   ├── css/
│   │   ├── themes.css        # Tokens de color/tipografía + modo oscuro
│   │   └── style.css         # Layout y componentes
│   └── js/
│       ├── likes.js          # Fetch API para likes + toggle de tema
│       └── search.js         # Búsqueda en tiempo real (debounce)
└── templates/
    ├── base.html              # Masthead, nav, pestañas de categoría, footer
    ├── _macros.html           # Macro de tarjeta de post + paginación
    ├── index.html             # Muro principal + ranking de prestigio
    ├── explorar.html          # Listado filtrable por categoría
    ├── login.html / registro.html
    ├── crear_post.html / editar_post.html
    ├── post_detalle.html      # Detalle + comentarios + like
    ├── perfil.html            # Perfil público con estadísticas
    └── error.html             # 403 / 404 / 500
```

**Patrón usado:** *application factory* (`create_app()`) + instancias de
extensiones separadas en `extensions.py`, justamente para evitar el clásico
problema de imports circulares entre `app.py` y `models.py`.

---

## 4. Gamificación: Puntos de Prestigio

Definidos en `models.py` (clase `PUNTOS`), fáciles de rebalancear:

| Acción | Puntos |
|---|---|
| Crear una publicación | +10 |
| Recibir un "me gusta" | +2 |
| Escribir un comentario | +1 |
| Recibir un comentario | +1 |

El campo `User.rango` traduce el puntaje acumulado en un título honorífico
("Nuevo Miembro" → "Miembro Comprometido" → "Colaborador Activo" →
"Mentor Destacado" → "Leyenda Triumphare"), visible en el perfil y en el
ranking de la página principal.

---

## 5. Puesta en marcha (desarrollo local)

```bash
# 1. Clonar / descomprimir el proyecto y entrar en la carpeta
cd triumphare-wiki

# 2. Crear y activar un entorno virtual
python3 -m venv venv
source venv/bin/activate          # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Abre .env y genera una SECRET_KEY real, por ejemplo con:
python -c "import secrets; print(secrets.token_hex(32))"

# 5. Inicializar la base de datos y las categorías base
python
>>> from app import create_app
>>> from extensions import db
>>> from models import Category
>>> app = create_app()
>>> with app.app_context():
...     db.create_all()
...     categorias = [
...         {"nombre": "Académico", "slug": "academico", "icono": "📚", "color": "#14213D"},
...         {"nombre": "Eventos", "slug": "eventos", "icono": "🎉", "color": "#E8A33D"},
...         {"nombre": "Deportes", "slug": "deportes", "icono": "🏆", "color": "#2E8B77"},
...         {"nombre": "Off-Topic", "slug": "off-topic", "icono": "💬", "color": "#8C5AA8"},
...     ]
...     for c in categorias:
...         db.session.add(Category(**c))
...     db.session.commit()
>>> exit()

# 6. Ejecutar el servidor de desarrollo
flask run
# o alternativamente:
python app.py
```

La plataforma quedará disponible en `http://127.0.0.1:5000`.

> 💡 Las 4 categorías (Académico, Eventos, Deportes, Off-Topic) son
> etiquetas estructurales del foro, no contenido del colegio — se crean
> una sola vez, igual que se crearían las carpetas de un archivador.
> A partir de ahí, todo el contenido lo generan los estudiantes.

### Notas para producción
- Cambia `FLASK_ENV=production` en tus variables de entorno reales.
- Usa una base de datos como PostgreSQL en vez de SQLite (`DATABASE_URL`).
- Sirve la aplicación con un servidor WSGI como Gunicorn detrás de Nginx.
- Nunca subas tu archivo `.env` real a un repositorio (ya está en `.gitignore`).

---

## 6. Funcionalidades ya verificadas

Se probó de punta a punta (registro → login → crear post → like → comentar →
editar → permisos → logout) antes de la entrega:

- Registro/login/logout con contraseñas hasheadas.
- CRUD de publicaciones restringido al autor (o admin); un intento de
  edición por parte de otro usuario responde `403`.
- Likes asíncronos sin recarga de página, con contador en vivo.
- Comentarios con acumulación correcta de Puntos de Prestigio.
- Búsqueda en tiempo real por título vía `/api/buscar`.
- Filtro por categoría y paginación en el muro y en "Explorar".
