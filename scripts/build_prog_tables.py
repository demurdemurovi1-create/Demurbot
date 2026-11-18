"""Build summaries.txt and result.txt (progression tables) from a BBGM export.

Usage: python scripts/build_prog_tables.py path/to/export.json[.gz]

Both files are derived from how ratings actually changed from one season to the
next in the export (age = age during the season the change starts from):
  summaries.txt - {age: {rating: mean change}}            (used by -reprog, league-wide)
  result.txt    - one JSON line {age: [[14 changes], ...]} (used by -simprogs and -reprog <player>)
Rating order in result.txt: stre spd jmp endu ins dnk ft fg tp oiq diq drb pss reb
"""
import gzip, json, random, sys, collections

ORDER = ['stre', 'spd', 'jmp', 'endu', 'ins', 'dnk', 'ft', 'fg', 'tp', 'oiq', 'diq', 'drb', 'pss', 'reb']
MIN_AGE, MAX_AGE, PER_AGE = 18, 37, 600

path = sys.argv[1]
opener = gzip.open if path.endswith('.gz') else open
with opener(path, 'rt') as f:
    export = json.load(f)

by_age = collections.defaultdict(list)
for p in export['players']:
    r = p['ratings']
    for a, b in zip(r, r[1:]):
        if b['season'] == a['season'] + 1 and all(k in a and k in b for k in ORDER):
            age = min(max(a['season'] - p['born']['year'], MIN_AGE), MAX_AGE)
            by_age[age].append([b[k] - a[k] for k in ORDER])

random.seed(1)
summaries, result = {}, {}
for age in range(MIN_AGE, MAX_AGE + 1):
    rows = by_age[age]
    assert len(rows) >= 20, f'not enough data for age {age}'
    summaries[str(age)] = {k: round(sum(r[i] for r in rows) / len(rows), 4) for i, k in enumerate(ORDER)}
    result[str(age)] = random.sample(rows, min(PER_AGE, len(rows)))

with open('summaries.txt', 'w') as f:
    json.dump(summaries, f)
with open('result.txt', 'w') as f:
    f.write(json.dumps(result) + '\n')
print({a: len(v) for a, v in by_age.items() if MIN_AGE <= a <= MAX_AGE})
