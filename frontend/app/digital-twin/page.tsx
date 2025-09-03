"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

interface User {
  user_id: string;
  email: string;
  name: string;
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

interface SimulationResult {
  scenario_id: string;
  scenario_name: string;
  execution_time: string;
  affected_workflows: string[];
  financial_impact: {
    cost_increase: number;
    revenue_at_risk: number;
    risk_exposure: number;
  };
  operational_impact: {
    delay_hours: number;
    efficiency_loss: number;
    resource_overhead: number;
  };
  compliance_impact: {
    violation_risk: number;
    audit_findings: number;
  };
  impact_narrative: string;
  simulation_confidence: number;
}

export default function DigitalTwinPage() {
  const [user, setUser] = useState<User | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState('contract_lifecycle');
  const [workflowInsights, setWorkflowInsights] = useState<WorkflowInsights | null>(null);
  const [simulationResults, setSimulationResults] = useState<SimulationResult | null>(null);
  const [isLoadingInsights, setIsLoadingInsights] = useState(false);
  const [isRunningSimulation, setIsRunningSimulation] = useState(false);
  const [documents, setDocuments] = useState<any[]>([]);
  
  // Simulation form state
  const [scenarioName, setScenarioName] = useState('');
  const [scenarioDescription, setScenarioDescription] = useState('');
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [parameterChanges, setParameterChanges] = useState<any>({});
  
  const router = useRouter();

  const workflowTypes = [
    { value: 'contract_lifecycle', label: '📄 Contract Lifecycle', description: 'Contract creation, review, approval, and monitoring' },
    { value: 'vendor_onboarding', label: '🤝 Vendor Onboarding', description: 'Vendor qualification, due diligence, and setup' },
    { value: 'procure_to_pay', label: '💳 Procure-to-Pay', description: 'Purchase requests, approvals, and payments' },
    { value: 'invoice_processing', label: '🧾 Invoice Processing', description: 'Invoice receipt, validation, and payment' },
    { value: 'compliance_cycle', label: '✅ Compliance Cycle', description: 'Regulatory compliance and audit processes' },
    { value: 'risk_management', label: '⚠️ Risk Management', description: 'Risk identification, assessment, and mitigation' }
  ];

  useEffect(() => {
    // Check authentication
    const userData = localStorage.getItem('docushield_user');
    if (!userData) {
      router.push('/auth');
      return;
    }

    const currentUser: User = JSON.parse(userData);
    setUser(currentUser);
    
    // Load initial data
    loadWorkflowInsights(selectedWorkflow);
    loadDocuments(currentUser.user_id);
  }, [router, selectedWorkflow]);

  const loadWorkflowInsights = async (workflowType: string) => {
    if (!user) return;
    
    setIsLoadingInsights(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/digital-twin/workflows/${workflowType}/insights?time_window_days=30`
      );
      
      if (response.ok) {
        const insights = await response.json();
        setWorkflowInsights(insights);
      }
    } catch (error) {
      console.error('Failed to load workflow insights:', error);
    } finally {
      setIsLoadingInsights(false);
    }
  };

  const loadDocuments = async (userId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/documents?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const runSimulation = async () => {
    if (!user || selectedDocuments.length === 0 || !scenarioName.trim()) {
      alert('Please provide a scenario name and select at least one document');
      return;
    }

    setIsRunningSimulation(true);
    try {
      const response = await fetch('http://localhost:8000/api/digital-twin/simulate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          scenario_name: scenarioName,
          description: scenarioDescription,
          document_ids: selectedDocuments,
          parameter_changes: parameterChanges
        })
      });

      if (response.ok) {
        const result = await response.json();
        setSimulationResults(result.simulation_results);
      } else {
        throw new Error('Simulation failed');
      }
    } catch (error) {
      console.error('Simulation error:', error);
      alert('Simulation failed. Please try again.');
    } finally {
      setIsRunningSimulation(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const formatPercentage = (value: number) => {
    return (value * 100).toFixed(1) + '%';
  };

  const getRiskColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600 bg-red-100';
    if (score >= 0.6) return 'text-orange-600 bg-orange-100';
    if (score >= 0.4) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <img 
              src="/docushield-logo-svg.svg" 
              alt="DocuShield Logo" 
              className="h-10 w-auto"
            />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Digital Twin Dashboard</h1>
              <p className="text-gray-600 mt-2">
                Simulate business workflow impacts and analyze document-driven risks
              </p>
              {user && (
                <p className="text-sm text-gray-500">Logged in as: {user.name}</p>
              )}
            </div>
          </div>
          <div className="flex space-x-4">
            <Link
              href="/search"
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
            >
              🔍 Advanced Search
            </Link>
            <Link
              href="/documents"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
            >
              📄 Documents
            </Link>
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-800"
            >
              ← Home
            </Link>
          </div>
        </div>

        {/* Workflow Selection */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Select Workflow Type</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {workflowTypes.map((workflow) => (
              <button
                key={workflow.value}
                onClick={() => setSelectedWorkflow(workflow.value)}
                className={`p-4 rounded-lg border-2 transition-all ${
                  selectedWorkflow === workflow.value
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="text-left">
                  <div className="font-medium text-gray-900 mb-1">{workflow.label}</div>
                  <div className="text-sm text-gray-600">{workflow.description}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Workflow Insights */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Metrics */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Workflow Metrics</h3>
            {isLoadingInsights ? (
              <div className="flex items-center justify-center h-32">
                <div className="text-gray-500">Loading insights...</div>
              </div>
            ) : workflowInsights ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-blue-50 p-3 rounded">
                    <div className="text-2xl font-bold text-blue-600">
                      {workflowInsights.metrics.total_executions}
                    </div>
                    <div className="text-sm text-blue-800">Total Executions</div>
                  </div>
                  <div className="bg-green-50 p-3 rounded">
                    <div className="text-2xl font-bold text-green-600">
                      {formatPercentage(workflowInsights.metrics.success_rate)}
                    </div>
                    <div className="text-sm text-green-800">Success Rate</div>
                  </div>
                  <div className="bg-yellow-50 p-3 rounded">
                    <div className="text-2xl font-bold text-yellow-600">
                      {workflowInsights.metrics.average_duration_hours}h
                    </div>
                    <div className="text-sm text-yellow-800">Avg Duration</div>
                  </div>
                  <div className="bg-purple-50 p-3 rounded">
                    <div className="text-2xl font-bold text-purple-600">
                      {formatCurrency(workflowInsights.metrics.cost_per_execution)}
                    </div>
                    <div className="text-sm text-purple-800">Cost per Execution</div>
                  </div>
                </div>
                
                {workflowInsights.metrics.bottlenecks.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">🚧 Bottlenecks</h4>
                    <div className="flex flex-wrap gap-2">
                      {workflowInsights.metrics.bottlenecks.map((bottleneck, index) => (
                        <span key={index} className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">
                          {bottleneck}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-gray-500">No insights available</div>
            )}
          </div>

          {/* Risk Patterns */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 Risk Patterns</h3>
            {workflowInsights?.risk_patterns ? (
              <div className="space-y-3">
                {workflowInsights.risk_patterns.map((pattern, index) => (
                  <div key={index} className="border-l-4 border-orange-400 pl-4">
                    <div className="font-medium text-gray-900">{pattern.pattern}</div>
                    <div className="text-sm text-gray-600 mt-1">{pattern.description}</div>
                    <div className="flex items-center mt-2 space-x-4">
                      <span className="text-xs text-gray-500">
                        Frequency: {formatPercentage(pattern.frequency)}
                      </span>
                      <span className={`px-2 py-1 text-xs rounded ${getRiskColor(pattern.impact_score)}`}>
                        Impact: {formatPercentage(pattern.impact_score)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-500">No risk patterns identified</div>
            )}
          </div>
        </div>

        {/* Recommendations */}
        {workflowInsights?.recommendations && workflowInsights.recommendations.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">💡 Recommendations</h3>
            <div className="space-y-2">
              {workflowInsights.recommendations.map((recommendation, index) => (
                <div key={index} className="flex items-start space-x-3">
                  <span className="text-green-500 mt-1">✓</span>
                  <span className="text-gray-700">{recommendation}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Simulation Section */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🔬 What-If Simulation</h3>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Simulation Setup */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3">Simulation Setup</h4>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Scenario Name
                  </label>
                  <input
                    type="text"
                    value={scenarioName}
                    onChange={(e) => setScenarioName(e.target.value)}
                    placeholder="e.g., High-risk contract impact analysis"
                    className="w-full p-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <textarea
                    value={scenarioDescription}
                    onChange={(e) => setScenarioDescription(e.target.value)}
                    placeholder="Describe the scenario you want to simulate..."
                    rows={3}
                    className="w-full p-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Select Documents ({selectedDocuments.length} selected)
                  </label>
                  <div className="max-h-40 overflow-y-auto border border-gray-300 rounded p-2">
                    {documents.map((doc) => (
                      <label key={doc.contract_id} className="flex items-center space-x-2 py-1">
                        <input
                          type="checkbox"
                          checked={selectedDocuments.includes(doc.contract_id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedDocuments([...selectedDocuments, doc.contract_id]);
                            } else {
                              setSelectedDocuments(selectedDocuments.filter(id => id !== doc.contract_id));
                            }
                          }}
                          className="rounded"
                        />
                        <span className="text-sm text-gray-700">{doc.filename}</span>
                      </label>
                    ))}
                  </div>
                </div>
                
                <button
                  onClick={runSimulation}
                  disabled={isRunningSimulation || !scenarioName.trim() || selectedDocuments.length === 0}
                  className={`w-full py-2 px-4 rounded font-medium ${
                    isRunningSimulation || !scenarioName.trim() || selectedDocuments.length === 0
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-blue-600 hover:bg-blue-700'
                  } text-white`}
                >
                  {isRunningSimulation ? '🔄 Running Simulation...' : '🚀 Run Simulation'}
                </button>
              </div>
            </div>
            
            {/* Simulation Results */}
            <div>
              <h4 className="font-medium text-gray-900 mb-3">Simulation Results</h4>
              {simulationResults ? (
                <div className="space-y-4">
                  {/* Impact Narrative */}
                  <div className="bg-blue-50 p-4 rounded">
                    <h5 className="font-medium text-blue-900 mb-2">Executive Summary</h5>
                    <p className="text-sm text-blue-800">{simulationResults.impact_narrative}</p>
                  </div>
                  
                  {/* Impact Metrics */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-red-50 p-3 rounded">
                      <div className="text-lg font-bold text-red-600">
                        {formatCurrency(simulationResults.financial_impact.cost_increase)}
                      </div>
                      <div className="text-xs text-red-800">Cost Increase</div>
                    </div>
                    <div className="bg-orange-50 p-3 rounded">
                      <div className="text-lg font-bold text-orange-600">
                        {formatCurrency(simulationResults.financial_impact.revenue_at_risk)}
                      </div>
                      <div className="text-xs text-orange-800">Revenue at Risk</div>
                    </div>
                    <div className="bg-yellow-50 p-3 rounded">
                      <div className="text-lg font-bold text-yellow-600">
                        {simulationResults.operational_impact.delay_hours}h
                      </div>
                      <div className="text-xs text-yellow-800">Delays</div>
                    </div>
                    <div className="bg-purple-50 p-3 rounded">
                      <div className="text-lg font-bold text-purple-600">
                        {formatPercentage(simulationResults.compliance_impact.violation_risk)}
                      </div>
                      <div className="text-xs text-purple-800">Compliance Risk</div>
                    </div>
                  </div>
                  
                  {/* Affected Workflows */}
                  {simulationResults.affected_workflows.length > 0 && (
                    <div>
                      <h5 className="font-medium text-gray-900 mb-2">Affected Workflows</h5>
                      <div className="flex flex-wrap gap-2">
                        {simulationResults.affected_workflows.map((workflow, index) => (
                          <span key={index} className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded">
                            {workflow.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="text-xs text-gray-500">
                    Confidence: {formatPercentage(simulationResults.simulation_confidence)}
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 text-center py-8">
                  Run a simulation to see results here
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Help Section */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 Digital Twin Capabilities</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-sm">
            <div>
              <h4 className="font-medium text-blue-800 mb-2">📊 Workflow Analytics</h4>
              <ul className="space-y-1 text-blue-700">
                <li>• Performance metrics tracking</li>
                <li>• Bottleneck identification</li>
                <li>• Success rate monitoring</li>
                <li>• Cost analysis per execution</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-purple-800 mb-2">🎯 Risk Pattern Detection</h4>
              <ul className="space-y-1 text-purple-700">
                <li>• Document-driven risk patterns</li>
                <li>• Impact frequency analysis</li>
                <li>• Business process correlations</li>
                <li>• Predictive risk modeling</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-green-800 mb-2">🔬 What-If Simulation</h4>
              <ul className="space-y-1 text-green-700">
                <li>• Financial impact modeling</li>
                <li>• Operational delay predictions</li>
                <li>• Compliance risk assessment</li>
                <li>• Multi-workflow analysis</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}