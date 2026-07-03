from pathlib import Path

from app.services.indexer import MAX_FILE_BYTES, MAX_FILES, load_rashidignore, should_skip
from app.services.prompt_registry import PromptRegistry


class ContextComposer:
    def __init__(self, project_root: Path, mode: str = "agent") -> None:
        self.project_root = project_root.resolve()
        self.mode = mode
        self.registry = PromptRegistry()
        self.excludes = load_rashidignore(self.project_root)

    def build_system_prompt(self) -> str:
        parts = [
            self.registry.load_persona(),
            self.registry.load_mode(self.mode),
            self.registry.load_edits_schema(),
            self.registry.load_negative_constraints(),
        ]
        return "\n\n".join(p for p in parts if p)

    def list_project_files(self) -> tuple[list[str], bool]:
        files: list[str] = []
        truncated = False
        for path in sorted(self.project_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(self.project_root)
            if should_skip(rel.parts, self.excludes):
                continue
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            files.append(str(rel).replace("\\", "/"))
            if len(files) >= MAX_FILES:
                truncated = True
                break
        return files, truncated

    def build_user_message(self, prompt: str) -> str:
        files, truncated = self.list_project_files()
        file_list = "\n".join(files[:50])
        trunc_note = "\n[truncated: more files omitted]" if truncated else ""
        return f"Project files ({len(files)}):\n{file_list}{trunc_note}\n\nUser request:\n{prompt}"
