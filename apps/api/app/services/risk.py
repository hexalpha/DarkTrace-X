"""Versioned deterministic scoring; a keyword match is not proof of compromise."""
def keyword_risk(trust_level):
    factors = {'configured_keyword_match': 25, 'source_reliability': {'high':20,'medium':10,'low':0}.get(trust_level,0), 'recent_collection':10}
    score = sum(factors.values())
    return {'version':'keyword-evidence-v1','score':score,'severity':'medium' if score>=40 else 'low',
            'factors':factors,'limitations':['Keyword relevance is observed; malicious activity is not established.']}
