from difflib import SequenceMatcher
from pathlib import PurePosixPath
from unicodedata import combining, normalize

DEFAULT_FILE_NAME_SIMILARITY_CUTOFF = 0.8
DEFAULT_MAX_FILE_NAME_SUGGESTIONS = 5


def suggest_similar_file_paths(
    requested_filename: str,
    candidate_paths: tuple[str, ...],
    *,
    cutoff: float = DEFAULT_FILE_NAME_SIMILARITY_CUTOFF,
    max_results: int = DEFAULT_MAX_FILE_NAME_SUGGESTIONS,
) -> tuple[str, ...]:
    if not 0 <= cutoff <= 1:
        raise ValueError("cutoff must be between zero and one")
    if max_results <= 0:
        raise ValueError("max_results must be positive")
    if not requested_filename or any(separator in requested_filename for separator in ("/", "\\")):
        return ()

    normalized_request = _normalize_filename(requested_filename)
    requested_extension = PurePosixPath(normalized_request).suffix
    if not normalized_request or not requested_extension:
        return ()

    ranked: list[tuple[float, str]] = []
    for path in candidate_paths:
        candidate_name = PurePosixPath(path).name
        normalized_candidate = _normalize_filename(candidate_name)
        if PurePosixPath(normalized_candidate).suffix != requested_extension:
            continue
        requested_stems = _stem_variants(PurePosixPath(normalized_request).stem)
        candidate_stems = _stem_variants(PurePosixPath(normalized_candidate).stem)
        score = max(
            SequenceMatcher(None, requested_stem, candidate_stem).ratio()
            for requested_stem in requested_stems
            for candidate_stem in candidate_stems
        )
        if score >= cutoff:
            ranked.append((score, path))

    ranked.sort(key=lambda item: (-item[0], item[1].casefold()))
    return tuple(path for _, path in ranked[:max_results])


def _normalize_filename(value: str) -> str:
    decomposed = normalize("NFKD", value.strip().casefold())
    return "".join(character for character in decomposed if not combining(character))


def _stem_variants(stem: str) -> tuple[str, ...]:
    variants = {stem}
    if len(stem) > 3 and stem.endswith("ies"):
        variants.add(f"{stem[:-3]}y")
    elif len(stem) > 1 and stem.endswith("s"):
        variants.add(stem[:-1])
    return tuple(variants)
