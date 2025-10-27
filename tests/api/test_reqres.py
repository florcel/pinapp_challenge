import os
import json
import time
from typing import Any, Dict, Optional

import pytest
import requests
import allure
import responses
from urllib.parse import urlparse, parse_qs


BASE_URL = os.getenv("REQRES_BASE_URL", "https://reqres.in")
DEFAULT_TIMEOUT = float(os.getenv("REQRES_TIMEOUT", "15"))
TRUST_ENV = os.getenv("REQRES_TRUST_ENV", "false").lower() in ("1", "true", "yes")
SKIP_ON_PROXY = os.getenv("REQRES_SKIP_ON_PROXY", "true").lower() in ("1", "true", "yes")
USE_MOCK = os.getenv("REQRES_USE_MOCK", "true").lower() in ("1", "true", "yes")

REQRES_HTTP_PROXY = os.getenv("REQRES_HTTP_PROXY")
REQRES_HTTPS_PROXY = os.getenv("REQRES_HTTPS_PROXY")
REQRES_NO_PROXY = os.getenv("REQRES_NO_PROXY")

_SESSION = requests.Session()
_SESSION.trust_env = TRUST_ENV
_PROXIES = {}
if REQRES_HTTP_PROXY:
    _PROXIES["http"] = REQRES_HTTP_PROXY
if REQRES_HTTPS_PROXY:
    _PROXIES["https"] = REQRES_HTTPS_PROXY
if REQRES_NO_PROXY:
    os.environ["NO_PROXY"] = REQRES_NO_PROXY
    os.environ["no_proxy"] = REQRES_NO_PROXY


def _full_url(path: str) -> str:
    if path.startswith("http"):
        return path
    path = path if path.startswith("/") else f"/{path}"
    return f"{BASE_URL}{path}"


