import json,re,sqlite3,hashlib,zlib,datetime,urllib.parse
def text(v):
 if isinstance(v,dict):return v.get('name') or v.get('fullLocation') or json.dumps(v)
 if isinstance(v,list):return '; '.join(text(x) for x in v)
 return str(v or '')
def canon(u):
 if not u:return ''
 p=urllib.parse.urlsplit(u);q=urllib.parse.parse_qsl(p.query);q=[(k,v) for k,v in q if k not in ['utm_source','utm_medium','utm_campaign','gh_src','source','ref']];return urllib.parse.urlunsplit((p.scheme,p.netloc,p.path.rstrip('/').removesuffix('/application').removesuffix('/apply'),urllib.parse.urlencode(q),''))
def listing_location(j):
 primary=text(j.get('location') or j.get('locationsText') or j.get('locations') or j.get('categories',{}).get('location') or j.get('multi_location') or j.get('cityState'))
 country=text((lambda a:(a.get('postalAddress') or {}).get('addressCountry') if isinstance(a,dict) and isinstance(a.get('postalAddress'),dict) else None)(j.get('address')))
 if country and country.lower() not in primary.lower():primary=primary+'; '+country if primary else country
 secondary=[text(v.get('location') or None) for v in j.get('secondaryLocations',[]) if isinstance(v,dict)]
 vals=list(dict.fromkeys([primary]+[v for v in secondary if v]));loc='; '.join(vals)
 if j.get('workplaceType')=='Remote' or (j.get('isRemote') is True and j.get('workplaceType') not in ['Hybrid','OnSite','On-site']):
  if not re.search(r'Remote',loc,re.I):loc='Remote - '+loc
 return loc

def eligible_location(loc):
 bay=bool(re.search(r'San Francisco|San Jose|Bay Area|Mountain View|Santa Clara|Palo Alto|San Mateo|Sunnyvale|Redwood|Oakland|Berkeley|Menlo Park|Pleasanton|San Ramon|Fremont|Burlingame|Cupertino',loc,re.I))
 # Generic Remote remains unresolved. US plus explicit remote in employer data qualifies.
 remote_us=bool(re.search(r'Remote',loc,re.I) and re.search(r'United States|\bUSA\b|\bUS\b|\bU\.S\.(?:A\.)?',loc,re.I))
 return bay or remote_us

