# User Manual

- [Getting started](#getting-started)
- [Pytest fixtures](#managing-test-variants)
- [Managing test variants](#managing-test-variants)
- [Navigation on the Web](#navigation-on-the-web)
- [Interacting with elements](#interacting-with-elements)
- Organizing test code with steps
- Async support

## Getting started

Install pytest and pytest-webstage.

```sh
# for pip:
pip install pytest-webstage

# for poetry:
poetry add --group dev pytest-webstage
```

It's recommended to use `webstage.toml` for the configuration.

```sh
webstage init > webstage.toml
```

Write your test in pytest:

```python
# tests/test_browser.py
from pytest_webstage.webstage import WebStage

def test_can_visit_url(webstage: WebStage):
    with webstage.step("Visit Google") as step:
        step.sync.go("https://google.com")
        step.sync.until_ready()
```

If you'd like to check the web drivers and the browsers used:

```sh
webstage check-cache
```

Execute the test:

```sh
pytest
```

## Pytest fixtures

pytest-webstage wraps around [selenium](https://selenium.dev) and has multiple fixtures to support the key feature:

- `browser_config` - `BrowserConfig` object contains browser name, version and paths of the driver and the browser
- `browser_service` - the browser service, the driver to be used to control the browser
- `browser` - a browser instance
- `webstage` - `WebStage` object. This is the entry point for most use.

## Managing test variants

You can specifiy the browser to used in two may:

- commandline arguments, like `pytest --browser firefox`;
- `webstage.toml` in current working directory.

Either way you can specify multiple targets and versions, pytest-webstage automatically parametrized the tests using fixtures `browser_config`, `browser_service`, `browser` and `webstage`.

## Use commandline arguments to specify the browsers to use

To see all arguments for pytest-webstage, use `pytest -h` in an environment with pytest-webstage.

```text
...
test web applications on real browsers:
  --browser=BROWSER [BROWSER ...]
                        Specify which browser should be included in tests. All tests depends on a browser are
                        skipped if unspecified. (default: None, supported: chrome, firefox)
  --browser-headless    Use headless mode for browsers if possible (default: False)
  --firefox-headless    Ask firefox to use headless mode (default: False)
  --firefox-version=FIREFOX_VERSION [FIREFOX_VERSION ...]
                        Specify firefox version for testing (default: stable)
  --chrome-headless     Ask chrome to use headless mode (default: False)
  --chrome-version=CHROME_VERSION [CHROME_VERSION ...]
                        Specify chrome version for testing (default: stable)
  --webstage-offline    This option prevents network requests for preparing tests (default: False). This option may
                        prevents the selenium uses cached browser binaries.
```

- use `--browser <name>` to specify the browsers to use,
- use `--<name>-version <version>` to specify the versions.

For example: use `--browser firefox chrome --firefox-version stable esr --chrome-version stable` to specify:

- Enable testing for firefox and chrome;
- Enable testing for firefox stable and firefox ESR;
- Enable testing for chrome stable.

## Use `webstage.toml` to persist the browsers to use

If the pytest is called without `--browser`, this method will be used.
You can use `webstage init > webstage.toml` to get a sample configuration.

```toml
[tool.webstage]
cached_browsers = "auto" # use cached browsers instead of the system one, availble choices: auto, always, no

[[tool.webstage.browsers]] # add a browser to the test list, will be applied if --browser is not present
browser = "firefox"
version = "stable"

[[tool.webstage.browsers]]
browser = "chrome"
version = "stable"
```

## Navigation on the Web

The basic of a web driver is navigating the web. Here is a sample:

```python
from pytest_webstage.webstage import WebStage

def test_can_visit_url(webstage: WebStage): # 1.
    webstage.sync.go("https://google.com") # 2. 3.
    webstage.sync.until_ready() # 4.
```

1. use the `webstage` fixture to get a web stage
2. `webstage.sync` to get the sync API. `webstage` itself is async API
3. `.go("https://google.com")` asks the browser to visit <https://google.com>
4. `.until_ready()` wait until the document is loaded

The `WebStage` supports additional methods like:

- `refresh()` to refresh the document
- `href()` to get current URL

## Interacting with elements

You must get the element representation before working on it. The `WebStage` has two methods to query elements:

- `query_selector(css_selector)`
- `query_selector_one(css_selector)`

They works like `document.querySelectorAll` and `document.querySelectorAll`. If the element exists, `Element` or `SyncElement` will be returned. They both support these operations:

- `query_selector` and `query_selector_one`: query elements under this subtree
- `click`: emulate click on this element
- `value`: get the value of the element, like `HTMLElement.value` in the JavaScript
- `keyboard`: get the keyboard object to emulate keyboard input

## Organizing test code with steps

A step is a block of code with description:

```python
from pytest_webstage.webstage import WebStage

def test_can_visit_url(webstage: WebStage):
    with webstage.step("Visit Google") as step: // 1.
        step.sync.go("https://google.com")
        step.sync.until_ready()
```

1. The `step` function returns a new `WebStage`, you cannot nest steps.

## Async support

The `WebStage` itself is the async API. To use async code, you must enable async support for pytest.

The async API does not help on the performance. It's intended to reduce the blocking of the main thread for the app code to be run.
