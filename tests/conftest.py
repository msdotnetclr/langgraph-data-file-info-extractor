import os
import shutil
import tempfile
from pathlib import Path


def pytest_configure(config):
    tmpdir = tempfile.mkdtemp(prefix="lg01_test_")
    os.environ["DATA_ROOT"] = tmpdir
    config._lg01_test_data_root = tmpdir

    import sys
    if "src.storage" in sys.modules:
        import src.storage
        src.storage.DATA_ROOT = Path(tmpdir)
    if "src.session_manager" in sys.modules:
        import src.session_manager
        src.session_manager.SESSIONS_ROOT = Path(tmpdir) / "sessions"


def pytest_unconfigure(config):
    tmpdir = getattr(config, "_lg01_test_data_root", None)
    if tmpdir and os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)
