---
task: "Filtro de fechas real y calendario de rango en el panel VX"
slug: 20260930-vx-registro-filtros
effort: standard
effort_source: auto
phase: verify
progress: 35/35
mode: iterate
started: 2026-09-30T12:40:00Z
updated: 2026-09-30T15:10:00Z
principal_stated_goal: "Querría que el filtro funcionara. Actualmente es el limit 500, no me sigue mostrando más allá del día de hoy. En cuanto a los filtros de arriba, me gustaría que, en un solo calendario, se pudieran seleccionar los días concretos arrastrando."
principal_stated_goal_source: prompt
principal_stated_goal_signal: 2
principal_stated_goal_locked: 2026-09-30T12:40:00Z
iteration: 6
---

# ISA — VX Control Center

## Problem

El panel web y la API de lectura están abiertos: cualquiera que alcance el puerto ve el
histórico completo de verificaciones de equipos, con nombre de usuario gráfico y `migasfreeCid`
de cada máquina del centro. La petición era "un login", pero una clave compartida editable
desde la UI traslada el problema en vez de resolverlo: si la conocen veinte profesores,
cualquiera de ellos puede rotarla y dejar fuera al resto, incluido el administrador.

## Vision

El panel exige credencial para leer. Tres llaves: una **clave de acceso** que se reparte
entre el profesorado y solo sirve para mirar; una **clave de administración** guardada en base
de datos, que su dueño rota desde el navegador sin tocar el servidor; y una **llave maestra**
en el entorno, cambiable solo por SSH, que entra siempre. Cambiar una clave expulsa a las
sesiones abiertas con ella y solo a esas, que es lo que hace que rotar signifique algo. La
ingesta de informes del cliente Tauri sigue funcionando sin cambios en los equipos.

## Out of Scope

- Cuentas nominales por profesor, registro, recuperación de contraseña o gestión de usuarios.
- Crear la primera clave de administración en el primer login sin credencial previa: abriría
  la administración al primero que alcance el puerto tras el despliegue.
- SSO / SAML contra el Google Workspace del centro.
- Autenticar `POST /v1/report`: rompería los clientes ya desplegados en las aulas. Se deja
  preparado un token opcional, desactivado por defecto.
- Cifrado en tránsito: lo resuelve el proxy que haya delante, no la aplicación.

## Principles

- La autorización, no la fuerza de la contraseña, es lo que resuelve el problema planteado.
- Ninguna medida puede dejar al administrador fuera de su propio panel.
- Los clientes ya instalados en los equipos no se rompen.

## Constraints

- Paridad `/v1/report*` con la API NestJS antigua (ver CLAUDE.md): forma del cuerpo, códigos
  de estado y semántica de los filtros no cambian.
- Sin literales de infraestructura (host, IP, puerto, usuario) en este repositorio: es público.
- Una única dependencia nueva permitida (`itsdangerous`, requerida por `SessionMiddleware`);
  el hashing usa `hashlib` de la biblioteca estándar.
- La suite existente sigue en verde sin reescribirla.

## Goal

Cerrar la lectura del panel y de la API detrás de una clave compartida rotable, donde rotar
exige la clave de administración y revoca las sesiones vivas, sin tocar el cliente Tauri
desplegado.

## Criteria

