"""
Document Intelligence Digital Twin router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from app.core.dependencies import get_current_active_user
from app.schemas.requests import SimulationRequest
from app.schemas.responses import DigitalTwinInsightsResponse
from app.services.digital_twin import document_digital_twin, SimulationScenario

router = APIRouter(prefix="/api/digital-twin", tags=["digital-twin"])

@router.get("/insights")
async def get_workflow_insights(
    current_user = Depends(get_current_active_user)
):
    """Get Document Processing Digital Twin insights"""
    try:
        # Get insights from digital twin service
        insights = await document_digital_twin.get_workflow_insights(
            user_id=current_user.user_id
        )
        
        return {
            "user_id": current_user.user_id,
            "insights": insights,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Digital twin insights failed: {str(e)}")

@router.get("/scenarios")
async def list_scenarios(
    current_user = Depends(get_current_active_user)
):
    """Get available simulation scenarios"""
    try:
        scenarios = await document_digital_twin.get_available_scenarios()
        return {
            "scenarios": scenarios,
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get scenarios: {str(e)}")

@router.get("/system-state")
async def get_system_state(
    current_user = Depends(get_current_active_user)
):
    """Get current document processing system state"""
    try:
        state = await document_digital_twin.get_current_system_state(current_user.user_id)
        return {
            "user_id": current_user.user_id,
            "system_state": {
                "total_documents": state.total_documents,
                "processing_capacity": state.processing_capacity,
                "average_processing_time": state.average_processing_time,
                "accuracy_rate": state.accuracy_rate,
                "risk_distribution": state.risk_distribution,
                "compliance_rate": state.compliance_rate,
                "knowledge_coverage": state.knowledge_coverage,
                "system_health": state.system_health
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system state: {str(e)}")

@router.post("/simulate")
async def create_simulation(
    request: SimulationRequest,
    current_user = Depends(get_current_active_user)
):
    """Create a new Document Processing simulation"""
    try:
        # Convert scenario name to enum
        try:
            scenario_type = SimulationScenario(request.scenario_name.lower().replace(" ", "_"))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid scenario type: {request.scenario_name}")
        
        # Create simulation
        simulation_result = await document_digital_twin.create_simulation(
            scenario_type=scenario_type,
            user_id=current_user.user_id,
            custom_parameters=request.parameter_changes
        )
        
        return {
            "simulation_id": simulation_result.scenario_id,
            "scenario_name": request.scenario_name,
            "baseline_state": {
                "total_documents": simulation_result.baseline_state.total_documents,
                "processing_capacity": simulation_result.baseline_state.processing_capacity,
                "average_processing_time": simulation_result.baseline_state.average_processing_time,
                "accuracy_rate": simulation_result.baseline_state.accuracy_rate,
                "system_health": simulation_result.baseline_state.system_health
            },
            "simulated_state": {
                "total_documents": simulation_result.simulated_state.total_documents,
                "processing_capacity": simulation_result.simulated_state.processing_capacity,
                "average_processing_time": simulation_result.simulated_state.average_processing_time,
                "accuracy_rate": simulation_result.simulated_state.accuracy_rate,
                "system_health": simulation_result.simulated_state.system_health
            },
            "impact_analysis": simulation_result.impact_analysis,
            "recommendations": simulation_result.recommendations,
            "confidence_score": simulation_result.confidence_score,
            "execution_time_ms": simulation_result.execution_time_ms
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation creation failed: {str(e)}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation creation failed: {str(e)}")

@router.get("/simulations")
async def list_simulations(
    limit: int = 20,
    current_user = Depends(get_current_active_user)
):
    """List user's Digital Twin simulations"""
    try:
        simulations = await digital_twin_service.get_user_simulations(
            user_id=current_user.user_id,
            limit=limit
        )
        
        return {
            "simulations": simulations,
            "total": len(simulations),
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list simulations: {str(e)}")

@router.get("/simulations/{simulation_id}")
async def get_simulation(
    simulation_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get specific simulation details and results"""
    try:
        simulation = await digital_twin_service.get_simulation(
            simulation_id=simulation_id,
            user_id=current_user.user_id
        )
        
        if not simulation:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        return simulation
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get simulation: {str(e)}")

@router.get("/workflows")
async def list_workflows(current_user = Depends(get_current_active_user)):
    """List available Digital Twin workflows"""
    try:
        workflows = [
            {
                "type": workflow.value,
                "name": workflow.value.replace("_", " ").title(),
                "description": f"Digital Twin analysis for {workflow.value.replace('_', ' ')}"
            }
            for workflow in WorkflowType
        ]
        
        return {
            "workflows": workflows,
            "total": len(workflows),
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")

@router.post("/workflows/{workflow_type}/run")
async def run_workflow(
    workflow_type: str,
    document_ids: List[str],
    current_user = Depends(get_current_active_user)
):
    """Run a Digital Twin workflow on specific documents"""
    try:
        # Convert string to enum
        workflow = WorkflowType(workflow_type.lower())
        
        # Run the workflow
        result = await digital_twin_service.run_workflow(
            workflow_type=workflow,
            document_ids=document_ids,
            user_id=current_user.user_id
        )
        
        return {
            "workflow_type": workflow_type,
            "document_ids": document_ids,
            "result": result,
            "user_id": current_user.user_id,
            "status": "completed"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid workflow type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")
