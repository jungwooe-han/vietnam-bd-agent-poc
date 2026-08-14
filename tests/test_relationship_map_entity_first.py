import unittest

from src.vietnam_bd.demo_data_v2 import demo_v2_result
from src.vietnam_bd.models import (
    CanonicalRelationship,
    EntityIdentity,
    ProjectActor,
    ProjectIntelligence,
    ProjectLocation,
    ProjectParticipation,
    ProjectRelationship,
    RelationshipDecisionMap,
)
from src.vietnam_bd.reasoning import build_relationship_map
from src.vietnam_bd.research_models import (
    DeepResearchResult,
    DiscoveredEntity,
    DiscoveredRelationship,
    QuickResearchResult,
    ResearchBundle,
    ResearchRoundResult,
    SeedUnderstanding,
)
from src.vietnam_bd.v3_rule_engine import build_v3_result


SOURCE_URL = "https://example.com/nic-thermo-mou"


def nic_thermo_v2_map() -> RelationshipDecisionMap:
    bundle = ResearchBundle(
        quick=QuickResearchResult(company="National Innovation Centre (NIC)"),
        research_mode="deep",
        stage_gate_status="targeting",
        stage_gate_reason="MoU planning stage",
        seed_understanding=SeedUnderstanding(
            company="Thermo Fisher Scientific",
            owner_candidate="National Innovation Centre (NIC)",
        ),
        research_rounds=[ResearchRoundResult(
            round_number=1,
            focus="Current project participants",
            findings=DeepResearchResult(),
            discovered_entities=[
                DiscoveredEntity(
                    name="National Innovation Centre (NIC)",
                    entity_type="host",
                    credibility="confirmed",
                    evidence_labels=["NIC–Thermo Fisher MoU"],
                    source_urls=[SOURCE_URL],
                ),
                DiscoveredEntity(
                    name="Thermo Fisher Scientific",
                    entity_type="technology_partner",
                    credibility="confirmed",
                    evidence_labels=["NIC–Thermo Fisher MoU"],
                    source_urls=[SOURCE_URL],
                ),
            ],
            discovered_relationships=[DiscoveredRelationship(
                from_entity="National Innovation Centre (NIC)",
                to_entity="Thermo Fisher Scientific",
                relationship_type="MoU / joint roadmap development",
                description="Co-development of a shared laboratory.",
                credibility="confirmed",
                evidence_labels=["NIC–Thermo Fisher MoU"],
                source_urls=[SOURCE_URL],
            )],
        )],
    )
    return build_relationship_map(bundle, ProjectIntelligence())


