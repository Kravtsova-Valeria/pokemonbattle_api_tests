from http import HTTPStatus
import ast

import pytest
# import requests
import allure
from jsonschema import validate
from deepdiff import DeepDiff

from data.api_constants import TRAINER_ID
from config.api_config import BASE_URL_TRAINER, BASE_URL_POKEMON, BASE_URL_BATTLE, BASE_URL_ACHIEVEMENTS
from helpers.file_helpers import load_yaml
from helpers.api_helpers import ApiSession


@allure.feature("Trainers")
class TestGetTrainers:
    @pytest.mark.trainers
    @allure.title("GET /trainers - поиск тренеров по городу Москва")
    @allure.tag("trainers")
    def test__get__trainers_city(self, trainer_get_session):
        with allure.step("Отправить GET-запрос с параметром city=Москва"):
            params = {"city": "Москва"}
            response = trainer_get_session.get(BASE_URL_TRAINER, params=params)
        with allure.step("Проверить статус-код 200 и статус 'success'"):
            assert response.status_code == HTTPStatus.OK
            body = response.json()
            assert body["status"] == "success"
        with allure.step("Убедиться, что все тренеры из Москвы"):
            for trainer in body["data"]:
                assert trainer["city"] == "Москва", f'Expected: "Москва", Actual: {trainer["city"]}'

    # @pytest.mark.skip("ID search. No need")
    @pytest.mark.trainers
    @allure.title("GET /trainers - поиск ID тренера из списка")
    def test__get__trainers_id_search(self, trainer_get_session):
        with allure.step("Получить всех тренеров и взять первый ID"):
            all_trainers_search = trainer_get_session.get(BASE_URL_TRAINER).json()
            assert all_trainers_search["status"] == "success"
            existing_id = all_trainers_search["data"][0]["id"]
        with allure.step(f"Запросить тренера с ID {existing_id}"):
            params = {"trainer_id": existing_id}
            response = trainer_get_session.get(BASE_URL_TRAINER, params=params)
        with allure.step("Проверить ответ"):
            assert response.status_code == HTTPStatus.OK
            body = response.json()
            assert body["status"] == "success"
            assert body["data"][0]["id"] == existing_id

    @pytest.mark.trainers
    @allure.title("GET /trainers - поиск тренера по конкретному ID")
    @allure.tag("trainers")
    def test__get__trainers_by_id(self, trainer_get_session):
        with allure.step("Отправить запрос"):
            params = {"trainer_id": 60438}
            response = trainer_get_session.get(BASE_URL_TRAINER, params=params)
        with allure.step("Проверить ответ"):
            assert response.status_code == HTTPStatus.OK
            body = response.json()
            assert body["status"] == "success"
            assert len(body["data"]) > 0, "Тренер не найден"
            assert body["data"][0]["id"] == "60438"

    @pytest.mark.skip("API отдаёт данные с рассинхронизацией регистров (баг или грязные данные)")
    @pytest.mark.trainers
    @allure.title("GET /trainers - сортировка по уровню (desc), город Москва")
    @allure.tag("trainers")
    def test__get__trainers_city__sorted_desc_level(self, trainer_get_session):
        with allure.step("Запрос с сортировкой desc_level"):
            params = {"city": "Москва", "sort": "desc_level"}
            response = trainer_get_session.get(BASE_URL_TRAINER, params=params)
        with allure.step("Проверить сортировку"):
            assert response.status_code == HTTPStatus.OK
            body = response.json()
            assert body["status"] == "success"
            for trainer in body["data"]:
                assert trainer["city"] == "Москва"
            if len(body["data"]) >= 2:
                levels_trainer = [int(trainer["level"]) for trainer in body["data"]]
                assert levels_trainer == sorted(levels_trainer, reverse=True), \
                    f"Ошибка: сортировка не по убыванию: {levels_trainer}"


