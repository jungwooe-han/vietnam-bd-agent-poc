import unittest

from src.vietnam_bd.models_v3 import V3RelationshipMap


class V3HistoryCompatibilityTest(unittest.TestCase):
    def test_relationship_map_accepts_legacy_and_entity_first_statuses(self) -> None:
        for status in ("confirmed", "inferred", "partial", "unconfirmed", "unknown"):
            with self.subTest(status=status):
                self.assertEqual(V3RelationshipMap(status=status).status, status)


if __name__ == "__main__":
    unittest.main()