- [x] ISC-1: `GET /` sin sesión responde 303 a `/login`; con sesión válida responde 200 con la tabla.
- [x] ISC-2: `GET /v1/report` y `GET /v1/report/{id}` sin sesión responden 401.
- [x] ISC-3: `POST /v1/report` sin sesión responde 201 con `AUTH_ENABLED=true` (el cliente desplegado no se rompe).
- [x] ISC-4: `POST /login` con la clave de acceso correcta abre sesión con rol `viewer`.
- [x] ISC-5: `POST /login` con la clave de administración abre sesión con rol `admin`.
- [x] ISC-6: `POST /login` con clave incorrecta responde 401 y no crea sesión.
- [x] ISC-7: `GET /admin` con sesión `viewer` responde 403; con sesión `admin` responde 200.
- [x] ISC-8: rotar la clave desde `/admin` exige reescribir la clave de administración en el formulario; sin ella responde 403 y la clave no cambia.
- [x] ISC-9: tras rotar, una sesión `viewer` abierta con la clave antigua queda invalidada en la siguiente petición.
- [x] ISC-10: la clave de acceso se guarda hasheada (scrypt con sal aleatoria); un `SELECT` sobre `app_settings` no revela la clave en claro.
- [x] ISC-11: `/health` y `/static/*` siguen accesibles sin sesión.
- [x] ISC-12: la suite previa (`tests/test_reports_v1.py`, `test_health.py`, `test_schemas_reports.py`) pasa sin modificar sus asserts.
- [x] ISC-13: con la llave maestra se crea desde `/admin` una clave de administración guardada en base de datos, y esa clave abre sesión con rol `admin`.
- [x] ISC-14: el administrador delegado cambia su propia clave desde `/admin` sin perder su sesión; la anterior deja de valer.
- [x] ISC-15: la llave maestra del entorno sigue abriendo sesión aunque el delegado haya cambiado su clave por una que el maestro desconoce.
- [x] ISC-16: cambiar la clave delegada no cierra las sesiones abiertas con la llave maestra, ni al revés.
- [x] ISC-17: con el login quitado, `GET /` y `GET /v1/report` responden 200 sin credencial.
- [x] ISC-18: con el login quitado, `/admin` y sus rutas POST siguen exigiendo sesión de administración.
- [x] ISC-19: el administrador puede volver a activar el login, y el panel se cierra otra vez.
- [x] ISC-20: recién instalado, `vxloginadmin` abre sesión de administración y `vxlogindocente` de lectura.
- [x] ISC-21: `POST /v1/report` con `etiquetas` las persiste y las devuelve; sin `etiquetas` sigue devolviendo 201.
- [x] ISC-22: tras eliminar `empresa` y `tipo_verificacion` del esquema, un cliente que aún los envía sigue recibiendo 201 y la respuesta no los contiene.

### Anti-criteria

- [x] AC-1: NO existe ninguna ruta que permita cambiar ninguna clave conociendo solo la clave de acceso.
- [x] AC-4: NO existe ninguna ruta que cambie la llave maestra del entorno, ni ninguna combinación de acciones en la interfaz que impida entrar con ella.
- [x] AC-2: NO se rompe ningún campo ni código de estado de `/v1/report*` (paridad NestJS intacta).
- [x] AC-3: NO aparece ninguna contraseña, ni en claro ni hasheada, en logs, plantillas o este repositorio.

### Iteración 6 — filtro de fechas y calendario de rango (2026-09-30)

Contexto medido antes de tocar nada: la base de datos de producción tiene 915 informes desde el
2026-09-23 09:00Z (el `.deb` instalado ese día creó el volumen `vx-registro_postgres_data`
nuevo y dejó huérfano `vx-registro-de-uso_postgres_data`, del 2026-04-09, con el histórico).
El panel pide las 200 últimas filas y filtra después; el contenedor de la tabla vuelve a pedir
`/?partial=1` sin filtros ni límite al cargar y cada 30 s, así que `?limit=500` y cualquier
filtro se pierden en el primer refresco.

