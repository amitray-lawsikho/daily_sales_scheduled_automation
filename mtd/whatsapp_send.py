#!/usr/bin/env python3
"""Send the MTD report PDF on WhatsApp (official WhatsApp Cloud API) to numbers and groups.

Flow per run:
  1. upload the PDF once:  POST /{phone_number_id}/media  (multipart, type=application/pdf) -> media id
  2. for every enabled recipient / group, send the approved template `mtd_daily_report`
     (document header = the PDF, body = headline numbers):
       POST /{phone_number_id}/messages
       {"messaging_product": "whatsapp", "recipient_type": "individual"|"group", "to": <number|group id>,
        "type": "template", "template": {...}}
  3. append message ids / errors to reports/YYYY-MM/whatsapp_log.json

Auth: the access token is NOT stored in the repo. It is saved as a network secret for
graph.facebook.com on the Claude environment; the proxy injects it into the Authorization
header, so this script sends a placeholder bearer value.

Usage:
  python3 mtd/whatsapp_send.py --summary "reports/2026-11/summary Nov 1-9.json" [--dry-run]
  python3 mtd/whatsapp_send.py --test-to 91XXXXXXXXXX --summary ...   (one number only)
"""
import argparse, json, os, sys, datetime as dt, mimetypes, uuid, urllib.request, urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(REPO, 'config', 'whatsapp.json')
GRAPH = 'https://graph.facebook.com'
PLACEHOLDER = 'Bearer injected-by-proxy'   # real token injected by the Claude network proxy


def lakh(v):
    return f"{v / 1e5:,.2f} lakh"


def inr(v):
    """Indian digit grouping: 1557724 -> 15,57,724"""
    s = f"{abs(v):.0f}"
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        s = ','.join(parts) + ',' + tail
    return ('-' if v < 0 else '') + s


def body_params(summ, seg):
    x = summ['segments'][seg]
    chg = 'n/a' if x['vs_prev_pct'] is None else f"{x['vs_prev_pct']:+.1f}% vs {summ['prev_period']}"
    ach = 'no target loaded' if x['achievement_pct'] is None else f"{x['achievement_pct']}%"
    vals = [summ['period'], seg, f"Rs {inr(x['revenue'])}", chg, ach, f"{x['enrollments']} (prev {x['prev_enrollments']})"]
    return [{'type': 'text', 'text': v} for v in vals]


def http(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers={'Authorization': PLACEHOLDER, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b'{}')
        except Exception:
            return e.code, {'error': str(e)}


def upload_pdf(cfg, path):
    boundary = uuid.uuid4().hex
    fn = os.path.basename(path)
    parts = []
    for k, v in (('messaging_product', 'whatsapp'), ('type', 'application/pdf')):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{fn}"\r\n'
                 f'Content-Type: application/pdf\r\n\r\n'.encode() + open(path, 'rb').read() + b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    st, js = http('POST', f"{GRAPH}/{cfg['api_version']}/{cfg['phone_number_id']}/media", b''.join(parts),
                  {'Content-Type': f'multipart/form-data; boundary={boundary}'})
    if st != 200 or 'id' not in js:
        raise SystemExit(f'media upload failed ({st}): {js}')
    return js['id']


def payload(cfg, to, kind, media_id, filename, params):
    return {'messaging_product': 'whatsapp', 'recipient_type': kind, 'to': to, 'type': 'template',
            'template': {'name': cfg['template']['name'], 'language': {'code': cfg['template']['language']},
                         'components': [
                             {'type': 'header', 'parameters': [{'type': 'document', 'document': {'id': media_id, 'filename': filename}}]},
                             {'type': 'body', 'parameters': params}]}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--summary', required=True, help='reports/YYYY-MM/summary <Mon> 1-N.json written by run_mtd.py')
    ap.add_argument('--dry-run', action='store_true', help='print the requests, send nothing')
    ap.add_argument('--test-to', help='send only to this number (ignores the recipient list)')
    a = ap.parse_args()
    cfg = json.load(open(CFG))
    if not cfg.get('enabled') and not (a.dry_run or a.test_to):
        print(json.dumps({'status': 'DISABLED', 'message': 'WhatsApp delivery is not enabled in config/whatsapp.json'})); return 0
    summ = json.load(open(a.summary if os.path.isabs(a.summary) else os.path.join(REPO, a.summary)))
    targets = ([('individual', a.test_to, 'test')] if a.test_to else
               [('individual', r['number'], r['name']) for r in cfg['recipients'] if r.get('enabled') and r.get('number')] +
               [('group', g['group_id'], g['name']) for g in cfg['groups'] if g.get('enabled') and g.get('group_id')])
    if not targets:
        print(json.dumps({'status': 'NO_RECIPIENTS'})); return 0
    if not a.dry_run and not cfg.get('phone_number_id'):
        sys.exit('phone_number_id missing in config/whatsapp.json')
    log, out = [], []
    for seg in cfg.get('segments', ['Team Uzair']):
        if seg not in summ['segments']:
            continue
        pdf = os.path.join(REPO, summ['segments'][seg]['pdf']); fn = os.path.basename(pdf)
        media_id = '<media-id>' if a.dry_run else upload_pdf(cfg, pdf)
        params = body_params(summ, seg)
        for kind, to, name in targets:
            p = payload(cfg, to, kind, media_id, fn, params)
            if a.dry_run:
                out.append(p); continue
            st, js = http('POST', f"{GRAPH}/{cfg['api_version']}/{cfg['phone_number_id']}/messages", json.dumps(p).encode(),
                          {'Content-Type': 'application/json'})
            ok = st == 200 and js.get('messages')
            log.append(dict(time=dt.datetime.utcnow().isoformat() + 'Z', segment=seg, to_name=name, kind=kind, status=st,
                            message_id=(js.get('messages') or [{}])[0].get('id'), error=None if ok else js.get('error', js)))
    if a.dry_run:
        print(json.dumps(out, indent=2, ensure_ascii=False)); return 0
    lp = os.path.join(os.path.dirname(os.path.join(REPO, summ['segments'][cfg['segments'][0]]['pdf'])), 'whatsapp_log.json')
    old = json.load(open(lp)) if os.path.exists(lp) else []
    json.dump(old + log, open(lp, 'w'), indent=2)
    bad = [l for l in log if l['error']]
    # never print phone numbers in the summary line
    print(json.dumps({'status': 'OK' if not bad else 'PARTIAL', 'sent': len(log) - len(bad), 'failed': len(bad),
                      'errors': [{'to': l['to_name'], 'error': l['error']} for l in bad]}, indent=2))
    return 0 if not bad else 6


if __name__ == '__main__':
    sys.exit(main())
