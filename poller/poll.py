"""Scan employer boards and sync Bay Area + US-remote roles into Postgres.
Usage: python3 poll.py [--tier fast|slow|all] [--only "A,B"] [--limit N]
Needs DATABASE_URL. Public endpoints only, 3 workers, no retries.
"""
import sys,csv,json,sqlite3,pathlib,datetime,re,zlib,html,concurrent.futures,os
import psycopg
from psycopg.types.json import Jsonb
from daily_store import collect
from listing_store import ingest
from geo import classify
from scoring import score,load_profile
P=pathlib.Path(__file__).parent
FAST={'greenhouse','ashby','lever'}
SCHEMA=open(P/'schema.sql').read()
MEM_SCHEMA="""CREATE TABLE listings(key TEXT PRIMARY KEY,company TEXT,ats TEXT,req_id TEXT,url TEXT,title TEXT,location TEXT,employer_date TEXT,date_meaning TEXT,first_seen TEXT,last_seen TEXT,status TEXT,relevance_flags TEXT,excluded_reason TEXT,source_endpoint TEXT,raw_json BLOB,first_seen_kind TEXT);CREATE TABLE scans(id TEXT PRIMARY KEY,observed_at TEXT,source_endpoint TEXT,status TEXT,count INTEGER);CREATE TABLE sightings(scan_id TEXT,key TEXT,PRIMARY KEY(scan_id,key));"""

def body_text(j):
  c=j.get('descriptionPlain') or j.get('content') or j.get('description') or j.get('descriptionBodyPlain') or j.get('descriptionBody') or ''
  if not isinstance(c,str):c=json.dumps(c)
  c=html.unescape(c);c=re.sub(r'<[^>]+>',' ',c)
  return html.unescape(re.sub(r'\s+',' ',c)).strip()

def posted_at(j,seen):
  """Employer-stated posting time, or None. Greenhouse first_published, Ashby publishedAt,
  Lever createdAt, Workday 'Posted N Days Ago' (date only, so end of that day)."""
  try:
    if j.get('first_published'):return datetime.datetime.fromisoformat(j['first_published'])
    if j.get('publishedAt'):return datetime.datetime.fromisoformat(j['publishedAt'])
    if j.get('createdAt'):return datetime.datetime.fromtimestamp(j['createdAt']/1000,datetime.timezone.utc)
    po=j.get('postedOn')
    if po:
      m=re.search(r'(\d+)\+?\s*Days? Ago',po)
      if 'Today' in po:return seen
      d=1 if 'Yesterday' in po else int(m.group(1)) if m and '+' not in po else None
      if d is None:return None
      day=(seen.astimezone()-datetime.timedelta(days=d)).replace(hour=23,minute=59,second=0,microsecond=0)
      return min(day,seen)
  except Exception:return None

def apply_url(r,j,url):
  if r['ATS']=='greenhouse' and j.get('id') and r.get('Board slug'):
    # The embed form is the same application page, but it does not redirect to a company's own careers
    # site (Pinterest and others do), so the Application Helper extension can still run on it.
    return f"https://job-boards.greenhouse.io/embed/job_app?for={r['Board slug']}&token={j['id']}"
  if r['ATS'] in('ashby','lever') and j.get('applyUrl'):return j['applyUrl']
  return url

PAY=re.compile(r'\$\s?\d{2,3}(?:,\d{3})?(?:\.\d+)?[kK]?\s*(?:-|–|—|to|and)\s*\$?\s?\d{2,3}(?:,\d{3})?[kK]?')
def snippet(text):
  m=re.search(r"(?:what you(?:'|’)ll do|about the role|the role|responsibilities|about this role|in this role)\s*:?\s*",text,re.I)
  s=text[m.end():] if m and m.end()<len(text)-200 else text
  return s[:300].strip()

def normalize(r,js,seen,enabled,cfgs,prof):
  mem=sqlite3.connect(':memory:');mem.executescript(MEM_SCHEMA)
  ingest(mem,r,js,seen.isoformat(),enabled,cfgs)
  out=[]
  for key,url,title,loc,raw in mem.execute('select key,url,title,location,raw_json from listings'):
    j=json.loads(zlib.decompress(raw))
    c=classify(loc,j.get('workplaceType') or '')
    if not c or not title:continue
    mode,sf=c;body=body_text(j)
    sc,yrs,detail=score(title,body,mode,sf,prof)
    pa=posted_at(j,seen)
    pay=PAY.search(body)
    out.append(dict(key=key,company=r['Company'],ats=r['ATS'],title=title,location=loc,mode=mode,is_sf=sf,
      apply_url=apply_url(r,j,url) or url,posted_at=pa,years_req=yrs,score=sc,score_detail=detail,
      pay=pay.group(0) if pay else None,snippet=snippet(body),description=body[:6000],source_endpoint=r['Public board endpoint']))
  return out

