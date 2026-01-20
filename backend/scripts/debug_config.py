from app.core.config import settings
import sys

print(f"DEBUG_CONFIG: AUTOCODE_ARTIFACTS_DIR={settings.AUTOCODE_ARTIFACTS_DIR}")
if settings.AUTOCODE_ARTIFACTS_DIR is None:
    print("DEBUG_CONFIG: It is None!")
else:
    print(f"DEBUG_CONFIG: Type is {type(settings.AUTOCODE_ARTIFACTS_DIR)}")
