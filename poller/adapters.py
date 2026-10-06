"""Unauthenticated employer-published job feeds only. Stop on throttling/challenges.
No applications, auth cookies, LinkedIn endpoints, or paid services.
"""
import urllib.request,urllib.error,urllib.parse,json,time,html,re,pathlib
HEAD={'User-Agent':'JobResearch/1.0','Accept':'application/json','Content-Type':'application/json'}
def request(url,body=None):
 req=urllib.request.Request(url,data=json.dumps(body).encode() if body is not None else None,headers=HEAD)
 try:
  with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
 except urllib.error.HTTPError as e:
  if e.code in (403,429):raise RuntimeError(f'STOP HTTP {e.code} at {url}') from e
  raise

def fetch(config):
 a=config['ats'];u=config['endpoint'];out=[];expected=None;offset=0
 if a=='workable':
  d=request(u)
  if not isinstance(d.get('jobs'),list):raise ValueError('Workable widget missing jobs')
  jobs=d['jobs'];verify=request(config['verify_endpoint'],{'query':''});allv=verify.get('results',[]);expected=verify.get('total');token=verify.get('nextPage');tokens=set()
  while token:
   if token in tokens:raise ValueError('Workable repeated pagination token')
   tokens.add(token);verify=request(config['verify_endpoint'],{'query':'','token':token});allv.extend(verify.get('results',[]));token=verify.get('nextPage')
   if len(tokens)>200:raise ValueError('Workable pagination bound')
  a_ids=list(dict.fromkeys(j['shortcode'] for j in jobs));b_ids=[j['shortcode'] for j in allv]
  if len(allv)!=expected or len(set(a_ids))!=len(a_ids) or len(set(b_ids))!=len(b_ids) or set(a_ids)!=set(b_ids):raise ValueError('Workable widget/v3 mismatch')
  merged={}
  for j in jobs:
   key=j['shortcode']
   if key in merged:
    old=merged[key]
    if old['title']!=j['title']:raise ValueError('Workable conflicting location variants')
    old['locations'].extend(j.get('locations',[]))
   else:merged[key]=dict(j,locations=list(j.get('locations',[])))
  out=[]
  for j in merged.values():
   x=dict(j);x['id']=j['shortcode'];x['location']={'name':'; '.join(dict.fromkeys(', '.join(filter(None,[l.get('city'),l.get('region'),l.get('country')])) for l in j.get('locations',[]))) or ', '.join(filter(None,[j.get('city'),j.get('state'),j.get('country')]))};x['isRemote']=j.get('telecommuting',False);x['postedDate']=j.get('published_on','');out.append(x)
  return out,{'returned':len(out),'total':expected,'complete':True}
 if a=='gem':
  d=request(u)
  if not isinstance(d,list):raise ValueError('Gem non-list response')
  return d,{'returned':len(d),'total':len(d),'complete':True}
 while True:
  if a=='workday':
   d=request(u,{'appliedFacets':{},'limit':20,'offset':offset,'searchText':''});jobs=d.get('jobPostings',[]);expected=d.get('total') if offset==0 else expected;step=20
  elif a=='rippling':
   d=request(u+'?pageSize=200&page='+str(offset));jobs=d.get('items',[]);expected=d.get('totalItems');step=1
  elif a=='smartrecruiters':
   d=request(u+'?limit=100&offset='+str(offset));jobs=d.get('content',[]);expected=d.get('totalFound');step=100
  else:raise ValueError('unsupported '+a)
  if expected is None:raise ValueError('Missing total field')
  out.extend(jobs)
  if len(out)>=expected:break
  if not jobs:raise ValueError(f'Incomplete pagination: {len(out)} of {expected}')
  offset+=step;time.sleep(.18)
  if offset>20000:raise ValueError('Pagination bound exceeded')
 ids=[str(j.get('externalPath') or j.get('id')) for j in out]
 if len(ids)!=len(set(ids)):raise ValueError('Duplicate page results')
 return out,{'returned':len(out),'total':expected,'complete':len(out)==expected}

def detail(config,job):
 a=config['ats'];u=config['endpoint']
 if a=='workday':return request(u.removesuffix('/jobs')+job['externalPath'])
 if a=='smartrecruiters':return request(u+'/'+job['id'])
 if a=='rippling':return request(u+'/'+job['id'])
 return job
if __name__=='__main__':
 import concurrent.futures,sys
 P=pathlib.Path(__file__).parent;(P/'boards').mkdir(exist_ok=True);cs=json.load(open(P/'adapter-candidates.json'))
 # Student-only board isn't another employer. Broken JS suffix is not a validated route.
 cs=[c for c in cs if 'Agilent_Student' not in c['board'] and "'" not in c['board']]
 def run(c):
  r=dict(c);start=time.monotonic()
  try:
   jobs,stats=fetch(c);r.update(stats,status='Active custom board' if jobs else 'Empty custom board');key=re.sub('[^a-zA-Z0-9_-]','_',c['company']+'-'+c['ats']);json.dump(jobs,open(P/'boards'/(key+'.json'),'w'));r['file']=str(P/'boards'/(key+'.json'));r['sample']=next((j.get('absolute_url') or j.get('url') or j.get('ref') for j in jobs if j.get('absolute_url') or j.get('url') or j.get('ref')),'')
  except Exception as e:r.update(status=str(e),returned=0,complete=False)
  r['seconds']=round(time.monotonic()-start,2);return r
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:out=list(ex.map(run,cs))
 json.dump(out,open(P/'adapter-results.json','w'),indent=2)
 for r in out:print(r['company'],r['ats'],r['status'],r['returned'],r.get('complete'))
 print('total',len(out),'complete',sum(r['complete'] for r in out),'postings',sum(r['returned'] for r in out))
