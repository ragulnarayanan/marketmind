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

    # Extract the first complete JSON object — handles trailing text after }
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise ValueError(f"No JSON object found in LLM response: {text[:200]}")
