CI en GitHub Actions
====================

Este repositorio incluye un workflow en `.github/workflows/ci.yml`.

Jobs
----

- api-mock (Ubuntu):
  - Instala dependencias y ejecuta `pytest -m "api and not api_live" -q`.
  - Genera `allure-report` y sube artefactos: `allure-report` y `allure-results`.

- mobile (opcional, self-hosted):
  - Requiere runner con Android/Appium (label `android`).
  - Se dispara manualmente (`workflow_dispatch`) con `run_mobile=true`.
  - Secrets necesarios:
    - `APPIUM_SERVER_URL` (p. ej. `http://127.0.0.1:4723`).
    - `DEVICE_NAME` (p. ej. `emulator-5554`).
    - `ANDROID_SERIAL` (udid del dispositivo/emulador).

Artefactos
----------

- `allure-results/` y `allure-report/` se publican para su descarga desde la página del workflow.

Notas
-----

- La suite de API corre en modo mock por defecto (no requiere Internet). Para ejecutar en vivo, usar `REQRES_USE_MOCK=false` y el marcador `api_live`.
- Para móviles en CI, es necesario un runner con ADB, Appium y un dispositivo/emulador accesible.