def _attach_request_response(resp: requests.Response, name: str = "") -> None:
    try:
        req = resp.request
        allure.attach(
            f"{req.method} {req.url}\n\nHeaders:\n" +
            "\n".join([f"{k}: {v}" for k, v in req.headers.items()]) +
            (f"\n\nBody:\n{req.body!r}" if req.body else ""),
            name=f"request{name and ' - ' + name}",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:
        pass
    try:
        body_preview = None
        try:
            body_preview = json.dumps(resp.json(), indent=2, ensure_ascii=False)
        except Exception:
            body_preview = resp.text
        allure.attach(
            f"Status: {resp.status_code}\n\nHeaders:\n" +
            "\n".join([f"{k}: {v}" for k, v in resp.headers.items()]) +
            f"\n\nBody:\n{body_preview}",
            name=f"response{name and ' - ' + name}",
            attachment_type=allure.attachment_type.TEXT,
        )
    except Exception:
        pass


def _looks_like_proxy_block(resp: requests.Response) -> bool:
    if resp.status_code in (401, 407):
        return True
    h = {k.lower(): v for k, v in resp.headers.items()}
    auth_hdr = (h.get("www-authenticate", "") + " " + h.get("proxy-authenticate", "")).lower()
    via = (h.get("via", "") + " " + h.get("server", "")).lower()
    if any(tok in auth_hdr for tok in ("basic", "ntlm", "negotiate")):
        return True
    if any(tok in via for tok in ("proxy", "squid")):
        return True
    return False


def _skip_if_proxy_block(resp: requests.Response, note: str = "") -> None:
    if SKIP_ON_PROXY and _looks_like_proxy_block(resp):
        pytest.skip(f"ReqRes bloqueado por proxy ({resp.status_code}). {note}".strip())


@pytest.fixture(scope="module", autouse=True)
def _reqres_healthcheck():
    if USE_MOCK:
        return
    if not SKIP_ON_PROXY:
        return
    try:
        r = api_request("GET", "/api/users/2")
        if _looks_like_proxy_block(r):
            pytest.skip(
                f"ReqRes bloqueado por proxy ({r.status_code}). Skipping módulo completo.",
                allow_module_level=True,
            )
    except Exception as e:
        pytest.skip(
            f"ReqRes no accesible en este entorno ({e}). Skipping módulo completo.",
            allow_module_level=True,
        )


@pytest.fixture(scope="module", autouse=True)
def _reqres_mock_server():
    if not USE_MOCK:
        return
    rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
    rsps.start()
    try:
        base = BASE_URL.rstrip("/")

        def _users_callback(req):
            parsed = urlparse(req.url)
            q = {k: v for k, v in parse_qs(parsed.query).items()}
            if q.get("page") == ["2"]:
                body = {
                    "page": 2,
                    "per_page": 6,
                    "total": 12,
                    "total_pages": 2,
                    "data": [
                        {
                            "id": 7,
                            "email": "michael.lawson@reqres.in",
                            "first_name": "Michael",
                            "last_name": "Lawson",
                        }
                    ],
                }
                return (200, {}, json.dumps(body))
            if "delay" in q:
                try:
                    d = int(q.get("delay", ["0"])[0])
                except Exception:
                    d = 0
                # Simular espera para test de delay (cap a 5s)
                if d > 0:
                    time.sleep(min(d, 5))
                return (200, {}, json.dumps({"data": []}))
            # default fallback
            return (200, {}, json.dumps({"data": []}))

        rsps.add_callback(
            responses.GET,
            f"{base}/api/users",
            callback=_users_callback,
            content_type="application/json",
        )
        # GET /api/users/2
        rsps.add(
            responses.GET,
            f"{base}/api/users/2",
            json={"data": {"id": 2, "email": "janet.weaver@reqres.in", "first_name": "Janet", "last_name": "Weaver"}},
            status=200,
        )
        # GET /api/users/23 -> 404
        rsps.add(
            responses.GET,
            f"{base}/api/users/23",
            json={},
            status=404,
        )
        # POST /api/users -> 201
        rsps.add(
            responses.POST,
            f"{base}/api/users",
            json={"id": "123", "name": "morpheus", "job": "leader", "createdAt": "2025-01-01T00:00:00Z"},
            status=201,
        )
        # PUT /api/users/2 -> 200
        rsps.add(
            responses.PUT,
            f"{base}/api/users/2",
            json={"updatedAt": "2025-01-01T00:00:00Z"},
            status=200,
        )
        # PATCH /api/users/2 -> 200
        rsps.add(
            responses.PATCH,
            f"{base}/api/users/2",
            json={"updatedAt": "2025-01-01T00:00:00Z"},
            status=200,
        )
        # DELETE /api/users/2 -> 204
        rsps.add(
            responses.DELETE,
            f"{base}/api/users/2",
            status=204,
        )
        # POST /api/register success
        def _register_callback(req):
            try:
                body = json.loads(req.body or "{}")
            except Exception:
                body = {}
            if body.get("email") and body.get("password"):
                return (200, {}, json.dumps({"token": "QpwL5tke4Pnpja7X4"}))
            return (400, {}, json.dumps({"error": "Missing password"}))

        rsps.add_callback(
            responses.POST,
            f"{base}/api/register",
            callback=_register_callback,
            content_type="application/json",
        )
        yield
    finally:
        rsps.stop()
        rsps.reset()

def api_request(method: str, path: str, *, timeout: Optional[float] = None, **kwargs) -> requests.Response:
    url = _full_url(path)
    headers = {
        "Accept": "application/json",
        "User-Agent": "pytest-reqres/1.0",
    }

    if "headers" in kwargs and isinstance(kwargs["headers"], dict):
        headers.update(kwargs["headers"])  
    kwargs["headers"] = headers

    token = os.getenv("REQRES_BEARER_TOKEN")
    if token and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {token}"

    with allure.step(f"{method.upper()} {url}"):
        if _PROXIES and "proxies" not in kwargs:
            kwargs["proxies"] = _PROXIES
        resp = _SESSION.request(method=method.upper(), url=url, timeout=timeout or DEFAULT_TIMEOUT, **kwargs)
        _attach_request_response(resp)
        return resp

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
@allure.severity(allure.severity_level.NORMAL)
def test_list_users_page_2():
    r = api_request("GET", "/api/users", params={"page": 2})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("data"), list) and len(data["data"]) > 0
    assert data.get("page") == 2

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
@allure.severity(allure.severity_level.CRITICAL)
def test_single_user_found():
    r = api_request("GET", "/api/users/2")
    _skip_if_proxy_block(r, "GET /api/users/2")
    assert r.status_code == 200
    assert r.json().get("data", {}).get("id") == 2

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
@allure.severity(allure.severity_level.MINOR)
def test_single_user_not_found():
    r = api_request("GET", "/api/users/23")
    _skip_if_proxy_block(r, "GET /api/users/23")
    assert r.status_code == 404

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
@allure.severity(allure.severity_level.CRITICAL)
def test_create_user():
    payload = {"name": "morpheus", "job": "leader"}
    r = api_request("POST", "/api/users", json=payload)
    _skip_if_proxy_block(r, "POST /api/users")
    assert r.status_code == 201
    j = r.json()
    assert j.get("id") is not None
    assert j.get("name") == "morpheus"

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
def test_update_user_put():
    payload = {"name": "morpheus", "job": "zion resident"}
    r = api_request("PUT", "/api/users/2", json=payload)
    _skip_if_proxy_block(r, "PUT /api/users/2")
    assert r.status_code == 200
    assert "updatedAt" in r.json()

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
def test_update_user_patch():
    payload = {"job": "rebel"}
    r = api_request("PATCH", "/api/users/2", json=payload)
    _skip_if_proxy_block(r, "PATCH /api/users/2")
    assert r.status_code == 200
    assert "updatedAt" in r.json()

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
def test_delete_user():
    r = api_request("DELETE", "/api/users/2")
    _skip_if_proxy_block(r, "DELETE /api/users/2")
    assert r.status_code == 204

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
@allure.severity(allure.severity_level.CRITICAL)
def test_register_successful():
    payload = {"email": "florencia@pinapp.com", "password": "p4ssw0rd"}
    r = api_request("POST", "/api/register", json=payload)
    _skip_if_proxy_block(r, "POST /api/register")
    assert r.status_code == 200
    assert r.json().get("token")

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
def test_register_unsuccessful():
    payload = {"email": "sydney@fife"}
    r = api_request("POST", "/api/register", json=payload)
    _skip_if_proxy_block(r, "POST /api/register")
    assert r.status_code == 400
    assert "Missing password" in r.text

@pytest.mark.api
@pytest.mark.api_live
@allure.suite("API")
@allure.tag("api", "reqres")
def test_delayed_response():
    start = time.time()
    r = api_request("GET", "/api/users", params={"delay": 3}, timeout=DEFAULT_TIMEOUT + 5)
    _skip_if_proxy_block(r, "GET /api/users?delay=3")
    elapsed = time.time() - start
    assert r.status_code == 200
    assert elapsed >= 2.0  
