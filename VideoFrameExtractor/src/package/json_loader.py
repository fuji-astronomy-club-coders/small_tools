"""JSON instruction parsing and validation."""
from __future__ import annotations

import json
from pathlib import Path


REQUIRED_FIELDS = {"source", "frame", "output_dir", "filename"}


def load_instructions(path: Path) -> list[dict]:
    """Load extraction jobs from a JSON file.

    Parameters
    ----------
    path : pathlib.Path
        Instruction JSON path.

    Returns
    -------
    list[dict]
        Validated extraction jobs.
    """
    with path.open("r", encoding="utf-8-sig") as stream:
        data = json.load(stream)
    if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
        raise ValueError('JSONのルートに "tasks" 配列が必要です。')
    if not data["tasks"]:
        raise ValueError('"tasks" が空です。')

    jobs = []
    for index, task in enumerate(data["tasks"], start=1):
        if not isinstance(task, dict):
            raise ValueError(f"tasks[{index - 1}] はオブジェクトである必要があります。")
        missing = REQUIRED_FIELDS - task.keys()
        if missing:
            raise ValueError(f"tasks[{index - 1}] に必須項目がありません: {sorted(missing)}")
        if not isinstance(task["frame"], int) or isinstance(task["frame"], bool) or task["frame"] < 0:
            raise ValueError(f"tasks[{index - 1}].frame は0以上の整数にしてください。")
        for field in ("source", "output_dir", "filename"):
            if not isinstance(task[field], str) or not task[field].strip():
                raise ValueError(f"tasks[{index - 1}].{field} は空でない文字列にしてください。")
        filename = Path(task["filename"])
        if filename.name != task["filename"] or filename.suffix.lower() not in (".tif", ".tiff"):
            raise ValueError(f"tasks[{index - 1}].filename はファイル名のみ、拡張子は.tif/.tiffにしてください。")
        jobs.append(task)
    return jobs
