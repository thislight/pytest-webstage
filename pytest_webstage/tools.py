from click import group, progressbar, echo, option
from .conf import read_config
from selenium.webdriver.common.selenium_manager import SeleniumManager
import json

@group
def webstage():
    pass


@webstage.command
@option("--offline/--no-offline", help="Avoid netwrok requests (default: False).", default=False)
def check_cache(offline: bool) -> None:
    """Check if the browsers and the drivers used are downloaded."""
    conf = read_config(".")
    mgr = SeleniumManager()
    results: list[dict] = []
    with progressbar(conf.browsers, item_show_func=lambda x: f"{x.browser}({x.version})" if x else None) as pb:
        for b in pb:
            args = ["--browser", b.browser, "--browser-version", b.version]
            if offline:
                args.append("--offline")
            if conf.cached_browsers == "always":
                args.append("--force-browser-download")
            elif conf.cached_browsers == "no":
                args.append("--avoid-browser-download")
            results.append(mgr.binary_paths(args))
    echo(json.dumps(results, indent=2))

@webstage.command
def init() -> None:
    """Output the sample configuration."""
    echo('\n'.join([
        "[tool.webstage]",
        "cached_browsers = \"auto\" # use cached browsers instead of the system one, availble choices: auto, always, no",
        "",
        "[[tool.webstage.browsers]] # add a browser to the test list, will be applied if --browser is not present",
        "browser = \"firefox\"",
        "version = \"stable\"",
        "",
        "[[tool.webstage.browsers]]",
        "browser = \"chrome\"",
        "version = \"stable\"",
        "",
    ]))

if __name__ == "__main__":
    webstage()