- [x] ISC-23: `GET /` con `from`/`to` (YYYY-MM-DD) devuelve exactamente los informes cuyo `timestamp` cae en esos días, aunque existan más de 200 informes más recientes fuera del rango. Falsador: 201 informes de hoy + 1 de hace tres días; filtrar el día antiguo devuelve ese 1.
- [x] ISC-24: Los límites del día son en Europe/Madrid, ambos extremos inclusive: un informe a las 23:30 de D (21:30Z) entra en `to=D`; uno a las 00:30 de D+1 (22:30Z de D) no entra.
- [x] ISC-25: El refresco periódico de la tabla lleva los mismos parámetros que el formulario: con un rango aplicado, 31 s después la tabla sigue filtrada.
- [x] ISC-26: `?limit=500` en la URL se respeta y sobrevive al refresco: la última fila no es de hoy.
- [x] ISC-27: Un solo calendario sustituye a Desde/Hasta: arrastrar sobre los días selecciona el rango, rellena `from`/`to` y filtra la tabla sin pulsar Filtrar.
- [x] ISC-28: Un clic selecciona un solo día; «Borrar fechas» quita el rango y vuelve a los últimos 200.
- [x] ISC-29: La URL tras filtrar es limpia y recargable: `/?from=…&to=…`, sin `partial=1`; al recargarla se pinta la página completa con el calendario mostrando el rango.
- [x] ISC-30: La tabla dice cuántos informes hay en el rango y si se está truncando («mostrando N de M»).
- [x] ISC-31: El calendario no carga nada de internet: cero URLs externas en plantillas y estáticos (el panel vive en la red del centro).
- [x] ISC-32: `/v1/report*` no cambia: `tests/test_reports_v1.py` intacto y en verde.

Anti-claims de esta iteración:

- [x] AC-5: NO se toca el filtrado de `/v1/report` (contrato congelado con el cliente `.deb`).
- [x] AC-6: NO se añade ninguna dependencia JavaScript ni CSS externa; el calendario es vanilla y se sirve desde `/static`.
- [x] AC-7: NO hay migración ni cambio de esquema; el volumen antiguo NO se toca hasta que Jesús decida qué hacer con él.

## Test Strategy

| ISC | Probe |
|-----|-------|
| ISC-1 | `pytest` sobre cliente httpx + navegador real (Chrome) contra el servidor local |
| ISC-2, ISC-3 | `pytest` con `AUTH_ENABLED=true`, asserts de código de estado |
| ISC-4..ISC-9 | `pytest` de flujo con cookies de sesión |
| ISC-10 | `SELECT value FROM app_settings` y comprobar el prefijo `scrypt$` |
| ISC-13..ISC-16 | `pytest` con tres clientes httpx simultáneos (maestro, delegado, tercero) + navegador real |
| AC-4 | `grep` sobre `services/auth.py` — `settings.admin_password` solo se lee, nunca se escribe |
| ISC-11 | `curl -i /health` sin cookie |
| ISC-12 | `uv run pytest -v` completo |
| AC-1 | `grep` sobre `routers/auth.py` — toda ruta de escritura verifica `admin_password` |
| AC-3 | `grep -rn` de las claves de prueba sobre el árbol de trabajo |

## Features

- [x] F1: Configuración y hashing (`core/config.py`, `core/security.py`)
- [x] F2: Modelo `app_settings` + migración `0003`
- [x] F3: Servicio de autenticación (semilla, verificación, rotación, sello de versión)
- [x] F4: Middleware de sesión y guardia de rutas
- [x] F5: Rutas y plantillas `/login`, `/logout`, `/admin`
- [x] F6: Tests, `.env.example`, compose de producción y README
- [x] F7: Clave de administración delegada, rotable desde el navegador (iteración 2)
- [x] F8: Documentación con capturas: README, `CLAUDE.md` y `docs/img/` (iteración 2)
- [x] F9: Generación de secretos en la instalación del `.deb` (iteración 3)
- [x] F10: Claves de fábrica públicas, interruptor de login y campo `etiquetas` (iteración 4)

## Decisions

