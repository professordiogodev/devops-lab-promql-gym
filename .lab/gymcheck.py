#!/usr/bin/env python3
import json, os, re, sys, urllib.parse, urllib.request, urllib.error
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
START = 1767225600
PROM = "http://127.0.0.1:9099"
passed = failed = 0

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is missing:  python3 -m pip install pyyaml")

REF = {   # the reference answers: the same question asked in the cleanest way
    "q01": ('sum(rate(beanie_http_requests_total{service="gateway"}[5m]))', None),
    "q02": ('sum(rate(beanie_http_requests_total{service="gateway",status=~"5.."}[5m])) / sum(rate(beanie_http_requests_total{service="gateway"}[5m]))', None),
    "q03": ('histogram_quantile(0.95, sum by (le) (rate(beanie_http_request_duration_seconds_bucket{service="payments"}[5m])))', None),
    "q04": ('topk(1, sum by (service) (rate(beanie_http_requests_total{status=~"5.."}[5m])) / sum by (service) (rate(beanie_http_requests_total[5m])))', ["service"]),
    "q05": ('sum(increase(beanie_orders_total{status="paid"}[1h]))', None),
    "q06": ('sum(increase(beanie_payments_total{result="declined"}[6h])) / sum(increase(beanie_payments_total[6h]))', None),
    "q07": ('count(up{job="beanie"} == 1)', None),
    "q08": ('deriv(process_resident_memory_bytes{service="orders"}[1h])', None),
    "q09": ('predict_linear(process_resident_memory_bytes{service="orders"}[1h], 7200)', None),
    "q10": ('sum(rate(beanie_http_request_duration_seconds_bucket{service="gateway",le="0.5"}[1h])) / sum(rate(beanie_http_request_duration_seconds_count{service="gateway"}[1h]))', None),
    "q11": ('1 - sum(increase(beanie_http_requests_total{service="gateway",status=~"5.."}[6h])) / sum(increase(beanie_http_requests_total{service="gateway"}[6h]))', None),
    "q12": ('sort_desc(sum by (service) (rate(beanie_http_requests_total[5m])))', ["service"]),
}
NEEDS = {"q01": "beanie_http_requests_total", "q02": "beanie_http_requests_total", "q03": "_bucket", "q04": "beanie_http_requests_total", "q05": "beanie_orders_total",
         "q06": "beanie_payments_total", "q07": "up", "q08": "process_resident_memory_bytes", "q09": "process_resident_memory_bytes", "q10": "_bucket", "q11": "beanie_http_requests_total",
         "q12": "beanie_http_requests_total"}


def check(desc, ok, hint=""):
    global passed, failed
    if ok:
        passed += 1; print("PASS  " + desc)
    else:
        failed += 1; print("FAIL  " + desc + (("   -> " + hint) if hint else ""))


def secs(t):
    m = re.fullmatch(r"(\d+)h(\d+)m", t.strip())
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60


def query(expr, at):
    u = PROM + "/api/v1/query?" + urllib.parse.urlencode({"query": expr, "time": at})
    try:
        d = json.load(urllib.request.urlopen(u, timeout=30))
    except urllib.error.HTTPError as e:
        return None, json.loads(e.read().decode()).get("error", "error")
    if d["status"] != "success":
        return None, d.get("error", "error")
    r = d["data"]
    if r["resultType"] == "scalar":
        return {(): float(r["result"][1])}, ""
    if r["resultType"] != "vector":
        return None, "the expression returns a %s: use an instant query (no bare range selector)" % r["resultType"]
    return [(m["metric"], float(m["value"][1])) for m in r["result"]], ""


def norm(res, keys):
    if res is None:
        return None
    if isinstance(res, dict):
        return [((), res[()])]
    return [(tuple((k, m.get(k)) for k in (keys or [])), v) for m, v in res]


doc = yaml.safe_load(open("queries.yaml"))
qs = {q["id"]: q for q in doc["questions"]}
for qid in sorted(REF):
    q = qs.get(qid)
    at = START + secs(q["time"]) if q else None
    expr = str(q.get("expr", "")).strip() if q else ""
    label = "%s (at %s): %s" % (qid, q["time"] if q else "?", (q["question"][:70] + "...") if q else "")
    if not expr or expr == "TODO":
        check(label, False, "write the expression in queries.yaml"); continue
    if re.fullmatch(r"[\d.eE+\-*/() ]+", expr):
        check(label, False, "that is a number, not a query: ask the data"); continue
    if NEEDS[qid] not in expr:
        check(label, False, "this question is answered from the metric %s" % NEEDS[qid]); continue
    ref_expr, keys = REF[qid]
    exp, e1 = query(ref_expr, at)
    got, e2 = query(expr, at)
    if got is None:
        check(label, False, "Prometheus says: %s" % e2[:150]); continue
    en, gn = norm(exp, keys), norm(got, keys)
    ok = False
    if en is not None and len(gn) == len(en):
        if keys:   # compare by label: order matters only for the ranking question
            ok = sorted(k for k, _ in gn) == sorted(k for k, _ in en)
            if qid == "q12":   # a ranking: the values must come out in descending order (ties may swap places)
                vals = [v for _, v in gn]
                ok = ok and all(vals[i] >= vals[i + 1] - 1e-9 for i in range(len(vals) - 1))
            ok = ok and all(abs(v - dict(en)[k]) <= max(1e-6, abs(dict(en)[k]) * 0.01) for k, v in gn if k in dict(en))
        else:
            ok = abs(gn[0][1] - en[0][1]) <= max(1e-6, abs(en[0][1]) * 0.01)
    check(label, ok, "expected %s, your query returns %s" % ([round(v, 4) for _, v in en][:3] if en else en, [round(v, 4) for _, v in gn][:3]))
print()
print(("ALL CHECKS PASSED (%d/%d)" % (passed, passed)) if failed == 0 else ("%d check(s) failed, %d passed" % (failed, passed)))
sys.exit(1 if failed else 0)
