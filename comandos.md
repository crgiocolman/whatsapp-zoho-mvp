# Comandos de referencia — WhatsApp Zoho MVP

## Entorno virtual

| Comando                 | Descripción                                                               |
| ----------------------- | ------------------------------------------------------------------------- |
| `python -m venv venv`   | Crea el entorno virtual en la carpeta `venv/`                             |
| `venv\Scripts\activate` | Activa el entorno virtual (Windows). Deberías ver `(venv)` en la terminal |
| `deactivate`            | Desactiva el entorno virtual                                              |

## Dependencias

| Comando                           | Descripción                                         |
| --------------------------------- | --------------------------------------------------- |
| `pip install -r requirements.txt` | Instala todas las dependencias del proyecto         |
| `pip install nombre-paquete`      | Instala un paquete específico                       |
| `pip freeze > requirements.txt`   | Genera el archivo requirements.txt con lo instalado |
| `pip list`                        | Lista todos los paquetes instalados en el entorno   |

## Correr el servidor

| Comando                                               | Descripción                                                    |
| ----------------------------------------------------- | -------------------------------------------------------------- |
| `python -m uvicorn app.main:app --reload`             | Inicia FastAPI con recarga automática. Forma segura en Windows |
| `python -m uvicorn app.main:app --reload --port 8001` | Igual pero en otro puerto (útil si el 8000 está ocupado)       |

## Git

| Comando                   | Descripción                                   |
| ------------------------- | --------------------------------------------- |
| `git add .`               | Agrega todos los cambios al staging           |
| `git commit -m "mensaje"` | Guarda los cambios con un mensaje descriptivo |
| `git push`                | Sube los cambios a GitHub                     |
| `git status`              | Muestra qué archivos cambiaron                |

## Docker

| Comando                                                                                                                                            | Descripción                                                 |
| -------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| `docker run --name whatsapp-zoho-db -e POSTGRES_USER=admin -e POSTGRES_PASSWORD=admin123 -e POSTGRES_DB=whatsapp_zoho -p 5432:5432 -d postgres:15` | Crea y levanta el contenedor PostgreSQL por primera vez     |
| `docker ps`                                                                                                                                        | Lista los contenedores corriendo                            |
| `docker start whatsapp-zoho-db`                                                                                                                    | Levanta el contenedor si ya existe (después del primer run) |
| `docker stop whatsapp-zoho-db`                                                                                                                     | Detiene el contenedor                                       |

## PgAdmin (Levantar dentro de Docker)

| Comando                                                                                                                             | Descripción                          |
| ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| `docker run -d --name pgadmin -e PGADMIN_DEFAULT_EMAIL=admin@admin.com -e PGADMIN_DEFAULT_PASSWORD=admin -p 5050:80 dpage/pgadmin4` | Levanta el pgadmin en localhost:5050 |

## PostgreSQL (dentro de Docker)

| Comando                                                                                             | Descripción                     |
| --------------------------------------------------------------------------------------------------- | ------------------------------- |
| `docker exec -it whatsapp-zoho-db psql -U admin -d whatsapp_zoho -c "\dt"`                          | Lista las tablas de la DB       |
| `docker exec -it whatsapp-zoho-db psql -U admin -d whatsapp_zoho -c "SELECT * FROM conversations;"` | Ver registros de conversaciones |
| `docker exec -it whatsapp-zoho-db psql -U admin -d whatsapp_zoho -c "SELECT * FROM messages;"`      | Ver registros de mensajes       |

## ngrok

| Comando           | Descripción                                        |
| ----------------- | -------------------------------------------------- |
| `ngrok http 8000` | Expone el puerto 8000 públicamente para el webhook |

## Alembic — Migraciones de base de datos

| Comando                                            | Descripción                                                    |
| -------------------------------------------------- | -------------------------------------------------------------- |
| `alembic init alembic`                             | Inicializa Alembic en el proyecto (solo una vez)               |
| `alembic revision --autogenerate -m "descripcion"` | Genera una migración automática basada en cambios en models.py |
| `alembic upgrade head`                             | Aplica todas las migraciones pendientes a la DB                |
| `alembic stamp head`                               | Marca el estado actual como línea base sin ejecutar nada       |
| `alembic current`                                  | Muestra la migración actualmente aplicada                      |
| `alembic downgrade -1`                             | Revierte la última migración                                   |
| `alembic history`                                  | Lista todas las migraciones del proyecto                       |

## PgAdmin

| docker run -d --name pgadmin -e PGADMIN_DEFAULT_EMAIL=admin@admin.com -e PGADMIN_DEFAULT_PASSWORD=admin -p 5050:80 dpage/pgadmin4
