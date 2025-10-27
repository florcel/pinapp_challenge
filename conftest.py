import os
import platform
import subprocess
import logging
from typing import Optional

import pytest
import allure

from appium import webdriver
from appium.options.android import UiAutomator2Options

from tests.utils.adb import wait_for_boot, list_connected_devices


def _ensure_allure_env(config: pytest.Config) -> None:
    """
    Crea el archivo environment.properties para Allure con metadata útil.
    Esto hace que el reporte muestre info del entorno donde corrieron los tests.
    """
    results_dir = config.getoption("--alluredir", default=None)
    if not results_dir:
        return
    os.makedirs(results_dir, exist_ok=True)
    env_path = os.path.join(results_dir, "environment.properties")
    lines = [
        f"OS={platform.system()} {platform.release()}",
        f"Python={platform.python_version()}",
        f"AppiumServerURL={os.getenv('APPIUM_SERVER_URL', 'http://127.0.0.1:4723')}",
    ]
    if os.getenv("DEVICE_NAME"):
        lines.append(f"DeviceName={os.getenv('DEVICE_NAME')}")
    if os.getenv("ANDROID_SERIAL"):
        lines.append(f"UDID={os.getenv('ANDROID_SERIAL')}")
    if os.getenv("UDID") and not os.getenv("ANDROID_SERIAL"):
        lines.append(f"UDID={os.getenv('UDID')}")
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass  


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    _ensure_allure_env(config)
    lvl = os.getenv("LOG_LEVEL", "INFO").upper()
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=getattr(logging, lvl, logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )


def _try_attach_screenshot_from_driver(driver) -> bool:
    try:
        png = driver.get_screenshot_as_png()
        if png:
            allure.attach(png, name="screenshot", attachment_type=allure.attachment_type.PNG)
            try:
                src = driver.page_source
                if src:
                    allure.attach(src, name="page_source", attachment_type=allure.attachment_type.XML)
            except Exception:
                pass 
            return True
    except Exception:
        pass
    return False


def _adb_udid() -> Optional[str]:
    return os.getenv("ANDROID_SERIAL") or os.getenv("UDID")


def _try_attach_screenshot_via_adb() -> bool:
    udid = _adb_udid()
    cmd = ["adb"]
    if udid:
        cmd += ["-s", udid]
    cmd += ["exec-out", "screencap", "-p"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and res.stdout:
            allure.attach(res.stdout, name="adb_screenshot", attachment_type=allure.attachment_type.PNG)
            return True
    except Exception:
        pass
    return False


def _try_attach_logcat() -> None:
    udid = _adb_udid()
    cmd = ["adb"]
    if udid:
        cmd += ["-s", udid]
    cmd += ["logcat", "-d", "-t", "2000"]
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace"
        )
        if res.returncode == 0 and res.stdout:
            allure.attach(res.stdout, name="logcat", attachment_type=allure.attachment_type.TEXT)
    except Exception:
        pass
    finally:
        try:
            clear_cmd = ["adb"] + (["-s", udid] if udid else []) + ["logcat", "-c"]
            subprocess.run(clear_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """
    Hook que se ejecuta después de cada test.
    Si el test falló, adjunta automáticamente screenshots y logs.
    """
    outcome = yield
    rep = outcome.get_result()

    if rep.when != "call" or rep.passed:
        return

    driver = None
    try:
        for key in ("driver", "appium_driver", "wd", "client"):
            if key in getattr(item, "funcargs", {}):
                driver = item.funcargs.get(key)
                break
        if not driver and hasattr(item, "instance"):
            for key in ("driver", "appium_driver"):
                driver = getattr(item.instance, key, None)
                if driver:
                    break
    except Exception:
        driver = None

    attached = False
    if driver:
        attached = _try_attach_screenshot_from_driver(driver)
    if not attached:
        _try_attach_screenshot_via_adb()
    
    _try_attach_logcat()


@pytest.fixture(scope="function")
def driver() -> webdriver.Remote:
    apk = os.path.abspath(os.path.join(os.path.dirname(__file__), "downloads", "mda-2.2.0-25.apk"))
    assert os.path.exists(apk), f"APK not found at: {apk}"

    udid_env = os.getenv("ANDROID_SERIAL") or os.getenv("UDID")
    if not udid_env:
        devices = list_connected_devices()
        if len(devices) == 0:
            raise AssertionError("No hay dispositivos/emuladores Android conectados (adb devices vacio)")
        if len(devices) > 1:
            raise AssertionError("Hay múltiples dispositivos. Define ANDROID_SERIAL")
        udid = devices[0]
    else:
        udid = udid_env

    # Esperar a que el device esté listo
    try:
        wait_for_boot(udid, timeout_sec=240)
    except Exception:
        pass  # Si falla el wait, intentar igualmente

    # Capabilities: después de mucho trial & error, estas son las que mejor funcionan
    caps = {
        "platformName": "Android",
        "automationName": "UiAutomator2",
        "deviceName": os.getenv("DEVICE_NAME", "Android Emulator"),
        **({"udid": udid} if udid else {}),
        "app": apk,
        "autoGrantPermissions": True,
        
        "appPackage": "com.saucelabs.mydemoapp.android",
        "appActivity": "com.saucelabs.mydemoapp.android.view.activities.SplashActivity",
        "appWaitActivity": "com.saucelabs.mydemoapp.android.view.activities.*",
        
        "newCommandTimeout": 120,
        "adbExecTimeout": 120000,
        "uiautomator2ServerInstallTimeout": 120000,
        "uiautomator2ServerLaunchTimeout": 120000,
        
        "ignoreHiddenApiPolicyError": True,
        
        "noReset": True,
        
        "disableWindowAnimation": True,
    }

    options = UiAutomator2Options().load_capabilities(caps)
    server_url = os.getenv("APPIUM_SERVER_URL", "http://127.0.0.1:4723")

    drv = webdriver.Remote(server_url, options=options)
    
    try:
        drv.implicitly_wait(5)  # Wait global de 5 seg para encontrar elementos
        drv.update_settings({
            "waitForIdleTimeout": 0,  
            "waitForSelectorTimeout": 15000,  
            "actionAcknowledgmentTimeout": 200,  
        })
    except Exception:
        pass  # Si falla, no es crítico
    
    try:
        yield drv
    finally:
        # Siempre cerrar la sesión al final
        drv.quit()