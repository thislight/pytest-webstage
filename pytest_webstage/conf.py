from pathlib import Path
import tomllib
from typing import Literal
from pydantic import BaseModel, Field

class Browser(BaseModel):
    browser: str
    version: str = "stable"


class Config(BaseModel):
    cached_browsers: Literal["always"] | Literal["auto"] | Literal["no"] = "auto"
    browsers: list[Browser] = Field(default_factory=list)

def read_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.is_file():
        path = path / "webstage.toml"
    with open(path, 'rb') as f:
        root = tomllib.load(f)
    conf = root.get('tool', {}).get('webstage', {})
    return Config(**conf)
