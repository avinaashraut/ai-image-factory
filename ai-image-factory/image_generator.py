"""Generate images from prompts/prompts.csv and save to output/."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PROMPTS_CSV_PATH = BASE_DIR / "prompts" / "prompts.csv"
OUTPUT_DIR_PATH = BASE_DIR / "output"
IMAGES_API_URL = "https://api.openai.com/v1/images/generations"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate images from prompts/prompts.csv."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of prompts to process.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
        help="Image model name (default: gpt-image-1).",
    )
    parser.add_argument(
        "--size",
        default=os.getenv("OPENAI_IMAGE_SIZE", "1024x1024"),
        help="Image size (default: 1024x1024).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Retries per prompt on API/network failure (default: 3).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="HTTP timeout in seconds per request (default: 120).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Optional delay in seconds between requests (default: 0).",
    )
    return parser.parse_args()


def read_prompts(csv_path: Path, limit: int | None = None) -> list[str]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Prompts CSV not found: {csv_path}")

    prompts: list[str] = []
    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames and "prompt" in reader.fieldnames:
            for row in reader:
                prompt = (row.get("prompt") or "").strip()
                if prompt:
                    prompts.append(prompt)
        else:
            csv_file.seek(0)
            plain_reader = csv.reader(csv_file)
            for row in plain_reader:
                if not row:
                    continue
                prompt = row[0].strip()
                if prompt and prompt.lower() != "prompt":
                    prompts.append(prompt)

    if limit is not None:
        if limit <= 0:
            raise ValueError("--limit must be greater than 0.")
        prompts = prompts[:limit]

    if not prompts:
        raise ValueError(f"No prompts found in {csv_path}.")

    return prompts


def request_image_bytes(
    prompt: str,
    api_key: str,
    model: str,
    size: str,
    timeout: int,
) -> bytes:
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
    }
    request = urllib.request.Request(
        IMAGES_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")

    data = json.loads(body)
    image_data = data.get("data") or []
    if not image_data:
        raise RuntimeError("Image API response did not include image data.")

    b64_image = image_data[0].get("b64_json")
    if not b64_image:
        raise RuntimeError("Image API response did not include b64_json.")

    return base64.b64decode(b64_image)


def generate_image_with_retries(
    prompt: str,
    api_key: str,
    model: str,
    size: str,
    retries: int,
    timeout: int,
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return request_image_bytes(
                prompt=prompt,
                api_key=api_key,
                model=model,
                size=size,
                timeout=timeout,
            )
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(
                f"HTTP {exc.code} from image API on attempt {attempt}/{retries}: {details}"
            )
        except Exception as exc:  # noqa: BLE001
            last_error = exc

        if attempt < retries:
            backoff_seconds = min(2**attempt, 10)
            print(
                f"Request failed (attempt {attempt}/{retries}). "
                f"Retrying in {backoff_seconds}s..."
            )
            time.sleep(backoff_seconds)

    assert last_error is not None
    raise RuntimeError(f"Failed to generate image after {retries} attempts.") from last_error


def save_images(
    prompts: list[str],
    output_dir: Path,
    api_key: str,
    model: str,
    size: str,
    retries: int,
    timeout: int,
    delay: float,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(prompts)
    print(f"Starting image generation for {total} prompts...")

    for index, prompt in enumerate(prompts, start=1):
        image_bytes = generate_image_with_retries(
            prompt=prompt,
            api_key=api_key,
            model=model,
            size=size,
            retries=retries,
            timeout=timeout,
        )

        filename = f"image_{index:03d}.png"
        file_path = output_dir / filename
        file_path.write_bytes(image_bytes)
        print(f"[{index}/{total}] Saved {file_path}")

        if delay > 0 and index < total:
            time.sleep(delay)

    print(f"Done. Generated {total} images in {output_dir}")


def main() -> None:
    args = parse_args()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("Please set OPENAI_API_KEY before running this script.")

    prompts = read_prompts(PROMPTS_CSV_PATH, limit=args.limit)
    save_images(
        prompts=prompts,
        output_dir=OUTPUT_DIR_PATH,
        api_key=api_key,
        model=args.model,
        size=args.size,
        retries=args.retries,
        timeout=args.timeout,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()
