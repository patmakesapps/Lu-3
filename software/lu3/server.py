"""Start and stop llama-server, which runs the Lu-3 GGUF model and serves it over HTTP."""
import subprocess
import time
import urllib.request
from pathlib import Path


class LlamaServer:
    """Runs llama-server for the length of a `with` block.

    If a server is already answering on the port (started by hand, or by another
    process), it is used as is and left running afterwards.
    """

    def __init__(self, executable, model, port, context_size, log_path):
        self.executable = executable
        self.model = Path(model)
        self.port = port
        self.context_size = context_size
        self.log_path = Path(log_path)
        self.process = None

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def healthy(self):
        try:
            with urllib.request.urlopen(f"{self.url}/health", timeout=2) as response:
                return response.status == 200
        except OSError:
            return False

    def __enter__(self):
        if self.healthy():
            return self
        if not self.model.is_file():
            raise SystemExit(f"Model file not found: {self.model}")

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        log = self.log_path.open("w", encoding="utf-8")
        command = [self.executable, "-m", str(self.model), "--port", str(self.port),
                   "-c", str(self.context_size), "-ngl", "99", "--jinja", "--no-webui"]
        try:
            self.process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        except FileNotFoundError:
            raise SystemExit(f"llama-server not found: {self.executable} (set llama_server in config.json "
                             "or pass --server)")
        finally:
            log.close()

        for _ in range(300):
            if self.process.poll() is not None:
                raise SystemExit(f"llama-server exited with code {self.process.returncode}; see {self.log_path}")
            if self.healthy():
                return self
            time.sleep(1)
        self.__exit__(None, None, None)
        raise SystemExit(f"llama-server did not become ready; see {self.log_path}")

    def __exit__(self, *exc):
        if self.process is not None:
            self.process.terminate()
            self.process.wait()
            self.process = None
