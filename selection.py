"""Parse chart selections: numbers, ranges, or all."""
import re


def parse_selection(value: str, count: int) -> list[int]:
    value = value.strip().lower()
    if value == "all":
        return list(range(1, count + 1))
    selected = []
    for token in value.split(","):
        match = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", token)
        if not match:
            raise ValueError("Enter numbers such as 1,3,5 or 2-6, or all")
        start = int(match[1])
        end = int(match[2] or match[1])
        if not 1 <= start <= end <= count:
            raise ValueError(f"Choose numbers between 1 and {count}, with ascending ranges")
        for number in range(start, end + 1):
            if number not in selected:
                selected.append(number)
    return selected
