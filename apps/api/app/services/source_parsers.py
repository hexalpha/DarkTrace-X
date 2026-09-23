"""Explicit feed/API parsers; no scripts or external XML entities are evaluated."""
import json
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree


def parse_structured(body, kind, url, html_normalizer):
    entries = []
    if kind in {'rss', 'atom'}:
        if '<!DOCTYPE' in body.upper() or '<!ENTITY' in body.upper():
            raise ValueError('XML declarations with entities are not supported')
        try:
            root = ElementTree.fromstring(body)
        except ElementTree.ParseError:
            raise ValueError('Invalid XML source') from None
        def local(tag):
            return tag.rsplit('}', 1)[-1]
        for node in root.iter():
            if local(node.tag) not in {'item', 'entry'}:
                continue
            item = {}
            for child in node:
                name = local(child.tag)
                value = ''.join(child.itertext()).strip()
                if name == 'link':
                    value = child.attrib.get('href', value)
                if name in {'title','description','summary','content','link','author','creator','pubDate','published','updated'}:
                    item[name] = value
            entries.append(item)
    elif kind == 'json':
        value = json.loads(body)
        if isinstance(value, dict):
            values = next((value[k] for k in ('items','entries','results','data','vulnerabilities') if isinstance(value.get(k), list)), [value])
        elif isinstance(value, list):
            values = value
        else:
            raise ValueError('JSON source must contain objects or an array')
        entries = [item for item in values if isinstance(item, dict)]
    else:
        raise ValueError('Unsupported structured parser')
    if len(entries) > 5000:
        raise ValueError('Source contains more than 5000 records')
    normalized = []
    links = []
    for item in entries:
        title = str(item.get('title') or item.get('vulnerabilityName') or item.get('name') or 'Source entry')[:512]
        content = item.get('content') or item.get('description') or item.get('summary') or item.get('text') or json.dumps(item,ensure_ascii=False)
        text = html_normalizer(str(content),'text/html')[1]
        link = urljoin(url,str(item.get('link') or item.get('url') or ''))
        if urlsplit(link).scheme not in {'http','https'}:
            link = url
        links.append(link)
        normalized.append({'title':title,'text':text,'author':str(item.get('author') or item.get('creator') or '')[:256],
            'published_at':item.get('published') or item.get('pubDate') or item.get('dateAdded') or item.get('updated'), 'canonical_url':link})
    if not normalized:
        raise ValueError('No records found in structured source')
    return normalized[0]['title'], '\n\n'.join(item['title']+'\n'+item['text'] for item in normalized), links[:200], normalized
