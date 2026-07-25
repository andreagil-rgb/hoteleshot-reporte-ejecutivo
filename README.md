# Reporte Ejecutivo Semanal — Reclutamiento y Bajas (Hoteles HOT)

Envía cada **domingo** un correo ejecutivo **solo a Manolo** con:
- Entrevistas de la semana: hotel, puesto, medio de reclutamiento, status, si fue contratado.
- Bajas de la semana: hotel, puesto, fecha de ingreso, fecha de baja, antigüedad.

Sigue el mismo patrón de autenticación que `hoteleshot-headcount` y
`hoteleshot-reclutamiento`: OAuth2 vía el secreto `GOOGLE_TOKEN_JSON`, proyecto
de Google Cloud `hoteleshot-rrhh`.

## Lógica de datos (importante)

- **Personas que acuden a entrevista / están en proceso**: se cuentan por la
  columna **A — SEMANA** de BASE DE DATOS (número de semana ISO del año, ej.
  30). No se usa la fecha de la columna C porque tiene un typo en el
  encabezado ("FECHA DE INCIO DE PROCESO").
- **Personas que ingresan (contrataciones)**: se cuentan por la columna
  **K — SEMANA DE INGRESO**, de forma independiente. Esto es importante
  porque alguien pudo haber iniciado su proceso una semana e ingresar en
  otra distinta — por eso no se puede inferir la contratación solo a partir
  de las filas que aparecen en la lista de entrevistas de la semana.
- **Bajas**: siguen filtrándose por fecha (columna FECHA DE BAJA en TRACKER),
  ya que esa base no tiene una columna de número de semana equivalente.

## Fuentes de datos

| Reporte | Sheet | Pestaña |
|---|---|---|
| Reclutamiento | BASE RECLUTAMIENTO (`1HSFoDgmkXhPBihMhI7qq_hnxNjwyeoa78ObZHRM2g_g`) | BASE DE DATOS |
| Bajas | BASE HOTELES HOT (`1eKrw_gD8SX9xEk3_7LB2ubnye8dkN7ERWx8KT4pI2_k`) | TRACKER |

## ⚠️ Puntos a verificar antes de activarlo

1. **Correo de Manolo**: en `config.py` puse `manolo@hoteleshot.com` como
   placeholder — cámbialo por su correo real en `DESTINATARIOS_TO`.
2. **Columna FECHA DE BAJA en TRACKER**: el script asume que esa columna solo
   tiene fecha cuando la persona realmente causó baja (si a veces se usa para
   otra cosa, o si el status usa otra palabra distinta a "ACTIVO", ajusta
   `STATUS_ACTIVO_TRACKER` en `config.py`).
3. **Nombre exacto de la pestaña**: confirma que la pestaña se llama
   literalmente `TRACKER` (con ese nombre exacto, sin espacios extra) — si el
   secreto `GOOGLE_TOKEN_JSON` no tiene acceso de lectura a `spreadsheets.readonly`
   (los otros repos usan Gmail/Sheets, así que debería ya estar cubierto, pero
   vale la pena correrlo una vez en modo prueba).
4. **Ventana de la semana**: por default toma los últimos 7 días naturales
   terminando el día que corre el script (domingo). Si prefieres que sea
   lunes-domingo de la semana que acaba de cerrar, dime y lo ajusto.

## Configuración (igual que tus otros repos)

1. Crear repo nuevo en GitHub: `hoteleshot-reporte-ejecutivo`.
2. Subir todos estos archivos.
3. En **Settings → Secrets and variables → Actions**, agregar el secreto
   `GOOGLE_TOKEN_JSON` (puedes reusar el mismo valor que ya tienes en
   `hoteleshot-headcount` / `hoteleshot-reclutamiento`, siempre que ese token
   tenga scope de Gmail Send y Sheets Readonly — si no, genera uno nuevo con
   ambos scopes).
4. El workflow corre automáticamente los domingos 9am CDMX. También puedes
   correrlo manualmente desde la pestaña **Actions → Run workflow**
   (`workflow_dispatch`).

## Probar en local

```bash
pip install -r requirements.txt
export GOOGLE_TOKEN_JSON='{"token": "...", "refresh_token": "...", ...}'
python main.py
```
