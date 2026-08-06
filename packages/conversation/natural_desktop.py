import re
from pathlib import PureWindowsPath

from packages.conversation.capability_router import (
    OpenWorkspaceFileProposal,
    OpenWorkspaceLocationProposal,
)

_EXPLICIT_OPEN_LOCATION = re.compile(
    r"^\s*abra\s+(?:a\s+|o\s+)?(?:pasta|diret[oó]rio)\s+"
    r"(?P<path>.+?)\s+(?:no|com\s+o)\s+(?:explorador|explorer)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_EXPLICIT_OPEN_EXPLORER = re.compile(
    r"^\s*(?:abra|abre)\s+(?:o\s+)?(?:programa\s+)?"
    r"(?:explorador(?:\s+de\s+arquivos)?|explorer)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_EXPLICIT_OPEN_EXPLORER_AT = re.compile(
    r"^\s*abra\s+(?:o\s+)?(?:explorador|explorer)\s+"
    r"(?:em|na\s+pasta|no\s+diret[oó]rio)\s+(?P<path>.+?)\s*[.!?]?\s*$",
    re.IGNORECASE,
)
_EXPLICIT_OPEN_FILE = re.compile(
    r"^\s*(?:abra|abre)\s+(?:(?:o|a)\s+)?(?:arquivo\s+)?(?P<path>.+?)\s*[.!?]?\s*$",
    re.IGNORECASE,
)


def detect_explicit_open_location(
    user_input: str,
) -> OpenWorkspaceLocationProposal | None:
    message = user_input.strip()
    if not _is_single_line(message):
        return None
    explorer_at_match = _EXPLICIT_OPEN_EXPLORER_AT.fullmatch(message)
    if explorer_at_match is not None:
        path = _validated_path(explorer_at_match.group("path"))
        return OpenWorkspaceLocationProposal(path) if path is not None else None
    if _EXPLICIT_OPEN_EXPLORER.fullmatch(message) is not None:
        return OpenWorkspaceLocationProposal(".")
    match = _EXPLICIT_OPEN_LOCATION.fullmatch(message)
    if match is None:
        return None
    path = _validated_path(match.group("path"))
    return OpenWorkspaceLocationProposal(path) if path is not None else None


def detect_explicit_open_file(user_input: str) -> OpenWorkspaceFileProposal | None:
    message = user_input.strip()
    if not _is_single_line(message) or detect_explicit_open_location(message) is not None:
        return None
    match = _EXPLICIT_OPEN_FILE.fullmatch(message)
    if match is None:
        return None
    path = _validated_path(match.group("path"))
    if path is None or path.casefold().startswith(("pasta ", "diretório ", "diretorio ")):
        return None
    if " " in path and "/" not in path and "\\" not in path and not PureWindowsPath(path).drive:
        return None
    return OpenWorkspaceFileProposal(path)


def _validated_path(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not _is_single_line(normalized) or "\0" in normalized:
        return None
    return normalized


def _is_single_line(value: str) -> bool:
    return bool(value and "\n" not in value and "\r" not in value)
