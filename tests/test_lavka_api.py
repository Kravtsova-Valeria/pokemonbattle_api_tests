from http import HTTPStatus
import allure
import pytest
from helpers.api_helpers import ApiSession
from config.api_config import BASE_URL_ME


@allure.suite("Тесты покупок в Лавке")
class TestLavka:
    @allure.title("Успешная покупка премиума")
    def test_buy_premium_successful(
        self,
        pokemon_patch_session: ApiSession,
        api_session_lavka: ApiSession,
        cancel_premium_teardown,
    ):
        with allure.step("Убеждаемся, что у тренера нет премиум-подписки"):
            me_response = pokemon_patch_session.get(BASE_URL_ME)
            assert me_response.status_code == HTTPStatus.OK
            assert me_response.json()["data"][0]["is_premium"] is False
        with allure.step("Оплачиваем покупку премиума"):
            payload = {
                "order_type": "premium",
                "details": {
                    "card_number": "2200240723301087",
                    "secure_code": "56456",
                    "card_name": "michael",
                    "card_cvv": "125",
                    "card_actual": "12/29",
                    "days": 3
                }
            }
            buy_response = api_session_lavka.post("/payments", json=payload)
            assert buy_response.status_code == HTTPStatus.OK
            assert buy_response.json()["message"] == "Транзакция успешна"
        with allure.step("Проверяем, что премиум в подключён"):
            me_response = pokemon_patch_session.get(BASE_URL_ME)
            assert me_response.json()["data"][0]["is_premium"] is True

    @allure.title("Провальная попытка покупки премиума")
    @pytest.mark.parametrize("param,value", [
        ("card_number", "11111"),
        ("secure_code", "11111"),
        ("card_cvv", "11111"),
        ("card_actual", "11111"),
    ])
    def test_buy_premium_fail(
        self,
        pokemon_patch_session: ApiSession,
        api_session_lavka: ApiSession,
        cancel_premium_teardown,
        param,
        value,
    ):
        with allure.step("Убеждаемся, что сейчас у тренера нет премиум-подписки"):
            me_response = pokemon_patch_session.get(BASE_URL_ME)
            assert me_response.json()["data"][0]["is_premium"] is False
        with allure.step("Пытаемся оплатить покупку с некорректными данными"):
            details = {
                "card_number": "2200240723301087",
                "secure_code": "56456",
                "card_name": "michael",
                "card_cvv": "125",
                "card_actual": "12/29",
                "days": 3
            }
            details[param] = value
            payload = {"order_type": "premium", "details": details}
            buy_response = api_session_lavka.post("/payments", json=payload)
            assert buy_response.status_code == HTTPStatus.BAD_REQUEST
            assert buy_response.json()["status"] == "error"
        with allure.step("Проверяем, что премиум не подключился"):
            me_response = pokemon_patch_session.get(BASE_URL_ME)
            assert me_response.json()["data"][0]["is_premium"] is False
