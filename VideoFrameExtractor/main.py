"""Command-line entry point for VideoFrameExtractor."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.package.config import load_config
from src.package.json_loader import load_instructions
from src.package.extractor import run_extraction
from utils import setup_logging, ensure_project_dirs


def select_instruction_file() -> Path | None:
    """Show a file dialog and return the selected instruction JSON."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise RuntimeError(
            "JSON選択ダイアログを利用できません。--input でJSONファイルを指定してください。"
        ) from exc

    dialog_root = tk.Tk()
    dialog_root.withdraw()
    try:
        dialog_root.update()
        selected = filedialog.askopenfilename(
            title="抽出指示JSONを選択",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
    finally:
        dialog_root.destroy()
    return Path(selected) if selected else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract selected SER/AVI frames as losslessly written TIFF images."
    )
    parser.add_argument(
        "-i", "--input", default=None,
        help="Path to the JSON instruction file. If omitted, a file dialog is shown."
    )
    parser.add_argument("--config", default="config.json", help="Runtime config JSON.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    config = load_config(project_root / args.config)
    ensure_project_dirs(project_root, config)
    setup_logging(project_root / config["log_dir"], config.get("log_level", "INFO"))
    logger = logging.getLogger(__name__)

    if args.input:
        instruction_path = Path(args.input)
    else:
        try:
            instruction_path = select_instruction_file()
        except Exception:
            logger.exception("JSON選択ダイアログを開けません。")
            return 2
        if instruction_path is None:
            logger.info("JSON選択がキャンセルされました。処理を終了します。")
            return 0

    if not instruction_path.is_absolute():
        instruction_path = Path.cwd() / instruction_path
    instruction_path = instruction_path.resolve()

    try:
        instructions = load_instructions(instruction_path)
    except Exception:
        logger.exception("指示ファイルを読み込めません: %s", instruction_path)
        return 2

    summary = run_extraction(
        instructions=instructions,
        project_root=project_root,
        temp_dir=project_root / config["temp_dir"],
        overwrite=bool(config.get("overwrite", False)),
        ser_endian_mode=config.get("ser_endian_mode", "legacy"),
    )
    logger.info("処理終了: 成功=%d / 失敗=%d", summary["succeeded"], summary["failed"])
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
