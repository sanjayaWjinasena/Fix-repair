"""v1.0.386: Repair teams / types and general stages for databases installed from the rename trial.

Those databases are past v1.0.372 / v1.0.373, so the steps that mark the Repair teams and
Repair ticket types and give the other teams the general stages never ran there. Both steps are
idempotent (already flagged records and tickets already in a general stage are left as they are)
and are run again here. ORM only.
"""

import importlib.util
import os


def _run(folder, version, cr):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), folder, "post-migrate.py")
    spec = importlib.util.spec_from_file_location("fix_repair_" + folder.replace(".", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.migrate(cr, version)


def migrate(cr, version):
    if not version:
        return
    _run("17.0.1.0.372", version, cr)
    _run("17.0.1.0.373", version, cr)
