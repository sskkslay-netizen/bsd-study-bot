import html
import json
import re
from urllib.request import Request, urlopen


def parse_question_text(text):
    """Parse Quizlet-style tab-separated or question|answer text."""
    questions = []

    for line in text.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        if "\t" in line:
            prompt, answer = line.split("\t", 1)
        elif "|" in line:
            prompt, answer = line.split("|", 1)
        else:
            continue

        prompt = prompt.strip()
        answer = answer.strip()

        if prompt and answer:
            questions.append((prompt, answer))

    return questions


def _find_question_pairs(value):
    pairs = []

    if isinstance(value, dict):
        prompt = value.get("word") or value.get("term") or value.get("question")
        answer = value.get("definition") or value.get("answer")

        if isinstance(prompt, str) and isinstance(answer, str):
            pairs.append((prompt, answer))

        for child in value.values():
            pairs.extend(_find_question_pairs(child))
    elif isinstance(value, list):
        for child in value:
            pairs.extend(_find_question_pairs(child))

    return pairs


def _parse_quizlet_page(page):
    pairs = []

    for script in re.findall(
        r"<script[^>]*>(.*?)</script>", page, flags=re.IGNORECASE | re.DOTALL
    ):
        candidate = html.unescape(script).strip()

        if not candidate or not candidate.startswith(("{", "[")):
            continue

        try:
            pairs.extend(_find_question_pairs(json.loads(candidate)))
        except json.JSONDecodeError:
            continue

    if not pairs:
        pattern = (
            r'"(?:word|term)"\s*:\s*"((?:\\.|[^"\\])*)".*?'
            r'"(?:definition|answer)"\s*:\s*"((?:\\.|[^"\\])*)"'
        )

        for prompt, answer in re.findall(pattern, page, flags=re.DOTALL):
            try:
                pairs.append((json.loads(f'"{prompt}"'), json.loads(f'"{answer}"')))
            except json.JSONDecodeError:
                continue

    unique_pairs = []
    seen = set()

    for prompt, answer in pairs:
        key = (prompt.strip(), answer.strip())

        if key[0] and key[1] and key not in seen:
            seen.add(key)
            unique_pairs.append(key)

    return unique_pairs


def import_source(source):
    """Import either a public Quizlet URL or pasted export text."""
    source = source.strip()

    if source.startswith(("http://", "https://")):
        request = Request(source, headers={"User-Agent": "Mozilla/5.0"})

        with urlopen(request, timeout=15) as response:
            page = response.read().decode("utf-8", errors="replace")

        questions = _parse_quizlet_page(page)
    else:
        questions = parse_question_text(source)

    if not questions:
        raise ValueError(
            "No questions found. Use a public Quizlet URL or paste exported "
            "term<TAB>definition lines."
        )

    return questions