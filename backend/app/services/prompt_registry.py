from pathlib import Path

import yaml


class PromptRegistry:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent / "prompts"

    def load_manifest(self) -> dict:
        path = self.base_dir / "manifest.yaml"
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _read(self, relative: str) -> str:
        path = self.base_dir / relative
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()

    def load_persona(self) -> str:
        text = self._read("persona_fa.txt")
        if text:
            return text
        legacy = self.base_dir / "persona.yaml"
        if legacy.exists():
            with legacy.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, str):
                return data
        return ""

    def load_mode(self, mode: str) -> str:
        return self._read(f"modes/{mode}.txt") or self._read("modes/agent.txt")

    def load_edits_schema(self) -> str:
        return self._read("edits_schema_compact.txt")

    def load_negative_constraints(self) -> str:
        return self._read("negative_constraints.txt")