| Fecha | Decisión | Razón |
|-------|----------|-------|
| 2026-09-04 | Dos niveles de clave en vez de cuentas nominales | Veinte lectores que solo miran una tabla no justifican gestión de usuarios; separa quién lee de quién rota, que era el peligro real planteado |
| 2026-09-04 | Cerrar también `GET /v1/report*` | Devuelve exactamente los mismos datos que el panel; un login solo en `/` sería decorativo |
| 2026-09-04 | `POST /v1/report` sigue abierto | El cliente Tauri está desplegado por `.deb` en los equipos del centro; exigir token rompería las versiones instaladas. Se añade `INGEST_TOKEN` opcional, vacío por defecto |
| 2026-09-04 | Sello de versión consultado en cada petición protegida, sin caché | Una fila indexada por petición en un panel de uso escaso; una caché con TTL haría que rotar tardase en revocar, que es justo lo que rotar debe garantizar |
| 2026-09-04 | Clave de admin en variable de entorno, no en base de datos | Ningún camino desde la UI puede modificarla, así que nadie puede dejar fuera al administrador |
| 2026-09-04 | Rechazado crear la clave de administración en el primer login | Deja la creación abierta a quien alcance el puerto entre el despliegue y el primer acceso, y además no elimina el SSH: lo mueve al momento de recuperar una clave olvidada |
| 2026-09-04 | Dos llaves de administración: maestra en entorno + delegada en base de datos | Separa arrancar el sistema (una vez, desde el servidor) de administrarlo a diario (desde el navegador). El delegado nunca necesita SSH y el maestro nunca se queda fuera |
| 2026-09-04 | Cambiar la clave delegada exige teclear una clave de administración válida | Una sesión olvidada abierta en un aula no basta para apoderarse de la administración |
| 2026-09-04 | Rechazado que la CI escriba una clave de admin por defecto en el `.env` del paquete | El `.deb` se adjunta a una GitHub Release pública: sería una credencial publicada e idéntica en todas las instalaciones, peor que no tener nada porque parece protección |
| 2026-09-04 | Los secretos los genera `postinst.sh` en el servidor, idempotente | Cada máquina tiene los suyos, nunca salen de ella, y actualizar el paquete no pisa lo que el administrador haya puesto |
| 2026-09-04 | `POSTGRES_PASSWORD` queda fuera de la generación automática | En un host con el volumen ya inicializado, cambiarla no cambia la contraseña real de Postgres y dejaría la aplicación sin conexión |
| 2026-09-04 | Claves de fábrica públicas en el repositorio, revirtiendo la generación aleatoria | Decisión explícita del principal tras exponerle el riesgo: el despliegue es la red local del centro y la prioridad es que funcione al instalarlo. `SESSION_SECRET` queda fuera de esa decisión y se sigue generando por servidor, porque publicarlo permitiría falsificar sesiones sin conocer ninguna clave |
| 2026-09-04 | Quitar el login abre el panel pero nunca `/admin` | Si `/admin` se abriera también, cualquiera podría reactivar el login o cambiar las claves, y no habría forma de volver atrás |
| 2026-09-05 | Se eliminan `empresa` y `tipo_verificacion` del esquema | Nunca se almacenaron; declararlos solo sugería que hacían algo. `extra="ignore"` sigue aceptando a los clientes que los envían, así que quitarlos no rompe ningún equipo |
| 2026-09-05 | Las etiquetas se leen sin `sudo`, como el CID | Evita tener que instalar una regla `NOPASSWD` en cada equipo del centro. Si el comando exigiera privilegios, fallaría y el informe llegaría con las etiquetas vacías en vez de bloquearse |
| 2026-09-05 | Las etiquetas NO caen a stderr cuando stdout viene vacío, al contrario que el CID | El CID sí lo hace y puede acabar guardando un mensaje de error como identificador del equipo; no se replica ese defecto en el campo nuevo |
| 2026-09-04 | `etiquetas` se almacena como la cadena que devuelve el comando, sin parsear | No pude verificar el formato de salida de `vx-migasfree-tags -g` (el comando no existe en esta máquina). Guardar el texto crudo no inventa una estructura; el panel lo parte por espacios solo para pintarlo |
| 2026-09-30 | El rango de fechas del panel se resuelve en SQL (`find_for_panel`), `/v1/report` sigue filtrando en Python tras el LIMIT | El panel no tiene contrato de paridad; la API sí. Filtrar tras cortar hacía que «Desde/Hasta» solo viera las 200 filas más recientes |
| 2026-09-30 | Los días del calendario se interpretan en Europe/Madrid, `to` inclusive | Un profesor elige «el día 24», no «desde las 00:00 UTC». El filtro antiguo excluía el propio día `to` y estaba desplazado dos horas |
| 2026-09-30 | Sin rango, 200 filas; con rango, hasta 2000, con aviso si se trunca | Sin rango el panel es «lo último», y el refresco de 30 s debe ser barato; con rango la pregunta es «qué pasó esos días», y truncar en 200 sin avisar es mentir |
| 2026-09-30 | Calendario vanilla en un partial, sin CDN ni librería | El panel vive en la red del centro y tiene que pintarse sin internet; una librería añade una dependencia por un widget de 150 líneas |
| 2026-09-30 | El refresco periódico incluye el formulario (`hx-include`) y ya no dispara en `load` | Era la causa de que `?limit=500` y cualquier filtro se perdieran: el contenedor pedía `/?partial=1` a secas al cargar y cada 30 s |
| 2026-09-30 | El volumen antiguo `vx-registro-de-uso_postgres_data` NO se toca en esta iteración | Recuperar el histórico exige parar el stack o restaurar sobre la base viva; es decisión de Jesús, no mía |

