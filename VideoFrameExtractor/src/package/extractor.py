"""Batch extraction orchestration."""
from __future__ import annotations

import logging
from pathlib import Path

from .ser_reader import SerReader
from .avi_reader import AviReader
from .tiff_writer import write_tiff_atomic

logger = logging.getLogger(__name__)


def run_extraction(
    instructions: list[dict],
    project_root: Path,
    temp_dir: Path,
    overwrite: bool = False,
    ser_endian_mode: str = "legacy",
) -> dict:
    """Execute all extraction jobs, continuing after individual failures."""
    succeeded = failed = 0
    reader_cache = {}

    for number, task in enumerate(instructions, start=1):
        source = Path(task["source"])
        if not source.is_absolute():
            source = project_root / source
        output_dir = Path(task["output_dir"])
        if not output_dir.is_absolute():
            output_dir = project_root / output_dir
        destination = output_dir / task["filename"]
        kind = task.get("format", source.suffix.lstrip(".")).lower()

        logger.info("[%d/%d] 抽出開始: %s frame=%d -> %s",
                    number, len(instructions), source, task["frame"], destination)
        try:
            if not source.is_file():
                raise FileNotFoundError(f"入力動画がありません: {source}")
            if destination.exists() and not overwrite:
                raise FileExistsError(f"出力先が既に存在します（上書き無効）: {destination}")
            if kind not in ("ser", "avi"):
                raise ValueError(f"未対応形式: {kind}")

            task_endian_mode = task.get("ser_endian_mode", ser_endian_mode)
            cache_key = (str(source.resolve()), kind, task_endian_mode if kind == "ser" else None)
            if cache_key not in reader_cache:
                reader_cache[cache_key] = (
                    SerReader(source, endian_mode=task_endian_mode)
                    if kind == "ser" else AviReader(source)
                )
            image = reader_cache[cache_key].read_frame(task["frame"])
            write_tiff_atomic(image, destination, temp_dir)
            logger.info(
                "保存完了: %s shape=%s dtype=%s min=%s max=%s",
                destination, image.shape, image.dtype,
                int(image.min()) if image.size else "n/a",
                int(image.max()) if image.size else "n/a",
            )
            succeeded += 1
        except Exception:
            logger.exception("抽出失敗: task=%d source=%s frame=%s",
                             number, source, task.get("frame"))
            failed += 1

    for reader in reader_cache.values():
        try:
            reader.close()
        except Exception:
            logger.exception("動画リーダーの終了処理に失敗しました。")

    return {"succeeded": succeeded, "failed": failed}
