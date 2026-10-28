import os

import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)
django.setup()

script_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "audit_frontal_fppa.py",
)

with open(script_path, encoding="utf-8") as f:
    code = compile(f.read(), script_path, "exec")

exec(code)
