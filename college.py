"""Estimated college stats for -college.

BBGM exports have no college stats, so these are generated: each player's draft-year
ratings are walked back through their college years (undoing the average yearly
progression), then turned into per-game numbers using the same rating composites that
define builds (shooting, athleticism, playmaking, rebounding, interior/perimeter defense...).
Output is stable for a given player (seeded by pid) and is labelled as an estimate.
"""
import json
import random

import player_commands

RATING_KEYS = ['stre', 'spd', 'jmp', 'endu', 'ins', 'dnk', 'ft', 'fg', 'tp', 'oiq', 'diq', 'drb', 'pss', 'reb']
YEAR_NAMES = ['Fr', 'So', 'Jr', 'Sr']


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _load_mean_changes():
    try:
        with open('summaries.txt') as f:
            return json.load(f)
    except Exception:
        return {}


def college_years(draft_age):
    """Seasons spent in college, inferred from age when drafted (19 -> 1 ... 22+ -> 4)."""
    return int(_clamp(draft_age - 18, 1, 4))


def ratings_by_college_year(draft_ratings, draft_age, years):
    """Return [ratings for year 1, ..., ratings for last college year (= draft ratings)]."""
    means = _load_mean_changes()
    out = [dict(draft_ratings)]
    cur = dict(draft_ratings)
    for back in range(1, years):
        age_prev = int(_clamp(draft_age - back, 18, 37))
        step = means.get(str(age_prev), {})
        prev = dict(cur)
        for k in RATING_KEYS:
            prev[k] = _clamp(round(cur[k] - float(step.get(k, 0))), 0, 100)
        prev['ovr'] = player_commands.ovr(prev)
        out.insert(0, prev)
        cur = prev
    return out


def season_line(r, rng, class_year, years):
    """Per-game stat line for one college season from that season's ratings."""
    c = player_commands.calccompsingle(r, True)
    ovr = r.get('ovr') or player_commands.ovr(r)
    jitter = lambda spread=0.08: 1 + rng.uniform(-spread, spread)

    gp = rng.randint(28, 36)
    mpg = _clamp(14 + (ovr - 25) * 0.6 - (1.5 if class_year == 0 and years > 1 else 0), 9, 35) * jitter(0.04)
    mpg = round(_clamp(mpg, 8, 36), 1)
    scale = mpg / 36.0

    usage = c['Usage']
    pts36 = _clamp(7 + 0.45 * (usage - 35) + 0.12 * (r['oiq'] - 45) + 0.30 * (ovr - 45), 4, 34) * jitter()

    tpa36 = _clamp((c['3'] - 38) * 0.16, 0, 9) * jitter(0.1)
    tp_pct = _clamp(0.27 + 0.0024 * (c['3'] - 35), 0.25, 0.44) + rng.uniform(-0.02, 0.02)
    fta36 = _clamp(1.2 + 0.09 * (c['Draw Foul'] - 40) + 0.04 * (usage - 45), 0.8, 8) * jitter(0.1)
    ft_pct = _clamp(0.52 + 0.0042 * r['ft'], 0.5, 0.93) + rng.uniform(-0.02, 0.02)

    tpm36 = tpa36 * tp_pct
    ftm36 = fta36 * ft_pct
    pts_from_twos = max(0.0, pts36 - 3 * tpm36 - ftm36)
    two_pct = _clamp(0.42 + 0.0033 * (c['Rim'] - 30), 0.42, 0.66) + rng.uniform(-0.015, 0.015)
    twom36 = pts_from_twos / 2
    twoa36 = twom36 / two_pct
    pts36 = 2 * twom36 + 3 * tpm36 + ftm36

    trb36 = _clamp(2.5 + 0.28 * (c['R'] - 30) + 0.08 * (ovr - 45), 1.5, 16) * jitter()
    orb_share = _clamp(0.22 + 0.0018 * (r['hgt'] - 40), 0.2, 0.4)
    ast36 = _clamp(1.0 + 0.20 * (c['Ps'] - 30) + 0.06 * (ovr - 45), 0.4, 12) * jitter()
    stl36 = _clamp(0.6 + 0.04 * (c['Stl'] - 45) + 0.01 * (ovr - 45), 0.3, 3.2) * jitter(0.12)
    blk36 = _clamp(0.25 + 0.065 * (c['Bl'] - 40) + 0.01 * (ovr - 45), 0.05, 4.5) * jitter(0.15)
    tov36 = _clamp(1.1 + 0.035 * (c['Tov'] - 35) + 0.02 * (usage - 45), 0.9, 4.8) * jitter(0.1)

    fga36 = twoa36 + tpa36
    fgm36 = twom36 + tpm36
    return {
        'gp': gp, 'mpg': mpg,
        'pts': pts36 * scale, 'trb': trb36 * scale, 'orb': trb36 * scale * orb_share,
        'ast': ast36 * scale, 'stl': stl36 * scale, 'blk': blk36 * scale, 'tov': tov36 * scale,
        'fg_pct': fgm36 / fga36 if fga36 else 0, 'tp_pct': tp_pct if tpa36 * scale >= 0.2 else None,
        'tpa': tpa36 * scale, 'ft_pct': ft_pct, 'fta': fta36 * scale,
    }


def build_college_stats(player, draft_ratings, draft_age):
    years = college_years(draft_age)
    rs = ratings_by_college_year(draft_ratings, draft_age, years)
    seasons = []
    for i, r in enumerate(rs):
        rng = random.Random(player['pid'] * 10 + i)
        seasons.append((YEAR_NAMES[i], season_line(r, rng, i, years)))
    return seasons


YEAR_LONG = ['Freshman', 'Sophomore', 'Junior', 'Senior']


def fmt_lines(s):
    """Two short lines per season; reads fine on mobile, no wide table."""
    tp = f"{s['tp_pct'] * 100:.1f}%" if s['tp_pct'] is not None else 'n/a'
    return (f"**{s['pts']:.1f}** pts  **{s['trb']:.1f}** reb  **{s['ast']:.1f}** ast  "
            f"{s['stl']:.1f} stl  {s['blk']:.1f} blk\n"
            f"FG {s['fg_pct'] * 100:.1f}%  |  3P {tp}  |  FT {s['ft_pct'] * 100:.1f}%  |  {s['mpg']:.1f} min  |  {s['gp']} GP")


def career_line(seasons):
    total_gp = sum(s['gp'] for _, s in seasons)
    avg = lambda k: sum(s[k] * s['gp'] for _, s in seasons) / total_gp
    tpa_total = sum(s['tpa'] * s['gp'] for _, s in seasons)
    tp = (sum((s['tp_pct'] or 0) * s['tpa'] * s['gp'] for _, s in seasons) / tpa_total) if tpa_total else None
    fta_total = sum(s['fta'] * s['gp'] for _, s in seasons)
    ft = sum(s['ft_pct'] * s['fta'] * s['gp'] for _, s in seasons) / fta_total
    return {'gp': total_gp, 'mpg': avg('mpg'), 'pts': avg('pts'), 'trb': avg('trb'), 'ast': avg('ast'),
            'stl': avg('stl'), 'blk': avg('blk'), 'fg_pct': avg('fg_pct'), 'tp_pct': tp, 'ft_pct': ft,
            'tpa': 0, 'fta': 0}
