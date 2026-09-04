import base64
import importlib.util
import io
import json
from pathlib import Path

from PIL import Image


SCRIPTS = Path(__file__).parents[1] / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def png_bytes(size=(3840, 2160)):
    image = Image.new("RGB", size, "#6b6256")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_vellum_edit_sends_source_and_native_size(tmp_path, monkeypatch):
    helper = load("generate_frame_vellum")
    source = tmp_path / "image.png"
    source.write_bytes(png_bytes())
    response_image = base64.b64encode(png_bytes()).decode()

    class Response:
        def __enter__(self):
            return io.StringIO(json.dumps({"data": [{"b64_json": response_image}]}))

        def __exit__(self, *args):
            return False

    captured = {}
    monkeypatch.setattr(helper, "urlopen", lambda request, timeout: captured.setdefault("request", request) or Response())
    # The lambda above returns the stored request; make the fake response explicit.
    monkeypatch.setattr(helper, "urlopen", lambda request, timeout: (captured.setdefault("request", request), Response())[1])
    edited, _ = helper.request_edit(source, "not-a-real-key")
    assert edited == png_bytes()
    body = captured["request"].data
    assert b"3840x2160" in body
    assert b"name=\"image\"" in body
    assert source.read_bytes() in body
    assert helper.PROMPT.encode() in body


def test_display_uses_flexible_matte_then_content_id(tmp_path, monkeypatch):
    helper = load("display_frame_art")
    output = tmp_path / "frame-art.json"
    calls = []

    class Result:
        def __init__(self, stdout):
            self.returncode, self.stdout, self.stderr = 0, stdout, ""

    monkeypatch.setattr(helper, "run", lambda command: calls.append(command) or Result("Uploaded. content_id: MY_F1234" if "upload" in command else "Displaying"))
    monkeypatch.setattr("sys.argv", ["display_frame_art.py", "--frame-cli", "/bin/frame-art", "--image", "art.png", "--host", "tv", "--token-file", "token", "--matte", "flexible_antique", "--output", str(output)])
    assert helper.main() == 0
    assert calls[0][calls[0].index("--matte") + 1] == "flexible_antique"
    assert calls[1][calls[1].index("display") + 1] == "MY_F1234"
    assert json.loads(output.read_text())["status"] == "displayed"


def test_display_timeout_keeps_uploaded_content_pending(tmp_path, monkeypatch):
    helper = load("display_frame_art")
    output = tmp_path / "frame-art.json"
    calls = []

    class Result:
        def __init__(self, returncode, stdout="", stderr=""):
            self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

    def fake_run(command):
        calls.append(command)
        if "upload" in command:
            return Result(0, "Uploaded. content_id: MY_F1234")
        return Result(124, stderr="timed out")

    monkeypatch.setattr(helper, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["display_frame_art.py", "--frame-cli", "/bin/frame-art", "--image", "art.png", "--host", "tv", "--token-file", "token", "--matte", "flexible_antique", "--output", str(output)])
    assert helper.main() == 0
    recorded = json.loads(output.read_text())
    assert recorded["status"] == "uploaded-pending-display"
    assert recorded["contentId"] == "MY_F1234"
    assert calls[1][0:2] == ["timeout", "45"]
