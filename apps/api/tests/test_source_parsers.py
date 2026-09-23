import unittest
from app.services.source_parsers import parse_structured
from app.services.source_management import normalize_html


class StructuredParserTests(unittest.TestCase):
    def test_rss_and_atom_preserve_provenance(self):
        for kind, body in [('rss','<rss><channel><item><title>Advisory</title><description>Review CVE-2026-1234</description><link>/advisory</link><author>SOC</author></item></channel></rss>'),('atom','<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Advisory</title><summary>Review CVE-2026-1234</summary><link href="/advisory"/><author><name>SOC</name></author></entry></feed>')]:
            title,text,links,entries=parse_structured(body,kind,'https://example.com/feed',normalize_html)
            self.assertEqual(title,'Advisory')
            self.assertIn('CVE-2026-1234',text)
            self.assertEqual(links,['https://example.com/advisory'])
            self.assertEqual(entries[0]['author'],'SOC')

    def test_json_and_xml_entity_rejection(self):
        result=parse_structured('{"items":[{"title":"Bulletin","text":"IOC example.com","url":"/news"}]}','json','https://example.com/api',normalize_html)
        self.assertIn('IOC example.com',result[1])
        with self.assertRaises(ValueError):
            parse_structured('<!DOCTYPE rss [<!ENTITY x SYSTEM "file:///etc/passwd">]><rss/>','rss','https://example.com',normalize_html)
