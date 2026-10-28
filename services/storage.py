"""Supabase Storage integration for public item photographs."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class StorageError(RuntimeError):
    """Raised when an image cannot be uploaded to Supabase Storage."""


def is_storage_configured(config):
    return bool(config.get("SUPABASE_URL") and config.get("SUPABASE_SECRET_KEY"))


def _object_path(config, filename):
    bucket = quote(config["SUPABASE_STORAGE_BUCKET"], safe="")
    object_name = quote(filename, safe="/")
    return f"{config['SUPABASE_URL'].rstrip('/')}/storage/v1/object/{bucket}/{object_name}"


def public_image_url(config, filename):
    bucket = quote(config["SUPABASE_STORAGE_BUCKET"], safe="")
    object_name = quote(filename, safe="/")
    return (
        f"{config['SUPABASE_URL'].rstrip('/')}/storage/v1/object/public/"
        f"{bucket}/{object_name}"
    )


def upload_image_to_storage(config, filename, image_bytes, content_type):
    request = Request(
        _object_path(config, filename),
        data=image_bytes,
        headers={
            "Authorization": f"Bearer {config['SUPABASE_SECRET_KEY']}",
            "apikey": config["SUPABASE_SECRET_KEY"],
            "Content-Type": content_type,
            "Cache-Control": "public, max-age=3600",
            "x-upsert": "false",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            if response.status not in (200, 201):
                raise StorageError(
                    f"Supabase Storage returned unexpected HTTP status {response.status}."
                )
            response.read()
    except HTTPError as error:
        detail = "Supabase Storage rejected the image upload."
        try:
            response_body = json.loads(error.read().decode("utf-8"))
            if isinstance(response_body, dict):
                message = response_body.get("message") or response_body.get("error")
                if message:
                    detail = f"Supabase Storage rejected the image upload: {message}"
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        raise StorageError(f"{detail} (HTTP {error.code}).") from error
    except URLError as error:
        raise StorageError("Could not connect to Supabase Storage.") from error
