import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from io import BytesIO

from services.storage import (
    StorageError,
    is_storage_configured,
    public_image_url,
    upload_image_to_storage,
)


class SupabaseStorageTestCase(unittest.TestCase):
    def setUp(self):
        self.config = {
            "SUPABASE_URL": "https://project.supabase.co/",
            "SUPABASE_SECRET_KEY": "server-secret",
            "SUPABASE_STORAGE_BUCKET": "item images",
        }

    def test_storage_is_configured_only_with_url_and_secret(self):
        self.assertTrue(is_storage_configured(self.config))
        self.assertFalse(is_storage_configured({"SUPABASE_URL": self.config["SUPABASE_URL"]}))

    def test_public_image_url_escapes_bucket_and_filename(self):
        self.assertEqual(
            public_image_url(self.config, "photo one.png"),
            "https://project.supabase.co/storage/v1/object/public/item%20images/photo%20one.png",
        )

    @patch("services.storage.urlopen")
    def test_upload_sends_image_to_supabase_with_server_credentials(self, mocked_urlopen):
        response = mocked_urlopen.return_value.__enter__.return_value
        response.status = 200

        upload_image_to_storage(self.config, "photo.png", b"image-data", "image/png")

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://project.supabase.co/storage/v1/object/item%20images/photo.png")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer server-secret")
        self.assertEqual(request.get_header("Content-type"), "image/png")
        self.assertEqual(request.data, b"image-data")

    @patch("services.storage.urlopen")
    def test_upload_reports_supabase_http_errors_without_credentials(self, mocked_urlopen):
        mocked_urlopen.side_effect = HTTPError(
            "https://project.supabase.co/storage/v1/object/item%20images/photo.png",
            403,
            "Forbidden",
            {},
            BytesIO(b'{"message":"Bucket not found"}'),
        )

        with self.assertRaisesRegex(StorageError, "Bucket not found.*HTTP 403"):
            upload_image_to_storage(self.config, "photo.png", b"image-data", "image/png")


if __name__ == "__main__":
    unittest.main()
