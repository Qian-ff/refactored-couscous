"""Generate project-local development configuration; preserve existing configuration."""
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    target = ROOT / ".env"
    if target.exists():
        print("Existing .env preserved")
        return
    password = secrets.token_urlsafe(24)
    values = {
        "APP_ENV": "development", "SECRET_KEY": secrets.token_urlsafe(48),
        "POSTGRES_USER": "safelab", "POSTGRES_PASSWORD": password, "POSTGRES_DB": "safelab",
        "DATABASE_URL": f"postgresql+psycopg://safelab:{password}@127.0.0.1:55432/safelab",
        "SAFELAB_DEMO_PASSWORD": "88888888",
    }
    with target.open("x", encoding="utf-8", newline="\n") as file:
        file.write("# Generated for local development; ignored by Git.\n")
        file.writelines(f"{key}={value}\n" for key, value in values.items())
    print("Generated ignored .env; no global environment changes")


if __name__ == "__main__":
    main()
