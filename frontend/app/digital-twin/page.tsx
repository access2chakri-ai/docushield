"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface WorkflowNode {
  id: string;
  name: string;
  type: string;
  status: 'normal' | 'warning' | 'critical';
  impact: number;
  dependencies: string[];
}

interface WorkflowInsights {
  workflow_type: string;
  metrics: {
    total_executions: number;
    average_duration_hours: number;
    success_rate: number;
    cost_per_execution: number;
    bottlenecks: string[];
    risk_incidents: number;
  };
  risk_patterns: Array<{
    pattern: string;
    description: string;
    frequency: number;
    impact_score: number;
  }>;
  recommendations: string[];
}

interface SimulationScenario {
  name: string;
  description: string;
  document_ids: string[];
  parameter_changes: Record<string, any>;
}

export default function DigitalTwinPage() {
  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('contract_lifecycle');
  const [workflowInsights, setWorkflowInsights] = useState<WorkflowInsights | null>(null);
  const [simulationScenario, setSimulationScenario] = useState<SimulationScenario>({
    name: '',
    description: '',
    document_ids: [],
    parameter_changes: {}
  });
  const [simulationResults, setSimulationResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Mock workflow data
  const workflows = {
    contract_lifecycle: {
      name: 'Contract Lifecycle Management',
      nodes: [
        { id: 'request', name: 'Contract Request', type: 'process', status: 'normal', impact: 0, dependencies: [] },
        { id: 'review', name: 'Legal Review', type: 'process', status: 'warning', impact: 0.3, dependencies: ['request'] },
        { id: 'negotiate', name: 'Negotiation', type: 'process', status: 'critical', impact: 0.7, dependencies: ['review'] },
        { id: 'approve', name: 'Approval', type: 'decision', status: 'warning', impact: 0.4, dependencies: ['negotiate'] },
        { id: 'execute', name: 'Execution', type: 'process', status: 'normal', impact: 0.1, dependencies: ['approve'] },
        { id: 'monitor', name: 'Monitoring', type: 'process', status: 'normal', impact: 0.2, dependencies: ['execute'] }
      ]
    },
    vendor_onboarding: {
      name: 'Vendor Onboarding',
      nodes: [
        { id: 'application', name: 'Application', type: 'process', status: 'normal', impact: 0, dependencies: [] },
        { id: 'diligence', name: 'Due Diligence', type: 'process', status: 'warning', impact: 0.5, dependencies: ['application'] },
        { id: 'contract', name: 'Contract Negotiation', type: 'process', status: 'critical', impact: 0.8, dependencies: ['diligence'] },
        { id: 'onboard', name: 'Onboarding', type: 'process', status: 'normal', impact: 0.2, dependencies: ['contract'] }
      ]
    },
    procure_to_pay: {
      name: 'Procure to Pay',
      nodes: [
        { id: 'request', name: 'Purchase Request', type: 'process', status: 'normal', impact: 0, dependencies: [] },
        { id: 'approve', name: 'Approval', type: 'decision', status: 'normal', impact: 0.1, dependencies: ['request'] },
        { id: 'po', name: 'PO Creation', type: 'process', status: 'normal', impact: 0.1, dependencies: ['approve'] },
        { id: 'receipt', name: 'Goods Receipt', type: 'process', status: 'warning', impact: 0.3, dependencies: ['po'] },
        { id: 'invoice', name: 'Invoice Processing', type: 'process', status: 'critical', impact: 0.6, dependencies: ['receipt'] },
        { id: 'payment', name: 'Payment', type: 'process', status: 'normal', impact: 0.2, dependencies: ['invoice'] }
      ]
    }
  };

  useEffect(() => {
    fetchWorkflowInsights();
  }, [selectedWorkflow]);

  const fetchWorkflowInsights = async () => {
    setLoading(true);
    try {
      // Mock API call - replace with actual endpoint
      setTimeout(() => {
        const mockInsights: WorkflowInsights = {
          workflow_type: selectedWorkflow,
          metrics: {
            total_executions: Math.floor(Math.random() * 500) + 100,
            average_duration_hours: Math.floor(Math.random() * 120) + 24,
            success_rate: 0.85 + Math.random() * 0.1,
            cost_per_execution: Math.floor(Math.random() * 3000) + 1000,
            bottlenecks: ['legal_review', 'approval'],
            risk_incidents: Math.floor(Math.random() * 20) + 5
          },
          risk_patterns: [
            {
              pattern: 'liability_clause_correlation',
              description: 'Contracts with unlimited liability clauses cause 60% more delays in legal review',
              frequency: 0.3,
              impact_score: 0.7
            },
            {
              pattern: 'auto_renewal_oversight',
              description: 'Auto-renewal clauses are missed in 25% of contract monitoring cycles',
              frequency: 0.25,
              impact_score: 0.5
            }
          ],
          recommendations: [
            '🔧 Implement automated quality checks to improve success rate',
            '⚡ Consider parallel legal review processes for low-risk contracts',
            '🎯 Address liability clause correlation pattern'
          ]
        };
        setWorkflowInsights(mockInsights);
        setLoading(false);
      }, 1000);
    } catch (error) {
      console.error('Failed to fetch workflow insights:', error);
      setLoading(false);
    }
  };

  const runSimulation = async () => {
    if (!simulationScenario.name) return;

    setLoading(true);
    try {
      // Mock simulation
      setTimeout(() => {
        const mockResults = {
          scenario: {
            scenario_id: 'sim_' + Date.now(),
            name: simulationScenario.name,
            description: simulationScenario.description
          },
          simulation_results: {
            scenario_id: 'sim_' + Date.now(),
            execution_time: new Date().toISOString(),
            affected_workflows: [selectedWorkflow],
            financial_impact: {
              cost_increase: Math.random() * 50000,
              revenue_impact: Math.random() * -25000,
              risk_exposure: Math.random() * 100000
            },
            operational_impact: {
              delay_hours: Math.floor(Math.random() * 72),
              efficiency_loss: Math.random() * 0.3,
              resource_overhead: Math.random() * 0.2
            },
            compliance_impact: {
              violation_risk: Math.random() * 0.4,
              audit_findings: Math.floor(Math.random() * 5)
            }
          }
        };
        setSimulationResults(mockResults);
        setLoading(false);
      }, 2000);
    } catch (error) {
      console.error('Simulation failed:', error);
      setLoading(false);
    }
  };

  const getNodeColor = (status: string) => {
    switch (status) {
      case 'critical': return 'bg-red-500 border-red-600';
      case 'warning': return 'bg-yellow-500 border-yellow-600';
      case 'normal': return 'bg-green-500 border-green-600';
      default: return 'bg-gray-500 border-gray-600';
    }
  };

  const getNodeTextColor = (status: string) => {
    switch (status) {
      case 'critical': return 'text-red-700';
      case 'warning': return 'text-yellow-700';
      case 'normal': return 'text-green-700';
      default: return 'text-gray-700';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Digital Twin Visualization</h1>
            <p className="text-gray-600">Document-to-workflow mapping and impact simulation</p>
          </div>
          <Link
            href="/"
            className="text-blue-600 hover:text-blue-800 flex items-center"
          >
            ← Back to Home
          </Link>
        </div>

        {/* Workflow Selection */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-semibold mb-4">Select Workflow</h2>
          <div className="grid md:grid-cols-3 gap-4">
            {Object.entries(workflows).map(([key, workflow]) => (
              <button
                key={key}
                onClick={() => setSelectedWorkflow(key)}
                className={`p-4 rounded-lg border-2 text-left transition-all ${
                  selectedWorkflow === key
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <h3 className="font-semibold text-gray-900">{workflow.name}</h3>
                <p className="text-sm text-gray-600">{workflow.nodes.length} process steps</p>
              </button>
            ))}
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Workflow Visualization */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-6">Workflow Visualization</h2>
              
              {/* Workflow Diagram */}
              <div className="space-y-4">
                {workflows[selectedWorkflow as keyof typeof workflows]?.nodes.map((node, index) => (
                  <div key={node.id} className="relative">
                    {/* Connection Line */}
                    {index > 0 && (
                      <div className="absolute -top-4 left-1/2 w-0.5 h-4 bg-gray-300 transform -translate-x-1/2"></div>
                    )}
                    
                    {/* Node */}
                    <div className={`flex items-center p-4 rounded-lg border-2 ${getNodeColor(node.status)}`}>
                      <div className="flex-1">
                        <div className="flex items-center mb-2">
                          <div className={`w-3 h-3 rounded-full mr-3 ${getNodeColor(node.status).split(' ')[0]}`}></div>
                          <h3 className="font-semibold text-white">{node.name}</h3>
                        </div>
                        <p className="text-sm text-white opacity-90 capitalize">{node.type}</p>
                      </div>
                      
                      {node.impact > 0 && (
                        <div className="text-right">
                          <div className="text-white font-semibold">
                            {Math.round(node.impact * 100)}%
                          </div>
                          <div className="text-xs text-white opacity-75">Impact</div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Workflow Metrics */}
            {workflowInsights && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Performance Metrics</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-3 bg-blue-50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">
                      {workflowInsights.metrics.total_executions}
                    </div>
                    <div className="text-sm text-gray-600">Total Executions</div>
                  </div>
                  
                  <div className="text-center p-3 bg-green-50 rounded-lg">
                    <div className="text-2xl font-bold text-green-600">
                      {Math.round(workflowInsights.metrics.success_rate * 100)}%
                    </div>
                    <div className="text-sm text-gray-600">Success Rate</div>
                  </div>
                  
                  <div className="text-center p-3 bg-yellow-50 rounded-lg">
                    <div className="text-2xl font-bold text-yellow-600">
                      {workflowInsights.metrics.average_duration_hours}h
                    </div>
                    <div className="text-sm text-gray-600">Avg Duration</div>
                  </div>
                  
                  <div className="text-center p-3 bg-purple-50 rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">
                      ${workflowInsights.metrics.cost_per_execution.toLocaleString()}
                    </div>
                    <div className="text-sm text-gray-600">Cost per Execution</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Simulation Panel */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">What-If Simulation</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Scenario Name
                  </label>
                  <input
                    type="text"
                    value={simulationScenario.name}
                    onChange={(e) => setSimulationScenario(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="e.g., High Risk Contract Impact"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Description
                  </label>
                  <textarea
                    value={simulationScenario.description}
                    onChange={(e) => setSimulationScenario(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={3}
                    placeholder="Describe the scenario to simulate..."
                  />
                </div>
                
                <button
                  onClick={runSimulation}
                  disabled={loading || !simulationScenario.name}
                  className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Running Simulation...' : 'Run Simulation'}
                </button>
              </div>
            </div>

            {/* Simulation Results */}
            {simulationResults && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Simulation Results</h2>
                
                <div className="space-y-4">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <h3 className="font-semibold text-gray-900 mb-2">Financial Impact</h3>
                    <div className="grid grid-cols-1 gap-2 text-sm">
                      <div className="flex justify-between">
                        <span>Cost Increase:</span>
                        <span className="font-medium text-red-600">
                          +${simulationResults.simulation_results.financial_impact.cost_increase.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Risk Exposure:</span>
                        <span className="font-medium text-orange-600">
                          ${simulationResults.simulation_results.financial_impact.risk_exposure.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <h3 className="font-semibold text-gray-900 mb-2">Operational Impact</h3>
                    <div className="grid grid-cols-1 gap-2 text-sm">
                      <div className="flex justify-between">
                        <span>Delay:</span>
                        <span className="font-medium text-yellow-600">
                          +{simulationResults.simulation_results.operational_impact.delay_hours}h
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Efficiency Loss:</span>
                        <span className="font-medium text-orange-600">
                          {Math.round(simulationResults.simulation_results.operational_impact.efficiency_loss * 100)}%
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <h3 className="font-semibold text-gray-900 mb-2">Compliance Impact</h3>
                    <div className="grid grid-cols-1 gap-2 text-sm">
                      <div className="flex justify-between">
                        <span>Violation Risk:</span>
                        <span className="font-medium text-red-600">
                          {Math.round(simulationResults.simulation_results.compliance_impact.violation_risk * 100)}%
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Audit Findings:</span>
                        <span className="font-medium text-yellow-600">
                          {simulationResults.simulation_results.compliance_impact.audit_findings}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Risk Patterns */}
            {workflowInsights && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Risk Patterns</h2>
                <div className="space-y-3">
                  {workflowInsights.risk_patterns.map((pattern, index) => (
                    <div key={index} className="p-3 bg-red-50 border-l-4 border-red-400 rounded">
                      <h3 className="font-medium text-red-900">{pattern.pattern.replace(/_/g, ' ').toUpperCase()}</h3>
                      <p className="text-sm text-red-700 mt-1">{pattern.description}</p>
                      <div className="flex justify-between mt-2 text-xs text-red-600">
                        <span>Frequency: {Math.round(pattern.frequency * 100)}%</span>
                        <span>Impact: {Math.round(pattern.impact_score * 100)}%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {workflowInsights && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-semibold mb-4">Recommendations</h2>
                <div className="space-y-2">
                  {workflowInsights.recommendations.map((recommendation, index) => (
                    <div key={index} className="flex items-start p-3 bg-blue-50 rounded-lg">
                      <div className="text-blue-600 mr-2">💡</div>
                      <p className="text-sm text-blue-800">{recommendation}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
