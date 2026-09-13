import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app

if __name__ == "__main__":
    app.ensure_dirs()
    app.app.run(host="0.0.0.0", port=7860, debug=False, threaded=True, use_reloader=False)
