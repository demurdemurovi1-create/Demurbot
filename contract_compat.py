"""Compatibility between the new BBGM contract format and the legacy one Eldobot uses.

New BBGM exports (Nov 2026+) store player['contracts'] = [{start, amounts, type?, endedEarly?}]
and put released players' dead money inside players. Eldobot's logic expects
p['contract'] = {amount, exp}, p['salaries'] and export['releasedPlayers'].

upgrade_export(): derive the legacy fields in memory (idempotent, no-op on old exports).
to_v2(): build the structure to write back to disk / Dropbox in the new format.
"""
import copy

_TMP = ('contract', 'salaries', '_c0')


def _amount_for(c, season):
    a = c['amounts']
    return a[max(0, min(season - c['start'], len(a) - 1))]


def _active(cs):
    live = [c for c in cs if 'endedEarly' not in c and c.get('amounts')]
    return live[-1] if live else None


def is_v2(export):
    return any('contracts' in p for p in export.get('players', []))


def upgrade_export(export):
    if export.get('_contractsV2') or not is_v2(export):
        return export
    ga = export['gameAttributes']
    season = ga['season']
    owed, rid = [], 0
    for p in export['players']:
        cs = p.get('contracts') or []
        c = _active(cs)
        if c:
            p['contract'] = {'amount': round(_amount_for(c, season)), 'exp': c['start'] + len(c['amounts']) - 1}
        elif 'contract' not in p:
            p['contract'] = {'amount': ga.get('minContract', 750), 'exp': season}
        p['_c0'] = copy.deepcopy(p['contract'])
        p['salaries'] = sorted(
            ({'season': c2['start'] + i, 'amount': a, 'rookie': c2.get('type') == 'rookie'}
             for c2 in cs for i, a in enumerate(c2['amounts'])),
            key=lambda s: s['season'])
        for c2 in cs:
            ee = c2.get('endedEarly')
            end = c2['start'] + len(c2['amounts']) - 1
            if ee and 'tid' in ee and end >= season:
                owed.append({'pid': p['pid'], 'tid': ee['tid'], 'rid': rid,
                             'contract': {'amount': round(_amount_for(c2, season)), 'exp': end}})
                rid += 1
    export['releasedPlayers'] = owed
    export['_contractsV2'] = True
    return export


def to_v2(export):
    """Return a shallow-copied export in the new format. Does not mutate `export`."""
    if not export.get('_contractsV2'):
        return export
    ga = export['gameAttributes']
    season, phase = ga['season'], ga.get('phase', 0)
    released = {(r['pid'], r['tid']): r for r in export.get('releasedPlayers', [])}
    out = {k: v for k, v in export.items() if k not in ('_contractsV2', 'releasedPlayers')}
    players = []
    for p in export['players']:
        q = {k: v for k, v in p.items() if k not in _TMP}
        cs = copy.deepcopy(p.get('contracts') or [])
        cur, c0 = p.get('contract'), p.get('_c0')
        if cur and c0 and p['tid'] >= 0 and cur != c0:
            start = season if phase <= 3 else season + 1
            start = min(start, cur['exp'])
            cs.append({'start': start, 'amounts': [cur['amount']] * (cur['exp'] - start + 1)})
        # sync dead-money markers with export['releasedPlayers']
        for c in cs:
            ee = c.get('endedEarly')
            if ee and 'tid' in ee and (p['pid'], ee['tid']) not in released:
                del ee['tid']
        for (pid, tid) in released:
            if pid == p['pid'] and not any(c.get('endedEarly', {}).get('tid') == tid for c in cs):
                live = [c for c in cs if 'endedEarly' not in c and c.get('amounts')]
                if live:
                    live[-1]['endedEarly'] = {'season': season, 'phase': phase, 'tid': tid}
        q['contracts'] = cs
        players.append(q)
    out['players'] = players
    return out
