"""Score a role 0-100 against the profile: relevance (50) + years-of-experience fit (30) + location (20)."""
import re,json,os,pathlib
P=pathlib.Path(__file__).parent

def load_profile():
  env=os.environ.get('PROFILE_JSON')
  if env:return json.loads(env)
  for n in ('profile.json','profile.example.json'):
    if (P/n).exists():return json.loads((P/n).read_text())

def has(term,text):
  return re.search(r'(?<![a-z0-9])'+re.escape(term)+r'(?![a-z0-9])',text) is not None

SOFT=re.compile(r'preferred|bonus|nice to have|even better|better if|a plus|\bplus\b|ideally|desirable|not required',re.I)
SKIP=re.compile(r'sabbatical|best workplaces|for over|named|founded|since|history|in business|our customers|we(?:\'|’)ve|over \d+ years|more than \d+ years of (?:history|experience building)',re.I)
YRS=re.compile(r'(\d{1,2})\s*\+?\s*(?:(?:-|–|to)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)\b',re.I)
def years_required(text):
  """Largest 'N+ years' in a requirement context; ignores preferred/bonus and company-history mentions."""
  vals=[]
  for m in YRS.finditer(text):
    n=int(m.group(1))
    if not 0<n<=15:continue
    before=text[max(0,m.start()-40):m.start()];ctx=text[max(0,m.start()-60):m.end()+100]
    if SOFT.search(before) or SKIP.search(text[max(0,m.start()-30):m.end()+30]):continue
    if not re.search(r'experience|years? of|yrs? of|in a |working|building|as a',ctx,re.I):continue
    vals.append(n)
  return max(vals) if vals else None

LANGS='spanish|french|german|italian|portuguese|mandarin|cantonese|chinese|japanese|korean|hindi|arabic|russian|dutch|polish|turkish|hebrew|swedish|danish|norwegian|finnish|vietnamese|thai|indonesian|tagalog|ukrainian|greek|czech'
LANG_REQ=re.compile(r'(?:fluen(?:t|cy)|bilingual|native[- ](?:level|speaker|proficiency)|business[- ]level|professional (?:working )?proficiency|proficien(?:t|cy) in)[^.;]{0,50}?\b('+LANGS+r')\b|\b('+LANGS+r')\b[^.;]{0,30}?(?:fluen(?:t|cy)|bilingual|native[- ]speaker)',re.I)
def languages_required(text):
  """Non-English languages the posting requires (not 'preferred'/'a plus'). Matches 'fluent in either Spanish, French or Russian'."""
  found=[]
  for m in LANG_REQ.finditer(text):
    before=text[max(0,m.start()-45):m.start()]
    if SOFT.search(before) or SOFT.search(text[m.start():m.end()+25]):continue
    window=text[m.start():m.end()+40]
    found+= [x.capitalize() for x in re.findall(r'\b('+LANGS+r')\b',window,re.I)]
  return sorted(set(found))

def seniority_years(title):
  t=title.lower()
  if re.search(r'\b(staff|principal|distinguished|fellow|director|vp|vice president|head of)\b',t):return 8
  if re.search(r'\b(manager|lead|architect)\b',t):return 6
  if re.search(r'\b(senior|sr\.?)\b',t):return 5
  if re.search(r'\b(iii|3)\b',t):return 4
  return None

def exp_points(eff):
  """30 for 0-2 yrs, 24 for 3, then nothing: 4+ years is not worth applying to."""
  if eff is None or eff<=2:return 30
  return 24 if eff<=3 else 0

def score(title,body,mode,is_sf,prof):
  t=title.lower();b=(body or '').lower()
  neg=[n for n in prof['negative_title'] if has(n,t)]
  hits=sorted((w,k) for k,w in prof['title_terms'].items() if has(k,t))[::-1]
  title_pts=0 if neg else min(25,(hits[0][0]+3*(len(hits)-1)) if hits else 0)
  skills=[k for k in prof['skills'] if has(k,b)]
  skill_pts=min(25,sum(prof['skills'][k] for k in skills))
  if neg:skill_pts=min(skill_pts,6)
  yrs=years_required(body or '');sen=seniority_years(title);langs=languages_required(body or '')
  eff=max([x for x in (yrs,sen) if x is not None],default=None)
  exp=exp_points(eff)
  early=bool(re.search(r'\b(intern|internship|co-op|student)\b',t))
  newgrad=bool(re.search(r'new grad|university grad|graduate|early career',t))
  if early:exp=min(exp,5)
  elif newgrad:exp=min(exp,12)
  loc=0 if mode=='remote' else 20 if is_sf else 12
  total=title_pts+skill_pts+exp+loc
  # Asking 4+ years (stated) or a senior-or-above title sinks the role below everything else.
  if yrs is not None and yrs>=4:total=min(total,30)
  elif sen is not None and sen>=5:total=min(total,40)
  if langs:total=min(total,30)
  return int(round(total)),yrs,dict(title=title_pts,skills=skill_pts,exp=exp,loc=loc,years=yrs,seniority=sen,matched=skills[:8],negative=neg,languages=langs)
