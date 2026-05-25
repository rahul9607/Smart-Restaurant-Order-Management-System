import argparse
import os
import sys
from pathlib import Path

import qrcode
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models import RestaurantTable

DEFAULT_BASE_URL = "http://192.168.1.41:5000"


def _normalize_base_url(value: str) -> str:
    url = (value or "").strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ValueError("Base URL must start with http:// or https://")
    return url


def _get_base_url() -> str:
    parser = argparse.ArgumentParser(description="Generate table QR codes")
    parser.add_argument(
        "--base-url",
        dest="base_url",
        default=os.environ.get("PUBLIC_BASE_URL", "").strip() or DEFAULT_BASE_URL,
        help="Public base URL, e.g. http://192.168.1.8:5000",
    )
    args = parser.parse_args()
    if args.base_url == DEFAULT_BASE_URL:
        print(f"Using default base URL: {args.base_url}")
    return _normalize_base_url(args.base_url)


def main() -> None:
    base_url = _get_base_url()
    output_dir = Path("app/static/qr_codes")
    output_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine("sqlite:///instance/restaurant.db")
    with Session(engine) as session:
        tables = session.query(RestaurantTable).order_by(RestaurantTable.id).all()
        for table in tables:
            qr_url = f"{base_url}/?table_id={table.id}"
            file_name = f"table_{table.table_number}.png"
            file_path = output_dir / file_name
            img = qrcode.make(qr_url)
            img.save(file_path)
            table.qr_code = qr_url
            print(f"Generated: {file_path} -> {qr_url}")

        session.commit()

    print(f"\nDone. QR codes saved in: {output_dir}")


if __name__ == "__main__":
    main()
