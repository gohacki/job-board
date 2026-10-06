"""Classify a location string as Bay Area on-site/hybrid, US remote, or neither."""
import re
BAY=re.compile(r"san francisco|\bsf\b|south san francisco|bay area|oakland|berkeley|emeryville|alameda|san leandro|hayward|fremont|newark, ca|union city|milpitas|san jose|santa clara|sunnyvale|mountain view|los altos|palo alto|menlo park|redwood city|redwood shores|san carlos|belmont, ca|foster city|san mateo|burlingame|millbrae|san bruno|brisbane, ca|daly city|pacifica|half moon bay|cupertino|campbell, ca|los gatos|saratoga|pleasanton|dublin, ca|livermore|walnut creek|concord, ca|san ramon|danville, ca|san rafael|mill valley|sausalito|novato|petaluma|palo alto|stanford|east palo alto|foster city",re.I)
SF=re.compile(r"san francisco|\bsf\b|south san francisco",re.I)
REMOTE=re.compile(r'remote|work from home|anywhere',re.I)
INOFFICE=re.compile(r'hybrid|on-?site|in[- ]office',re.I)
US=re.compile(r'united states|\busa?\b|\bu\.s\.',re.I)
NONUS=re.compile(r'poland|canada|india|europe|\buk\b|united kingdom|germany|ireland|france|spain|netherlands|portugal|brazil|mexico|japan|australia|singapore|israel|argentina|colombia|philippines|emea|apac|latam|romania|ukraine|turkey|nigeria|kenya|south africa|\bcan\b',re.I)

def classify(loc,workplace=''):
  l=(loc or '')+' '+(workplace or '')
  remote=bool(REMOTE.search(l)) or str(workplace).lower()=='remote'
  segs=[x for x in re.split(r'[;|]',loc or '') if x.strip()]
  # a Bay Area entry that is not itself marked remote means an in-person option exists
  inperson=[x for x in segs if BAY.search(x) and not REMOTE.search(x)]
  if inperson or (BAY.search(l) and not remote):
    return 'bay',bool(SF.search(' '.join(inperson) if inperson else l))
  if BAY.search(l) and INOFFICE.search(l):return 'bay',bool(SF.search(l))
  if remote:
    if NONUS.search(l) and not US.search(l):return None
    return 'remote',False
  return None
