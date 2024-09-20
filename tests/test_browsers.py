from pytest_webstage.webstage import WebStage

def test_can_visit_url(webstage: WebStage):
    with webstage.step("Visit Google") as step:
        step.sync.go("https://google.com")
        step.sync.until_ready()

