import re
SEN=re.compile(r'\b(staff|principal|distinguished|director|vp|vice president|head of|manager|architect|lead|senior manager|sr\.? manager)\b',re.I)
def years(t):
  v=[]
  for m in re.finditer(r'(\d{1,2})\s*(?:\+|–|-|to)?\s*(?:\d{1,2})?\+?\s*(?:or more\s*)?years',t):
    ctx=t[max(0,m.start()-60):m.end()+60].lower()
    if re.search(r'sabbatical|exercise|best workplaces|for over|named|founded|since|employment|after \d',ctx):continue
    v.append(int(m.group(1)))
  return v
def verdict(title,text):
  y=years(text);reasons=[]
  if SEN.search(title or ''):reasons.append('title scope: '+SEN.search(title).group(0))
  if y and min(y)>=5:reasons.append(f'{min(y)}+ yrs required')
  elif y and max(y)>=7:reasons.append(f'{max(y)}+ yrs mentioned')
  if re.search(r'\bmentor',text,re.I) and re.search(r'technical leadership|lead (a|the) team|lead engineers|technical strategy',text,re.I):reasons.append('leadership/mentoring scope')
  return ('CUT' if reasons else 'KEEP'),reasons,y
