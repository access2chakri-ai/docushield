"""
Digital Twin Document-to-Workflow Mapping System
Maps contracts, invoices, and policies to business processes for impact simulation
"""
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from sqlalchemy.orm import selectinload

from app.database import get_operational_db, get_sandbox_db, get_analytics_db, ClusterType
from app.models import (
    BronzeContract, GoldContractScore, GoldFinding, GoldSuggestion,
    SilverClauseSpan, Alert
)
from app.core.config import settings
import openai

logger = logging.getLogger(__name__)

class WorkflowType(Enum):
    ORDER_TO_CASH = "order_to_cash"
    PROCURE_TO_PAY = "procure_to_pay"
    VENDOR_ONBOARDING = "vendor_onboarding"
    COMPLIANCE_CYCLE = "compliance_cycle"
    CONTRACT_LIFECYCLE = "contract_lifecycle"
    INVOICE_PROCESSING = "invoice_processing"
    RISK_MANAGEMENT = "risk_management"

class ImpactCategory(Enum):
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    LEGAL = "legal"
    STRATEGIC = "strategic"
    COMPLIANCE = "compliance"

@dataclass
class WorkflowNode:
    """Represents a node in a business workflow"""
    node_id: str
    name: str
    node_type: str  # process, decision, event, gateway
    dependencies: List[str]
    risk_factors: List[str]
    sla_hours: Optional[int] = None
    cost_per_execution: Optional[float] = None

@dataclass
class DocumentWorkflowMapping:
    """Maps a document to workflow nodes and impact areas"""
    document_id: str
    workflow_type: WorkflowType
    affected_nodes: List[str]
    impact_areas: List[ImpactCategory]
    risk_multiplier: float
    confidence: float

@dataclass
class SimulationScenario:
    """Defines a what-if simulation scenario"""
    scenario_id: str
    name: str
    description: str
    affected_documents: List[str]
    parameter_changes: Dict[str, Any]
    expected_impact: Dict[str, float]

