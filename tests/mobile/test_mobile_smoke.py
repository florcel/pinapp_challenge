import logging
import os

import pytest
import allure
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


logger = logging.getLogger(__name__)


@pytest.mark.smoke
@allure.suite("Mobile")
@allure.tag("mobile", "android")
@allure.severity(allure.severity_level.CRITICAL)
def test_launch_main_activity(driver):
    with allure.step("Esperar actividad inicial"):
        WebDriverWait(driver, 15).until(lambda d: d.current_activity)
    activity = driver.current_activity
    package = driver.current_package
    logger.info("Activity: %s | Package: %s", activity, package)
    assert activity, "No se detectó actividad tras el lanzamiento"
    assert package == "com.saucelabs.mydemoapp.android"

@pytest.mark.smoke
@allure.suite("Mobile")
@allure.tag("mobile", "android")
@allure.severity(allure.severity_level.NORMAL)
def test_ui_interactions(driver):
    def _find_clickables_with_retry(max_attempts=2):
        last_err = None
        for attempt in range(1, max_attempts + 1):
            try:
                return WebDriverWait(driver, 20).until(
                    EC.presence_of_all_elements_located(
                        (AppiumBy.ANDROID_UIAUTOMATOR, 'new UiSelector().clickable(true)')
                    )
                )
            except WebDriverException as e:
                last_err = e
                if "socket hang up" in str(e).lower():
                    try:
                        pkg = driver.current_package
                        driver.activate_app(pkg)
                    except Exception:
                        try:
                            driver.launch_app()
                        except Exception:
                            pass
                    continue
                raise
        if last_err:
            raise last_err

    with allure.step("Esperar elementos clickeables"):
        elements = _find_clickables_with_retry()
    assert elements, "No se encontraron elementos clickeables"

    with allure.step("Click en primer elemento clickeable"):
        elements[0].click()

    with allure.step("Verificar app activa"):
        state = driver.query_app_state(driver.current_package)
        assert state in (3, 4), f"Estado de app no esperado: {state}"

@pytest.mark.regression
@allure.suite("Mobile")
@allure.tag("mobile", "android")
@allure.severity(allure.severity_level.CRITICAL)
def test_background_recovery(driver):
    with allure.step("Enviar app a background y recuperar"):
        driver.background_app(2)
    with allure.step("Verificar actividad tras recuperar"):
        WebDriverWait(driver, 10).until(lambda d: d.current_activity)
        assert driver.current_activity, "La app no recuperó actividad"
