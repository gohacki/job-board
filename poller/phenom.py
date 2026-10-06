import pathlib,json,re,html,urllib.request,time,concurrent.futures
P=pathlib.Path(__file__).parent

def config(htmlpath):
 s=html.unescape(pathlib.Path(htmlpath).read_text());m=re.search(r'phApp\s*=\s*phApp\s*\|\|\s*(\{.*?\});',s,re.S);return json.loads(m[1])
def fetch(cfg):
 u=cfg['widgetApiEndpoint'];out=[];offset=0;total=None
 while True:
  p={'ddoKey':'refineSearch','refNum':cfg['refNum'],'locale':cfg['locale'],'deviceType':'desktop','country':cfg['country'],'pageName':'search-results','from':offset,'size':500,'jobs':True,'all_fields':[],'selected_fields':{},'sortBy':'','keywords':''}
  d=json.load(urllib.request.urlopen(urllib.request.Request(u,data=json.dumps(p).encode(),headers={'User-Agent':'JobResearch/1.0','Content-Type':'application/json','Referer':cfg['baseUrl']}),timeout=25));rs=d['refineSearch']
  if rs.get('status')!=200:raise ValueError('non-200')
  js=rs['data']['jobs'];total=rs['totalHits'] if total is None else total;out+=js
  if len(out)>=total:break
  if not js:raise ValueError('incomplete empty page')
  offset+=len(js);time.sleep(.3)
  if offset>10000:raise ValueError('pagination bound')
 ids=[j['jobSeqNo'] for j in out]
 if len(set(ids))!=len(ids) or len(out)!=total:raise ValueError(f'duplicate/count mismatch: fetched={len(out)} unique={len(set(ids))} expected={total}')
 return out
if __name__=='__main__':
 routes=json.load(open(P/'routes.json'))
 def run(r):
  r=dict(r,ats='phenom');cfg=config(r['file']);r['config']=cfg;r['endpoint']=cfg['widgetApiEndpoint']
  try:
   js=fetch(cfg);r.update(count=len(js),complete=True,status='Active custom board' if js else 'Empty custom board');r['jobs_file']=str(P/(re.sub('[^a-zA-Z0-9]','',r['company'])+'-phenom-jobs.json'));json.dump(js,open(r['jobs_file'],'w'));r['sample']=js[0].get('applyUrl','') if js else ''
  except Exception as e:r.update(count=0,complete=False,status=str(e))
  return r
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:out=list(ex.map(run,[r for r in routes if 'phenom' in r['types']]))
 json.dump(out,open(P/'phenom-results.json','w'),indent=2)
 for r in out:print(r['company'],r['count'],r['status'],r['complete'])
