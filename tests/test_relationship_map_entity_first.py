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

    def test_avc_style_aliases_and_scoped_contract_are_simplified(self) -> None:
        v2 = demo_v2_result()
        v2.context.business_structure = []
        v2.context.business_stage.claim = "시공"
        v2.relationship_map = RelationshipDecisionMap(
            entities=[
                EntityIdentity(entity_id="org:avc", canonical_name="Asia Vital Components Co., Ltd. (AVC)", organization_scope="global_hq", organization_type="PRIVATE_COMPANY", status="confirmed"),
                EntityIdentity(entity_id="org:avc-tech-long", canonical_name="AVC Tech. (Vietnam) Co., Ltd. / AVC Technology (Vietnam) Company Limited", organization_scope="local_entity", organization_type="PRIVATE_COMPANY", status="confirmed"),
                EntityIdentity(entity_id="org:avc-technology", canonical_name="AVC Technology (Vietnam) Company Limited", organization_scope="local_entity", organization_type="PRIVATE_COMPANY", status="confirmed"),
                EntityIdentity(entity_id="org:unknown", canonical_name="創興國際建設有限公司", organization_type="CONSTRUCTION_COMPANY", status="confirmed"),
                EntityIdentity(entity_id="org:gov-a", canonical_name="UBND / provincial authorities of Ninh Binh", organization_type="PUBLIC_INSTITUTION", status="confirmed"),
                EntityIdentity(entity_id="org:gov-b", canonical_name="UBND / Ninh Binh provincial authorities", organization_type="PUBLIC_INSTITUTION", status="confirmed"),
                EntityIdentity(entity_id="org:project", canonical_name="AVC Technology Vietnam – Kim Bang project / plant", organization_scope="project_company", organization_type="OTHER", status="confirmed"),
                EntityIdentity(entity_id="org:ticker", canonical_name="奇鋐 (listed company; ticker referenced in disclosure)", organization_scope="regional_hq", organization_type="PRIVATE_COMPANY", status="confirmed"),
            ],
            participations=[
                ProjectParticipation(project_id="project:avc", entity_id="org:avc", roles=["PROJECT_OWNER", "INVESTOR"], role_statuses={"PROJECT_OWNER": "confirmed", "INVESTOR": "confirmed"}, temporal_scope="current"),
                ProjectParticipation(project_id="project:avc", entity_id="org:avc-tech-long", roles=["PROJECT_OWNER"], role_statuses={"PROJECT_OWNER": "confirmed"}, temporal_scope="current"),
                ProjectParticipation(project_id="project:avc", entity_id="org:avc-technology", roles=["PROJECT_OWNER", "OTHER"], role_statuses={"PROJECT_OWNER": "confirmed", "OTHER": "confirmed"}, temporal_scope="current"),
                ProjectParticipation(project_id="project:avc", entity_id="org:unknown", roles=["EPC", "GENERAL_CONTRACTOR"], role_statuses={"EPC": "confirmed", "GENERAL_CONTRACTOR": "confirmed"}, temporal_scope="current"),
                ProjectParticipation(project_id="project:avc", entity_id="org:gov-a", roles=["GOVERNMENT_PARTNER", "REGULATORY_AUTHORITY"], role_statuses={"GOVERNMENT_PARTNER": "confirmed", "REGULATORY_AUTHORITY": "confirmed"}, temporal_scope="current"),
                ProjectParticipation(project_id="project:avc", entity_id="org:gov-b", roles=["GOVERNMENT_PARTNER"], role_statuses={"GOVERNMENT_PARTNER": "confirmed"}, temporal_scope="current"),
                ProjectParticipation(project_id="project:avc", entity_id="org:project", roles=["OTHER"], role_statuses={"OTHER": "confirmed"}, temporal_scope="current"),
                ProjectParticipation(project_id="project:avc", entity_id="org:ticker", roles=["OTHER"], role_statuses={"OTHER": "confirmed"}, temporal_scope="current"),
            ],
            canonical_relationships=[
                CanonicalRelationship(from_entity_id="org:avc", to_entity_id="org:avc-technology", relationship_type="SUBSIDIARY_OF", status="confirmed", temporal_scope="current"),
                CanonicalRelationship(from_entity_id="org:avc-tech-long", to_entity_id="org:unknown", relationship_type="AWARDS_CONTRACT_TO", description="Mechanical & electrical and fit-out works contract", status="confirmed", temporal_scope="current"),
            ],
            research_gaps=["Investor company not confirmed", "Design / Engineering — Not confirmed"],
        )

        result = build_v3_result(v2, "AVC Kim Bang plant")
        nodes = result.relationship_map.nodes

        self.assertEqual(sum("AVC Technology (Vietnam)" in node.company for node in nodes), 1)
        self.assertEqual(sum("Ninh Binh provincial authorities" in node.company for node in nodes), 1)
        self.assertFalse(any("listed company" in node.company for node in nodes))
        self.assertFalse(any("Kim Bang project" in node.company for node in nodes))
        contractor = next(node for node in nodes if node.company == "創興國際建設有限公司")
        self.assertEqual(contractor.roles, ["MEP_CONTRACTOR"])
        self.assertNotIn("Investor company not confirmed", result.relationship_map.research_gaps)
        self.assertEqual(result.priority_1[0].company, "AVC Technology (Vietnam) Company Limited")
        subsidiary = next(item for item in result.relationship_map.relations if item.relation_type == "SUBSIDIARY_OF")
        self.assertIn("avc-technology", subsidiary.from_node)
        self.assertIn("org:avc", subsidiary.to_node)
        contract = next(item for item in result.relationship_map.relations if item.relation_type == "AWARDS_CONTRACT_TO")
        self.assertEqual(contract.label, "M&E / Fit-out 계약")
        self.assertNotIn("disclosure", contract.label.casefold())
        self.assertEqual(len(result.questions_to_ask), 4)
        self.assertIn("M&E와 Fit-out 외에", result.questions_to_ask[0].question)
        self.assertIn("발주 일정과 공급사 등록", result.questions_to_ask[2].question)
        self.assertIn("추가 투자 계획", result.questions_to_ask[3].question)
        self.assertFalse(any("투자 의사결정에도 참여" in item.question for item in result.questions_to_ask))

    def test_ecosystem_mentions_do_not_clutter_current_project_map(self) -> None:
        v2 = demo_v2_result()
        v2.context.business_structure = []
        v2.relationship_map = nic_thermo_v2_map()
        nic_id = next(entity.entity_id for entity in v2.relationship_map.entities if "Innovation" in entity.canonical_name)
        thermo_id = next(entity.entity_id for entity in v2.relationship_map.entities if "Thermo" in entity.canonical_name)
        additions = [
            ("org:fpt", "FPT Corporation", ["END_CLIENT", "STRATEGIC_PARTNER"], ["Named participant / collaborator; intended user at forum"]),
            ("org:distributor", "Vietnam Lab Distributor", ["EQUIPMENT_SUPPLIER", "VENDOR"], ["Authorized distributor channel for product groups"]),
            ("org:official", "Deputy Prime Minister Example Person", ["GOVERNMENT_PARTNER", "REGULATORY_AUTHORITY"], ["Meeting with delegation"]),
        ]
        for entity_id, name, roles, evidence in additions:
            v2.relationship_map.entities.append(EntityIdentity(
                entity_id=entity_id,
                canonical_name=name,
                organization_type="PRIVATE_COMPANY",
                organization_scope="local_entity",
                status="confirmed",
                evidence_labels=evidence,
            ))
            v2.relationship_map.participations.append(ProjectParticipation(
                project_id=v2.relationship_map.project_id,
                entity_id=entity_id,
                roles=roles,
                role_statuses={role: "confirmed" for role in roles},
                temporal_scope="current",
                evidence_labels=evidence,
            ))
        v2.relationship_map.canonical_relationships.extend([
            CanonicalRelationship(
                from_entity_id=nic_id,
                to_entity_id="org:fpt",
                relationship_type="STRATEGIC_PARTNERSHIP",
                relationship_basis="Named as intended partners / users at the forum",
                status="confirmed",
                temporal_scope="current",
            ),
            CanonicalRelationship(
                from_entity_id=thermo_id,
                to_entity_id="org:official",
                relationship_type="INVESTS_IN",
                relationship_basis="Government meeting with company delegation",
                description="Political engagement and facilitation intent",
                status="confirmed",
                temporal_scope="current",
            ),
        ])

        result = build_v3_result(v2, "NIC Thermo Fisher shared laboratory MOU")
        companies = {node.company for node in result.relationship_map.nodes}

        self.assertIn("National Innovation Centre (NIC)", companies)
        self.assertIn("Thermo Fisher Scientific", companies)
        self.assertNotIn("FPT Corporation", companies)
        self.assertNotIn("Vietnam Lab Distributor", companies)
        self.assertNotIn("Deputy Prime Minister Example Person", companies)
        self.assertEqual([edge.relation_type for edge in result.relationship_map.relations], ["CO_DEVELOPMENT"])
        candidate_ids = {
            item.entity_id for item in result.v2_snapshot.relationship_map.participations
            if item.temporal_scope == "candidate"
        }
        self.assertTrue({"org:fpt", "org:distributor", "org:official"}.issubset(candidate_ids))

    def test_upstream_gate_separates_current_participants_from_research_leads(self) -> None:
        bundle = ResearchBundle(
            quick=QuickResearchResult(company="Thermo Fisher Scientific", project_name="Shared lab"),
            research_mode="deep",
            stage_gate_status="targeting",
            stage_gate_reason="MOU",
            seed_understanding=SeedUnderstanding(
                company="Thermo Fisher Scientific",
                owner_candidate="Vietnam National Innovation Center (NIC)",
            ),
            research_rounds=[ResearchRoundResult(
                round_number=1,
                focus="Current participants",
                findings=DeepResearchResult(),
                discovered_entities=[
                    DiscoveredEntity(
                        name="Vietnam National Innovation Center (NIC)",
                        entity_type="owner",
                        project_roles=["PROJECT_OWNER", "HOST"],
                        credibility="confirmed",
                        project_specific=True,
                        participation_status="current_participant",
                        participation_basis="Official MOU signatory and project host",
                        role_evidence="NIC signed the project MOU as host.",
                        evidence_labels=["Official MOU"],
                        source_urls=[SOURCE_URL],
                    ),
                    DiscoveredEntity(
                        name="Thermo Fisher Scientific",
                        entity_type="technology_partner",
                        project_roles=["CO_DEVELOPMENT_PARTNER", "TECHNOLOGY_PROVIDER"],
                        credibility="confirmed",
                        project_specific=True,
                        participation_status="current_participant",
                        participation_basis="Official MOU signatory",
                        role_evidence="Thermo Fisher signed the project MOU as technology partner.",
                        evidence_labels=["Official MOU"],
                        source_urls=[SOURCE_URL],
                    ),
                    DiscoveredEntity(
                        name="FPT Corporation",
                        entity_type="end_client",
                        project_roles=["END_CLIENT", "STRATEGIC_PARTNER"],
                        credibility="confirmed",
                        project_specific=False,
                        participation_status="candidate",
                        participation_basis="Intended user mentioned at forum",
                        role_evidence="Named as an intended user, not a contracted participant.",
                        evidence_labels=["Forum coverage"],
                        source_urls=[SOURCE_URL],
                    ),
                    DiscoveredEntity(
                        name="Vietnam Lab Distributor",
                        entity_type="vendor",
                        project_roles=["VENDOR", "EQUIPMENT_SUPPLIER"],
                        credibility="confirmed",
                        project_specific=False,
                        participation_status="reference_only",
                        participation_basis="General authorized distributor channel",
                        role_evidence="Distributor listing is not tied to this project.",
                        evidence_labels=["Distributor page"],
                        source_urls=[SOURCE_URL],
                    ),
                ],
                discovered_relationships=[
                    DiscoveredRelationship(
                        from_entity="Vietnam National Innovation Center (NIC)",
                        to_entity="Thermo Fisher Scientific",
                        relationship_type="MOU",
                        canonical_relationship_type="MOU",
                        credibility="confirmed",
                        project_specific=True,
                        role_evidence="Both parties signed the project MOU.",
                        evidence_labels=["Official MOU"],
                        source_urls=[SOURCE_URL],
                    ),
                    DiscoveredRelationship(
                        from_entity="Thermo Fisher Scientific",
                        to_entity="FPT Corporation",
                        relationship_type="strategic partnership",
                        canonical_relationship_type="STRATEGIC_PARTNERSHIP",
                        credibility="confirmed",
                        project_specific=False,
                        role_evidence="Only an intended-user reference.",
                        evidence_labels=["Forum coverage"],
                        source_urls=[SOURCE_URL],
                    ),
                ],
            )],
        )
        intelligence = ProjectIntelligence()

        relmap = build_relationship_map(bundle, intelligence)
        participation_by_name = {
            entity.canonical_name: next(item for item in relmap.participations if item.entity_id == entity.entity_id)
            for entity in relmap.entities
        }

        self.assertEqual(participation_by_name["Vietnam National Innovation Center (NIC)"].temporal_scope, "current")
        self.assertEqual(participation_by_name["Thermo Fisher Scientific"].temporal_scope, "current")
        self.assertEqual(participation_by_name["FPT Corporation"].temporal_scope, "candidate")
        self.assertEqual(participation_by_name["Vietnam Lab Distributor"].temporal_scope, "candidate")
        self.assertEqual(intelligence.owner_summary, "Vietnam National Innovation Center (NIC)")
        self.assertEqual(
            [(item.relationship_type, item.status, item.temporal_scope) for item in relmap.canonical_relationships],
            [("MOU", "confirmed", "current"), ("STRATEGIC_PARTNERSHIP", "candidate", "candidate")],
        )


if __name__ == "__main__":
    unittest.main()
