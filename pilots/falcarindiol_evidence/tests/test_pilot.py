import sys
import unittest
from pathlib import Path
from rdflib import Graph, Namespace, RDF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from run import load_graph, validate_graph  # noqa: E402

DEMO = Namespace('https://example.org/falcarindiol-demo/')


class PilotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = load_graph()

    def test_shapes_parse(self):
        shape = Graph().parse(ROOT / 'shapes' / 'pilot_shapes.ttl', format='turtle')
        self.assertGreater(len(shape), 20)

    def test_publication_and_claims(self):
        self.assertIn((DEMO.Claim_270_Catalysis, RDF.type, DEMO.ProposedFunctionClaim), self.g)
        self.assertNotIn((DEMO.CER1LikeProtein, DEMO.catalyzedBy, DEMO.ACET1Conversion), self.g)
        self.assertNotIn((DEMO.ACET1Conversion, DEMO.catalyzedBy, DEMO.CER1LikeProtein), self.g)

    def test_queries_parse_and_execute(self):
        for path in (ROOT / 'queries').glob('*.rq'):
            with self.subTest(query=path.name):
                list(self.g.query(path.read_text()))

    def test_gpml_references_and_mapping(self):
        from xml.etree import ElementTree as ET
        root = ET.parse(ROOT / 'diagram' / 'falcarindiol_teaching.gpml').getroot()
        ids = {el.attrib['elementId'] for el in root.iter() if 'elementId' in el.attrib}
        refs = {el.attrib['elementRef'] for el in root.iter() if 'elementRef' in el.attrib}
        self.assertTrue(refs <= ids)
        self.assertIn((DEMO.ACET1Conversion, RDF.type, DEMO.CharacterizedReaction), self.g)

    def test_supported_gene_rows(self):
        rows = list(self.g.query((ROOT/'queries'/'supported_genes.rq').read_text()))
        self.assertEqual(len(rows), 3)

    def test_synthetic_and_scenario_stay_distinct(self):
        rows = list(self.g.query((ROOT/'queries'/'lagged_findings.rq').read_text()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0].status), str(DEMO.SyntheticDemonstration))

    @unittest.skipUnless(__import__('importlib').util.find_spec('pyshacl'), 'pyshacl not installed')
    def test_shacl_valid(self):
        self.assertTrue(validate_graph(load_graph()))

    @unittest.skipUnless(__import__('importlib').util.find_spec('pyshacl'), 'pyshacl not installed')
    def test_shacl_invalid(self):
        self.assertFalse(validate_graph(load_graph(broken=True)))


if __name__ == '__main__':
    unittest.main()
