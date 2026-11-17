"""Forecast a game launch day's Twitch viewers, hour by hour (make.fun
gta6-twitch-ccu-forecast-01, program/v1, Python standard library only).

Model: empirical quantiles of log-ratios from comparable launches.

Every case carries past big launches ("comparables"), each with hourly
viewers from 14 days before to 3 days after its own release day. For a
comparable whose release-day hour 1 is a real launch hour -- its hour-1
viewers are at least 20% of its release-day peak, so the game had already
unlocked around the start of the UTC day the way a rolling midnight-local
console launch (GTA VI's shape) has -- the curve

    L_h = ln(viewers_h / viewers_1),  h = 2..24

says how a launch day typically unfolds relative to its first hour. The
forecast for a case with hour-1 print p is

    q_tau(h) = p * exp(quantile_tau of {L_h} over those comparables),

with the five scored levels tau = 0.05, 0.25, 0.5, 0.75, 0.95. Launches
whose hour 1 was still a pre-unlock trickle (a single global unlock late
in the UTC day) have explosive, unrepresentative ratios and are left out
of this pool.

One hedge: the day's main wave can still arrive later than hour 1 (the
US unlocks land at 05:00Z and 08:00Z for GTA VI), so the scored
distribution is a mixture -- 80% the launch-shaped pool above, 20% the
pool of every usable comparable, whose wider, higher curves cover a
slower-building day. A leave-one-out backtest over all 37 usable
comparables (each launch day forecast from the others, scored with the
contest's exact pinball loss) chose this mixture: it beats the house
baseline overall (0.848 vs 0.930), on rolling-launch days like this one
(0.221 vs 0.251, with 90.7% of hours inside the 5%-95% band), and on
late-unlock days (1.768 vs 1.925). Hours no curve covers fall back to
the house persistence shape.

The program reads every *.in file in $MAKEFUN_INPUT_DIR (else /input),
in name order, and writes <id>.out to $MAKEFUN_OUTPUT_DIR (else /output).
It is deterministic: two runs on the same case write the same bytes.
"""

import json
import math
import os
from datetime import datetime
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# Standard-normal quantiles at LEVELS, for the persistence fallback.
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
BASE_SIGMA = 0.15

# A comparable joins the launch-shaped pool when its release-day hour 1
# reached at least this fraction of its release-day peak.
EARLY_MIN_FRAC = 0.20
# A comparable's release day is usable when at least this many of the
# hours 2..24 have a positive count.
MIN_DAY_HOURS = 18
# Mixture weight on the full pool (every usable comparable); the rest
# sits on the launch-shaped pool.
MIX_FULL = 0.20


def parse_ts(ts):
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))


def release_day(comp):
    """{hour: viewers} for the 24 UTC hours of a comparable's release day."""
    try:
        start = parse_ts(comp["day_start"])
    except (KeyError, ValueError):
        return {}
    day = {}
    for pt in comp.get("hourly") or []:
        try:
            off = (parse_ts(pt["from"]) - start).total_seconds()
            viewers = pt.get("viewers")
        except (KeyError, ValueError, TypeError):
            continue
        if off % 3600 != 0:
            continue
        hour = int(off // 3600) + 1
        if 1 <= hour <= 24 and viewers is not None and viewers > 0:
            day[hour] = float(viewers)
    return day


def log_ratios(day):
    """{hour: ln(viewers_hour / viewers_1)} for hours 2..24 of a release day."""
    if 1 not in day:
        return {}
    v1 = day[1]
    return {h: math.log(day[h] / v1) for h in range(2, 25) if h in day}


def weighted_quantile(pairs, tau):
    """Linear-interpolated weighted empirical quantile of [(value, weight)]."""
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    if total <= 0:
        return pairs[len(pairs) // 2][0]
    target = tau * total
    acc = 0.0
    prev_value, prev_acc = pairs[0][0], 0.0
    for value, weight in pairs:
        acc += weight
        if acc >= target:
            if acc == weight:
                return value
            frac = (target - prev_acc) / weight
            return prev_value + frac * (value - prev_value)
        prev_value, prev_acc = value, acc
    return pairs[-1][0]


def persistence_row(p1, hour):
    """The house baseline's row for one hour: flat median, widening spread."""
    return [p1 * math.exp(z * BASE_SIGMA * math.sqrt(hour - 1)) for z in Z]


def build_pools(case):
    """Split the case's comparables into (early, full) log-ratio curve lists.

    early: release-day hour 1 was already a launch hour (frac of peak >=
    EARLY_MIN_FRAC). full: every usable comparable.
    """
    early, full = [], []
    for comp in case.get("comparables") or []:
        day = release_day(comp)
        ratios = log_ratios(day)
        if len(ratios) < MIN_DAY_HOURS:
            continue
        full.append(ratios)
        if day[1] >= EARLY_MIN_FRAC * max(day.values()):
            early.append(ratios)
    return early, full


def hour_quantiles(early, full, hour, p1):
    """The five quantiles of one hour's viewers, in viewers.

    The weighted sample for the hour mixes the two pools: each
    launch-shaped curve carries (1 - MIX_FULL) / n_early of the weight,
    each remaining curve MIX_FULL / n_full, so the empirical quantiles
    are those of the mixture distribution described in the docstring.
    """
    near = [ratios[hour] for ratios in early if hour in ratios]
    wide = [ratios[hour] for ratios in full if hour in ratios]
    pairs = []
    if near:
        w = (1.0 - MIX_FULL) / len(near)
        pairs += [(value, w) for value in near]
    if wide:
        w = MIX_FULL / len(wide)
        pairs += [(value, w) for value in wide]
    if not pairs:
        return persistence_row(p1, hour)
    row = []
    prev = 0.0
    for tau in LEVELS:
        value = min(p1 * math.exp(weighted_quantile(pairs, tau)), 1e9)
        value = round(max(value, prev), 2)  # quantiles never decrease
        row.append(value)
        prev = value
    return row


def forecast_case(case):
    known = next((k for k in case.get("known") or [] if k.get("hour") == 1), None)
    p1 = 1.0
    if known is not None and known.get("viewers"):
        p1 = max(1.0, float(known["viewers"]))
    early, full = build_pools(case)
    rows = []
    for spec in sorted(case.get("forecast") or [], key=lambda r: r["hour"]):
        hour = spec["hour"]
        rows.append({"hour": hour, "q": hour_quantiles(early, full, hour, p1)})
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        result = forecast_case(case)
        text = json.dumps(result, separators=(",", ":")) + "\n"
        (OUTPUT_DIR / f"{path.stem}.out").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