## Changelog

- **2026-09-04** — conjectured: el agente que envía informes es externo y no se puede tocar (CLAUDE.md). refuted by: `vx-login-app/src-tauri/src/main.rs` es la app Tauri del propio principal, versión 1.0.24, con pipeline de release. learned: el cliente sí es modificable, pero está desplegado por `.deb` en cada equipo, así que la restricción real es el coste de redespliegue, no la propiedad del código. criterion now: ISC-3 exige que `POST` siga abierto, y el token de ingesta se añade como opcional en vez de obligatorio.
- **2026-09-04** — conjectured: cerrar `GET /v1/report` rompería a algún consumidor. refuted by: `grep` sobre `vx-login-app` no encuentra ni un solo GET; el panel llama al servicio en proceso, no por HTTP. learned: los endpoints GET no tienen consumidor conocido. criterion now: ISC-2 los cierra con 401 en vez de dejarlos abiertos.

## Changelog (iteración 2)

- **2026-09-04** — conjectured: crear la clave de administración en el primer login resolvería el caso de administradores sin SSH. refuted by: entre el despliegue y el primer acceso la pantalla de creación queda abierta a cualquiera que alcance el puerto, y el servicio arranca solo al encender el servidor; además, recuperar una clave olvidada guardada en base de datos exige SSH igualmente. learned: el problema real no es el arranque —ese día ya se está dentro del servidor— sino cada cambio posterior. criterion now: ISC-13..ISC-16 delegan la administración diaria al navegador manteniendo una llave maestra intocable desde la interfaz.

## Changelog (iteración 4)

- **2026-09-04** — conjectured: unas claves por defecto públicas en un repositorio abierto son un riesgo que no debe asumirse. refuted by: el principal, informado del riesgo, lo asume explícitamente — el panel vive en la red local del centro y la prioridad es que funcione al instalarlo. learned: el modelo de amenaza aquí no es internet, es el aula; y una clave que nadie sabe dónde encontrar produce llamadas al administrador, no seguridad. criterion now: ISC-20 exige que las claves documentadas funcionen recién instalado, y el interruptor de login (ISC-17..ISC-19) hace explícito que se puede prescindir de ellas.
- **2026-09-04** — conjectured: el contrato `/v1/report` está congelado y no admite campos nuevos. refuted by: el propio autor del cliente pide el campo `etiquetas`, y el único consumidor de la respuesta no existe (la app Tauri solo hace POST). learned: lo congelado es lo que los equipos ya desplegados ENVÍAN, no lo que el servidor devuelve. criterion now: ISC-21 exige que un POST sin `etiquetas` siga dando 201, que es la parte del contrato que sí importa.

## Changelog (iteración 6)

