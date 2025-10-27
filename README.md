# QA Automation Challenge - PinApp

Este proyecto fue desarrollado como parte del desafío técnico para PinApp. Combina automatización móvil con Appium y pruebas de API, aplicando patrones como Page Object Model y generando reportes con Allure.

## ¿Qué hace este proyecto?

Básicamente cubre dos áreas:
- **Testing móvil**: Pruebas automatizadas sobre la app "My Demo App" de Sauce Labs (Android)
- **Testing de API**: Validación de endpoints REST usando ReqRes como API de prueba

## Estructura del proyecto

```
.
├── downloads/
│   └── mda-2.2.0-25.apk          # APK de la demo app
├── tests/
│   ├── mobile/                    # Tests para la app Android
│   ├── api/                       # Tests de API REST
│   └── utils/                     # Helpers (ADB principalmente)
├── conftest.py                    # Configuración de fixtures y Allure
├── pytest.ini                     # Config de pytest
└── requirements.txt               # Dependencias Python
```

## Casos de prueba

**Mobile**
- Login exitoso y fallido
- Agregar productos al carrito
- Tests de smoke básicos (launch, interacciones UI)
- Test de background/foreground de la app

**API (ReqRes.in)**
- CRUD de usuarios (GET, POST, PUT, PATCH, DELETE)
- Registro exitoso y fallido
- Validación de códigos de respuesta
- Test con respuesta con delay

## Requisitos previos

Necesitás tener instalado:
- **Windows 10/11** (el proyecto está probado en Windows)
- **Java JDK 11+** - para que corra Appium
- **Android SDK** con `adb` en el PATH
- **Node.js LTS** - para instalar Appium
- **Python 3.11+**
- **Allure** - para los reportes (`scoop install allure` o bajalo de GitHub)

## Setup paso a paso

### 1. Crear virtualenv e instalar dependencias

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Instalar Appium 2 y el driver de UiAutomator2

```bash
npx -y appium@2.13.1 -v
appium driver install --source=npm appium-uiautomator2-driver@2.44.3
```

> **Nota**: Elegí versiones específicas porque tuve problemas de compatibilidad con versiones más nuevas en Android 13. La 2.13.1 de Appium con UiAutomator2 2.44.3 es estable.

### 3. Iniciar el servidor de Appium

```bash
npx -y appium@2.13.1 --address 127.0.0.1 --port 4723 --session-override --log appium.log --log-timestamp --log-level debug:debug
```

### 4. Verificar que el emulador o dispositivo esté conectado

```bash
adb devices
```

Si tenés más de un dispositivo, definí cuál usar:
```powershell
$env:ANDROID_SERIAL = "emulator-5554"
```

## Ejecutar los tests

```bash
# Activar virtualenv
.\.venv\Scripts\Activate.ps1

# Todos los tests
pytest

# Solo smoke
pytest -m smoke

# Solo regression
pytest -m regression

# Solo API
pytest -m api
```

## Ver los reportes con Allure

```bash
allure generate allure-results --clean -o allure-report
allure open allure-report
```

Cuando un test falla, el reporte incluye automáticamente:
- Screenshot (via Appium driver y también via ADB como backup)
- Page source XML
- Logcat completo

## Variables de entorno (opcional)

Si necesitás customizar algo:

```powershell
# Para mobile
$env:APPIUM_SERVER_URL = "http://127.0.0.1:4723"
$env:DEVICE_NAME = "emulator-5554"
$env:ANDROID_SERIAL = "emulator-5554"

# Para API
$env:REQRES_BASE_URL = "https://reqres.in"
$env:REQRES_USE_MOCK = "false" 
```
## Troubleshooting común

**"No se detectan dispositivos"**
- Verificá que `adb devices` muestre tu emulador/dispositivo
- Si usás emulador, asegurate que esté completamente iniciado