@allure.feature("Pokemons")
class TestPatchPokemons:
    def _knockout_pokemons(self, session, trainer_id):
        with allure.step(f"Отправить в нокаут всех активных покемонов тренера {trainer_id}"):
            response = session.get(BASE_URL_POKEMON, params={"trainer_id": trainer_id})
            if response.status_code != HTTPStatus.OK:
                return
            pokemons = response.json().get("data", [])
            for pokemon in pokemons:
                if pokemon.get("status") == 1:
                    knockout_data_pokemon = {"pokemon_id": pokemon["id"]}
                    session.post(f"{BASE_URL_POKEMON}/knockout", json=knockout_data_pokemon)

    def _create_new_pokemon(self, session, name="Zendaya", photo_id=2):
        with allure.step(f"Создать нового покемона '{name}'"):
            data = {"name": name, "photo_id": photo_id}
            response = session.post(BASE_URL_POKEMON, json=data)
            if response.status_code != HTTPStatus.CREATED:
                return None
            body = response.json()
            return body.get("id")

    def _update_pokemon_name(self, session, pokemon_id, new_name):
        with allure.step(f"Переименовать покемона {pokemon_id} в '{new_name}'"):
            data = {"pokemon_id": pokemon_id, "name": new_name}
            response = session.patch(BASE_URL_POKEMON, json=data)
            return response.status_code, response.json()

    def _get_pokemon_info_return(self, session, pokemon_id):
        with allure.step(f"Получить информацию о покемоне {pokemon_id}"):
            response = session.get(BASE_URL_POKEMON, params={"pokemon_id": pokemon_id})
            if response.status_code != HTTPStatus.OK:
                return None
            body = response.json()
            for pokemon in body.get("data", []):
                if str(pokemon["id"]) == str(pokemon_id):
                    return pokemon
            return None

    @pytest.mark.pokemons
    @allure.title("PATCH /pokemons - переименование покемона")
    @allure.tag("pokemons")
    def test__pokemon_rename(self, pokemon_patch_session):
        trainer_id = TRAINER_ID
        with allure.step("Подготовка: нокаут всех активных покемонов"):
            self._knockout_pokemons(pokemon_patch_session, trainer_id)
        original_name = "Zendaya"
        pokemon_id = self._create_new_pokemon(pokemon_patch_session, name=original_name, photo_id=2)
        assert pokemon_id is not None, "Покемон не был создан"
        new_name = "Alice"
        status_code, response_body = self._update_pokemon_name(pokemon_patch_session, pokemon_id, new_name)
        with allure.step("Проверить успешность PATCH-запроса"):
            assert status_code == HTTPStatus.OK, f"Запрос patch неуспешный. Статус: {status_code}"
            assert response_body.get("message") == "Информация о покемоне обновлена", \
                f"Ошибка: {response_body.get('message')}"

        pokemon_info = self._get_pokemon_info_return(pokemon_patch_session, pokemon_id)
        assert pokemon_info is not None, f"Покемон с ID {pokemon_id} не найден"
        assert pokemon_info["status"] == 1, f"Ожидание: status=1, получен status={pokemon_info['status']}"
        assert pokemon_info["name"] == new_name, \
            f'Ожидаемое имя: "{new_name}", получено: "{pokemon_info["name"]}"'


@allure.feature("Battle")
class TestGetBattle:
    @allure.title("GET /battle - проверка структуры ответа")
    @pytest.mark.api
    def test__get_battle_pokemons(self, pokemon_patch_session):
        with allure.step("Получить список битв"):
            response = pokemon_patch_session.get(BASE_URL_BATTLE)
        with allure.step("Проверить статус-код и JSON-схему"):
            assert response.status_code == HTTPStatus.OK
            body = response.json()
            template = load_yaml("battle_get.yml")
            validate(body, template)


