import json
import re


def parse_llm_json(text: str) -> dict:
    """
    Parse JSON from an LLM response that may be wrapped in markdown code fences
    or have trailing text after the closing brace.
    Handles: ```json...```, ```...```, raw JSON, and JSON with extra trailing content.
    """
    text = text.strip()
    # Strip opening fence (```json or ```)
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    # Strip closing fence
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    # Try direct parse first (fast path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # raw_decode parses the first complete JSON value and ignores trailing text,
    # correctly handling nested braces that would trip up a naive regex.
    try:
        # Seek to the first { in case there's leading text before the JSON
        start = text.index("{")
        obj, _ = json.JSONDecoder().raw_decode(text, start)
        return obj
    except (ValueError, KeyError):
        pass

    raise ValueError(f"No JSON object found in LLM response: {text[:200]}")