- **2026-09-30** — conjectured: el panel solo enseña dos días porque el servidor borra o rota registros. refuted by: `SELECT count(*), min("createdAt")` en producción da 915 filas desde el 2026-09-23 09:00Z, y el volumen `vx-registro-de-uso_postgres_data` (2026-04-09) sigue existiendo junto al nuevo `vx-registro_postgres_data` (2026-09-23 10:31, misma hora que `apt install vx-registro-de-uso` en `dpkg.log`). learned: el `.deb` levanta el stack desde `/opt/vx-registro`, y Compose nombra los volúmenes por el directorio, así que la instalación creó una base vacía y dejó la antigua huérfana. criterion now: AC-7 deja el volumen antiguo intacto hasta que Jesús decida; la recuperación es una tarea aparte.
- **2026-10-01** — decided (Jesús): fusionar el histórico del volumen huérfano en producción. done: copia del volumen → Postgres temporal → `\copy` a tabla temporal → `INSERT … WHERE NOT EXISTS (mismo migasfreeCid+timestamp) ON CONFLICT (id) DO NOTHING`, en una transacción. 724 filas (abr 73, may 356, jun 221, sep 74), 0 ids repetidos, 0 duplicados; `reports` pasó de 1024 a 1748. Copia previa en `~/vx_backups/vx_live_before_merge_20261001_105806.dump` del servidor. El volumen huérfano sigue intacto. verified: `/?from=2026-06-01&to=2026-06-30` en Chrome muestra «221 informes en el rango elegido».
- **2026-09-30** — conjectured: `?limit=500` no funciona en el servidor. refuted by: `/?limit=500&partial=1` (sin HTMX) devuelve filas del 28/09. learned: el contenedor de la tabla tenía `hx-get="/?partial=1"` con `hx-trigger="load, every 30s"`, y ese primer `load` sustituía las 500 filas por las 200 por defecto medio segundo después de pintarse. criterion now: ISC-25 e ISC-26 exigen que el refresco lleve el formulario y que `limit` sobreviva 31 s.
- **2026-09-30** — gotcha: la suite de tests TRUNCA `reports` en la base de desarrollo (5433); lanzarla con el servidor local sembrado apuntando a la misma base deja el panel vacío a media verificación. Sembrar después de los tests, no antes.

## Verification

Suite completa: **39 pasan** (16 previas sin tocar + 23 nuevas), `uv run pytest -q`.
Lint: `uv run ruff check src/ tests/` limpio. `migrations/` seguía en rojo antes de
este trabajo (0001 y 0002, reglas UP/W) y sigue igual; no se ha tocado.

