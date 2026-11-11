#!/usr/bin/env python3
"""PROVIDED. Writes six hours of recorded Beanie metrics, in OpenMetrics format, for `promtool tsdb create-blocks-from`.

Nothing here is random: the same file comes out every time. The story it tells is for you to find with PromQL.
Time zero is START (a fixed date); the night runs for six hours with a sample every 15 seconds.
"""
import math, sys

START = 1767225600          # 2026-01-01 00:00:00 UTC
STEP, HOURS = 15, 6
BUCKETS = [0.05, 0.1, 0.25, 0.5, 1, 2.5, 5]
SERVICES = ["gateway", "menu", "orders", "payments", "notifications"]
PORT = {"gateway": 8000, "menu": 8001, "orders": 8002, "payments": 8003, "notifications": 8004}
H = 3600


def window(t, a, b):
    return a <= t < b


def rates(t):
    """requests per second per (service, route) and the share of 5xx, at time t (seconds from START)."""
    pay_slow = window(t, 3 * H, 3 * H + 1800)          # payments is slow: 03:00 to 03:30
    menu_bad = window(t, 4 * H + 1800, 4 * H + 3000)   # menu fails 40% of the time: 04:30 to 04:50
    base_menu, base_order = 25.0, 15.0
    out = {}
    out[("gateway", "/api/menu")] = (base_menu, 0.4 if menu_bad else 0.001)
    out[("gateway", "/api/orders")] = (base_order, 0.3 if pay_slow else (0.2 if menu_bad else 0.002))
    out[("menu", "/menu")] = (base_menu + base_order, 0.4 if menu_bad else 0.0005)
    out[("orders", "/orders")] = (base_order, 0.3 if pay_slow else (0.2 if menu_bad else 0.002))
    out[("payments", "/charge")] = (base_order * (0.7 if pay_slow else 1.0), 0.0005)
    out[("notifications", "/notify")] = (base_order, 0.0005)
    return out


def median_latency(service, t):
    m = {"gateway": 0.08, "menu": 0.02, "orders": 0.06, "payments": 0.04, "notifications": 0.01}[service]
    if window(t, 3 * H, 3 * H + 1800):
        if service == "payments":
            m = 1.2
        elif service in ("orders", "gateway"):
            m = m + 1.0
    return m


def cdf(le, mean):
    return 1.0 - math.exp(-le / mean)


def main(out_path):
    counters = {}
    lines = []
    t = 0
    samples = {}
    n = HOURS * H // STEP + 1
    state = {"req": {}, "bucket": {}, "count": {}, "sum": {}, "orders": {"paid": 0.0, "payment_failed": 0.0, "payment_error": 0.0}, "pay": {"approved": 0.0, "declined": 0.0}}
    restart_at = 2 * H
    orders_offset = 0.0
    for i in range(n):
        t = i * STEP
        ts = START + t
        r = rates(t)
        # counters (orders restarts at 02:00: its in-process counters go back to zero)
        if t == restart_at:
            for key in list(state["req"]):
                if key[0] == "orders":
                    state["req"][key] = 0.0
            for key in list(state["bucket"]):
                if key[0] == "orders":
                    state["bucket"][key] = 0.0
            for key in list(state["count"]):
                if key[0] == "orders":
                    state["count"][key] = 0.0
                    state["sum"][key] = 0.0
            state["orders"] = {"paid": 0.0, "payment_failed": 0.0, "payment_error": 0.0}
        if t > 0:
            for (svc, route), (rps, err) in r.items():
                ok_status = "201" if route == "/api/orders" else "200"
                err_status = {"gateway": "503", "menu": "500", "orders": "503", "payments": "500", "notifications": "500"}[svc]
                if svc == "gateway" and window(t, 3 * H, 3 * H + 1800):
                    err_status = "504"
                req = rps * STEP
                for status, share in ((ok_status, 1 - err), (err_status, err)):
                    k = (svc, route, status)
                    state["req"][k] = state["req"].get(k, 0.0) + req * share
                kk = (svc, route)
                state["count"][kk] = state["count"].get(kk, 0.0) + req
                mean = median_latency(svc, t)
                state["sum"][kk] = state["sum"].get(kk, 0.0) + req * mean
                prev = 0.0
                for le in BUCKETS:
                    state["bucket"][(svc, route, le)] = state["bucket"].get((svc, route, le), 0.0) + req * cdf(le, mean)
            # business counters
            o = r[("orders", "/orders")]
            ords = o[0] * STEP
            pay_err = 0.3 if window(t, 3 * H, 3 * H + 1800) else 0.002
            state["orders"]["paid"] += ords * (1 - 0.06 - pay_err)
            state["orders"]["payment_failed"] += ords * 0.06
            state["orders"]["payment_error"] += ords * pay_err
            p = r[("payments", "/charge")][0] * STEP
            state["pay"]["declined"] += p * 0.06
            state["pay"]["approved"] += p * 0.94
        # emit
        def emit(name, labels, value):
            lab = ",".join('%s="%s"' % kv for kv in labels)
            samples.setdefault(name, []).append("%s{%s} %.6f %d" % (name, lab, value, ts))
        for (svc, route, status), v in state["req"].items():
            emit("beanie_http_requests_total", [("service", svc), ("method", "POST" if route in ("/api/orders", "/orders", "/charge", "/notify") else "GET"), ("route", route), ("status", status)], v)
        for (svc, route), v in state["count"].items():
            emit("beanie_http_request_duration_seconds_count", [("service", svc), ("route", route)], v)
            emit("beanie_http_request_duration_seconds_sum", [("service", svc), ("route", route)], state["sum"][(svc, route)])
            emit("beanie_http_request_duration_seconds_bucket", [("service", svc), ("route", route), ("le", "+Inf")], v)
        for (svc, route, le), v in state["bucket"].items():
            emit("beanie_http_request_duration_seconds_bucket", [("service", svc), ("route", route), ("le", ("%g" % le))], v)
        for st, v in state["orders"].items():
            emit("beanie_orders_total", [("status", st)], v)
        for res, v in state["pay"].items():
            emit("beanie_payments_total", [("result", res)], v)
        # memory: every service ~ flat, orders leaks 40 MB per hour since its restart at 02:00 (and had a different slope before)
        for svc in SERVICES:
            if svc == "orders":
                since = (t - restart_at) if t >= restart_at else t
                mem = 150e6 + (40e6 / H) * since
            else:
                mem = 90e6 + 2e6 * math.sin(t / 900.0)
            emit("process_resident_memory_bytes", [("service", svc)], mem)
        # up: notifications is down 05:00 to 05:20
        for svc in SERVICES:
            down = svc == "notifications" and window(t, 5 * H, 5 * H + 1200)
            emit("up", [("job", "beanie"), ("instance", "%s:%d" % (svc, PORT[svc]))], 0.0 if down else 1.0)
    with open(out_path, "w") as f:
        for name, rows in samples.items():
            f.write("# TYPE %s gauge\n" % name)
            f.write("\n".join(rows) + "\n")
        f.write("# EOF\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "incident.om")
