import hashlib

from src.approaches._common import GUIDE_SHA256, ROOT


def test_base_prompt_was_checked_against_current_labelling_guide():
    guide = (ROOT / "data" / "scenarios" / "LABELLING_GUIDE.md").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(guide).hexdigest() == GUIDE_SHA256, (
        "LABELLING_GUIDE.md has changed. Re-check the verdict rules in BASE_PROMPT "
        "(src/approaches/_common.py) against it, then update GUIDE_SHA256 there.")
