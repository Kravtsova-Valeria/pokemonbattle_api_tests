import os
from http import HTTPStatus
from types import SimpleNamespace

import pytest
import requests

from helpers.api_helpers import ApiSession
from config.api_config import LAVKA_BASE_URL, BASE_URL_ME, BASE_URL_POKEMON, BASE_URL_TRAINER
from data.api_constants import TRAINER_ID


@pytest.fixture(scope="session")
def trainer_get_session():
    with requests.Session() as raw_session:
        api = ApiSession(raw_session, base_url="")
        yield api


@pytest.fixture(scope="session")
def pokemon_patch_session():
    with requests.Session() as raw_session:
        raw_session.headers.update({"trainer_token": os.getenv("POKEMON_AUTH_TOKEN")})
        raw_session.headers.update({"Content-Type": "application/json"})
        api = ApiSession(raw_session, base_url="")
        yield api


@pytest.fixture(scope="session")
def api_session_lavka():
    token = os.getenv("POKEMON_AUTH_TOKEN")
    with requests.Session() as session:
        session.headers.update({"trainer_token": token})
        session.headers.update({"Content-Type": "application/json"})
        yield ApiSession(session, base_url=LAVKA_BASE_URL)


@pytest.fixture
def cancel_premium_teardown(api_session_lavka: ApiSession):
    yield
    response = api_session_lavka.post("/cancel_premium")
    assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)


@pytest.fixture
def trainer():
    token = os.getenv("POKEMON_AUTH_TOKEN")
    return SimpleNamespace(id=TRAINER_ID, token=token)


@pytest.fixture
def prepare_and_clear_battle(pokemon_patch_session: ApiSession, trainer):
    api = pokemon_patch_session
    me_response = api.get(BASE_URL_ME)
    assert me_response.status_code == HTTPStatus.OK
    me_body = me_response.json()
    data = me_body["data"][0]
    if pokemon_list := data.get("pokemons_in_pokeballs"):
        pokemon_id = pokemon_list[0]["id"]
    else:
        if pokemon_list := data.get("pokemons_alive"):
            pokemon_id = pokemon_list[0]
        else:
            create_response = api.post(
                BASE_URL_POKEMON,
                json={"name": "NewOrlean", "photo_id": 1}
            )
            assert create_response.status_code == HTTPStatus.CREATED
            pokemon_id = create_response.json()["id"]
        add_response = api.post(
            f"{BASE_URL_TRAINER}/add_pokeball",
            json={"pokemon_id": pokemon_id}
        )
        assert add_response.status_code == HTTPStatus.OK
    yield pokemon_id
    api.post(
        f"{BASE_URL_POKEMON}/knockout",
        json={"pokemon_id": pokemon_id}
    )
