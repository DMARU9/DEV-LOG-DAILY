"""ファイル I/O ユーティリティ — UTF-8/LF での読み書き・ディレクトリ確認・再帰的ファイル検索."""

from __future__ import annotations

from pathlib import Path


def read_text(file_path: str | Path) -> str:
    """UTF-8 でファイルを読み込み、内容を返す.

    Args:
        file_path: 読み込むファイルのパス

    Returns:
        ファイルの内容（文字列）

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        UnicodeDecodeError: UTF-8 としてデコードできない場合
    """
    path = Path(file_path)
    return path.read_text(encoding="utf-8")


def write_text(file_path: str | Path, content: str) -> None:
    """内容を UTF-8/LF でファイルに書き込む（同名ファイルは上書き）.

    Args:
        file_path: 書き込むファイルのパス
        content: 書き込む内容

    Raises:
        OSError: ディレクトリが存在しない・書き込み権限がない場合
    """
    path = Path(file_path)
    # LF 改行を強制し、UTF-8 で書き込み
    normalized = content.replace("\r\n", "\n")
    path.write_text(normalized, encoding="utf-8")


def ensure_directory(dir_path: str | Path) -> Path:
    """ディレクトリが存在することを確認する。存在しない場合は作成する.

    Args:
        dir_path: 確認・作成するディレクトリのパス

    Returns:
        確認・作成されたディレクトリの Path オブジェクト
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def directory_exists(dir_path: str | Path) -> bool:
    """ディレクトリが存在するか確認する.

    Args:
        dir_path: 確認するディレクトリのパス

    Returns:
        存在する場合は True
    """
    return Path(dir_path).is_dir()


def file_exists(file_path: str | Path) -> bool:
    """ファイルが存在するか確認する.

    Args:
        file_path: 確認するファイルのパス

    Returns:
        存在する場合は True
    """
    return Path(file_path).is_file()


def find_files(
    root_dir: str | Path,
    pattern: str = "**/*",
    recursive: bool = True,
) -> list[Path]:
    """ディレクトリ配下のファイルを再帰的に検索する.

    Args:
        root_dir: 検索起点ディレクトリ
        pattern: 検索パターン（glob 形式、デフォルトは全ファイル）
        recursive: 再帰的に検索するかどうか

    Returns:
        一致したファイルの Path リスト（昇順ソート済み）
    """
    root = Path(root_dir)
    if not root.is_dir():
        return []

    if recursive:
        files = sorted(root.glob(pattern))
    else:
        files = sorted(root.glob(pattern))

    # ファイルのみをフィルタリング
    return [f for f in files if f.is_file()]
