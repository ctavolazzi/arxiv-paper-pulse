# tests/conftest.py
import sys
from pathlib import Path

print("sys.executable:", sys.executable)
print("Original sys.path:", sys.path)

# Compute what we expect for the Poetry venv's site-packages:
venv_path = Path(sys.executable).resolve().parent.parent
expected_site_packages = venv_path / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
print("Expected site-packages path:", expected_site_packages)

# Append the project root (if not already present)
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

print("Final sys.path:", sys.path)

# Register custom pytest marks
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark a test as an integration test")
    config.addinivalue_line("markers", "gui: mark a test as a GUI test that requires a display")
    config.addinivalue_line("markers", "live_api: mark a test as requiring live API calls")
    config.addinivalue_line("markers", "saves_images: mark a test as saving actual image files")