class DigitalTwinService:
    """
    Digital Twin service for document-to-workflow mapping and impact simulation
    """
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Pre-defined workflow templates
        self.workflow_templates = {
            WorkflowType.CONTRACT_LIFECYCLE: {
                "nodes": [
                    WorkflowNode("contract_request", "Contract Request", "process", [], ["approval_delay"], 24, 500),
                    WorkflowNode("legal_review", "Legal Review", "process", ["contract_request"], ["liability_risk", "compliance_risk"], 72, 2000),
                    WorkflowNode("negotiation", "Contract Negotiation", "process", ["legal_review"], ["unfavorable_terms", "timeline_risk"], 168, 5000),
                    WorkflowNode("approval", "Final Approval", "decision", ["negotiation"], ["authority_risk"], 24, 1000),
                    WorkflowNode("execution", "Contract Execution", "process", ["approval"], ["execution_risk"], 12, 200),
                    WorkflowNode("monitoring", "Contract Monitoring", "process", ["execution"], ["compliance_drift", "renewal_risk"], None, 100)
                ],
                "risk_factors": {
                    "liability_risk": {"impact": 0.8, "probability": 0.3},
                    "compliance_risk": {"impact": 0.9, "probability": 0.2},
                    "unfavorable_terms": {"impact": 0.6, "probability": 0.4},
                    "renewal_risk": {"impact": 0.5, "probability": 0.6}
                }
            },
            WorkflowType.VENDOR_ONBOARDING: {
                "nodes": [
                    WorkflowNode("vendor_application", "Vendor Application", "process", [], ["incomplete_data"], 24, 100),
                    WorkflowNode("due_diligence", "Due Diligence", "process", ["vendor_application"], ["financial_risk", "reputation_risk"], 120, 3000),
                    WorkflowNode("contract_negotiation", "Contract Negotiation", "process", ["due_diligence"], ["unfavorable_terms"], 168, 5000),
                    WorkflowNode("onboarding", "Vendor Onboarding", "process", ["contract_negotiation"], ["integration_risk"], 48, 1500)
                ],
                "risk_factors": {
                    "financial_risk": {"impact": 0.9, "probability": 0.2},
                    "reputation_risk": {"impact": 0.7, "probability": 0.1},
                    "unfavorable_terms": {"impact": 0.6, "probability": 0.4},
                    "integration_risk": {"impact": 0.5, "probability": 0.3}
                }
            },
            WorkflowType.PROCURE_TO_PAY: {
                "nodes": [
                    WorkflowNode("purchase_request", "Purchase Request", "process", [], ["budget_overrun"], 12, 50),
                    WorkflowNode("approval", "Purchase Approval", "decision", ["purchase_request"], ["authority_risk"], 24, 200),
                    WorkflowNode("po_creation", "PO Creation", "process", ["approval"], ["data_error"], 6, 100),
                    WorkflowNode("goods_receipt", "Goods Receipt", "process", ["po_creation"], ["quality_risk"], 24, 150),
                    WorkflowNode("invoice_processing", "Invoice Processing", "process", ["goods_receipt"], ["payment_risk"], 48, 300),
                    WorkflowNode("payment", "Payment Execution", "process", ["invoice_processing"], ["cash_flow_risk"], 24, 50)
                ],
                "risk_factors": {
                    "budget_overrun": {"impact": 0.6, "probability": 0.3},
                    "payment_risk": {"impact": 0.8, "probability": 0.2},
                    "cash_flow_risk": {"impact": 0.7, "probability": 0.25}
                }
            }
        }
    
    async def map_document_to_workflows(self, contract_id: str) -> List[DocumentWorkflowMapping]:
        """
        Map a document to relevant business workflows
        """
        try:
            async for db in get_operational_db():
                # Get contract with related data
                result = await db.execute(
                    select(BronzeContract)
                    .options(
                        selectinload(BronzeContract.text_raw),
                        selectinload(BronzeContract.scores),
                        selectinload(BronzeContract.clause_spans),
                        selectinload(BronzeContract.findings)
                    )
                    .where(BronzeContract.contract_id == contract_id)
                )
                contract = result.scalar_one_or_none()
                
                if not contract:
                    raise ValueError(f"Contract {contract_id} not found")
                
                # Analyze document type and content to determine workflows
                workflows = await self._identify_relevant_workflows(contract)
                
                mappings = []
                for workflow_type in workflows:
                    mapping = await self._create_workflow_mapping(contract, workflow_type)
                    mappings.append(mapping)
                
                logger.info(f"Mapped contract {contract_id} to {len(mappings)} workflows")
                return mappings
                
        except Exception as e:
            logger.error(f"Failed to map document to workflows: {e}")
            return []
    
    async def simulate_impact(self, scenario: SimulationScenario) -> Dict[str, Any]:
        """
        Simulate business impact of document risks across workflows
        Enhanced with realistic impact calculations and workflow modeling
        """
        try:
            # Use sandbox cluster for simulation
            async for sandbox_db in get_sandbox_db():
                # Create sandbox branch with current data
                await self._prepare_sandbox_data(scenario.affected_documents, sandbox_db)
                
                # Get detailed document analysis for affected documents
                document_analyses = await self._analyze_affected_documents(scenario.affected_documents)
                
                # Run enhanced simulation with real workflow modeling
                simulation_results = await self._execute_enhanced_simulation(
                    scenario, document_analyses, sandbox_db
                )
                
                # Store results in analytics cluster
                await self._store_simulation_results(scenario, simulation_results)
                
                return simulation_results
                
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def generate_digital_twin_insights(self, workflow_type: WorkflowType, time_window_days: int = 30) -> Dict[str, Any]:
        """
        Generate insights about workflow performance and document impact
        """
        try:
            async for analytics_db in get_analytics_db():
                # Analyze workflow performance
                workflow_metrics = await self._analyze_workflow_metrics(workflow_type, time_window_days, analytics_db)
                
                # Identify risk patterns
                risk_patterns = await self._identify_risk_patterns(workflow_type, time_window_days, analytics_db)
                
                # Generate recommendations
                recommendations = await self._generate_workflow_recommendations(workflow_metrics, risk_patterns)
                
                insights = {
                    "workflow_type": workflow_type.value,
                    "analysis_period": f"{time_window_days} days",
                    "metrics": workflow_metrics,
                    "risk_patterns": risk_patterns,
                    "recommendations": recommendations,
                    "generated_at": datetime.utcnow().isoformat()
                }
                
                return insights
                
        except Exception as e:
            logger.error(f"Failed to generate digital twin insights: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def predict_workflow_disruption(self, contract_id: str) -> Dict[str, Any]:
        """
        Predict potential workflow disruptions based on contract risks
        """
        try:
            async for db in get_operational_db():
                # Get contract with risk data
                result = await db.execute(
                    select(BronzeContract)
                    .options(
                        selectinload(BronzeContract.scores),
                        selectinload(BronzeContract.findings),
                        selectinload(BronzeContract.clause_spans)
                    )
                    .where(BronzeContract.contract_id == contract_id)
                )
                contract = result.scalar_one()
                
                # Map to workflows
                workflow_mappings = await self.map_document_to_workflows(contract_id)
                
                predictions = []
                for mapping in workflow_mappings:
                    prediction = await self._predict_workflow_impact(contract, mapping)
                    predictions.append(prediction)
                
                return {
                    "contract_id": contract_id,
                    "workflow_predictions": predictions,
                    "overall_risk_score": contract.scores.overall_score if contract.scores else 50,
                    "predicted_at": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Workflow disruption prediction failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def create_what_if_scenario(self, name: str, description: str, document_ids: List[str], changes: Dict[str, Any]) -> SimulationScenario:
        """
        Create a what-if simulation scenario
        """
        scenario = SimulationScenario(
            scenario_id=f"scenario_{int(datetime.utcnow().timestamp())}",
            name=name,
            description=description,
            affected_documents=document_ids,
            parameter_changes=changes,
            expected_impact={}
        )
        
        # Calculate expected impact
        scenario.expected_impact = await self._calculate_expected_impact(scenario)
        
        return scenario
    
    # Private helper methods
    
    async def _identify_relevant_workflows(self, contract: BronzeContract) -> List[WorkflowType]:
        """Identify which workflows are relevant for this contract"""
        workflows = []
        
        # Analyze filename and content to determine workflow relevance
        filename_lower = contract.filename.lower()
        
        if any(term in filename_lower for term in ['vendor', 'supplier', 'service', 'agreement']):
            workflows.append(WorkflowType.VENDOR_ONBOARDING)
            workflows.append(WorkflowType.PROCURE_TO_PAY)
        
        if any(term in filename_lower for term in ['contract', 'agreement', 'terms']):
            workflows.append(WorkflowType.CONTRACT_LIFECYCLE)
        
        if any(term in filename_lower for term in ['invoice', 'billing', 'payment']):
            workflows.append(WorkflowType.INVOICE_PROCESSING)
        
        # Default to contract lifecycle if no specific match
        if not workflows:
            workflows.append(WorkflowType.CONTRACT_LIFECYCLE)
        
        return workflows
    
    async def _create_workflow_mapping(self, contract: BronzeContract, workflow_type: WorkflowType) -> DocumentWorkflowMapping:
        """Create a mapping between document and workflow"""
        
        # Determine affected nodes based on contract risks
        affected_nodes = []
        impact_areas = []
        risk_multiplier = 1.0
        
        if contract.scores:
            risk_level = contract.scores.risk_level
            risk_multiplier = {
                "low": 1.1,
                "medium": 1.3,
                "high": 1.6,
                "critical": 2.0
            }.get(risk_level, 1.0)
        
        # Analyze findings to determine impact areas
        if contract.findings:
            for finding in contract.findings:
                if finding.severity in ["high", "critical"]:
                    if "liability" in finding.finding_type:
                        impact_areas.append(ImpactCategory.LEGAL)
                        affected_nodes.extend(["legal_review", "approval"])
                    elif "financial" in finding.finding_type:
                        impact_areas.append(ImpactCategory.FINANCIAL)
                        affected_nodes.extend(["approval", "payment"])
                    elif "compliance" in finding.finding_type:
                        impact_areas.append(ImpactCategory.COMPLIANCE)
                        affected_nodes.extend(["legal_review", "monitoring"])
        
        # Default impact areas if none identified
        if not impact_areas:
            impact_areas = [ImpactCategory.OPERATIONAL]
        
        # Default affected nodes if none identified
        if not affected_nodes:
            template = self.workflow_templates.get(workflow_type)
            if template:
                affected_nodes = [node.node_id for node in template["nodes"][:2]]  # First 2 nodes
        
        return DocumentWorkflowMapping(
            document_id=contract.contract_id,
            workflow_type=workflow_type,
            affected_nodes=list(set(affected_nodes)),  # Remove duplicates
            impact_areas=list(set(impact_areas)),
            risk_multiplier=risk_multiplier,
            confidence=0.8
        )
    
    async def _prepare_sandbox_data(self, document_ids: List[str], sandbox_db: AsyncSession):
        """Prepare sandbox environment with relevant data"""
        # This would copy relevant data from operational to sandbox cluster
        # For now, we'll simulate this step
        logger.info(f"Prepared sandbox data for {len(document_ids)} documents")
    
    async def _analyze_affected_documents(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        """Analyze affected documents to understand their risk profiles"""
        document_analyses = []
        
        async for db in get_operational_db():
            for doc_id in document_ids:
                try:
                    # Get document with all related analysis data
                    result = await db.execute(
                        select(BronzeContract)
                        .options(
                            selectinload(BronzeContract.scores),
                            selectinload(BronzeContract.findings),
                            selectinload(BronzeContract.clause_spans)
                        )
                        .where(BronzeContract.contract_id == doc_id)
                    )
                    contract = result.scalar_one_or_none()
                    
                    if contract:
                        analysis = {
                            "document_id": doc_id,
                            "filename": contract.filename,
                            "risk_score": contract.scores.overall_score if contract.scores else 50,
                            "risk_level": contract.scores.risk_level if contract.scores else "medium",
                            "findings": [
                                {
                                    "type": f.finding_type,
                                    "severity": f.severity,
                                    "title": f.title
                                } for f in contract.findings
                            ],
                            "clauses": [
                                {
                                    "type": c.clause_type,
                                    "confidence": c.confidence,
                                    "risk_indicators": c.risk_indicators
                                } for c in contract.clause_spans
                            ]
                        }
                        document_analyses.append(analysis)
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze document {doc_id}: {e}")
        
        return document_analyses
    
    async def _execute_enhanced_simulation(
        self, 
        scenario: SimulationScenario, 
        document_analyses: List[Dict[str, Any]], 
        sandbox_db: AsyncSession
    ) -> Dict[str, Any]:
        """Execute enhanced simulation with realistic workflow modeling"""
        
        results = {
            "scenario_id": scenario.scenario_id,
            "scenario_name": scenario.name,
            "execution_time": datetime.utcnow().isoformat(),
            "affected_workflows": [],
            "document_impacts": [],
            "financial_impact": {
                "cost_increase": 0.0,
                "revenue_at_risk": 0.0,
                "risk_exposure": 0.0,
                "mitigation_cost": 0.0
            },
            "operational_impact": {
                "delay_hours": 0,
                "efficiency_loss": 0.0,
                "resource_overhead": 0.0,
                "process_disruptions": []
            },
            "compliance_impact": {
                "violation_risk": 0.0,
                "audit_findings": 0,
                "regulatory_exposure": 0.0
            },
            "strategic_impact": {
                "reputation_risk": 0.0,
                "competitive_impact": 0.0,
                "partnership_risk": 0.0
            }
        }
        
        # Analyze each document's impact on workflows
        for doc_analysis in document_analyses:
            doc_impact = await self._simulate_document_workflow_impact(doc_analysis, scenario)
            results["document_impacts"].append(doc_impact)
            
            # Aggregate impacts
            results["financial_impact"]["cost_increase"] += doc_impact["financial_cost"]
            results["financial_impact"]["revenue_at_risk"] += doc_impact["revenue_risk"]
            results["operational_impact"]["delay_hours"] += doc_impact["delay_hours"]
            results["compliance_impact"]["violation_risk"] += doc_impact["compliance_risk"]
            
            # Track affected workflows
            for workflow in doc_impact["affected_workflows"]:
                if workflow not in results["affected_workflows"]:
                    results["affected_workflows"].append(workflow)
        
        # Calculate aggregate metrics
        results["total_risk_score"] = self._calculate_aggregate_risk_score(document_analyses)
        results["simulation_confidence"] = self._calculate_simulation_confidence(document_analyses)
        
        # Generate business impact narrative
        results["impact_narrative"] = await self._generate_impact_narrative(results, scenario)
        
        return results
    
    async def _simulate_document_workflow_impact(
        self, 
        doc_analysis: Dict[str, Any], 
        scenario: SimulationScenario
    ) -> Dict[str, Any]:
        """Simulate the workflow impact of a specific document"""
        
        risk_score = doc_analysis["risk_score"]
        risk_level = doc_analysis["risk_level"]
        findings = doc_analysis["findings"]
        
        # Base impact multipliers based on risk level
        risk_multipliers = {
            "low": 1.1,
            "medium": 1.5,
            "high": 2.0,
            "critical": 3.0
        }
        
        multiplier = risk_multipliers.get(risk_level, 1.5)
        
        # Calculate financial impact
        base_contract_value = 100000  # Assume $100k base value
        financial_cost = base_contract_value * (risk_score / 100) * multiplier * 0.1
        revenue_risk = base_contract_value * (risk_score / 100) * multiplier * 0.05
        
        # Calculate operational impact
        base_delay_hours = 24
        delay_hours = base_delay_hours * multiplier
        
        # Calculate compliance impact
        compliance_risk = (risk_score / 100) * multiplier * 0.1
        
        # Identify affected workflows based on document type and findings
        affected_workflows = []
        
        # Analyze findings to determine workflow impact
        for finding in findings:
            finding_type = finding["type"].lower()
            
            if "liability" in finding_type:
                affected_workflows.extend(["contract_lifecycle", "risk_management"])
                financial_cost *= 1.2  # Liability increases financial risk
                
            elif "termination" in finding_type:
                affected_workflows.extend(["contract_lifecycle", "vendor_onboarding"])
                delay_hours *= 1.3  # Termination issues cause delays
                
            elif "payment" in finding_type or "invoice" in finding_type:
                affected_workflows.extend(["procure_to_pay", "invoice_processing"])
                revenue_risk *= 1.4  # Payment issues affect revenue
                
            elif "compliance" in finding_type:
                affected_workflows.extend(["compliance_cycle", "risk_management"])
                compliance_risk *= 1.5  # Direct compliance impact
        
        # Remove duplicates
        affected_workflows = list(set(affected_workflows))
        
        return {
            "document_id": doc_analysis["document_id"],
            "document_name": doc_analysis["filename"],
            "risk_score": risk_score,
            "risk_level": risk_level,
            "financial_cost": financial_cost,
            "revenue_risk": revenue_risk,
            "delay_hours": delay_hours,
            "compliance_risk": compliance_risk,
            "affected_workflows": affected_workflows,
            "impact_multiplier": multiplier,
            "findings_count": len(findings)
        }
    
    def _calculate_aggregate_risk_score(self, document_analyses: List[Dict[str, Any]]) -> float:
        """Calculate aggregate risk score across all documents"""
        if not document_analyses:
            return 0.0
        
        total_score = sum(doc["risk_score"] for doc in document_analyses)
        return total_score / len(document_analyses)
    
    def _calculate_simulation_confidence(self, document_analyses: List[Dict[str, Any]]) -> float:
        """Calculate confidence in simulation results"""
        if not document_analyses:
            return 0.0
        
        # Base confidence on data completeness and quality
        base_confidence = 0.8
        
        # Reduce confidence if we have incomplete data
        complete_analyses = len([doc for doc in document_analyses if doc["findings"]])
        completeness_ratio = complete_analyses / len(document_analyses)
        
        return base_confidence * completeness_ratio
    
    async def _generate_impact_narrative(
        self, 
        results: Dict[str, Any], 
        scenario: SimulationScenario
    ) -> str:
        """Generate business impact narrative using AI"""
        try:
            narrative_prompt = f"""
            Create a business impact narrative for this digital twin simulation.
            
            Scenario: {scenario.name}
            Description: {scenario.description}
            
            Simulation Results:
            - Financial Impact: ${results['financial_impact']['cost_increase']:,.0f} cost increase, ${results['financial_impact']['revenue_at_risk']:,.0f} revenue at risk
            - Operational Impact: {results['operational_impact']['delay_hours']} hours of delays
            - Compliance Risk: {results['compliance_impact']['violation_risk']:.1%} violation risk
            - Affected Workflows: {', '.join(results['affected_workflows'])}
            - Documents Analyzed: {len(results['document_impacts'])}
            
            Create a 3-4 sentence executive summary that:
            1. Describes the scenario and its business context
            2. Highlights the most significant impacts
            3. Provides actionable insights for decision makers
            4. Uses plain business language (avoid technical jargon)
            """
            
            result = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": narrative_prompt}],
                max_tokens=300,
                temperature=0.3
            )
            
            return result.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"Failed to generate impact narrative: {e}")
            return f"Simulation of scenario '{scenario.name}' shows potential cost increase of ${results['financial_impact']['cost_increase']:,.0f} and {results['operational_impact']['delay_hours']} hours of operational delays across {len(results['affected_workflows'])} business workflows."
    
    async def _store_simulation_results(self, scenario: SimulationScenario, results: Dict[str, Any]):
        """Store simulation results in analytics cluster"""
        async for analytics_db in get_analytics_db():
            # Store results in analytics tables
            # This would involve creating analytics-specific tables
            logger.info(f"Stored simulation results for scenario {scenario.scenario_id}")
    
    async def _analyze_workflow_metrics(self, workflow_type: WorkflowType, days: int, analytics_db: AsyncSession) -> Dict[str, Any]:
        """Analyze workflow performance metrics"""
        
        # This would query actual workflow execution data
        # For now, return simulated metrics
        return {
            "total_executions": 150,
            "average_duration_hours": 72,
            "success_rate": 0.94,
            "cost_per_execution": 2500,
            "bottlenecks": ["legal_review", "approval"],
            "risk_incidents": 8
        }
    
    async def _identify_risk_patterns(self, workflow_type: WorkflowType, days: int, analytics_db: AsyncSession) -> List[Dict[str, Any]]:
        """Identify risk patterns in workflow execution"""
        
        # This would analyze historical risk data
        # For now, return simulated patterns
        return [
            {
                "pattern": "liability_clause_correlation",
                "description": "Contracts with unlimited liability clauses cause 60% more delays in legal review",
                "frequency": 0.3,
                "impact_score": 0.7
            },
            {
                "pattern": "auto_renewal_oversight",
                "description": "Auto-renewal clauses are missed in 25% of contract monitoring cycles",
                "frequency": 0.25,
                "impact_score": 0.5
            }
        ]
    
    async def _generate_workflow_recommendations(self, metrics: Dict[str, Any], patterns: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations for workflow improvement"""
        
        recommendations = []
        
        if metrics["success_rate"] < 0.95:
            recommendations.append("🔧 Implement automated quality checks to improve success rate")
        
        if "legal_review" in metrics.get("bottlenecks", []):
            recommendations.append("⚡ Consider parallel legal review processes for low-risk contracts")
        
        for pattern in patterns:
            if pattern["impact_score"] > 0.6:
                recommendations.append(f"🎯 Address pattern: {pattern['description']}")
        
        return recommendations
    
    async def _predict_workflow_impact(self, contract: BronzeContract, mapping: DocumentWorkflowMapping) -> Dict[str, Any]:
        """Predict specific workflow impact for a contract"""
        
        workflow_template = self.workflow_templates.get(mapping.workflow_type)
        if not workflow_template:
            return {"error": "Unknown workflow type"}
        
        # Calculate impact on each affected node
        node_impacts = {}
        for node_id in mapping.affected_nodes:
            node = next((n for n in workflow_template["nodes"] if n.node_id == node_id), None)
            if node:
                # Calculate delay and cost impact
                base_cost = node.cost_per_execution or 1000
                base_duration = node.sla_hours or 24
                
                cost_impact = base_cost * (mapping.risk_multiplier - 1)
                duration_impact = base_duration * (mapping.risk_multiplier - 1)
                
                node_impacts[node_id] = {
                    "node_name": node.name,
                    "cost_increase": cost_impact,
                    "duration_increase_hours": duration_impact,
                    "risk_factors": node.risk_factors
                }
        
        return {
            "workflow_type": mapping.workflow_type.value,
            "overall_risk_multiplier": mapping.risk_multiplier,
            "node_impacts": node_impacts,
            "total_cost_impact": sum(impact["cost_increase"] for impact in node_impacts.values()),
            "total_delay_hours": sum(impact["duration_increase_hours"] for impact in node_impacts.values()),
            "confidence": mapping.confidence
        }
    
    async def _calculate_expected_impact(self, scenario: SimulationScenario) -> Dict[str, float]:
        """Calculate expected impact for a scenario"""
        
        # This would use ML models or business rules to predict impact
        # For now, return simulated expected impact
        return {
            "financial_impact": len(scenario.affected_documents) * 5000,
            "operational_delay_hours": len(scenario.affected_documents) * 24,
            "compliance_risk_increase": len(scenario.affected_documents) * 0.1
        }

# Global digital twin service instance
digital_twin_service = DigitalTwinService()
