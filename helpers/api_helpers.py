import re
import time
import json
from http import HTTPStatus

import allure
from requests import Session


class ApiRequestsLimitError(Exception):
    pass


class ApiSession:
    def __init__(self, session: Session, base_url: str = ""):
        self.session = session
        self.base_url = base_url

    def _prepare_url(self, url: str):
        if re.match(r"https?://", url.lower()):
            return url
        return f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"

    def _send(self, method: str, url: str, **kwargs):
        timestamp = time.time() + 5
        while time.time() < timestamp:
            retry_is_possible = True
            response = self.session.request(method=method, url=self._prepare_url(url), **kwargs)

            if isinstance(response.request.body, bytes):
                request_body = response.request.body.decode(encoding="utf-8")
            else:
                request_body = response.request.body

            response_body = {}
            try:
                response_body = response.json()
                response_body_string = json.dumps(response_body, indent=4, ensure_ascii=False)
            except Exception:
                response_body_string = response.content.decode(encoding="utf-8")
                retry_is_possible = False

            allure.attach(
                body=f"Request:\n"
                     f"Method: {method}\n"
                     f"URL: {response.request.url}\n"
                     f"Headers: {json.dumps(dict(response.request.headers), indent=4, ensure_ascii=False)}\n"
                     f"Body: {json.dumps(request_body, indent=4, ensure_ascii=False)}\n\n"
                     f"Response:\n"
                     f"Status code: {response.status_code}\n"
                     f"Headers: {json.dumps(dict(response.headers), indent=4, ensure_ascii=False)}\n"
                     f"Body: {response_body_string}\n",
                name="Детальная информация о запросе и ответе",
                attachment_type=allure.attachment_type.TEXT,
            )
            if (
                retry_is_possible and
                response.status_code == HTTPStatus.BAD_REQUEST and
                response_body.get("message") == "Лимит запросов превышен"
            ):
                time.sleep(1)
            else:
                break
        else:
            raise ApiRequestsLimitError(
                "Не удалось прорваться через rate limiter или возникла другая ошибка, см. репорт allure"
            )
        return response

    @allure.step("GET-запрос к адресу {url}")
    def get(self, url: str, params: dict | None = None, headers: dict | None = None):
        return self._send("GET", url=url, params=params, headers=headers)

    @allure.step("POST-запрос к адресу {url}")
    def post(self, url: str, params: dict | None = None, json: dict | None = None, headers: dict | None = None):
        return self._send("POST", url=url, params=params, json=json, headers=headers)

    @allure.step("PATCH-запрос к адресу {url}")
    def patch(self, url: str, params: dict | None = None, json: dict | None = None):
        return self._send("PATCH", url=url, params=params, json=json)

    @allure.step("PUT-запрос к адресу {url}")
    def put(self, url: str, json: dict | None = None):
        return self._send("PUT", url=url, json=json)
