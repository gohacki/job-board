import re
BAY=re.compile(r'san francisco|bay area|san mateo|sunnyvale|redwood city|palo alto|san jose|oakland|mountain view|menlo park|santa clara|south san francisco|\bsf\b|berkeley|fremont|cupertino|emeryville|foster city|burlingame|san carlos|los gatos|milpitas|san bruno|, ca\b',re.I)
def mode(loc,wt=''):
  l=(loc or '')+' '+(wt or '')
  if re.search(r'remote',l,re.I) and not re.search(r'hybrid|on-?site|in office',l,re.I):return 'Remote',2
  if BAY.search(l) and not re.search(r'los angeles|san diego|irvine|costa mesa|santa ana|sacramento',l,re.I):return 'Bay Area hybrid/onsite',0
  return 'Other US hybrid/onsite',1
