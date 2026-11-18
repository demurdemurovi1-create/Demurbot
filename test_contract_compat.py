import copy, contract_compat as cc
def mk():
    return {'gameAttributes': {'season': 2026, 'phase': 0, 'minContract': 750}, 'players': [
      {'pid': 1, 'tid': 3, 'contracts': [{'type': 'rookie', 'start': 2025, 'amounts': [5000, 5500, 6000]}]},
      {'pid': 2, 'tid': -1, 'contracts': [{'start': 2026, 'amounts': [10000, 10000], 'endedEarly': {'season': 2026, 'phase': 0, 'tid': 3}},
                                           {'start': 2026, 'amounts': [4000]}]},
      {'pid': 3, 'tid': 5, 'contracts': [{'start': 2024, 'amounts': [9000], 'endedEarly': {'season': 2025, 'phase': 1}}, {'start': 2026, 'amounts': [8000, 40000]}]}]}
e = cc.upgrade_export(mk())
p = {x['pid']: x for x in e['players']}
assert p[1]['contract'] == {'amount': 5500, 'exp': 2027} and p[1]['salaries'][0]['rookie']
assert p[3]['contract'] == {'amount': 8000, 'exp': 2027}
assert e['releasedPlayers'] == [{'pid': 2, 'tid': 3, 'rid': 0, 'contract': {'amount': 10000, 'exp': 2027}}]
# unchanged roundtrip
orig = mk(); o = cc.to_v2(e)
assert o['players'] == orig['players'] and 'releasedPlayers' not in o and 'contract' not in o['players'][0]
# bot signs player 3 to 12M through 2028, releases player 1
e['players'][2]['contract'] = {'amount': 12000, 'exp': 2028}
e['players'][0]['tid'] = -1; e['releasedPlayers'].append({'pid': 1, 'tid': 3, 'rid': 1, 'contract': {'amount': 5500, 'exp': 2027}})
o = cc.to_v2(e)
assert o['players'][2]['contracts'][-1] == {'start': 2026, 'amounts': [12000]*3}
assert o['players'][0]['contracts'][0]['endedEarly']['tid'] == 3
# bot clears dead money for player 2
e['releasedPlayers'] = [r for r in e['releasedPlayers'] if r['pid'] != 2]
assert 'tid' not in cc.to_v2(e)['players'][1]['contracts'][0]['endedEarly']
# idempotent / legacy no-op
assert cc.upgrade_export(e) is e
leg = {'players': [{'pid': 1, 'contract': {'amount': 1, 'exp': 2}}]}
assert cc.upgrade_export(leg) is leg and cc.to_v2(leg) is leg
print('ok')
