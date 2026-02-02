import subprocess
import time
import socket
import logging
import os
from pathlib import Path
from .config import LLAMA_BIN, LLAMA_HOST, LLAMA_PORT, MODEL_PATH, N_CTX, N_GPU_LAYERS, N_THREADS

logger = logging.getLogger(__name__)

class LlamaProcessManager:
    """Manages the llama-server subprocess."""
    
    def __init__(self):
        self.process = None

    def start(self):
        """Start the llama-server process if not already running."""
        if self.is_port_open(LLAMA_HOST, LLAMA_PORT):
            logger.info(f"Llama server already listing on {LLAMA_HOST}:{LLAMA_PORT}")
            return

        # Setup Environment for shared libs
        env = os.environ.copy()
        
        # Smartly locate binary if not absolute
        binary_path = LLAMA_BIN
        dist_dir = os.path.abspath("llm_runtime/llama_cpp/dist")
        
        # If relative, check dist folder
        if not os.path.isabs(binary_path) and os.path.exists(os.path.join(dist_dir, binary_path)):
             binary_path = os.path.join(dist_dir, binary_path)
        elif not os.path.isabs(binary_path) and os.path.exists(os.path.join(dist_dir, 'bin', binary_path)):
             binary_path = os.path.join(dist_dir, 'bin', binary_path)
             
        # Inject LD_LIBRARY_PATH
        runtime_libs = [dist_dir, os.path.join(dist_dir, "lib")]
        current_ld = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(runtime_libs) + ":" + current_ld

        if not os.path.exists(binary_path):
             # Try simple fallback
             if os.path.exists("./llama-server"):
                 binary_path = "./llama-server"
             else:
                 raise FileNotFoundError(f"llama-server binary not found at {binary_path} or in dist")
        
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")

        cmd = [
            binary_path,
            "-m", MODEL_PATH,
            "-c", str(N_CTX),
            "-ngl", str(N_GPU_LAYERS),
            "--port", str(LLAMA_PORT),
            "--host", LLAMA_HOST,
            "--threads", str(N_THREADS),
            "--mlock",
            "--parallel", "1"
            # Removed --continuous-batching
        ]
        
        logger.info(f"Starting llama-server: {' '.join(cmd)}")
        logger.info(f"LD_LIBRARY_PATH={env['LD_LIBRARY_PATH']}")
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        try:
            self._wait_for_startup()
        except Exception as e:
            self.stop()
            raise e

    def stop(self):
        """Stop the server process."""
        if self.process:
            logger.info("Stopping llama-server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutError:
                logger.warning("Force killing llama-server...")
                self.process.kill()
            self.process = None

    def is_running(self):
        """Check if process is active."""
        if self.process is None:
            return self.is_port_open(LLAMA_HOST, LLAMA_PORT)
        return self.process.poll() is None

    def _wait_for_startup(self, timeout=30):
        """Poll port until active."""
        start = time.time()
        while time.time() - start < timeout:
            if self.is_port_open(LLAMA_HOST, LLAMA_PORT):
                logger.info("✅ Llama server is up and listening.")
                return
            
            if self.process and self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise RuntimeError(f"Llama server failed to start. Exit code: {self.process.returncode}\nSTDERR: {stderr}")

            time.sleep(0.5)

        raise TimeoutError("Timed out waiting for llama server to start.")

    @staticmethod
    def is_port_open(host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) == 0
