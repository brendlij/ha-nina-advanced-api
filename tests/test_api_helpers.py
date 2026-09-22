"""Coverage for the small pure helpers behind two silent dashboard bugs."""
import importlib.util
from pathlib import Path
import sys
import unittest

PACKAGE = Path(__file__).parents[1] / "custom_components/nina_api"


def _load(name: str):
    """Import one module of the integration without Home Assistant."""
    if "nina_api" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "nina_api", PACKAGE / "__init__.py", submodule_search_locations=[str(PACKAGE)]
        )
        package = importlib.util.module_from_spec(spec)
        # Not executed: __init__ pulls in Home Assistant. The package only
        # has to exist so the relative imports inside the modules resolve.
        sys.modules["nina_api"] = package
    spec = importlib.util.spec_from_file_location(
        f"nina_api.{name}", PACKAGE / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


media_type = _load("api")._media_type
camera_state_of = _load("const").camera_state_of


class MediaTypeTests(unittest.TestCase):
    """EmbedIO labels images 'image/jpeg; charset=utf-8'.

    Passing that through looked harmless - the bytes were fine and the
    image/ prefix still matched - but Home Assistant hands the value to
    aiohttp when serving the frame, and aiohttp raises on a content type
    with parameters. The card stayed grey and nothing in this integration
    ever saw an error.
    """

    def test_charset_is_stripped(self):
        self.assertEqual(media_type("image/jpeg; charset=utf-8", "x"), "image/jpeg")

    def test_plain_type_survives(self):
        self.assertEqual(media_type("image/png", "x"), "image/png")

    def test_surrounding_space_is_trimmed(self):
        self.assertEqual(media_type("  image/jpeg ;q=1", "x"), "image/jpeg")

    def test_missing_or_empty_falls_back(self):
        for header in (None, "", "; charset=utf-8"):
            with self.subTest(header=header):
                self.assertEqual(media_type(header, "image/jpeg"), "image/jpeg")


class CameraStateTests(unittest.TestCase):
    """The plugin serializes CameraState as the enum name, not its number."""

    def test_enum_name_becomes_a_token(self):
        self.assertEqual(camera_state_of("Exposing"), "exposing")

    def test_multi_word_names_split(self):
        self.assertEqual(camera_state_of("NoState"), "no_state")
        self.assertEqual(camera_state_of("LoadingFile"), "loading_file")

    def test_number_from_older_builds_still_maps(self):
        # And lands on the same token as the name, so nothing downstream
        # has to know which build answered.
        self.assertEqual(camera_state_of(2), camera_state_of("Exposing"))
        self.assertEqual(camera_state_of(-1), "no_state")

    def test_nothing_usable_reads_as_unknown(self):
        for value in (None, "", True, False, 42):
            with self.subTest(value=value):
                self.assertIsNone(camera_state_of(value))


if __name__ == "__main__":
    unittest.main()
