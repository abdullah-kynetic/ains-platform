"""Egnyte CLI. Prints results only, never credentials or tokens.

uv run python -m app.egnyte_client whoami
uv run python -m app.egnyte_client ls /Shared/AINS-Dev
uv run python -m app.egnyte_client download <remote> <local-dest>
uv run python -m app.egnyte_client upload <local> <remote>
uv run python -m app.egnyte_client mkdir <remote>
uv run python -m app.egnyte_client get-token <file>   # writes tokens to <file> only
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from app.config import Settings, get_settings

from .client import EgnyteClient
from .errors import EgnyteError
from .paths import PathNotAllowedError


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.egnyte_client",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami", help="Show the Egnyte user the credentials act as")
    ls = sub.add_parser("ls", help="List a folder")
    ls.add_argument("path")
    dl = sub.add_parser("download", help="Download a file")
    dl.add_argument("path")
    dl.add_argument("dest")
    up = sub.add_parser("upload", help="Upload a local file")
    up.add_argument("local")
    up.add_argument("remote")
    mk = sub.add_parser("mkdir", help="Create a folder (no error if it exists)")
    mk.add_argument("path")
    gt = sub.add_parser(
        "get-token",
        help="Run the password flow once and write the tokens to FILE (never to stdout)",
    )
    gt.add_argument("file")
    gt.add_argument("--force", action="store_true", help="Overwrite FILE if it exists")
    return p


def _write_token_file(path: Path, access: str, refresh: str | None, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; pass --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"EGNYTE_ACCESS_TOKEN={access}"]
    if refresh:
        lines.append(f"EGNYTE_REFRESH_TOKEN={refresh}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


async def _run(args: argparse.Namespace, client: EgnyteClient, out: TextIO) -> None:
    if args.cmd == "whoami":
        info = await client.whoami()
        name = " ".join(x for x in (info.get("first_name"), info.get("last_name")) if x)
        print(f"username: {info.get('username')}", file=out)
        if name:
            print(f"name: {name}", file=out)
        print(f"id: {info.get('id')}", file=out)
        print(f"domain: {client.domain}", file=out)
    elif args.cmd == "ls":
        listing = await client.list_folder(args.path)
        print(listing.path, file=out)
        for d in listing.folders:
            print(f"  [dir]  {d.name}/", file=out)
        for f in listing.files:
            size = f"{f.size:,}" if f.size is not None else "?"
            print(f"  [file] {f.name}  ({size} bytes)", file=out)
        if not listing.folders and not listing.files:
            print("  (empty)", file=out)
    elif args.cmd == "download":
        data = await client.download_file(args.path)
        dest = Path(args.dest)
        if dest.is_dir():
            dest = dest / args.path.rstrip("/").rsplit("/", 1)[-1]
        dest.write_bytes(data)
        print(f"Saved {len(data):,} bytes to {dest}", file=out)
    elif args.cmd == "upload":
        result = await client.upload_file(args.remote, Path(args.local))
        print(f"Uploaded {args.local} -> {result.get('path', args.remote)}", file=out)
    elif args.cmd == "mkdir":
        result = await client.create_folder(args.path)
        note = " (already existed)" if result.get("already_existed") else ""
        print(f"Folder ready: {result.get('path', args.path)}{note}", file=out)
    elif args.cmd == "get-token":
        dest = Path(args.file)
        if dest.exists() and not args.force:
            raise FileExistsError(f"{dest} already exists; pass --force to overwrite")
        tok = await client.password_grant()
        _write_token_file(dest, tok.access_token, tok.refresh_token, args.force)
        print(
            f"Wrote EGNYTE_ACCESS_TOKEN"
            f"{' and EGNYTE_REFRESH_TOKEN' if tok.refresh_token else ''} to {dest} "
            "(permissions 600). Access tokens last 30 days. Copy the lines into your .env "
            "yourself, then delete the file. The token was not printed.",
            file=out,
        )


def main(
    argv: list[str] | None = None,
    *,
    settings: Settings | None = None,
    client_factory: Callable[[Settings], EgnyteClient] | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    args = _build_parser().parse_args(argv)
    settings = settings or get_settings()

    async def go() -> None:
        client = (client_factory or EgnyteClient.from_settings)(settings)
        try:
            await _run(args, client, out)
        finally:
            await client.aclose()

    try:
        asyncio.run(go())
    except (EgnyteError, PathNotAllowedError, FileExistsError, ValueError, OSError) as e:
        print(f"error: {e}", file=err)
        return 1
    return 0