def ingest(db,r,js,seen,enabled,configs,baseline=False):
 reqmap={};urlmap={}
 for key,c,req,u,first in db.execute('SELECT key,company,req_id,url,first_seen FROM listings'):
  if req:reqmap[(c.lower(),req)]=(key,first)
  if u:urlmap[u]=(key,first)
 endpoint=r['Public board endpoint'];sid=hashlib.sha256((endpoint+seen).encode()).hexdigest();db.execute('INSERT OR REPLACE INTO scans VALUES(?,?,?,?,?)',(sid,seen,endpoint,'complete',len(js)))
 for j in js:
  title=j.get('title') or j.get('text') or j.get('name') or '';loc=listing_location(j)
  req=text(j.get('atsJobId') or j.get('id') or j.get('jobId') or (((j.get('bulletFields') or [''])[0]) if re.search(r'^(?:R|JR|REQ|J|WD|[0-9])[A-Za-z0-9_-]*[0-9]',str((j.get('bulletFields') or [''])[0]),re.I) else '') or j.get('externalPath'));url=j.get('jobUrl') or j.get('absolute_url') or j.get('hostedUrl') or j.get('url') or j.get('applyUrl') or j.get('jobDetailUrl') or ''
  if r['ATS']=='smartrecruiters':url=j.get('ref') or url
  if r['ATS']=='eightfold':url='https://jobs.dolby.com'+j.get('positionUrl','')
  if r['ATS']=='workday' and j.get('externalPath'):
   cfg=next((c for c in configs if c['company']==r['Company'] or c.get('existing_company')==r['Company']),None)
   if not cfg:
    cfg=next((c for c in configs if c['company']==r['Company']),None)
   if cfg:
    boardurl=cfg['origin']+'/'+cfg['board'] if 'origin' in cfg else cfg['board'];url=boardurl+j['externalPath']
  url=canon(url);dt=text(j.get('first_published_at') or j.get('first_published') or j.get('publishedAt') or j.get('postedDate') or j.get('releasedDate'))
  if r['ATS']=='eightfold':meaning='Employer postedTs (publication/republication), not first seen'
  if j.get('postedTs'):dt=datetime.datetime.fromtimestamp(j['postedTs'],datetime.timezone.utc).isoformat()
  meaning=('Employer postedTs (publication/republication), not first seen' if r['ATS']=='eightfold' else 'Greenhouse first_published (employer first publication date)' if j.get('first_published') else r.get('Date caveat')) or 'Unknown original publication';dt=dt or ''
  if not dt:meaning='Unknown original publication; first seen recorded'
  technical=bool(re.search(r'engineer|architect|developer|data scientist|forward.deployed|deployment strategist|technical consultant',title,re.I));geo=eligible_location(loc)
  reasons=[]
  content=j.get('descriptionPlain') or j.get('content') or j.get('description') or ''
  if isinstance(content,dict):content=str(content)
  if re.search(r'defense|surveillance|military|federal.*clearance|security clearance',title,re.I):reasons.append('defense/surveillance role')
  values_content=re.sub(r'applicable government leave program(?:\(s\)|s)?','applicable statutory leave',content,flags=re.I) if r['Company']=='Tubi' else content
  if r['Company']=='Lattice':values_content=re.sub(r'veteran or military status','protected veteran status',values_content,flags=re.I)
  if re.search(r'government|defense|military|surveillance',values_content,re.I):flags_pending='dual-use/values detail review'
  else:flags_pending=''
  if not url:reasons.append('canonical URL unavailable')
  if not technical:reasons.append('nontechnical title or pure PM')
  if not geo:reasons.append('outside Bay/remote-US or location unverified')
  if r['Company'].lower() not in enabled:reasons.append('employer disabled/hold')
  flags=[flags_pending] if flags_pending else []
  if r.get('Values screen','').startswith('dual-use:'):
   flags.append(r['Values screen']);flags_pending=''
   flags=[x for x in flags if x!='dual-use/values detail review']
  if 'Unverified' in r.get('Stage screen',''):flags.append('employer stage unverified, not a recommendation')
  if flags_pending:reasons.append('values review pending')
  if re.search(r'defense|surveillance|military',r.get('Values screen',''),re.I) and r['Company'] in ['Anduril','Scale AI','Samsara','Guild','Flow Engineering','Cognition','Sofar Ocean','Roboflow']:reasons.append('employer values hold')
  if technical:flags.append('engineering-relevant')
  if geo:flags.append('Bay/US candidate')
  if re.search('senior|staff|principal|director|manager|lead',title,re.I):flags.append('seniority stretch')
  if re.search('intern|firmware|embedded|silicon|hardware|verification|physical design|electronics|actuator|mechanical',title,re.I):reasons.append('intern/hardware-specialist title')
  if re.search(r'Remote.*(?:Poland|Canada|India|Europe|UK)',loc,re.I) and not re.search('United States|USA|US.Remote',loc,re.I):reasons.append('remote not US')
  if r['Company']=='Typeform' and 'UK, Ireland, Germany, Portugal, Spain or the Netherlands' in content and 'US' in title:reasons.append('Employer US label contradicts EU-only description; location held pending clarification')
  if r['Company']=='Typeform' and 'ET timezone in the US' in content:reasons.append('Employer restricts US role to Eastern timezone; California not eligible')
  if r['Company']=='Intermedia' and title=='Forward Deployed Engineer':flags.append('Field Deployment Engineer in body: AI/contact-center implementation, 2-3+ years and contact-center domain stretch; pay field $100k-$150k vs body $95k-$150k discrepancy')
  if r['Company']=='Splice' and 'Sr Software Engineer II' in title:flags.append('Specialist audio-core C++/JUCE; 10+ years production audio software; major domain/tenure mismatch')
  if r['Company']=='Splice' and 'Data Engineer II' in title:flags.append('3+ years production data engineering; Python/SQL/BigQuery/SQLMesh/Dagster; $94,952-$118,690 below preferred benchmark')
  if r['Company']=='Productboard' and title=='AI Customer Success Engineer':
   flags.append('Founder-adjacent AI customer success; not software engineering');reasons.append('Commercial/customer-success lane; hands-on prompt/workflow coaching rather than implementation engineering, retain for separate lane review')
  if r['Company']=='Miro' and title=='AI Technical Architect':flags.append('Customer-facing AI implementation; 6+ years consulting/architecture stretch; salary unknown')
  if r['Company']=='Miro' and title=='Forward Deployed Consultant, Manufacturing':flags.append('8+ years industrial consulting stretch; ERP/PLM/MES expertise; up to 40% travel; salary unknown')
  if r['Company']=='PLOS' and 'following US states:' in content and not re.search(r'following US states:[^.]*\bCA\b',content):
   reasons.append('Employer remote-US state list excludes California; not Bay eligible')
  if r['Company']=='KQED' and title=='TV Maintenance Engineer':reasons.append('Broadcast equipment maintenance, not software engineering')
  # Dedupe by employer-scoped requisition OR canonical URL, preserve first seen.
  found=reqmap.get((r['Company'].lower(),req)) or urlmap.get(url);key=found[0] if found else hashlib.sha256((r['Company'].lower()+'|'+req+'|'+url).encode()).hexdigest();first=found[1] if found else seen
  kind=db.execute('SELECT first_seen_kind FROM listings WHERE key=?',(key,)).fetchone() if found else None
  if req:reqmap[(r['Company'].lower(),req)]=(key,first)
  if url:urlmap[url]=(key,first)
  db.execute('INSERT OR REPLACE INTO listings(key,company,ats,req_id,url,title,location,employer_date,date_meaning,first_seen,last_seen,status,relevance_flags,excluded_reason,source_endpoint,raw_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(key,r['Company'],r['ATS'],req,url,title,loc,dt,meaning,first,seen,'open','; '.join(flags),'; '.join(reasons),endpoint,zlib.compress(json.dumps(j,ensure_ascii=False).encode())));db.execute('UPDATE listings SET first_seen_kind=? WHERE key=?',('baseline import, not a new posting' if baseline else (kind[0] if kind and kind[0] else 'new observation'),key));db.execute('INSERT OR IGNORE INTO sightings VALUES(?,?)',(sid,key))
 db.execute("UPDATE listings SET status='closed' WHERE source_endpoint=? AND last_seen<? AND key NOT IN (SELECT key FROM sightings WHERE scan_id=?)",(endpoint,seen,sid))
 db.commit()
 return sid
