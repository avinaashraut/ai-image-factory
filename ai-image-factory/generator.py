"""Generate AI image prompts from configurable prompt parts."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "num_prompts": 1000,
    "progress_interval": 50,
    "output_csv": "prompts/prompts.csv",
    "subjects": [
        "astronaut",
        "samurai",
        "street musician",
        "wild fox",
        "ancient robot",
    ],
    "environments": [
        "in a neon-lit cyberpunk city",
        "on a misty mountain",
        "inside a futuristic laboratory",
        "in a dense rainforest",
        "on an alien planet",
    ],
    "actions": [
        "running",
        "meditating",
        "painting",
        "exploring",
        "performing a dance",
    ],
    "lighting": [
        "golden hour sunlight",
        "cinematic dramatic lighting",
        "soft diffused light",
        "moody low-key lighting",
        "colorful neon glow",
    ],
    "camera": [
        "wide-angle lens",
        "macro lens",
        "35mm film style",
        "aerial drone perspective",
        "portrait telephoto shot",
    ],
}


def load_config(config_path: Path) -> dict[str, Any]:
    """Load config from disk and merge with defaults."""
    config = DEFAULT_CONFIG.copy()

    if not config_path.exists():
        print(f"Config file not found at {config_path}. Using default settings.")
        return config

    raw_text = config_path.read_text(encoding="utf-8").strip()
    if not raw_text:
        print(f"Config file at {config_path} is empty. Using default settings.")
        return config

    data = json.loads(raw_text)
    if not isinstance(data, dict):
        raise ValueError("config.json must contain a JSON object.")

    config.update(data)

    list_keys = ("subjects", "environments", "actions", "lighting", "camera")
    for key in list_keys:
        value = config.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(f"'{key}' must be a non-empty list in config.json.")
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError(f"All entries in '{key}' must be non-empty strings.")
        config[key] = [item.strip() for item in value]

    num_prompts = config.get("num_prompts")
    if not isinstance(num_prompts, int) or num_prompts <= 0:
        raise ValueError("'num_prompts' must be a positive integer.")

    progress_interval = config.get("progress_interval")
    if not isinstance(progress_interval, int) or progress_interval <= 0:
        raise ValueError("'progress_interval' must be a positive integer.")

    output_csv = config.get("output_csv")
    if not isinstance(output_csv, str) or not output_csv.strip():
        raise ValueError("'output_csv' must be a non-empty string.")
    config["output_csv"] = output_csv.strip()

    return config


def build_prompt(config: dict[str, Any]) -> str:
    """Create one prompt from random configurable components."""
    subject = random.choice(config["subjects"])
    environment = random.choice(config["environments"])
    action = random.choice(config["actions"])
    lighting = random.choice(config["lighting"])
    camera = random.choice(config["camera"])

    return (
        f"{subject} {action} {environment}, "
        f"{lighting}, {camera}, highly detailed, 8k"
    )


def generate_prompts(config: dict[str, Any]) -> list[str]:
    """Generate prompts and print progress to stdout."""
    num_prompts = config["num_prompts"]
    progress_interval = config["progress_interval"]

    prompts: list[str] = []
    for index in range(1, num_prompts + 1):
        prompts.append(build_prompt(config))
        if index % progress_interval == 0 or index == num_prompts:
            print(f"Generated {index}/{num_prompts} prompts")

    return prompts


def save_prompts(prompts: list[str], output_path: Path) -> None:
    """Write prompts to CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["prompt"])
        for prompt in prompts:
            writer.writerow([prompt])


def main() -> None:
    config = load_config(CONFIG_PATH)

    output_path = Path(config["output_csv"])
    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path

    prompts = generate_prompts(config)
    save_prompts(prompts, output_path)
    print(f"Saved {len(prompts)} prompts to {output_path}")


if __name__ == "__main__":
    main()
