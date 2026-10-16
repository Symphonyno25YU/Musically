"""Start the Music Switcher frontend and local backend with one command."""

import signal
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


# Resolve paths relative to this script so it can be launched from any directory.
PROJECT_DIRECTORY = Path(__file__).resolve().parent
FRONTEND_DIRECTORY = PROJECT_DIRECTORY / "Frontend"
BACKEND_DIRECTORY = PROJECT_DIRECTORY / "Backend"
# Keep the frontend accessible only from this Mac, not other network devices.
HOST = "127.0.0.1"
FRONTEND_PORT = 5500


def stop_process(process):
    """Stop a child process without leaving it running in the background."""
    if process.poll() is not None:
        return

    # Allow graceful shutdown first; force termination if the child does not exit.
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run():
    """Run the static frontend server while the backend API runs alongside it."""
    # Use the same Python interpreter as the launcher, with the backend as its
    # working directory. Popen lets the API run alongside the frontend server.
    api_process = subprocess.Popen(
        [sys.executable, "api_server.py"],
        cwd=BACKEND_DIRECTORY,
    )
    # Serve only frontend files without changing this process's working directory.
    handler = partial(SimpleHTTPRequestHandler, directory=str(FRONTEND_DIRECTORY))

    try:
        frontend_server = ThreadingHTTPServer((HOST, FRONTEND_PORT), handler)
    except OSError:
        # Do not leave the API running if the frontend cannot bind its port.
        stop_process(api_process)
        raise

    def stop_services(_signal_number, _frame):
        # Route Control+C and termination requests through the cleanup below.
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, stop_services)
    signal.signal(signal.SIGTERM, stop_services)

    print(f"Welcome to Music switcher: enter http://{HOST}:{FRONTEND_PORT} in your browser.")
    print(f"  Frontend: http://{HOST}:{FRONTEND_PORT}")
    print("  Backend:  http://127.0.0.1:8000")
    print("Press Control+C to stop both services.")

    try:
        frontend_server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Music Switcher.")
    finally:
        # Release the listening socket and stop the child API on exit or error.
        frontend_server.server_close()
        stop_process(api_process)


if __name__ == "__main__":
    run()