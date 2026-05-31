from pathlib import Path
import unittest


ROOT_DIR = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT_DIR / "configs" / "profiles"

REQUIRED_TOP_LEVEL_KEYS = {
    "name",
    "description",
    "tls_version",
    "library",
    "key_exchange_group",
    "signature_algorithm",
    "certificate",
    "expected",
    "test",
}

REQUIRED_NESTED_KEYS = {
    "expected": {"group", "pqc", "hybrid"},
    "test": {"repeats", "timeout_seconds"},
}


def parse_minimal_yaml(path: Path) -> dict:
    """
    Minimal parser for the simple profile YAML files used in this project.

    It intentionally avoids PyYAML because the repository should remain
    runnable in a minimal Ubuntu/GitHub Actions environment without extra
    Python dependencies.
    """
    result: dict = {}
    current_section: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()

        if not line.strip() or line.strip().startswith("#"):
            continue

        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if value == "":
                result[key] = {}
                current_section = key
            else:
                result[key] = value
                current_section = None

            continue

        if line.startswith(" ") and current_section and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            result.setdefault(current_section, {})[key] = value

    return result


class ProfileConfigTests(unittest.TestCase):
    def test_expected_profile_files_exist(self) -> None:
        expected_files = {
            "classical.yml",
            "hybrid.yml",
            "pqc.yml",
        }

        actual_files = {path.name for path in PROFILES_DIR.glob("*.yml")}

        self.assertTrue(
            expected_files.issubset(actual_files),
            f"Missing profile files: {sorted(expected_files - actual_files)}",
        )

    def test_profiles_have_required_top_level_keys(self) -> None:
        for profile_file in sorted(PROFILES_DIR.glob("*.yml")):
            with self.subTest(profile=profile_file.name):
                profile = parse_minimal_yaml(profile_file)
                missing = REQUIRED_TOP_LEVEL_KEYS - set(profile)

                self.assertFalse(
                    missing,
                    f"{profile_file} is missing top-level keys: {sorted(missing)}",
                )

    def test_profiles_have_required_nested_keys(self) -> None:
        for profile_file in sorted(PROFILES_DIR.glob("*.yml")):
            with self.subTest(profile=profile_file.name):
                profile = parse_minimal_yaml(profile_file)

                for section, required_keys in REQUIRED_NESTED_KEYS.items():
                    self.assertIn(section, profile)
                    self.assertIsInstance(profile[section], dict)

                    missing = required_keys - set(profile[section])

                    self.assertFalse(
                        missing,
                        f"{profile_file} section {section!r} is missing keys: {sorted(missing)}",
                    )

    def test_profile_name_matches_filename(self) -> None:
        for profile_file in sorted(PROFILES_DIR.glob("*.yml")):
            with self.subTest(profile=profile_file.name):
                profile = parse_minimal_yaml(profile_file)
                expected_name = profile_file.stem

                self.assertEqual(
                    profile["name"],
                    expected_name,
                    f"{profile_file} name must match file stem",
                )

    def test_repeats_and_timeout_are_positive_integers(self) -> None:
        for profile_file in sorted(PROFILES_DIR.glob("*.yml")):
            with self.subTest(profile=profile_file.name):
                profile = parse_minimal_yaml(profile_file)

                repeats = int(profile["test"]["repeats"])
                timeout_seconds = int(profile["test"]["timeout_seconds"])

                self.assertGreater(repeats, 0)
                self.assertGreater(timeout_seconds, 0)

    def test_expected_group_matches_configured_group(self) -> None:
        for profile_file in sorted(PROFILES_DIR.glob("*.yml")):
            with self.subTest(profile=profile_file.name):
                profile = parse_minimal_yaml(profile_file)

                self.assertEqual(
                    profile["expected"]["group"],
                    profile["key_exchange_group"],
                    "For this prototype each profile restricts TLS to a single expected group",
                )

    def test_known_profile_groups(self) -> None:
        expected_groups = {
            "classical": "X25519",
            "hybrid": "X25519MLKEM768",
            "pqc": "MLKEM768",
        }

        for profile_name, expected_group in expected_groups.items():
            with self.subTest(profile=profile_name):
                profile_file = PROFILES_DIR / f"{profile_name}.yml"
                profile = parse_minimal_yaml(profile_file)

                self.assertEqual(profile["key_exchange_group"], expected_group)


if __name__ == "__main__":
    unittest.main()