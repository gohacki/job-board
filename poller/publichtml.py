"""Public employer-page readers. No submissions; stop on throttling/challenges."""
import urllib.request,re
from bs4 import BeautifulSoup

def fetch(cfg):
 if cfg['kind']=='pinpoint-postings':
  import json
  from urllib.parse import urljoin
  with urllib.request.urlopen(cfg['endpoint'],timeout=25) as r:h=r.read().decode('utf-8')
  own=BeautifulSoup(h,'html.parser');scopes=[json.loads(x.text) for x in own.select('script[type="application/json"]') if '\"url\":\"/postings.json\"' in x.text]
  if len(scopes)!=1 or scopes[0].get('showPagination') is not False:raise ValueError('Pinpoint scope/pagination changed')
  scope=scopes[0]
  with urllib.request.urlopen(urljoin(cfg['endpoint'],scope['url']),timeout=25) as r:d=json.load(r)
  if not isinstance(d.get('data'),list):raise ValueError('Pinpoint structure changed')
  jobs=[]
  for j in d['data']:
   if not j.get('id') or not j.get('url','').startswith(cfg['endpoint'].rstrip('/')+'/en/postings/') or not j.get('description'):raise ValueError('Pinpoint posting fields changed')
   excluded=False
   for f in scope.get('excludeFilters',[]):
    k=f['attribute'].removeprefix('exclude_').removesuffix('_id');obj=j.get(k) or j.get('job',{}).get(k) or {};excluded |= str(obj.get('id')) in {str(v) for v in f['values']}
   if excluded:continue
   k=dict(j);k['description']=' '.join(j.get(v) or '' for v in ['description','key_responsibilities','skills_knowledge_expertise','benefits']);k['location']=j['location'].get('name','');k['workplaceType']='Remote' if j.get('workplace_type')=='remote' else j.get('workplace_type_text','');jobs.append(k)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Pinpoint duplicate IDs')
  return jobs
 if cfg['kind'] in ['recruitee-offers','recruitee-direct-offers']:
  import json
  with urllib.request.urlopen(urllib.request.Request(cfg['endpoint'],headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:html=r.read().decode('utf-8')
  own=BeautifulSoup(html,'html.parser')
  slugs={a['href'].split('/o/')[1].split('/')[0] for a in own.select('a[href]') if a['href'].startswith(cfg['origin']+'/l/en/o/')}
  with urllib.request.urlopen(urllib.request.Request(cfg['feed'],headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:data=json.load(r)
  if not isinstance(data.get('offers'),list):raise ValueError('Recruitee offers structure changed')
  if cfg['kind']=='recruitee-offers' and (not slugs or slugs!={j.get('slug') for j in data['offers']}):raise ValueError('Recruitee own/full-offers mismatch')
  if cfg['kind']=='recruitee-direct-offers' and ('const apiURL = "'+cfg['feed']+'";') not in html:raise ValueError('Own direct API binding changed')
  jobs=[]
  for j in data['offers']:
   if not j.get('id') or j.get('status')!='published' or not j.get('careers_url','').startswith(cfg['origin']+'/o/'):raise ValueError('Recruitee structure/status changed')
   en=j.get('translations',{}).get('en') or j
   k=dict(j);k['title']=en.get('title') or j['title'];k['url']=j['careers_url'];k['description']=en.get('description','')+' '+en.get('requirements','');k['publishedAt']=j.get('published_at','');k['location']='; '.join(' / '.join(str(x[v]) for v in ['city','country'] if x.get(v)) for x in j.get('locations',[]))
   if j.get('remote') is True:k['location']='Remote - '+k['location']
   jobs.append(k)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Recruitee duplicate IDs')
  return jobs
 if cfg['kind']=='greenhouse-multiboard':
  import json
  out=[]
  for endpoint in cfg['feeds']:
   with urllib.request.urlopen(urllib.request.Request(endpoint,headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:d=json.load(r)
   if not isinstance(d.get('jobs'),list):raise ValueError('GH multiboard missing jobs')
   for j in d['jobs']:
    if not j.get('id') or not j.get('absolute_url') or not j.get('title'):raise ValueError('GH multiboard structure changed')
   out.extend(d['jobs'])
  if len({j['id'] for j in out})!=len(out):raise ValueError('GH multiboard duplicate ID needs reconciliation')
  return out
 if cfg['kind']=='sinch-json':
  import json
  with urllib.request.urlopen(urllib.request.Request(cfg['endpoint'],headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:raw=r.read()
  import gzip
  data=json.loads((gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw).decode('utf-8'))
  if not isinstance(data,list) or not data:raise ValueError('Sinch nonempty list structure absent')
  jobs=[]
  for j in data:
   if not j.get('_id') or not j.get('url') or j.get('externalPublishedJobStatus')!='ORA_POSTED' or j.get('status')!='Posted':raise ValueError('Sinch job structure/status changed')
   loc=j['location'];display=loc.get('locationStr','')
   if loc.get('country') and loc['country'] not in display:display+='; '+loc['country']
   if loc.get('workplaceType')=='REMOTE':display='Remote - '+display
   k=dict(j);k['rawLocation']=loc;k['id']=str(j['_id']);k['location']=display; k['description']='';jobs.append(k)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Sinch duplicate IDs')
  return jobs
 req=urllib.request.Request(cfg['endpoint'],headers={'User-Agent':'JobResearch/1.0'})
 with urllib.request.urlopen(req,timeout=25) as r:
  if r.status!=200:raise ValueError('Non-successful employer page')
  html=r.read().decode('utf-8')
 s=BeautifulSoup(html,'html.parser');jobs=[]
 if cfg['kind']=='futurehouse-shared-ashby':
  import json,gzip
  links={a['href'].split('/')[-1] for a in s.select('a[href]') if a['href'].startswith('https://jobs.ashbyhq.com/Edison%20Scientific/')}
  if not links:raise ValueError('FutureHouse own roles absent')
  with urllib.request.urlopen(urllib.request.Request(cfg['feed'],headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:raw=r.read()
  data=json.loads((gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw).decode('utf-8'))
  jobs=[j for j in data['jobs'] if j.get('department')=='FutureHouse' and j.get('isListed') is True]
  if {j['id'] for j in jobs}!=links or len(jobs)!=len(links):raise ValueError('FutureHouse shared tenant own-ID/department mismatch')
 elif cfg['kind'] in ['plos-eu-html','greenhouse-eu-html']:
  import json,time
  m=re.search(r'\b(\d+) jobs?\b',s.get_text(' ',strip=True))
  cards=s.select('tr.job-post')
  if not m or int(m[1])!=len(cards):raise ValueError('PLOS count incomplete')
  for tr in cards:
   a=tr.select_one('a[href]');ps=a.select('p') if a else []
   if len(ps)!=2 or not a['href'].startswith(cfg['endpoint']+'/jobs/'):raise ValueError('PLOS card structure changed')
   u=a['href']
   if cfg.get('cards_only') is True:
    jobs.append({'id':u.rsplit('/',1)[-1],'title':ps[0].get_text(' ',strip=True),'location':ps[1].get_text(' ',strip=True),'url':u,'description':str(tr)})
    continue
   with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:h=r.read().decode('utf-8')
   detail=BeautifulSoup(h,'html.parser');body=detail.select_one('#content') or detail.select_one('.job__description')
   if not body:raise ValueError('PLOS description absent')
   jobs.append({'id':u.rsplit('/',1)[-1],'title':ps[0].get_text(' ',strip=True),'location':ps[1].get_text(' ',strip=True),'url':u,'description':body.get_text(' ',strip=True)})
   time.sleep(.15)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('PLOS duplicate')
 elif cfg['kind']=='teamwork-table':
  import time
  from urllib.parse import urljoin
  cards=s.select('tr.opportunities-table-row')
  if not cards or s.select('a[rel=next]'):raise ValueError('Teamwork cards absent/pagination unresolved')
  for tr in cards:
   a=tr.select_one('td.opportunities-table-row__title a[href]');loc=tr.select_one('td.opportunities-table-row__location')
   if not a or not loc or not re.fullmatch(r'/careers/[a-z0-9]+\.[a-z0-9]+/',a['href']):raise ValueError('Teamwork card structure changed')
   u=urljoin(cfg['endpoint'],a['href'])
   with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:h=r.read().decode('utf-8')
   detail=BeautifulSoup(h,'html.parser');body=detail.select_one('section.careers-single-content')
   heading=detail.select_one('h1.careers-single-header__title')
   if not body or not heading or heading.get_text(' ',strip=True)!=a.get_text(' ',strip=True):raise ValueError('Teamwork detail title/body mismatch')
   jobs.append({'id':a['href'].strip('/').split('/')[-1],'title':a.get_text(' ',strip=True),'location':loc.get_text(' ',strip=True),'url':u,'description':body.get_text(' ',strip=True)})
   time.sleep(.2)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Teamwork duplicate IDs')
 elif cfg['kind']=='trinethire-table':
  import time
  from urllib.parse import urljoin
  cards=s.select('tbody.sortable tr.job')
  if not cards and 'no current job' not in s.get_text(' ',strip=True).lower():raise ValueError('TriNet explicit table absent')
  if s.select('.pagination a[href],a[rel=next]'):raise ValueError('TriNet pagination needs implementation')
  for tr in cards:
   a=tr.select_one('a[href]');loc=tr.select_one('td.location')
   if not a or not loc or not a['href'].startswith(cfg['path_prefix']):raise ValueError('TriNet card structure changed')
   u=urljoin(cfg['endpoint'],a['href'])
   with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:h=r.read().decode('utf-8')
   detail=BeautifulSoup(h,'html.parser');body=detail.select_one('.job-descr.content')
   if not body:raise ValueError('TriNet job description absent')
   jobs.append({'id':u.rsplit('/',1)[-1].split('-')[0],'title':a.get_text(' ',strip=True),'location':loc.get_text(' ',strip=True),'url':u,'description':body.get_text(' ',strip=True)})
   time.sleep(.15)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('TriNet duplicate IDs')
 elif cfg['kind']=='miro-nextdata':
  import json,time
  node=s.select_one('script#__NEXT_DATA__')
  if not node:raise ValueError('Miro jobs data absent')
  d=json.loads(node.string)
  if d.get('page')!='/open-positions':raise ValueError('Miro route changed')
  rawjobs=d['props']['pageProps']['jobs']
  if not isinstance(rawjobs,list) or not rawjobs:raise ValueError('Miro explicit empty state needs verification')
  ownlinks={a['href'].strip('/').split('/')[-1]:a['href'] for a in s.select('a[href^="/careers/vacancy/"]')}
  if not ownlinks or not set(ownlinks).issubset({str(j['id']) for j in rawjobs}):raise ValueError('Miro own link/data mismatch')
  for j in rawjobs:
   if not j.get('id') or not j.get('title') or not j.get('location'):raise ValueError('Miro job structure changed')
   url=cfg['origin']+'/careers/vacancy/'+str(j['id'])+'/'
   with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:h=r.read().decode('utf-8')
   node=BeautifulSoup(h,'html.parser').select_one('script#__NEXT_DATA__')
   if not node:raise ValueError('Miro role data absent')
   detail=json.loads(node.string)['props']['pageProps']
   if detail.get('jobNotFound') or str(detail.get('slug'))!=str(j['id']) or detail.get('title','').strip()!=j['title'].strip() or detail.get('location')!=', '.join(re.sub(r',\s*[A-Za-z]{2}$','',x.strip()) for x in j['location'].split(';')):raise ValueError('Miro role mismatch')
   k=dict(j);k['url']=url;k['description']=detail['content'];k['reqId']=detail.get('vacancyRequisitionId');jobs.append(k);time.sleep(.15)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Miro duplicate ID')
 elif cfg['kind']=='bamboo-list':
  import json,gzip
  with urllib.request.urlopen(urllib.request.Request(cfg['feed'],headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:raw=r.read()
  data=json.loads((gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw).decode('utf-8'))
  if not isinstance(data.get('result'),list) or data.get('meta',{}).get('totalCount')!=len(data['result']):raise ValueError('Bamboo list incomplete')
  for j in data['result']:
   if not j.get('id') or not j.get('jobOpeningName') or not isinstance(j.get('atsLocation'),dict):raise ValueError('Bamboo list structure changed')
   k=dict(j);k['title']=j['jobOpeningName'];k['location']='; '.join(str(j['atsLocation'][x]) for x in ['city','state','province','country'] if j['atsLocation'].get(x));k['url']=cfg['origin']+'/careers/'+str(j['id']);k['description']='';jobs.append(k)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Bamboo list duplicate')
 elif cfg['kind']=='bamboo-embed':
  import json,gzip
  with urllib.request.urlopen(urllib.request.Request(cfg['feed'],headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:raw=r.read()
  data=json.loads((gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw).decode('utf-8'))
  if data.get('success') is not True or not isinstance(data.get('departments'),list):raise ValueError('Bamboo feed structure missing')
  for dep in data['departments']:
   for j in dep['positions']:
    if not j.get('id') or not j.get('url') or not j['url'].startswith(cfg['origin']+'/careers/'):raise ValueError('Bamboo job changed/outside tenant')
    k=dict(j);k['title']=j['name'];k['description']='';jobs.append(k)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Bamboo duplicate IDs')
 elif cfg['kind']=='workco-inline':
  from urllib.parse import urljoin
  for a in s.select('a.RoleItem[href]'):
   title=a.select_one('.RoleItem-role');loc=a.select_one('.RoleItem-city')
   if not title or not loc or not re.match(r'^/careers/[^/]+/[^/]+/[^/]+/$',a['href']):raise ValueError('WorkCo card changed')
   jobs.append({'id':a['href'].strip('/'),'title':title.get_text(' ',strip=True),'location':loc.get_text(' ',strip=True),'url':urljoin(cfg['endpoint'],a['href']),'description':str(a)})
  if not jobs or len({j['id'] for j in jobs})!=len(jobs):raise ValueError('WorkCo cards absent/duplicate')
 elif cfg['kind']=='fundbox-inline':
  for a in s.select('a[href]'):
   if not a['href'].startswith('https://fundbox.careers.hibob.com/jobs/'):continue
   card=a.parent.parent; title=card.select_one('h4');button=card.select_one('button');sp=button.select('span') if button else []
   if not title or len(sp)!=2 or not a['href'].endswith('/apply'):raise ValueError('Fundbox card structure changed')
   jobs.append({'id':a['href'].split('/jobs/')[1].split('/')[0],'title':title.get_text(' ',strip=True),'location':sp[-1].get_text(' ',strip=True),'url':a['href'],'description':str(card)})
  if not jobs or len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Fundbox cards absent/duplicate')
 elif cfg['kind']=='ustwo-inline':
  for a in s.select('a[href]'):
   if not a['href'].startswith('https://ustwo.careers.hibob.com/jobs/'):continue
   title=a.find('div',class_=re.compile('jobItemName'));loc=a.find('div',class_=re.compile('smallBodyText'))
   if not title or not loc:raise ValueError('ustwo role structure changed')
   jobs.append({'id':a['href'].rsplit('/',1)[-1],'title':title.get_text(' ',strip=True),'location':loc.get_text(' ',strip=True),'url':a['href'],'description':str(a)})
  if not jobs or len({j['id'] for j in jobs})!=len(jobs):raise ValueError('ustwo cards absent/duplicate')
 elif cfg['kind']=='tuta-inline':
  from urllib.parse import urljoin
  for a in s.select('a[href]'):
   title=a.select_one('h3.position__title');loc=a.select_one('.position__summary')
   if not title:continue
   if not loc or not a['href'].startswith('/jobs/'):raise ValueError('Tuta position card changed')
   jobs.append({'id':a['href'].rsplit('/',1)[-1],'title':title.get_text(' ',strip=True),'location':loc.get_text(' ',strip=True),'url':urljoin(cfg['endpoint'],a['href']),'description':str(a)})
  if not jobs or len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Tuta cards absent/duplicated')
 elif cfg['kind']=='homerun-inline':
  import json
  node=s.select_one('job-list[v-bind]')
  if not node:raise ValueError('Homerun inline jobs absent')
  data=json.loads(node['v-bind'])['content'];loc={j['id']:j['name'] for j in data['locations']}
  for j in data['vacancies']:
   if not j.get('id') or not j.get('url') or j['location_id'] not in loc:raise ValueError('Homerun card structure changed')
   if not j['url'].startswith(cfg['endpoint']):raise ValueError('Homerun outside employer')
   k=dict(j);k['location']=loc[j['location_id']];k['description']='';jobs.append(k)
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Homerun duplicate IDs')
 elif cfg['kind']=='successfactors-html':
  from urllib.parse import urljoin
  import datetime
  queue=[cfg['endpoint']];seen=set();expected=None
  while queue:
   u=queue.pop(0)
   if u in seen:continue
   seen.add(u)
   if u!=cfg['endpoint']:
    with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'JobResearch/1.0'}),timeout=25) as r:page=BeautifulSoup(r.read().decode('utf-8'),'html.parser')
   else:page=s
   m=re.search(r'Results\s+\d+\s*[–-]\s*\d+\s+of\s+(\d+)',page.get_text(' ',strip=True))
   if not m:raise ValueError('SuccessFactors total missing')
   if expected is None:expected=int(m[1])
   if expected!=int(m[1]):raise ValueError('SuccessFactors unstable total')
   for tr in page.select('tr.data-row'):
    a=tr.select_one('a.jobTitle-link[href]');loc=tr.select_one('td.colLocation');dt=tr.select_one('td.colDate')
    if not a or not loc or not dt:raise ValueError('SuccessFactors card changed')
    link=urljoin(cfg['endpoint'],a['href']);date=dt.get_text(' ',strip=True)
    jobs.append({'id':link.rstrip('/').rsplit('/',1)[-1],'title':a.get_text(' ',strip=True),'url':link,'location':loc.get_text(' ',strip=True),'postedDate':datetime.datetime.strptime(date,'%b %d, %Y').date().isoformat(),'description':str(tr)})
   for a in page.select('a[href]'):
    if 'startrow=' in a['href']:
     nxt=urljoin(cfg['endpoint'],a['href'])
     if not nxt.startswith(cfg['endpoint']):raise ValueError('SuccessFactors pagination outside source')
     if nxt not in seen:queue.append(nxt)
   if len(seen)>100:raise ValueError('Pagination bound')
  if len(jobs)!=expected or len({j['id'] for j in jobs})!=expected:raise ValueError('SuccessFactors incomplete/doublecount')
 elif cfg['kind']=='inline-xata':
  from urllib.parse import urljoin
  cards=s.select('a[href^="/careers/"]')
  if not s.find(id='open-positions') or not cards:raise ValueError('Xata current roles structure absent')
  for a in cards:
   u=urljoin(cfg['endpoint'],a['href']);sp=a.find_all('span')
   if len(sp)<2:raise ValueError('Xata role card changed')
   jobs.append({'id':a['href'].rsplit('/',1)[-1],'title':sp[0].get_text(' ',strip=True),'location':sp[-1].get_text(' ',strip=True),'url':u,'description':str(a)})
  if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Xata duplicated job cards')
 elif cfg['kind']=='trinethire':
  from urllib.parse import urljoin
  table=s.select_one('table')
  if not table or 'Our Current Job Openings' not in s.get_text(' ',strip=True):raise ValueError('TriNet board structure absent')
  for tr in table.select('tr.job'):
   a=tr.select_one('a[href]')
   if not a:continue
   u=urljoin(cfg['endpoint'],a['href'])
   if not u.startswith(cfg['endpoint'].rstrip('/')+'/'):raise ValueError('TriNet outside bound employer')
   loc=tr.select_one('td.location');jobs.append({'id':u.split('/jobs/')[1].split('-')[0],'title':a.get_text(' ',strip=True),'url':u,'location':loc.get_text(' ',strip=True) if loc else '', 'description':str(tr)})
  links={urljoin(cfg['endpoint'],a['href']) for a in s.select('a[href]') if '/jobs/' in a['href']}
  if links!={j['url'] for j in jobs} or s.select('a[rel="next"]') or s.select('.pagination'):raise ValueError('Incomplete TriNet enumeration/pagination')
 elif cfg['kind']=='jazzhr':
  if not s.select('ul.list-group') and not s.select('.list-group-item'):raise ValueError('JazzHR listing selector absent')
  for li in s.select('li.list-group-item'):
   a=li.select_one('h3 a[href]')
   if not a:continue
   u=a['href'];loc=li.select_one('.list-group-item-text');jobs.append({'id':u.split('/apply/')[1].split('/')[0],'title':a.get_text(' ',strip=True),'url':u,'location':loc.get_text(' ',strip=True) if loc else '', 'description':str(li)})
  links={a['href'] for a in s.select('h3 a[href*="/apply/"]')}
  if links!={j['url'] for j in jobs}:raise ValueError('Incomplete JazzHR listing enumeration')
 elif cfg['kind']=='teamtailor-html':
  from urllib.parse import urlsplit
  host=urlsplit(cfg['endpoint']).netloc
  links={a['href'] for a in s.select('a[href]') if a['href'].startswith('https://'+host+'/jobs/') and '/applications/' not in a['href']}
  for u in sorted(links):
   a=s.find('a',href=u);li=a.find_parent('li')
   if not li:raise ValueError('Missing Teamtailor job card')
   meta=li.select_one('div.text-md');loc=meta.get_text(' ',strip=True) if meta else ''
   jobs.append({'id':u.split('/jobs/')[1].split('-')[0],'title':a.get_text(' ',strip=True),'location':loc,'url':u,'description':str(li)})
  counts=[int(m.group(1)) for txt in s.stripped_strings if (m:=re.fullmatch(r'(\d+) jobs?',txt))]
  if not counts or len(jobs)!=counts[0]:raise ValueError('Incomplete Teamtailor HTML pagination/count')
 elif cfg['kind']=='inline-yotpo':
  for a in s.select('a.yotpo-careers__job-card[href]'):
   title=a.select_one('.yotpo-careers__job-title');loc=a.select_one('.yotpo-careers__job-location');u=a['href']
   if not title or not loc or '/careers/gid-' not in u:raise ValueError('Changed Yotpo card structure')
   jobs.append({'id':u.rstrip('/').rsplit('gid-',1)[-1],'title':title.get_text(' ',strip=True),'location':loc.get_text(' ',strip=True),'url':u,'description':str(a)})
  links={a['href'] for a in s.select('a[href]') if '/careers/gid-' in a['href']}
  if links!={j['url'] for j in jobs}:raise ValueError('Incomplete own Yotpo listing enumeration')
 elif cfg['kind']=='inline-tyk':
  for a in s.select('h3.elementor-post__title a[href]'):
   u=a['href']
   if not u.startswith('https://tyk.io/jobs/'):continue
   jobs.append({'id':u.rstrip('/').rsplit('/',1)[-1],'title':a.get_text(' ',strip=True),'url':u,'location':'','description':str(a.find_parent('article'))})
  links={a['href'] for a in s.select('a[href]') if a['href'].startswith('https://tyk.io/jobs/')}
  if links!={j['url'] for j in jobs}:raise ValueError('Incomplete own Tyk job enumeration')
 elif cfg['kind']=='inline-aiven':
  links=s.select('a[href^="/careers/job/"]')
  if not links:raise ValueError('No own Aiven roles; validate explicit empty state')
  for a in links:
   ps=a.find_all('p')
   if len(ps)!=2:raise ValueError('Aiven title/location structure changed')
   u='https://aiven.io'+a['href'];jobs.append({'id':a['href'].rsplit('/',1)[-1],'title':ps[0].get_text(' ',strip=True),'location':ps[1].get_text(' ',strip=True),'url':u,'description':str(a)})
 elif cfg['kind']=='productboard-inline':
  from urllib.parse import urljoin
  for a in s.select('a[data-department][href]'):
   title=a.select_one('h4');loc=a.select_one('p')
   if not title or not loc or not a['href'].startswith('/careers/open-positions/'):raise ValueError('Productboard card changed')
   jobs.append({'id':a['href'].strip('/').split('/')[-1],'title':title.get_text(' ',strip=True),'location':loc.get_text(' ',strip=True),'url':urljoin(cfg['endpoint'],a['href']),'description':str(a)})
  if not jobs or len({j['id'] for j in jobs})!=len(jobs) or s.select('a[rel="next"]'):raise ValueError('Productboard absent/duplicate/pagination')
 elif cfg['kind']=='hrmdirect-html':
  from urllib.parse import urljoin
  grouped={}
  for tr in s.select('tr[data-req-id]'):
   a=tr.select_one('.posTitle a[href]');city=tr.select_one('.cities');state=tr.select_one('.state');ident=tr['data-req-id']
   if not a or not city or not state:raise ValueError('HRMdirect card changed')
   u=urljoin(cfg['endpoint'],a['href']);title=a.get_text(' ',strip=True);loc='; '.join(x.get_text(' ',strip=True) for x in [city,state] if x.get_text(' ',strip=True))
   if ident not in grouped:grouped[ident]={'id':ident,'title':title,'url':u,'location':loc,'description':str(tr),'location_variants':[{'location':loc,'url':u}]}
   else:
    j=grouped[ident]
    if j['title']!=title:raise ValueError('HRMdirect conflictingtitle')
    j['location_variants'].append({'location':loc,'url':u});j['description']+=str(tr)
    if loc and loc not in j['location']:j['location']='; '.join(filter(None,[j['location'],loc]))
  jobs=list(grouped.values())
  links={a['href'] for a in s.select('.posTitle a[href]')}
  if not jobs or len(links)!=sum(len(j['location_variants']) for j in jobs) or s.select('.pagination'):raise ValueError('HRMdirect incomplete enumeration')
 elif cfg['kind']=='newclassrooms-inline':
  for card in s.select('.nc__job'):
   a=card.select_one('a[href]');loc=card.select_one('.nc__job__location')
   if not a or not loc or 'recruiting.paylocity.com/recruiting/jobs/Details/' not in a['href']:raise ValueError('NewClassrooms owncard changed')
   jobs.append({'id':a['href'].split('/Details/')[1].split('/')[0],'title':a.get_text(' ',strip=True),'url':a['href'],'location':loc.get_text(' ',strip=True),'description':str(card)})
  links={a['href'] for a in s.select('a[href]') if 'recruiting.paylocity.com' in a['href'] and '/Details/' in a['href']}
  if not jobs or links!={j['url'] for j in jobs}:raise ValueError('NewClassrooms incomplete enumeration')
 elif cfg['kind']=='inline-paylocity':
  for a in s.select('h3 a[href]'):
   u=a['href']
   if 'recruiting.paylocity.com' not in u or '/Details/' not in u:continue
   box=a.find_parent('div',class_='cell');jobs.append({'id':u.split('/Details/')[1].split('/')[0],'title':a.get_text(' ',strip=True),'url':u,'location':'','description':str(box)})
  links={a['href'] for a in s.select('a[href]') if 'recruiting.paylocity.com' in a['href'] and '/Details/' in a['href']}
  if links!={j['url'] for j in jobs}:raise ValueError('Incomplete own Paylocity enumeration')
 elif cfg['kind']=='teamtailor-widget':
  import json
  widget=s.select_one('[data-teamtailor-api-key]')
  if not widget:raise ValueError('Missing own public widget binding')
  key=widget['data-teamtailor-api-key'];u=cfg['api_origin']+'/v1/jobs?include=locations,department&filter[feed]=public&page[size]=30';seen=set();expected=None
  while u:
   if u in seen or not u.startswith(cfg['api_origin']+'/v1/jobs?'):raise ValueError('Pagination invalid or outside bound origin')
   seen.add(u)
   req=urllib.request.Request(u,headers={'User-Agent':'JobResearch/1.0','Authorization':'Token token='+key,'X-Api-Version':'20240404'})
   with urllib.request.urlopen(req,timeout=25) as r:d=json.load(r)
   if expected is None:expected=d['meta']['record-count']
   locs={j['id']:j['attributes'] for j in d.get('included',[]) if j['type']=='locations'}
   for j in d['data']:
    a=j['attributes'];loc='; '.join(locs[v['id']].get('city','') for v in j.get('relationships',{}).get('locations',{}).get('data',[]) if v['id'] in locs);jobs.append({'id':j['id'],'title':a['title'],'url':j['links']['careersite-job-url'],'location':loc,'description':a.get('body',''),'original_record':j})
   u=d.get('links',{}).get('next')
  if len(jobs)!=expected:raise ValueError('Incomplete widget pagination')
 elif cfg['kind']=='inline-paycom':
  for a in s.select('h2 a[href]'):
   u=a['href']
   if cfg['bound_host'] not in u or '/jobs/' not in u:continue
   box=a.find_parent('div',class_='ckeditor-box');ps=box.find_all('p');loc=ps[0].get_text(' ',strip=True) if ps else ''
   jobs.append({'id':u.rsplit('/',1)[-1],'title':a.get_text(' ',strip=True),'url':u,'location':loc,'description':str(box)})
  links={a['href'] for a in s.select('a[href]') if cfg['bound_host'] in a['href'] and '/jobs/' in a['href']}
  if links!={j['url'] for j in jobs}:raise ValueError('Incomplete own inline job enumeration')
 else:raise ValueError('unsupported reader kind')
 if not jobs:raise ValueError('Zero roles needs explicit empty-board validation')
 if len({j['id'] for j in jobs})!=len(jobs):raise ValueError('Duplicate IDs')
 return jobs
