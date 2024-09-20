from typing import Any, Generator, Iterable, Literal, cast
import pytest
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.service import Service
from selenium.webdriver import (
    Firefox,
    FirefoxOptions,
    FirefoxService,
    Chrome,
    ChromeOptions,
    ChromeService,
)
from selenium.webdriver.common.selenium_manager import SeleniumManager
from .webstage import WebStage
from itertools import repeat
from dataclasses import dataclass
from .conf import read_config


@dataclass
class BrowserOptions:
    version: str


def pytest_addoption(parser: pytest.Parser):
    g = parser.getgroup(
        "webstage",
        "test web applications on real browsers",
    )
    g.addoption(
        "--browser",
        help=f"Specify which browser should be included in tests. All tests depends on a browser are skipped if unspecified. (default: None, supported: {', '.join(ALL_SUPPORTED_BROWSERS)})",
        default=[],
        action="extend",
        nargs="+",
        type=str,
    )
    g.addoption(
        "--browser-headless",
        action="store_true",
        help="Use headless mode for browsers if possible (default: False)",
        dest="browser_headless"
    )
    g.addoption(
        "--firefox-headless",
        action="store_true",
        help="Ask firefox to use headless mode (default: False)",
        dest="firefox_headless"
    )
    g.addoption(
        "--firefox-version",
        action="extend",
        nargs="+",
        type=str,
        help="Specify firefox version for testing (default: stable)",
    )
    g.addoption(
        "--chrome-headless",
        action="store_true",
        help="Ask chrome to use headless mode (default: False)",
        dest="chrome_headless"
    )
    g.addoption(
        "--chrome-version",
        help="Specify chrome version for testing (default: stable)",
        action="extend",
        nargs="+",
        type=str,
    )
    g.addoption(
        "--webstage-offline",
        help="This option prevents network requests for preparing tests (default: False). This option may prevents the selenium uses cached browser binaries.",
        action="store_true",
        dest="webstage_offline"
    )


def pytest_generate_tests(metafunc: pytest.Metafunc):
    if "browser_config" in metafunc.fixturenames:
        browser_names = set(cast(Any, metafunc.config.getoption("browser", skip=True)))
        unsupported_names = browser_names.difference(ALL_SUPPORTED_BROWSERS)
        if unsupported_names:
            raise ValueError(
                f"unsupported browser names: {' ,'.join(unsupported_names)}. (supported names: {' ,'.join(ALL_SUPPORTED_BROWSERS)})"
            )
        variants: list[tuple[str, str, Literal["auto"] | Literal["always"] | Literal["no"]]] = []
        for name in browser_names:
            versions = cast(
                Iterable[str],
                metafunc.config.getoption(f"{name}_version", cast(Any, None)),
            ) or ["stable"]
            variants.extend(zip(repeat(name), versions, repeat("auto")))
        else:
            conf = read_config(".")
            for b in conf.browsers:
                if b.browser not in ALL_SUPPORTED_BROWSERS:
                    raise ValueError(
                        f"unsupported browser names: {b.browser}. (supported names: {' ,'.join(ALL_SUPPORTED_BROWSERS)})"
                    )
                variants.append((b.browser, b.version, conf.cached_browsers))
        metafunc.parametrize(
            "browser_config",
            variants,
            indirect=True,
            ids=(f"{name}({version})" for name, version, _ in variants),
        )


ALL_SUPPORTED_BROWSERS = {"firefox", "chrome"}


def _check_headless(request: pytest.FixtureRequest, name: str):
    if (
        specified_headless := request.config.getoption(
            f"{name}_headless", cast(Any, None)
        )
    ) is not None:
        return bool(specified_headless)
    elif (
        browser_headless := request.config.getoption(
            "browser_headless", cast(Any, None)
        )
    ) is not None:
        return bool(browser_headless)
    else:
        return False

@dataclass
class BrowserConfig:
    browser: str
    version: str
    driver_path: str
    browser_path: str

@pytest.fixture(scope="session")
def browser_config(request: pytest.FixtureRequest) -> BrowserConfig:
    mgr = SeleniumManager()
    offline = request.config.getoption("webstage_offline", cast(Any, None))
    browser, version, cached_browser = request.param
    args = ["--browser", browser, "--browser-version", version]
    if offline:
        args.append("--offline")
    match cached_browser:
        case "always":
            args.append("--force-browser-download")
        case "no":
            args.append("--avoid-browser-download")
        case _:
            pass
    result = mgr.binary_paths(args)
    if result['code'] != 0:
        raise LookupError(f"could not find browser {browser}({version}), use \"webstage check-cache\" to update local cache")

    return BrowserConfig(
        browser=browser,
        version=version,
        driver_path=result['driver_path'],
        browser_path=result['browser_path'],
    )


@pytest.fixture(scope="session")
def browser_service(browser_config: BrowserConfig) -> tuple[Service, BrowserOptions]:
    """
    Get long-live browser service instance and browser options.
    """
    match browser_config.browser:
        case "firefox":
            return FirefoxService(executable_path=browser_config.driver_path), BrowserOptions(version=browser_config.version)
        case "chrome":
            return ChromeService(executable_path=browser_config.driver_path), BrowserOptions(
                version=browser_config.version
            )
        case _:
            raise ValueError(f"unsupported browser name: {browser_config.browser}")


@pytest.fixture
def browser(
    browser_service: tuple[Service, BrowserOptions],
    browser_config: BrowserConfig,
    request: pytest.FixtureRequest
) -> Generator[WebDriver, Any, None]:
    serv, opts = browser_service

    if isinstance(serv, FirefoxService):
        ffopts = FirefoxOptions()
        if _check_headless(request, "firefox"):
            ffopts.add_argument("-headless")
        ffopts.browser_version = opts.version
        ffopts.binary_location = browser_config.browser_path
        with Firefox(service=serv, options=ffopts) as firefox:
            yield firefox
    elif isinstance(serv, ChromeService):
        cropts = ChromeOptions()
        cropts.browser_version = opts.version
        cropts.binary_location = browser_config.browser_path
        if _check_headless(request, "chrome"):
            cropts.add_argument("--headless=new")
        with Chrome(service=serv, options=cropts) as cr:
            yield cr
    else:
        raise ValueError(f"unsupported service: {type(browser_service)}")


@pytest.fixture
def webstage(browser: WebDriver):
    return WebStage.fromdriver(browser)
