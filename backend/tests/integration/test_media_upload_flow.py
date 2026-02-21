"""Integration test: multi-file media upload flow.

Exercises uploading both video and audio files in sequence,
verifying the full pipeline from form parsing through to
file storage, type validation, and size enforcement.
"""

import io
from uuid import uuid4

from tests.conftest import auth_headers


class TestMultiFileUploadFlow:
    """Upload video then audio for the same session."""

    def test_video_and_audio_upload_sequence(self, client, tmp_path):
        headers = auth_headers()
        sid = str(uuid4())

        # Upload video
        resp = client.post(
            "/api/v1/media/video",
            data={"session_id": sid},
            files={"file": ("face.mp4", io.BytesIO(b"fake-video-bytes"), "video/mp4")},
            headers=headers,
        )
        assert resp.status_code == 201
        video_data = resp.json()
        assert video_data["session_id"] == sid
        assert video_data["media_type"] == "video"

        # Upload audio
        resp = client.post(
            "/api/v1/media/audio",
            data={"session_id": sid},
            files={"file": ("symptom.webm", io.BytesIO(b"fake-audio-bytes"), "audio/webm")},
            headers=headers,
        )
        assert resp.status_code == 201
        audio_data = resp.json()
        assert audio_data["session_id"] == sid
        assert audio_data["media_type"] == "audio"

        assert video_data["id"] != audio_data["id"]

    def test_rejects_video_on_audio_endpoint(self, client):
        headers = auth_headers()
        resp = client.post(
            "/api/v1/media/audio",
            data={"session_id": str(uuid4())},
            files={"file": ("vid.mp4", io.BytesIO(b"data"), "video/mp4")},
            headers=headers,
        )
        assert resp.status_code == 415

    def test_rejects_audio_on_video_endpoint(self, client):
        headers = auth_headers()
        resp = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("aud.wav", io.BytesIO(b"data"), "audio/wav")},
            headers=headers,
        )
        assert resp.status_code == 415

    def test_both_endpoints_enforce_size_limit(self, client):
        headers = auth_headers()
        oversized = b"x" * (2 * 1024 * 1024)

        resp = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("big.mp4", io.BytesIO(oversized), "video/mp4")},
            headers=headers,
        )
        assert resp.status_code == 413

        resp = client.post(
            "/api/v1/media/audio",
            data={"session_id": str(uuid4())},
            files={"file": ("big.wav", io.BytesIO(oversized), "audio/wav")},
            headers=headers,
        )
        assert resp.status_code == 413


class TestMediaUploadAuth:
    def test_video_requires_auth(self, client):
        resp = client.post(
            "/api/v1/media/video",
            data={"session_id": str(uuid4())},
            files={"file": ("f.mp4", io.BytesIO(b"data"), "video/mp4")},
        )
        assert resp.status_code == 401

    def test_audio_requires_auth(self, client):
        resp = client.post(
            "/api/v1/media/audio",
            data={"session_id": str(uuid4())},
            files={"file": ("f.webm", io.BytesIO(b"data"), "audio/webm")},
        )
        assert resp.status_code == 401
