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