UPSERT="""INSERT INTO listings(key,company,ats,title,location,mode,is_sf,apply_url,posted_at,first_seen,last_seen,baseline,effective_at,closed,years_req,score,score_detail,pay,snippet,description,source_endpoint)
VALUES(%(key)s,%(company)s,%(ats)s,%(title)s,%(location)s,%(mode)s,%(is_sf)s,%(apply_url)s,%(posted_at)s,%(seen)s,%(seen)s,%(baseline)s,%(effective_at)s,false,%(years_req)s,%(score)s,%(score_detail)s,%(pay)s,%(snippet)s,%(description)s,%(source_endpoint)s)
ON CONFLICT(key) DO UPDATE SET title=EXCLUDED.title,location=EXCLUDED.location,mode=EXCLUDED.mode,is_sf=EXCLUDED.is_sf,apply_url=EXCLUDED.apply_url,
 last_seen=EXCLUDED.last_seen,closed=false,years_req=EXCLUDED.years_req,score=EXCLUDED.score,score_detail=EXCLUDED.score_detail,pay=EXCLUDED.pay,snippet=EXCLUDED.snippet,description=EXCLUDED.description"""

def main():
  a=sys.argv[1:]
  tier=a[a.index('--tier')+1] if '--tier' in a else 'all'
  only={x.strip().lower() for x in a[a.index('--only')+1].split(',')} if '--only' in a else None
  limit=int(a[a.index('--limit')+1]) if '--limit' in a else None
  rows=list(csv.DictReader(open(P/'config'/'employers.csv')));cfgs=json.load(open(P/'config'/'reader-configs.json'))
  enabled={r['Company'].lower() for r in rows if r['Daily enabled']=='Yes'}
  blocked={l.strip().lower() for l in open(P/'blocklist.txt') if l.strip() and not l.startswith('#')}
  todo=[r for r in rows if r['Daily enabled']=='Yes' and r['Company'].lower() not in blocked and (not only or r['Company'].lower() in only)
        and (tier=='all' or (tier=='fast')==(r['ATS'] in FAST))]
  if limit:todo=todo[:limit]
  prof=load_profile()
  db=psycopg.connect(os.environ['DATABASE_URL'],autocommit=True,prepare_threshold=None);db.execute(SCHEMA)
  known={e for (e,) in db.execute('select endpoint from boards')}
  started=datetime.datetime.now(datetime.timezone.utc);ok=0;failed=[];total=0
  with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    for r,js,err,seen_s in ex.map(collect,todo):
      ep=r['Public board endpoint'];now=datetime.datetime.now(datetime.timezone.utc)
      if err:
        failed.append((r['Company'],err[:80]))
        db.execute("INSERT INTO boards(endpoint,company,last_scan,last_ok,last_error) VALUES(%s,%s,%s,false,%s) ON CONFLICT(endpoint) DO UPDATE SET last_scan=EXCLUDED.last_scan,last_ok=false,last_error=EXCLUDED.last_error",(ep,r['Company'],now,err[:300]));continue
      seen=datetime.datetime.fromisoformat(seen_s);baseline=ep not in known
      items=normalize(r,js,seen,enabled,cfgs,prof)
      with db.transaction():
        for it in items:
          pa=it['posted_at']
          if pa and pa.tzinfo is None:pa=pa.astimezone()
          if pa and pa>seen+datetime.timedelta(days=1):pa=None
          it.update(seen=seen,baseline=baseline,posted_at=pa,effective_at=pa or (None if baseline else seen),score_detail=Jsonb(it['score_detail']))
        if items:db.cursor().executemany(UPSERT,items)
        keys=[it['key'] for it in items]
        db.execute("UPDATE listings SET closed=true WHERE source_endpoint=%s AND closed=false AND NOT (key = ANY(%s))",(ep,keys))
        db.execute("INSERT INTO boards(endpoint,company,first_scan,last_scan,last_ok,last_error,listing_count) VALUES(%s,%s,%s,%s,true,null,%s) ON CONFLICT(endpoint) DO UPDATE SET last_scan=EXCLUDED.last_scan,last_ok=true,last_error=null,listing_count=EXCLUDED.listing_count",(ep,r['Company'],seen,seen,len(items)))
      ok+=1;total+=len(items)
  db.execute('INSERT INTO poll_runs(started_at,finished_at,tier,boards_ok,boards_failed,listings_seen) VALUES(%s,now(),%s,%s,%s,%s)',(started,tier,ok,len(failed),total))
  print(f'tier={tier} scanned {ok}/{len(todo)} boards, {total} Bay/remote roles; failed: {failed[:12]}{"..." if len(failed)>12 else ""}')

if __name__=='__main__':main()
