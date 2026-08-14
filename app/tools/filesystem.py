from pathlib import Path


class FilesystemTool:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_report(self, task_id: str, content: str, suffix: str = "md") -> Path:
        path = self.base_dir / f"{task_id}.{suffix}"
        path.write_text(content, encoding="utf-8")
        return path

    def read_report(self, task_id: str, suffix: str = "md") -> str | None:
        path = self.base_dir / f"{task_id}.{suffix}"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def list_reports(self) -> list[str]:
        return sorted(p.stem for p in self.base_dir.glob("*"))
