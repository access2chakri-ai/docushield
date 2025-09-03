"""
Digital Twin router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.core.dependencies import get_current_active_user
from app.schemas.requests import SimulationRequest
from app.schemas.responses import DigitalTwinInsightsResponse
from app.services.digital_twin import digital_twin_service, WorkflowType

router = APIRouter(prefix="/api/digital-twin", tags=["digital-twin"])

@router.get("/workflows/{workflow_type}/insights", response_model=DigitalTwinInsightsResponse)
async def get_workflow_insights(
    workflow_type: str,
    current_user = Depends(get_current_active_user)
):
    """Get Digital Twin insights for specific workflow"""
    try:
        # Convert string to enum
        workflow = WorkflowType(workflow_type.lower())
        
        # Get insights from digital twin service
        insights = await digital_twin_service.get_workflow_insights(
            workflow_type=workflow,
            user_id=current_user.user_id
        )
        
        return DigitalTwinInsightsResponse(
            workflow_type=workflow_type,
            metrics=insights.get("metrics", {}),
            risk_patterns=insights.get("risk_patterns", []),
            recommendations=insights.get("recommendations", [])
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid workflow type: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Digital twin insights failed: {str(e)}")

@router.post("/simulations")
async def create_simulation(
    request: SimulationRequest,
    current_user = Depends(get_current_active_user)
):
    """Create a new Digital Twin simulation"""
    try:
        # Create simulation
        simulation_result = await digital_twin_service.create_simulation(
            scenario_name=request.scenario_name,
            description=request.description,
            document_ids=request.document_ids,
            parameter_changes=request.parameter_changes,
            user_id=current_user.user_id
        )
        
        return {
            "simulation_id": simulation_result.get("simulation_id"),
            "scenario_name": request.scenario_name,
            "status": "created",
            "user_id": current_user.user_id,
            "message": "Simulation created successfully"
        }
        
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
