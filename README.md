# pytest-webstage

Test web apps with pytest.

- Automatic parametrized testing for different browsers
- Managing driver and browsers for testing
- Sync and async API

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

Execute the test:

```sh
pytest
```

If you'd like to check the web drivers and the browsers used:

```sh
webstage check-cache
```

You can see some examples at `tests/`.

## License

SPDX: Apache-2.0