| ISC | Evidencia |
|-----|-----------|
| ISC-1 | Chrome real: `http://127.0.0.1:3001/` redirige a `/login?next=/` y pinta la pantalla de acceso; tras entrar, el panel responde 200. `curl` sin cookie: `GET / -> 303` |
| ISC-2 | `curl` sin cookie: `GET /v1/report -> 401`; `GET /v1/report/{id} -> 401` en test |
| ISC-3 | `curl -X POST /v1/report` sin cookie con la app en `AUTH_ENABLED=true`: `HTTP/1.1 201 Created` |
| ISC-4, ISC-5 | `test_login_con_clave_de_acceso_abre_sesion_de_lectura`, `test_login_con_clave_de_admin_abre_sesion_de_administracion` |
| ISC-6 | `test_login_con_clave_incorrecta_no_abre_sesion` (401 y el panel sigue redirigiendo) |
| ISC-7 | Chrome real: sesión de lectura en `/admin` pinta «Sin permiso»; la cabecera del panel muestra «Salir» pero no «Administración», que sí aparece con sesión de administración |
| ISC-8 | `test_rotar_sin_clave_de_admin_responde_403_y_no_cambia_nada`: 403 y la clave antigua sigue valiendo en un cliente limpio |
| ISC-9 | `test_rotar_invalida_las_sesiones_de_lectura_abiertas`. **Comprobación de mutación**: al hacer que `resolve_role` ignore el sello, este test —y solo este— falla; con el código correcto vuelve a pasar |
| ISC-10 | `SELECT` sobre `app_settings` devuelve `access_password | scrypt$16384...`; el test comprueba además que la clave en claro no aparece dentro |
| ISC-11 | `curl`: `GET /health -> 200`, `/login -> 200`; el CSS de Tailwind se sirve en la propia pantalla de acceso |
| ISC-12 | `uv run pytest -q tests/test_reports_v1.py tests/test_health.py tests/test_schemas_reports.py` -> 16 pasan, sin editar sus asserts |
| AC-1 | `POST /admin/rotate` verifica `admin_password` antes de cualquier escritura (`routers/auth.py`); no hay otra ruta que escriba en `app_settings` |
| AC-2 | Los 16 tests de paridad NestJS pasan sin cambios; el único añadido a `POST /v1/report` es una dependencia que no hace nada con `INGEST_TOKEN` vacío |
| AC-3 | `grep` de literales de infraestructura sobre el árbol: sin coincidencias salvo un falso positivo en el `path` del SVG de GitHub |
| ISC-13 | Chrome real: entrando con la llave maestra, `/admin` ofrece «Crear la clave de administración»; tras enviarla, la tarjeta pasa a «Cambiar» y avisa de las sesiones cerradas. `test_la_llave_maestra_crea_la_clave_de_admin_delegada` |
| ISC-14 | `test_el_delegado_rota_su_propia_clave_sin_perder_la_sesion`: rota, conserva su sesión, y la clave anterior devuelve 401 |
| ISC-15 | `test_la_llave_maestra_sigue_entrando_pase_lo_que_pase`: el delegado cambia la clave a algo que el maestro no sabe, y el maestro entra igual. **Mutación**: desactivando la comprobación de la llave maestra, este test falla |
| ISC-16 | `test_cambiar_la_clave_delegada_no_cierra_las_sesiones_maestras` |
| ISC-17, ISC-18 | Sondas contra el servidor vivo con el login quitado desde el navegador: `GET / -> 200`, `GET /v1/report -> 200`, `GET /admin -> 303`, y `POST /admin/login-toggle` y `/admin/rotate` anónimos `-> 303`. `auth_required` vale `false` en base de datos |
| ISC-19 | `test_volver_a_pedir_clave` |
| ISC-20 | Sondas: `vxloginadmin` da panel 200 y `/admin` 200; `vxlogindocente` da panel 200 y `/admin` 403 |
| ISC-21 | `POST` real con `"etiquetas":"aula-musica planta-1 windows-dual"` devuelve el campo en la respuesta; un `POST` sin el campo devuelve 201. En Chrome, la columna «Etiquetas» pinta las tres etiquetas y un guion en el equipo que no las envía |
| ISC-22 | Sonda con el payload de un cliente antiguo (`empresa` + `tipo_verificacion`): `201`, y la respuesta trae solo las ocho claves esperadas. Un `SELECT` sobre `information_schema` confirma que la tabla nunca tuvo esas columnas |
| Cliente Tauri | `cargo check` en `~/vx-login-app/src-tauri` termina sin errores con la llamada a `vx-migasfree-tags -g` añadida (sin sudo, como el CID) |
| AC-4 | Sondas contra el servidor vivo, cuatro credenciales: delegada `login 303 / admin 200`, maestra `303 / 200`, profesor `303 / 403`, inválida `401`. `SELECT` sobre `app_settings` devuelve dos filas, ambas `scrypt$…` |

### Documentación (iteración 2)

Seis capturas en `docs/img/`, tomadas del panel real con datos de ejemplo inventados,
enlazadas desde el README y verificadas una a una: los seis enlaces resuelven a ficheros
JPEG válidos y ninguna clave de prueba aparece en README, CLAUDE.md, ISA.md ni
`.env.example`. `docs/` ya estaba excluido en `.dockerignore`, así que no engordan la
imagen.

`CLAUDE.md` corrige una afirmación que este trabajo demostró falsa: decía que el agente
que envía informes era externo e intocable, y es la app Tauri del propio autor. La
consecuencia práctica que sí se sostiene, y que queda escrita, es que está desplegada por
`.deb` en cada equipo, así que el contrato se trata como congelado.

### Despliegue (iteración 3)