class EntityFirstRelationshipMapTest(unittest.TestCase):
    def test_case_a_supported_entities_survive_unclassified_structure(self) -> None:
        v2 = demo_v2_result()
        v2.context.business_structure = []
        v2.relationship_map = nic_thermo_v2_map()

        result = build_v3_result(v2, "NIC Thermo Fisher shared laboratory MoU")

        companies = {node.company for node in result.relationship_map.nodes if node.company}
        self.assertEqual(result.relationship_map.structure_id, "OTHER")
        self.assertEqual(result.relationship_map.status, "partial")
        self.assertIn("National Innovation Centre (NIC)", companies)
        self.assertIn("Thermo Fisher Scientific", companies)
        self.assertTrue(any("MOU" in relation.label for relation in result.relationship_map.relations))
        self.assertFalse(any(not node.company for node in result.relationship_map.nodes))
        registry = {entity.canonical_name: entity for entity in v2.relationship_map.entities}
        roles = {
            item.entity_id: set(item.roles) for item in v2.relationship_map.participations
        }
        self.assertEqual(registry["National Innovation Centre (NIC)"].organization_type, "PUBLIC_INSTITUTION")
        self.assertEqual(registry["Thermo Fisher Scientific"].organization_type, "TECHNOLOGY_COMPANY")
        self.assertTrue({"PROJECT_OWNER", "HOST", "GOVERNMENT_PARTNER"}.issubset(
            roles[registry["National Innovation Centre (NIC)"].entity_id]
        ))
        self.assertTrue({"CO_DEVELOPMENT_PARTNER", "TECHNOLOGY_PROVIDER", "EQUIPMENT_SUPPLIER"}.issubset(
            roles[registry["Thermo Fisher Scientific"].entity_id]
        ))
        canonical_relation = v2.relationship_map.canonical_relationships[0]
        self.assertEqual(canonical_relation.relationship_type, "CO_DEVELOPMENT")
        self.assertEqual(canonical_relation.relationship_basis, "MOU")
        self.assertEqual(canonical_relation.status, "confirmed")
        thermo_id = registry["Thermo Fisher Scientific"].entity_id
        self.assertTrue(any(
            influence.entity_id == thermo_id
            and influence.domain == "TECHNICAL_SPECIFICATION"
            and influence.influence == "HIGH"
            for influence in v2.relationship_map.decision_influences
        ))

    def test_historical_epc_does_not_create_current_s1_pattern(self) -> None:
        result = build_v3_result(demo_v2_result(), "demo project")
        self.assertEqual(result.relationship_map.structure_id, "OTHER")
        self.assertTrue(result.relationship_map.nodes)
        self.assertFalse(any("EPC" in node.roles for node in result.relationship_map.nodes))

    def test_case_c_entity_survives_when_relationship_is_only_candidate(self) -> None:
        v2 = demo_v2_result()
        v2.context.business_structure = []
        v2.relationship_map = RelationshipDecisionMap(
            actors=[ProjectActor(
                actor_id="partner",
                role="Technology / Solution Partner",
                organization="Supported Partner",
                temporal_scope="current",
                actor_status="confirmed",
                participation_status="Current participant",
                credibility="confirmed",
                evidence_labels=["Participant announcement"],
                source_urls=[SOURCE_URL],
            )],
            relationships=[ProjectRelationship(
                from_actor_id="partner",
                to_actor_id="unknown_owner",
                relationship_type="Relationship to confirm",
                temporal_scope="current",
                credibility="unknown",
            )],
        )
        result = build_v3_result(v2, "technology participant")
        self.assertTrue(any(node.company == "Supported Partner" for node in result.relationship_map.nodes))
        self.assertEqual(result.relationship_map.status, "partial")

    def test_case_d_no_supported_entity_is_unconfirmed(self) -> None:
        v2 = demo_v2_result()
        v2.context.business_structure = []
        v2.relationship_map = RelationshipDecisionMap(actors=[ProjectActor(
            actor_id="unknown_epc",
            role="EPC",
            organization="UNKNOWN",
            temporal_scope="unknown",
            actor_status="unknown",
            participation_status="Not identified",
            credibility="unknown",
        )])
        result = build_v3_result(v2, "unidentified project")
        self.assertEqual(result.relationship_map.status, "unconfirmed")

    def test_case_e_hq_and_local_are_entities_not_owner_role_variants(self) -> None:
        v2 = demo_v2_result()
        v2.context.business_structure = []
        v2.relationship_map = RelationshipDecisionMap(
            entities=[
                EntityIdentity(
                    entity_id="org:seah-holdings",
                    canonical_name="SeAH Holdings",
                    organization_type="PRIVATE_COMPANY",
                    organization_scope="global_hq",
                    status="confirmed",
                ),
                EntityIdentity(
                    entity_id="org:seah-vietnam",
                    canonical_name="SeAH Vietnam",
                    organization_type="PRIVATE_COMPANY",
                    organization_scope="local_entity",
                    status="confirmed",
                ),
            ],
            participations=[ProjectParticipation(
                project_id="project:seah-vietnam-plant",
                entity_id="org:seah-vietnam",
                roles=["PROJECT_OWNER"],
                role_statuses={"PROJECT_OWNER": "confirmed"},
                temporal_scope="current",
            )],
            canonical_relationships=[CanonicalRelationship(
                from_entity_id="org:seah-vietnam",
                to_entity_id="org:seah-holdings",
                relationship_type="SUBSIDIARY_OF",
                status="confirmed",
                temporal_scope="current",
            )],
        )

        result = build_v3_result(v2, "SeAH Vietnam plant")

        self.assertTrue(any(node.layer_type == "corporate" for node in result.relationship_map.nodes))
        local_project_node = next(node for node in result.relationship_map.nodes if node.layer_type == "project")
        self.assertEqual(local_project_node.roles, ["PROJECT_OWNER"])
        self.assertNotIn("OWNER_HQ", local_project_node.roles)
        self.assertNotIn("OWNER_LOCAL", local_project_node.roles)
        self.assertTrue(any(relation.relation_type == "SUBSIDIARY_OF" for relation in result.relationship_map.relations))

    def test_case_f_missing_local_entity_creates_gap_not_entity(self) -> None:
        bundle = ResearchBundle(
            quick=QuickResearchResult(company="SeAH"),
            research_mode="deep",
            stage_gate_status="targeting",
            stage_gate_reason="New Vietnam plant announced",
            seed_understanding=SeedUnderstanding(company="SeAH", owner_candidate="SeAH"),
            research_rounds=[ResearchRoundResult(
                round_number=1,
                focus="Project owner",
                findings=DeepResearchResult(),
                discovered_entities=[DiscoveredEntity(
                    name="SeAH",
                    entity_type="owner",
                    credibility="confirmed",
                    evidence_labels=["SeAH Vietnam plant announcement"],
                    source_urls=["https://example.com/seah-vietnam-plant"],
                )],
            )],
        )
        intelligence = ProjectIntelligence(project_location=ProjectLocation(country="Vietnam"))

        relmap = build_relationship_map(bundle, intelligence)

        self.assertEqual([entity.canonical_name for entity in relmap.entities], ["SeAH"])
        self.assertNotIn("SeAH Vietnam", [entity.canonical_name for entity in relmap.entities])
        self.assertIn("Local Project Entity — Not confirmed", relmap.research_gaps)

    def test_legacy_mou_history_migrates_to_canonical_roles_and_relation(self) -> None:
        v2 = demo_v2_result()
        v2.executive_summary = (
            "National Innovation Centre and Thermo Fisher signed a memorandum of understanding "
            "to co-develop a shared laboratory with technology and equipment."
        )
        v2.context.business_structure = []
        v2.relationship_map = RelationshipDecisionMap(actors=[
            ProjectActor(
                actor_id="nic",
                role="Owner / End Client",
                organization="National Innovation Centre",
                temporal_scope="current",
                actor_status="confirmed",
                participation_status="Current participant",
                credibility="confirmed",
                source_urls=[SOURCE_URL],
            ),
            ProjectActor(
                actor_id="thermo",
                role="Company",
                organization="Thermo Fisher",
                temporal_scope="current",
                actor_status="confirmed",
                participation_status="Current participant",
                credibility="confirmed",
                source_urls=[SOURCE_URL],
            ),
        ])

        result = build_v3_result(v2, "NIC Thermo Fisher MOU")

        thermo = next(node for node in result.relationship_map.nodes if node.company == "Thermo Fisher")
        self.assertEqual(
            thermo.roles,
            ["CO_DEVELOPMENT_PARTNER", "TECHNOLOGY_PROVIDER", "EQUIPMENT_SUPPLIER"],
        )
        relation = result.relationship_map.relations[0]
        self.assertEqual(relation.relation_type, "CO_DEVELOPMENT")
        self.assertEqual(relation.relationship_basis, "MOU")
        self.assertEqual(relation.status, "confirmed")


if __name__ == "__main__":
    unittest.main()
