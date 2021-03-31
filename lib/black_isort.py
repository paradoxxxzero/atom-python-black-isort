"""
    black isort python interface
"""

import fileinput
import json
import os
import sys

import toml

try:
    import black
except ImportError:
    black = None

try:
    import isort
except ImportError:
    isort = None


def relativize(module, root, path):
    if not path or not path.startswith(root):
        return module
    path = os.path.relpath(path, root)
    path_parts = path.split(os.path.sep)
    mod_parts = module.split(".")
    common_parts = 0
    for (mod_part, path_part) in zip(mod_parts, path_parts):
        if mod_part == path_part:
            common_parts += 1
        else:
            break
    if not common_parts:
        return module
    path_parts = path_parts[common_parts:]
    mod_parts = mod_parts[common_parts:]
    module = "." * len(path_parts) + ".".join(mod_parts)
    return module


class Commands(object):
    def __init__(self):
        if isort is None or black is None:
            self.write(
                notification="error",
                message="black/isort not found",
                detail="You must install isort and black for %s"
                % sys.executable,
            )
            sys.exit(0)

        self.data = self.read()
        self.file_path = self.data.pop("filePath", None)
        self.only_when_a_project_config_is_found = self.data.pop(
            "onlyWhenAProjectConfigIsFound", None
        )
        self.cmd = self.data.pop("cmd", None)

    def run(self):
        fun = getattr(self, self.cmd, None)

        if not fun:
            self.write(
                notification="error",
                message=self.cmd,
                detail="Unknown command %s" % self.cmd,
            )
            return

        fun(**self.data)

    def read(self):
        return json.loads("".join(fileinput.input()))

    def write(self, **dct):
        sys.stdout.write(json.dumps(dct))
        sys.stdout.flush()

    def fix(self, source, black_then_isort, cwd=None):
        source = (
            self.isort(self.black(source))
            if black_then_isort
            else self.black(self.isort(source))
        )
        self.write(file=source)

    def isort(self, source):
        if self.only_when_a_project_config_is_found:
            has_conf = False
            root = black.find_project_root((self.file_path,))
            path = root / "pyproject.toml"
            if path.is_file():
                pyproject_toml = toml.load(str(path))
                config = pyproject_toml.get("tool", {}).get("isort", {})
                if config:
                    has_conf = True
            if not has_conf:
                path = root / ".isort.cfg"
                if path.is_file():
                    has_conf = True
            if not has_conf:
                path = root / "setup.cfg"
                if path.is_file():
                    import configparser

                    config = configparser.ConfigParser()
                    with open(path) as fp:
                        config.read_file(fp)
                    if config.has_section('isort') or config.has_section(
                        'tool:isort'
                    ):
                        has_conf = True
            if not has_conf:
                return source

        return isort.code(
            code=source,
            config=isort.settings.Config(settings_path=root),
        )

    def black(self, source):
        has_conf = False
        config = {}
        if self.file_path:
            root = black.find_project_root((self.file_path,))
            path = root / "pyproject.toml"
            if path.is_file():
                pyproject_toml = toml.load(str(path))
                config = pyproject_toml.get("tool", {}).get("black", {})
                if config:
                    has_conf = True
                config = {
                    k.replace("--", "").replace("-", "_"): v
                    for k, v in config.items()
                }

        if self.only_when_a_project_config_is_found and not has_conf:
            return source

        line_length = config.pop("line_length", black.DEFAULT_LINE_LENGTH)
        versions = (
            set(
                [
                    black.TargetVersion[v.upper()]
                    for v in config.get('target_version')
                ]
            )
            if config.get('target_version')
            else set()
        )
        pyi = config.get("pyi")
        skip_string_normalization = config.get("skip_string_normalization")

        mode = black.FileMode(
            target_versions=versions,
            line_length=line_length,
            is_pyi=pyi,
            string_normalization=not skip_string_normalization,
        )

        return black.format_str(source, mode=mode)


if __name__ == "__main__":
    Commands().run()
