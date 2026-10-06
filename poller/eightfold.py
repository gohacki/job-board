import json,pathlib,re,urllib.parse,urllib.request,html,time,concurrent.futures
P=pathlib.Path(__file__).parent

def fetch(base,domain):
 alljobs=[];start=0;total=None
 while True:
  u=base+'/api/pcsx/search?'+urllib.parse.urlencode({'domain':domain,'query':'','location':'','start':start})
  d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'JobResearch/1.0'}),timeout=20))
  if d.get('status')!=200:raise ValueError('non-200 response status')
  data=d['data'];jobs=data['positions'];total=data['count'] if total is None else total
  alljobs.extend(jobs)
  if len(alljobs)>=total:break
  if not jobs:raise ValueError(f'Incomplete pagination {len(alljobs)}/{total}')
  start+=len(jobs);time.sleep(.15)
 ids=[j['id'] for j in alljobs]
 if len(set(ids))!=len(ids):raise ValueError('duplicate IDs')
 if len(alljobs)!=total:raise ValueError('count mismatch')
 return alljobs,total
if __name__=='__main__':
 routes=json.load(open(P/'routes.json'));out=[]
 def run(r):
  s=pathlib.Path(r['file']).read_text();m=re.search(r'<code id="pcsx-data"[^>]*>(.*?)</code>',s,re.S);cfg=json.loads(html.unescape(m[1]));domain=cfg['domain'];q=urllib.parse.urlparse(r['careers']);base=f'{q.scheme}://{q.netloc}';r=dict(r,ats='eightfold',domain=domain,base=base)
  try:
   js,total=fetch(base,domain);r.update(count=total,status='Active custom board',complete=True);r['jobs_file']=str(P/(re.sub('[^a-zA-Z0-9]','',r['company'])+'-jobs.json'));json.dump(js,open(r['jobs_file'],'w'));r['sample']=base+js[0]['positionUrl'] if js else ''
  except Exception as e:r.update(count=0,status=str(e),complete=False)
  return r
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:out=list(ex.map(run,[r for r in routes if 'eightfold' in r['types']]))
 json.dump(out,open(P/'eightfold-results.json','w'),indent=2)
 for r in out:print(r['company'],r['count'],r['status'],r['complete'])
