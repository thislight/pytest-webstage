from __future__ import annotations
from asyncio import get_running_loop, Future, create_task, Queue, sleep
from datetime import datetime
from typing import Any, Coroutine, ParamSpec, Callable, Protocol, TypeVar, Awaitable, AsyncContextManager, ContextManager
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from contextlib import contextmanager
from dataclasses import dataclass
import time


__all__ = ["WebStage"]

_P = ParamSpec("_P")

_T = TypeVar("_T")


def _nsync(fn: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs) -> Future[_T]:
    return get_running_loop().run_in_executor(None, lambda args, kwargs: fn(*args, **kwargs), args, kwargs)  # type: ignore


class SendKeyProtocol(Protocol):
    def send_keys(self, *value: str): ...


class Keyboard(AsyncContextManager["Keyboard"], ContextManager["Keyboard"]):
    def __init__(self, e: SendKeyProtocol) -> None:
        self.e = e

    def _send_keys(self, value: str):
        self.e.send_keys(value)

    def typing(self, value: str):
        self._send_keys(value)
        return self
    
    def backspace(self):
        return self.typing("\uE003")
    
    def tab(self):
        return self.typing("\uE004")
    
    def clear(self):
        return self.typing("\uE005")
    
    def ret(self):
        return self.typing("\uE006")
    
    def enter(self):
        return self.typing("\uE007")

    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_typ, exc_val, tb):
        return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_typ, exc_val, tb):
        return None


class SyncElement:
    def __init__(self, e: WebElement) -> None:
        self.e = e

    def query_selector(self, selector: str):
        return list(
            map(
                Element,
                map(SyncElement, self.e.find_elements(By.CSS_SELECTOR, selector)),
            )
        )

    def query_selector_one(self, selector: str):
        try:
            return Element(SyncElement(self.e.find_element(By.CSS_SELECTOR, selector)))
        except NoSuchElementException:
            return None

    def click(self):
        self.e.click()

    def value(self) -> str:
        val = self.e.get_property("value")
        return str(val)

    def keyboard(self):
        return Keyboard(self.e)


class Element:
    def __init__(self, e: SyncElement) -> None:
        self.e = e

    def query_selector(self, selector: str):
        return _nsync(self.e.query_selector, selector)

    def query_selector_one(self, selector: str):
        return _nsync(self.e.query_selector_one, selector)

    def click(self):
        return _nsync(self.e.click)

    def value(self):
        return _nsync(self.e.value)
    
    def keyboard(self):
        return self.e.keyboard()


@dataclass
class Cookie:
    name: str
    value: str
    same_site: str = "Lax"

    @classmethod
    def fromdict(cls, d: dict):
        return cls(
            name=d['name'],
            value=d['value'],
            same_site=d['sameSite']
        )



class SyncWebStage:
    """Synchronous API for web stage."""
    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    def go(self, name: int | str):
        if isinstance(name, int):
            if name > 0:
                for _ in range(name):
                    self.driver.forward()
            elif name < 0:
                for _ in range(abs(name)):
                    self.driver.back()
        else:
            self.driver.get(name)

    def query_selector(self, selector: str):
        return list(
            map(
                Element,
                map(SyncElement, self.driver.find_elements(By.CSS_SELECTOR, selector)),
            )
        )

    def query_selector_one(self, selector: str):
        try:
            return Element(
                SyncElement(self.driver.find_element(By.CSS_SELECTOR, selector))
            )
        except NoSuchElementException:
            return None

    def href(self):
        return self.driver.current_url

    def refresh(self):
        return self.driver.refresh()
    
    def screenshot(self):
        return self.driver.get_screenshot_as_png()

    def is_ready(self):
        """Return if the document is ready.

        This checks the document. When this becomes `True`,
        the DOM operations from JavaScript may not be completed.
        So it could not be used for SPA to determine if the app is started.
        If it's the case, you can check for specific DOM element to see if the app is started.
        """
        return bool(self.driver.execute_script("return document.readyState === 'complete'"))

    def until_ready(self):
        while not self.is_ready():
            time.sleep(0)

    def capture_cookies(self) -> list[Cookie]:
        result: list[Cookie] = []
        a = self.driver.get_cookies()
        for o in a:
            c = Cookie.fromdict(o)
            result.append(c)
        return result

    def get_cookie(self, name: str):
        if c := self.driver.get_cookie(name):
            return Cookie.fromdict(c)
        else:
            return None


class WebStage:
    """Asynchronous API for web stage.

    To use this in pytest, asyncio support must be installed for pytest.

    You can access sync API at `.sync`. Most of methods in this class is a `run-in-exectutor` version
    of the one in the sync API.
    """
    def __init__(self, sync: SyncWebStage, *, parent: WebStage | None = None, description: str | None = None) -> None:
        self.sync = sync
        self.parent = parent
        self.description = description
        self.children: list[WebStage] = []

    @classmethod
    def fromdriver(cls, driver: WebDriver):
        return cls(SyncWebStage(driver))

    def go(self, name: int | str):
        return _nsync(self.sync.go, name)

    def query_selector(self, selector: str):
        return _nsync(self.sync.query_selector, selector)

    def query_selector_one(self, selector: str):
        return _nsync(self.sync.query_selector_one, selector)

    def href(self):
        return _nsync(self.sync.href)

    def refresh(self):
        return _nsync(self.sync.refresh)

    def screenshot(self):
        return _nsync(self.sync.screenshot)
    
    @contextmanager
    def step(self, description: str):
        """Declare a new step in test.
        
        Steps must not be nested. `TypeError` will be raised if nesting is detected.
        
        ```python
        with stage.step("Visit the website") as st:
            await st.go("http://google.com")
            
        with stage.step("Check the location") as st:
            location = await st.href()
            assert "https://www.google.com" in location
        ```
        """
        if self.parent:
            raise TypeError('stages could not be nested')
        new_stage = WebStage(self.sync, parent=self, description=description)
        self.children.append(new_stage)
        yield new_stage

    def is_ready(self):
        return _nsync(self.sync.is_ready)

    async def until_ready(self):
        while not (await self.is_ready()):
            await sleep(0)

    def capture_cookies(self):
        return _nsync(self.sync.capture_cookies)

    def get_cookie(self, name: str):
        return _nsync(self.sync.get_cookie, name)
