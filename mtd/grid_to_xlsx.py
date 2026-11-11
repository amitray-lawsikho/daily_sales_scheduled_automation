#!/usr/bin/env python3
"""Rebuild a minimal workbook (BASE DATA + Team Members) from a Google Sheets connector
`get_spreadsheet` response (includeGridData, fields = effectiveValue).

Fallback for when the full-workbook xlsx export is too large for the Drive connector.
effectiveValue carries the real cell values (numbers unformatted, text as text), so the result
reads exactly like the xlsx export: text-typed fees stay text, numbers stay numbers. Date-typed
cells come back as Sheets serial numbers and are converted to datetimes for the `Date` column.

Usage: python3 mtd/grid_to_xlsx.py <get_spreadsheet result .json/.txt> <out.xlsx>
"""
import json, sys, datetime as dt
import pandas as pd

EPOCH = dt.datetime(1899, 12, 30)
DATE_COLS = {'BASE DATA': ['Date']}


def cell(v):
    ev = (v or {}).get('effectiveValue')
    if not ev:
        return None
    for k in ('numberValue', 'stringValue', 'boolValue'):
        if k in ev:
            return ev[k]
    return None  # errorValue -> blank


def col_letter(i):
    s = ''
    i += 1
    while i:
        i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s


def build(sheet):
    """Merge every range block of one sheet into {col_index: [values by row]}; row 0 = header."""
    cols, maxrow = {}, 0
    for blk in sheet.get('data', []):
        r0, c0 = blk.get('startRow', 0), blk.get('startColumn', 0)
        for ri, row in enumerate(blk.get('rowData', [])):
            for ci, v in enumerate(row.get('values', [])):
                val = cell(v)
                if val is None:
                    continue
                cols.setdefault(c0 + ci, {})[r0 + ri] = val
                maxrow = max(maxrow, r0 + ri)
    if not cols:
        raise SystemExit(f"sheet {sheet['properties']['title']}: no data returned")
    header = {c: str(v.get(0, '')).strip() for c, v in cols.items()}
    data = {}
    for c in sorted(cols):
        h = header[c] or f'col_{col_letter(c)}'
        rows = cols[c]
        data[h] = [rows.get(r) for r in range(1, maxrow + 1)]
        if all(r == 0 for r in rows) and h in data:   # header-only column (from the A1:AF1 header range)
            data[h] = [None] * maxrow
    df = pd.DataFrame(data)
    df = df.dropna(how='all')
    return df


def main():
    src, out = sys.argv[1], sys.argv[2]
    d = json.load(open(src))
    if 'sheets' not in d and isinstance(d.get('content'), dict):   # newer connector wraps the response
        d = d['content']
    frames = {}
    for sh in d['sheets']:
        t = sh['properties']['title']
        df = build(sh)
        for c in DATE_COLS.get(t, []):
            if c in df:
                df[c] = df[c].map(lambda v: EPOCH + dt.timedelta(days=v) if isinstance(v, (int, float)) and v == v else v)
        frames[t] = df
    for need in ('BASE DATA', 'Team Members'):
        if need not in frames:
            raise SystemExit(f'missing sheet {need} in response')
    bd = frames['BASE DATA']
    must = ['Date', 'Fee paid', 'Transaction ID', 'Enrollment', 'Team Name', 'Course']
    miss = [c for c in must if c not in bd.columns] + \
           ([] if any(' '.join(c.split()) == 'Caller name (for ops) for enrollment link circulation' for c in bd.columns) else ['Caller'])
    if miss:
        raise SystemExit(f'BASE DATA columns not fetched (header moved?): {miss} — re-read row 1 and fetch the right letters')
    with pd.ExcelWriter(out) as w:
        for t, df in frames.items():
            df.to_excel(w, sheet_name=t, index=False)
    print(json.dumps({t: len(df) for t, df in frames.items()}))


if __name__ == '__main__':
    main()
