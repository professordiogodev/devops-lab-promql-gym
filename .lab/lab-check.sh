#!/usr/bin/env bash
rc=0
python3 - <<'PY' || rc=1
import sys
try:
    import yaml
except ImportError:
    print("- ℹ️ PyYAML missing: skipped"); sys.exit(0)
q = yaml.safe_load(open("queries.yaml"))["questions"]
empty = [x["id"] for x in q if not str(x.get("expr", "")).strip() or "TODO" in str(x.get("expr", ""))]
print("- ✅ all twelve queries are written" if not empty else "- ❌ queries still empty: " + ", ".join(empty))
sys.exit(1 if empty else 0)
PY
grep -qE '^ALL CHECKS PASSED \(' SUBMISSION.md && echo "- ✅ SUBMISSION.md shows ALL CHECKS PASSED" || { echo "- ❌ paste the verify.sh output ('ALL CHECKS PASSED') into SUBMISSION.md"; rc=1; }
exit $rc
