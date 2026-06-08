import subprocess

pytest_plugins = ["fixtures.api_fixtures"]


def pytest_addoption(parser):
    parser.addoption(
        "--html-report",
        action="store_true",
        help="Сгенерировать отчёт в формате HTML в директорию allure-report",
    )
    parser.addoption(
        "--prepare-data",
        action="store_true",
        help="Создать на стенде необходимые сущности перед стартом тестов. Использовать только для локального запуска!",
    )


def pytest_sessionfinish(session):
    if session.config.getoption("--html-report"):
        subprocess.call("allure generate --clean --single-file allure-results", shell=True)