@allure.feature("Achievements")
class TestGetAchievements:
    @allure.title("GET /achievements - проверка структуры и содержимого")
    @pytest.mark.api
    def test__get_achievements(self, pokemon_patch_session):
        with allure.step("Получить достижения"):
            response = pokemon_patch_session.get(BASE_URL_ACHIEVEMENTS)
        with allure.step("Проверить статус-код и схему"):
            assert response.status_code == HTTPStatus.OK
            body = response.json()
            schema_get = load_yaml("achievements_get.yml")
            validate(body, schema_get)
        with allure.step("Сравнить с ожидаемым шаблоном (без is_reached)"):
            template = {
                'data': [
                    {'is_reached': False, 'slug': 'beginning'},
                    {'is_reached': False, 'slug': 'out_of_battles'},
                    {'is_reached': False, 'slug': 'self_knockout'},
                    {'slug': 'max_level'},
                    {'is_reached': False, 'slug': 'one_vs_seven'},
                    {'is_reached': False, 'slug': 'five_battles'},
                    {'is_reached': False, 'slug': 'three_defends'}
                ]
            }
            compare = DeepDiff(
                template, body,
                exclude_regex_paths=[r"root\['data'\]\[\d+\]\['is_reached'\]"]
            )
            assert not compare, f"Ответ не соответствует: {compare}"

    @pytest.mark.xfail(reason="BUG: API возвращает 500 вместо 422 при передаче строки в is_reached")
    @allure.title("GET /achievements - негативный тест (is_reached='yes')")
    @allure.tag("negative")
    def test__negative__get_achievements_is_reached(self, pokemon_patch_session, check):
        with allure.step("Отправить запрос с некорректным is_reached"):
            response = pokemon_patch_session.get(
                BASE_URL_ACHIEVEMENTS,
                params={"is_reached": "yes"}
            )
        with allure.step("Тест mark.xfail"):
            check.equal(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
            body = response.json()
            with check:
                assert body['status'] == "error"
            with check:
                assert body['message'] == "Описание ошибки"

    @allure.title("GET /achievements - проверка сообщения об ошибке валидации (заглушка)")
    @pytest.mark.api
    def test__negative__get_achievements_is_reached_star(self, check):
        with allure.step("Проверить структуру мок-ответа"):
            mock_response = {
                "error": "ValidationError",
                "message": "{'type': 'type_error.bool', 'loc': ('query', 'is_reached'), 'msg': 'value could not be parsed to a boolean', 'input': 'yes'}"
            }
            with check:
                assert mock_response["error"] == "ValidationError"
            parsed_message = ast.literal_eval(mock_response["message"])
            with check:
                assert parsed_message["type"] == "type_error.bool"
                assert parsed_message["msg"] == "value could not be parsed to a boolean"
                assert parsed_message["input"] == "yes"
                assert parsed_message["loc"] == ("query", "is_reached")


@allure.suite("Тесты прохождения битвы покемонов")
class TestPokemonBattle:
    @allure.title("Битва покемонов: получение информации о битвах")
    def test_get_battle(self, pokemon_patch_session):
        with allure.step("Получить список битв"):
            response = pokemon_patch_session.get(BASE_URL_BATTLE)
        with allure.step("Проверить статус-код и JSON-схему"):
            assert response.status_code == HTTPStatus.OK
            body = response.json()
            template = load_yaml("battle_get.yml")
            validate(body, template)

    @allure.title("Битва покемонов: успешное прохождение")
    def test_run_battle_successfully(
        self,
        pokemon_patch_session: ApiSession,
        prepare_and_clear_battle: str,
        trainer
    ):
        my_pokemon_id = prepare_and_clear_battle
        api = pokemon_patch_session
        with allure.step("Находим нашему покемону соперника"):
            ready_response = api.get(
                BASE_URL_POKEMON,
                params={"in_pokeball": 1}
            )
            assert ready_response.status_code == HTTPStatus.OK
            ready_body = ready_response.json()
            suitable_pokemons = [
                p for p in ready_body["data"]
                if p["trainer_id"] != str(trainer.id)
            ]
            assert suitable_pokemons, "Нет доступных соперников в покеболах"
            enemy_pokemon_id = suitable_pokemons[0]["id"]
        with allure.step("Проводим битву"):
            battle_response = api.post(
                BASE_URL_BATTLE,
                json={
                    "attacking_pokemon": my_pokemon_id,
                    "defending_pokemon": enemy_pokemon_id
                }
            )
            assert battle_response.status_code == HTTPStatus.OK
            battle_body = battle_response.json()
            assert battle_body["message"] == "Битва проведена"
        with allure.step("Проверяем состояние покемонов после битвы"):
            my_state = api.get(
                BASE_URL_POKEMON,
                params={"pokemon_id": my_pokemon_id}
            ).json()["data"][0]
            enemy_state = api.get(
                BASE_URL_POKEMON,
                params={"pokemon_id": enemy_pokemon_id}
            ).json()["data"][0]
            if battle_body["result"] == "Твой покемон победил":
                assert my_state["status"] == 1, "Победитель должен быть жив"
                assert my_state["in_pokeball"] == 1, "Победитель должен оставаться в покеболе"
                assert enemy_state["status"] == 0, "Проигравший должен быть в нокауте"
                assert enemy_state["in_pokeball"] == 0, "Проигравший должен выпасть из покебола"
            else:
                assert my_state["status"] == 0, "Проигравший должен быть в нокауте"
                assert my_state["in_pokeball"] == 0, "Проигравший должен выпасть из покебола"
                assert enemy_state["status"] == 1, "Победитель должен быть жив"
                assert enemy_state["in_pokeball"] == 1, "Победитель должен оставаться в покеболе"
