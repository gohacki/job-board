"""Public feed collection and durable listing reconciliation. No sends/applications."""
import pathlib,json,sqlite3,datetime,urllib.request,concurrent.futures,hashlib,sys
from listing_store import ingest
from adapters import fetch
from eightfold import fetch as eightfold
from phenom import fetch as phenom
from publichtml import fetch as publichtml
P=pathlib.Path(__file__).parent
configs=json.load(open(P/'config'/'reader-configs.json'))
def collect(r):
 try:
  a=r['ATS'];cfg=next((c for c in configs if c['company']==r['Company'] or c.get('existing_company')==r['Company']),None)
  if a in ['workday','gem','rippling','smartrecruiters','workable']:
   if not cfg:raise ValueError('No verified reader config')
   js,stats=fetch(cfg)
   if not stats['complete']:raise ValueError('incomplete reader')
  elif a=='eightfold':js,_=eightfold(cfg['base'],cfg['domain'])
  elif a=='phenom':js=phenom(cfg['config'])
  elif a=='publichtml':js=publichtml(cfg)
  else:
   d=json.load(urllib.request.urlopen(urllib.request.Request(r['Public board endpoint'],headers={'User-Agent':'JobResearch/1.0'}),timeout=25));js=d if isinstance(d,list) else d.get('jobs')
   if not isinstance(js,list):raise ValueError('missing jobs list')
  ids=[str(j.get('id') or j.get('jobId') or j.get('externalPath') or j.get('url') or j.get('jobUrl')) for j in js]
  if len(set(ids))!=len(ids):raise ValueError('duplicate requisitions/incomplete pagination')
  return r,js,None,datetime.datetime.now(datetime.timezone.utc).isoformat()
 except Exception as e:return r,None,str(e),datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(rows,dbpath):
 db=sqlite3.connect(dbpath);enabled={r['Company'].lower() for r in rows if r['Daily enabled']=='Yes'};report=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
  for r,js,error,seen in ex.map(collect,[r for r in rows if r['Daily enabled']=='Yes']):
   if error:
    sid=hashlib.sha256((r['Public board endpoint']+seen).encode()).hexdigest();db.execute('INSERT OR REPLACE INTO scans VALUES(?,?,?,?,?)',(sid,seen,r['Public board endpoint'],'FAILED: '+error,0));db.commit();report.append({'company':r['Company'],'status':'failed','error':error});continue
   ingest(db,r,js,seen,enabled,configs);report.append({'company':r['Company'],'status':'complete','count':len(js)})
 db.close();json.dump(report,open(P/'daily-scan-report.json','w'),indent=2)
if __name__=='__main__':run(json.load(open(sys.argv[1])),sys.argv[2])