`postinst.sh` ejecutado dentro de `debian:stable-slim` sobre cinco escenarios: instalación
limpia, actualización repetida, `.env` con claves puestas a mano, fichero sin salto de línea
final, y el caso real de un `.env` de la versión anterior sin bloque de autenticación. En
todos: las variables existentes se conservan, no hay líneas duplicadas, el fichero queda en
`600 root:root` y `POSTGRES_PASSWORD` no se toca. La clave generada mide 28 caracteres
alfanuméricos.

`docker compose config` sobre el `.env` generado devuelve `ADMIN_PASSWORD`,
`SESSION_SECRET`, `AUTH_ENABLED` y `COOKIE_SECURE` en el entorno del contenedor, así que
lo que genera el paquete llega efectivamente a la aplicación.

Verificado además que `docker-entrypoint.sh` ejecuta `alembic upgrade head` antes de
arrancar Uvicorn: la migración `0003` se aplica sola al desplegar, sin paso manual.

### Pendiente para el principal

- Los cambios están **sin commitear**: la revisión del diff y el commit son suyos.
- El despliegue exige fijar `ADMIN_PASSWORD` y `SESSION_SECRET` en el `.env` de
  producción y aplicar la migración `0003` antes de arrancar la imagen nueva.

### Iteración 6 — evidencia (2026-09-30)

| Criterio | Evidencia |
|---|---|
| ISC-23 | `test_rango_de_fechas_alcanza_mas_alla_de_las_200_ultimas`: 201 informes de hoy + 1 del 27; `from=to=2026-09-27` devuelve 1 fila con `VIEJO`; sin rango, 200 filas y `VIEJO` ausente |
| ISC-24 | `test_limites_del_dia_en_hora_de_madrid`: 21:30Z del 24 entra en `to=24`; 22:30Z del 24 (00:30 Madrid del 25) entra solo en `from=25` |
| ISC-25 | Chrome real en `127.0.0.1:3001/?from=2026-09-22&to=2026-09-25`: 35 s después la tabla sigue en «100 informes en el rango elegido»; el log de uvicorn muestra la petición periódica `GET /?from=2026-09-22&to=2026-09-25&component=&onlyOperativo=` |
| ISC-26 | Chrome real en `/?limit=500`: a los 34 s, «500 informes (los más recientes) · de 580 en total» y filas `D19-*` (día 19) presentes; log: `GET /?limit=500&from=&to=…` |
| ISC-27 | Chrome real: `left_click_drag` del 22 al 25 en el calendario → etiqueta «22 sep 2026 – 25 sep 2026», tabla con 100 informes (4 días × 25), sin pulsar Filtrar |
| ISC-28 | Chrome real: clic en el 24 → «24 sep 2026», 25 informes, URL `/?from=2026-09-24&to=2026-09-24`; «Borrar fechas» → «Todas las fechas», 200 informes |
| ISC-29 | Chrome real: navegar a `/?from=2026-09-22&to=2026-09-25` pinta la página entera con el botón «22 sep 2026 – 25 sep 2026» y el rango resaltado en el calendario; la URL empujada por HTMX no lleva `partial=1` (`test_pagina_completa_y_refresco_conservan_los_filtros`) |
| ISC-30 | `test_truncado_avisa_con_el_total_del_rango`: con `limit=2` y 3 informes, «El rango tiene 3 informes y solo se muestran los 2 más recientes» |
| ISC-31 | `rg "https?://" src/app/templates src/app/static/css/tailwind.src.css` solo devuelve el `xmlns` de los SVG y el enlace a GitHub de la cabecera |
| ISC-32 | `tests/test_reports_v1.py` sin cambios (`git status`); suite completa 51/51 en verde |
| AC-5 | `git diff src/app/services/reports.py`: `find_all` intacto; lo nuevo es `find_for_panel` |
| AC-6 | `daterange_picker.html` no tiene `<script src>` ni `<link>`; único JS externo del panel sigue siendo `/static/vendor/htmx.min.js` |
| AC-7 | Sin ficheros nuevos en `migrations/`; en el servidor solo se ejecutaron `SELECT`, `docker inspect`, `docker volume ls` y lecturas de logs |
