import json
import re


def parse_llm_json(text: str) -> dict:
    """
    Parse JSON from an LLM response that may be wrapped in markdown code fences.
    Handles: ```json...```, ```...```, or raw JSON.
    """
    text = text.strip()
    # Strip opening fence (```json or ```)
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    # Strip closing fence
    text = re.sub(r"\n?```\s*$", "", text)
    return json.loads(text.strip())
