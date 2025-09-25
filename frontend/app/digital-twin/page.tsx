"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '@/utils/auth';
import { config } from '@/utils/config';

// User interface is now imported from @/utils/auth

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
    { 
      value: 'contract_lifecycle', 
      label: 'Contract Lifecycle', 
      icon: '📋',
      description: 'Contract creation, review, approval, and monitoring',
      color: 'from-blue-500 to-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-200'
    },
    { 
      value: 'vendor_onboarding', 
      label: 'Vendor Onboarding', 
      icon: '🤝',
      description: 'Vendor qualification, due diligence, and setup',
      color: 'from-green-500 to-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200'
    },
    { 
      value: 'procure_to_pay', 
      label: 'Procure-to-Pay', 
      icon: '💳',
      description: 'Purchase requests, approvals, and payments',
      color: 'from-purple-500 to-purple-600',
      bgColor: 'bg-purple-50',
      borderColor: 'border-purple-200'
    },
    { 
      value: 'invoice_processing', 
      label: 'Invoice Processing', 
      icon: '🧾',
      description: 'Invoice receipt, validation, and payment',
      color: 'from-orange-500 to-orange-600',
      bgColor: 'bg-orange-50',
      borderColor: 'border-orange-200'
    },
    { 
      value: 'compliance_cycle', 
      label: 'Compliance Cycle', 
      icon: '✅',
      description: 'Regulatory compliance and audit processes',
      color: 'from-teal-500 to-teal-600',
      bgColor: 'bg-teal-50',
      borderColor: 'border-teal-200'
    },
    { 
      value: 'risk_management', 
      label: 'Risk Management', 
      icon: '⚠️',
      description: 'Risk identification, assessment, and mitigation',
      color: 'from-red-500 to-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200'
    }
  ];

  useEffect(() => {
    // Check authentication using the proper auth utils
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }

    const currentUser = getUserData();
    if (currentUser) {
      setUser(currentUser);
      // Load initial data
      loadWorkflowInsights(selectedWorkflow);
      loadDocuments(currentUser.user_id);
    } else {
      router.push('/auth');
    }
  }, [router, selectedWorkflow]);

  const loadWorkflowInsights = async (workflowType: string) => {
    if (!user) return;
    
    setIsLoadingInsights(true);
    try {
      const response = await authenticatedFetch(
        `${config.apiBaseUrl}/api/digital-twin/workflows/${workflowType}/insights?time_window_days=30`,
        {}, 
        60000 // 1 minute timeout for workflow insights
      );
      
      if (response.ok) {
        const insights = await response.json();
        setWorkflowInsights(insights);
      } else if (response.status === 401) {
        // Redirect to auth if unauthorized
        router.push('/auth');
      } else {
        console.error('Failed to load workflow insights:', response.status, await response.text().catch(() => 'Unknown error'));
      }
    } catch (error) {
      console.error('Failed to load workflow insights:', error);
      // Set empty insights to prevent infinite loading
      setWorkflowInsights(null);
    } finally {
      setIsLoadingInsights(false);
    }
  };

  const loadDocuments = async (userId: string) => {
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/documents?user_id=${userId}`);
      
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
      } else if (response.status === 401) {
        router.push('/auth');
      } else {
        console.error('Failed to load documents:', response.status, await response.text().catch(() => 'Unknown error'));
        setDocuments([]); // Set empty array to prevent issues
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
      setDocuments([]); // Set empty array to prevent issues
    }
  };

  const runSimulation = async () => {
    if (!user || selectedDocuments.length === 0 || !scenarioName.trim()) {
      alert('Please provide a scenario name and select at least one document');
      return;
    }

    setIsRunningSimulation(true);
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/digital-twin/simulate`, {
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
      }, 180000); // 3 minutes timeout for simulations

      if (response.ok) {
        const result = await response.json();
        setSimulationResults(result.simulation_results);
      } else if (response.status === 401) {
        router.push('/auth');
      } else {
        const errorText = await response.text().catch(() => 'Unknown error');
        console.error('Simulation failed:', response.status, errorText);
        alert(`Simulation failed (${response.status}): ${errorText}`);
      }
    } catch (error) {
      console.error('Simulation error:', error);
      alert('Simulation failed. Please check if the backend is running and try again.');
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
    <div className="min-h-screen bg-digital-twin-pattern relative overflow-hidden">
      {/* Floating digital twin elements */}
      <div className="floating-document top-20 left-8 text-6xl">🔗</div>
      <div className="floating-document top-40 right-12 text-5xl">⚙️</div>
      <div className="floating-document bottom-36 left-1/4 text-4xl">🧠</div>
      <div className="floating-document bottom-20 right-1/5 text-5xl">⚡</div>
      
      {/* Digital twin processing flow */}
      <div className="data-flow top-0 left-1/3" style={{animationDelay: '1s'}}></div>
      <div className="data-flow top-0 right-1/4" style={{animationDelay: '2s'}}></div>
      <div className="data-flow top-0 left-2/3" style={{animationDelay: '3s'}}></div>

      <div className="relative container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 animate-fade-in">
          <div className="flex items-center space-x-6">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl blur-lg opacity-30 animate-pulse"></div>
              <div className="relative bg-white p-3 rounded-2xl shadow-lg">
                <img 
                  src="/docushield-logo-svg.svg" 
                  alt="DocuShield Logo" 
                  className="h-12 w-auto"
                />
              </div>
            </div>
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-gray-900 via-blue-800 to-purple-800 bg-clip-text text-transparent">
                Digital Twin Dashboard
              </h1>
              <p className="text-gray-600 mt-2 text-lg">
                🚀 Simulate business workflow impacts and analyze document-driven risks
              </p>
              {user && (
                <div className="flex items-center mt-2 text-sm text-gray-500">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                  Logged in as: <span className="font-medium ml-1">{user.name}</span>
                </div>
              )}
            </div>
          </div>
          <div className="flex space-x-3">
            <Link
              href="/search"
              className="group bg-gradient-to-r from-purple-600 to-purple-700 text-white px-6 py-3 rounded-xl hover:from-purple-700 hover:to-purple-800 transform hover:scale-105 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              <span className="flex items-center space-x-2">
                <span className="group-hover:animate-spin">🔍</span>
                <span>Advanced Search</span>
              </span>
            </Link>
            <Link
              href="/documents"
              className="group bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-3 rounded-xl hover:from-blue-700 hover:to-blue-800 transform hover:scale-105 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              <span className="flex items-center space-x-2">
                <span className="group-hover:animate-bounce">📄</span>
                <span>Documents</span>
              </span>
            </Link>
            <Link
              href="/"
              className="text-blue-600 hover:text-blue-800 px-4 py-3 rounded-xl hover:bg-blue-50 transition-all duration-200"
            >
              ← Home
            </Link>
          </div>
        </div>

        {/* Workflow Selection */}
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-8 mb-8 animate-slide-up border border-white/20">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
              <span className="text-white text-lg">⚡</span>
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Select Workflow Type</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {workflowTypes.map((workflow, index) => (
              <button
                key={workflow.value}
                onClick={() => setSelectedWorkflow(workflow.value)}
                className={`group relative p-6 rounded-2xl border-2 transition-all duration-300 transform hover:scale-105 hover:shadow-xl ${
                  selectedWorkflow === workflow.value
                    ? `border-transparent bg-gradient-to-br ${workflow.color} text-white shadow-lg`
                    : `${workflow.borderColor} ${workflow.bgColor} hover:border-opacity-60 hover:shadow-lg`
                } animate-fade-in`}
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <div className="text-left">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className={`text-3xl transform transition-transform group-hover:scale-110 ${
                      selectedWorkflow === workflow.value ? 'animate-bounce' : ''
                    }`}>
                      {workflow.icon}
                    </div>
                    <div className={`font-bold text-lg ${
                      selectedWorkflow === workflow.value ? 'text-white' : 'text-gray-900'
                    }`}>
                      {workflow.label}
                    </div>
                  </div>
                  <div className={`text-sm leading-relaxed ${
                    selectedWorkflow === workflow.value ? 'text-white/90' : 'text-gray-600'
                  }`}>
                    {workflow.description}
                  </div>
                </div>
                
                {/* Selection indicator */}
                {selectedWorkflow === workflow.value && (
                  <div className="absolute top-3 right-3">
                    <div className="w-6 h-6 bg-white/20 rounded-full flex items-center justify-center">
                      <div className="w-3 h-3 bg-white rounded-full animate-ping"></div>
                    </div>
                  </div>
                )}
                
                {/* Hover effect */}
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-white/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              </button>
            ))}
          </div>
        </div>

        {/* Workflow Insights */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Metrics */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-white/20 animate-slide-up">
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
                <span className="text-white text-lg">📊</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900">Workflow Metrics</h3>
            </div>
            {isLoadingInsights ? (
              <div className="flex items-center justify-center h-32">
                <div className="flex space-x-2 items-center">
                  <div className="w-4 h-4 bg-blue-500 rounded-full animate-bounce"></div>
                  <div className="w-4 h-4 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-4 h-4 bg-pink-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <span className="ml-2 text-gray-600">Loading insights...</span>
                </div>
              </div>
            ) : workflowInsights ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="group bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-xl hover:from-blue-100 hover:to-blue-200 transition-all duration-300 transform hover:scale-105 cursor-pointer">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-3xl font-bold text-blue-600 group-hover:animate-pulse">
                          {workflowInsights.metrics.total_executions}
                        </div>
                        <div className="text-sm text-blue-800 font-medium">Total Executions</div>
                      </div>
                      <div className="text-2xl opacity-60 group-hover:animate-bounce">🎯</div>
                    </div>
                  </div>
                  <div className="group bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-xl hover:from-green-100 hover:to-green-200 transition-all duration-300 transform hover:scale-105 cursor-pointer">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-3xl font-bold text-green-600 group-hover:animate-pulse">
                          {formatPercentage(workflowInsights.metrics.success_rate)}
                        </div>
                        <div className="text-sm text-green-800 font-medium">Success Rate</div>
                      </div>
                      <div className="text-2xl opacity-60 group-hover:animate-bounce">✅</div>
                    </div>
                  </div>
                  <div className="group bg-gradient-to-br from-yellow-50 to-yellow-100 p-4 rounded-xl hover:from-yellow-100 hover:to-yellow-200 transition-all duration-300 transform hover:scale-105 cursor-pointer">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-3xl font-bold text-yellow-600 group-hover:animate-pulse">
                          {workflowInsights.metrics.average_duration_hours}h
                        </div>
                        <div className="text-sm text-yellow-800 font-medium">Avg Duration</div>
                      </div>
                      <div className="text-2xl opacity-60 group-hover:animate-spin">⏱️</div>
                    </div>
                  </div>
                  <div className="group bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-xl hover:from-purple-100 hover:to-purple-200 transition-all duration-300 transform hover:scale-105 cursor-pointer">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-3xl font-bold text-purple-600 group-hover:animate-pulse">
                          {formatCurrency(workflowInsights.metrics.cost_per_execution)}
                        </div>
                        <div className="text-sm text-purple-800 font-medium">Cost per Execution</div>
                      </div>
                      <div className="text-2xl opacity-60 group-hover:animate-bounce">💰</div>
                    </div>
                  </div>
                </div>
                
                {workflowInsights.metrics.bottlenecks.length > 0 && (
                  <div className="bg-gradient-to-r from-red-50 to-orange-50 p-4 rounded-xl border border-red-100">
                    <h4 className="font-bold text-gray-900 mb-3 flex items-center space-x-2">
                      <span className="animate-pulse">🚧</span>
                      <span>Bottlenecks Detected</span>
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {workflowInsights.metrics.bottlenecks.map((bottleneck, index) => (
                        <span 
                          key={index} 
                          className="px-3 py-1 bg-red-100 text-red-800 text-sm rounded-full font-medium animate-fade-in hover:bg-red-200 transition-colors duration-200"
                          style={{ animationDelay: `${index * 100}ms` }}
                        >
                          {bottleneck}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="text-6xl mb-4 opacity-20">📊</div>
                <div className="text-gray-500">No insights available</div>
              </div>
            )}
          </div>

          {/* Risk Patterns */}
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-8 border border-white/20 animate-slide-up">
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-8 h-8 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg flex items-center justify-center">
                <span className="text-white text-lg">🎯</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900">Risk Patterns</h3>
            </div>
            {workflowInsights?.risk_patterns ? (
              <div className="space-y-4">
                {workflowInsights.risk_patterns.map((pattern, index) => (
                  <div 
                    key={index} 
                    className="group relative bg-gradient-to-r from-orange-50 to-red-50 border-l-4 border-orange-400 p-4 rounded-xl hover:from-orange-100 hover:to-red-100 transition-all duration-300 transform hover:scale-[1.02] animate-fade-in"
                    style={{ animationDelay: `${index * 150}ms` }}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-bold text-gray-900 mb-2 group-hover:text-orange-800 transition-colors">
                          {pattern.pattern.replace(/_/g, ' ').toUpperCase()}
                        </div>
                        <div className="text-sm text-gray-700 leading-relaxed mb-3">
                          {pattern.description}
                        </div>
                        <div className="flex items-center space-x-4">
                          <div className="flex items-center space-x-2">
                            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
                            <span className="text-xs font-medium text-gray-600">
                              Frequency: {formatPercentage(pattern.frequency)}
                            </span>
                          </div>
                          <div className={`px-3 py-1 text-xs font-bold rounded-full ${getRiskColor(pattern.impact_score)} transition-all duration-200 hover:scale-110`}>
                            Impact: {formatPercentage(pattern.impact_score)}
                          </div>
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="w-12 h-12 bg-white/50 rounded-full flex items-center justify-center group-hover:bg-white/80 transition-all duration-300">
                          <span className="text-xl group-hover:animate-spin">⚠️</span>
                        </div>
                      </div>
                    </div>
                    
                    {/* Progress bar for impact score */}
                    <div className="mt-3">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-gradient-to-r from-orange-400 to-red-500 h-2 rounded-full transition-all duration-1000 ease-out"
                          style={{ width: `${pattern.impact_score * 100}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="text-6xl mb-4 opacity-20">🎯</div>
                <div className="text-gray-500">No risk patterns identified</div>
                <div className="text-sm text-gray-400 mt-2">Upload documents to generate risk insights</div>
              </div>
            )}
          </div>
        </div>

        {/* Recommendations */}
        {workflowInsights?.recommendations && workflowInsights.recommendations.length > 0 && (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-8 mb-8 border border-white/20 animate-slide-up">
            <div className="flex items-center space-x-3 mb-6">
              <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg flex items-center justify-center">
                <span className="text-white text-lg">💡</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900">AI Recommendations</h3>
            </div>
            <div className="grid gap-4">
              {workflowInsights.recommendations.map((recommendation, index) => (
                <div 
                  key={index} 
                  className="group flex items-start space-x-4 p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl hover:from-green-100 hover:to-emerald-100 transition-all duration-300 transform hover:scale-[1.02] animate-fade-in border border-green-100"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center group-hover:bg-green-600 transition-colors duration-200">
                      <span className="text-white text-sm font-bold group-hover:animate-bounce">✓</span>
                    </div>
                  </div>
                  <div className="flex-1">
                    <span className="text-gray-800 font-medium leading-relaxed group-hover:text-green-800 transition-colors">
                      {recommendation.replace(/🔧|⚡|🎯/g, '')}
                    </span>
                  </div>
                  <div className="flex-shrink-0">
                    <div className="w-6 h-6 bg-green-100 rounded-full flex items-center justify-center group-hover:bg-green-200 transition-all duration-200">
                      <span className="text-green-600 text-xs group-hover:animate-pulse">→</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Simulation Section */}
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl p-8 mb-8 border border-white/20 animate-slide-up">
          <div className="flex items-center space-x-3 mb-8">
            <div className="w-10 h-10 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center">
              <span className="text-white text-xl">🔬</span>
            </div>
            <div>
              <h3 className="text-2xl font-bold text-gray-900">What-If Simulation</h3>
              <p className="text-gray-600 text-sm">Create scenarios and predict business impacts</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Simulation Setup */}
            <div className="space-y-6">
              <div className="flex items-center space-x-2 mb-4">
                <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">1</span>
                </div>
                <h4 className="font-bold text-gray-900">Simulation Setup</h4>
              </div>
              
              <div className="space-y-6">
                <div className="group">
                  <label className="block text-sm font-bold text-gray-700 mb-2 group-hover:text-blue-600 transition-colors">
                    🎯 Scenario Name
                  </label>
                  <input
                    type="text"
                    value={scenarioName}
                    onChange={(e) => setScenarioName(e.target.value)}
                    placeholder="e.g., High-risk contract impact analysis"
                    className="w-full p-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100 transition-all duration-200 hover:border-gray-300"
                  />
                </div>
                
                <div className="group">
                  <label className="block text-sm font-bold text-gray-700 mb-2 group-hover:text-purple-600 transition-colors">
                    📝 Description
                  </label>
                  <textarea
                    value={scenarioDescription}
                    onChange={(e) => setScenarioDescription(e.target.value)}
                    placeholder="Describe the scenario you want to simulate..."
                    rows={4}
                    className="w-full p-4 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500 focus:ring-4 focus:ring-purple-100 transition-all duration-200 hover:border-gray-300 resize-none"
                  />
                </div>
                
                <div className="group">
                  <label className="block text-sm font-bold text-gray-700 mb-2 group-hover:text-green-600 transition-colors">
                    📄 Select Documents ({selectedDocuments.length} selected)
                  </label>
                  <div className="max-h-48 overflow-y-auto border-2 border-gray-200 rounded-xl p-4 bg-gray-50 hover:border-gray-300 transition-colors">
                    {documents.length > 0 ? documents.map((doc, index) => (
                      <label 
                        key={doc.contract_id} 
                        className="flex items-center space-x-3 py-2 px-2 rounded-lg hover:bg-white transition-colors cursor-pointer group animate-fade-in"
                        style={{ animationDelay: `${index * 50}ms` }}
                      >
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
                          className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
                        />
                        <div className="flex items-center space-x-2 flex-1">
                          <span className="text-lg">📄</span>
                          <span className="text-sm font-medium text-gray-700 group-hover:text-blue-600 transition-colors">
                            {doc.filename}
                          </span>
                        </div>
                      </label>
                    )) : (
                      <div className="text-center py-8 text-gray-500">
                        <div className="text-4xl mb-2 opacity-30">📄</div>
                        <p>No documents available</p>
                        <p className="text-xs mt-1">Upload documents first</p>
                      </div>
                    )}
                  </div>
                </div>
                
                <button
                  onClick={runSimulation}
                  disabled={isRunningSimulation || !scenarioName.trim() || selectedDocuments.length === 0}
                  className={`group w-full py-4 px-6 rounded-xl font-bold text-lg transition-all duration-300 transform ${
                    isRunningSimulation || !scenarioName.trim() || selectedDocuments.length === 0
                      ? 'bg-gray-300 cursor-not-allowed text-gray-500'
                      : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl hover:scale-105'
                  }`}
                >
                  <span className="flex items-center justify-center space-x-3">
                    {isRunningSimulation ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Running Simulation...</span>
                      </>
                    ) : (
                      <>
                        <span className="group-hover:animate-bounce">🚀</span>
                        <span>Run Simulation</span>
                      </>
                    )}
                  </span>
                </button>
              </div>
            </div>
            
            {/* Simulation Results */}
            <div className="space-y-6">
              <div className="flex items-center space-x-2">
                <div className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">2</span>
                </div>
                <h4 className="font-bold text-gray-900">Simulation Results</h4>
              </div>
              
              {simulationResults ? (
                <div className="space-y-6 animate-fade-in">
                  {/* Impact Narrative */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-2xl border border-blue-100">
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                        <span className="text-white text-sm">📋</span>
                      </div>
                      <h5 className="font-bold text-blue-900">Executive Summary</h5>
                    </div>
                    <p className="text-blue-800 leading-relaxed font-medium">
                      {simulationResults.impact_narrative}
                    </p>
                  </div>
                  
                  {/* Impact Metrics */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="group bg-gradient-to-br from-red-50 to-red-100 p-4 rounded-xl border border-red-100 hover:shadow-lg transition-all duration-300 transform hover:scale-105">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-2xl font-bold text-red-600 group-hover:animate-pulse">
                            {formatCurrency(simulationResults.financial_impact.cost_increase)}
                          </div>
                          <div className="text-sm font-medium text-red-800">Cost Increase</div>
                        </div>
                        <div className="text-2xl opacity-60 group-hover:animate-bounce">💸</div>
                      </div>
                    </div>
                    
                    <div className="group bg-gradient-to-br from-orange-50 to-orange-100 p-4 rounded-xl border border-orange-100 hover:shadow-lg transition-all duration-300 transform hover:scale-105">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-2xl font-bold text-orange-600 group-hover:animate-pulse">
                            {formatCurrency(simulationResults.financial_impact.revenue_at_risk)}
                          </div>
                          <div className="text-sm font-medium text-orange-800">Revenue at Risk</div>
                        </div>
                        <div className="text-2xl opacity-60 group-hover:animate-bounce">⚠️</div>
                      </div>
                    </div>
                    
                    <div className="group bg-gradient-to-br from-yellow-50 to-yellow-100 p-4 rounded-xl border border-yellow-100 hover:shadow-lg transition-all duration-300 transform hover:scale-105">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-2xl font-bold text-yellow-600 group-hover:animate-pulse">
                            {simulationResults.operational_impact.delay_hours}h
                          </div>
                          <div className="text-sm font-medium text-yellow-800">Process Delays</div>
                        </div>
                        <div className="text-2xl opacity-60 group-hover:animate-spin">⏰</div>
                      </div>
                    </div>
                    
                    <div className="group bg-gradient-to-br from-purple-50 to-purple-100 p-4 rounded-xl border border-purple-100 hover:shadow-lg transition-all duration-300 transform hover:scale-105">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="text-2xl font-bold text-purple-600 group-hover:animate-pulse">
                            {formatPercentage(simulationResults.compliance_impact.violation_risk)}
                          </div>
                          <div className="text-sm font-medium text-purple-800">Compliance Risk</div>
                        </div>
                        <div className="text-2xl opacity-60 group-hover:animate-bounce">🛡️</div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Affected Workflows */}
                  {simulationResults.affected_workflows.length > 0 && (
                    <div className="bg-gradient-to-r from-gray-50 to-slate-50 p-4 rounded-xl border border-gray-100">
                      <h5 className="font-bold text-gray-900 mb-3 flex items-center space-x-2">
                        <span className="animate-pulse">🔄</span>
                        <span>Affected Workflows</span>
                      </h5>
                      <div className="flex flex-wrap gap-2">
                        {simulationResults.affected_workflows.map((workflow, index) => (
                          <span 
                            key={index} 
                            className="px-3 py-1 bg-gradient-to-r from-gray-100 to-gray-200 text-gray-800 text-sm rounded-full font-medium animate-fade-in hover:from-blue-100 hover:to-blue-200 hover:text-blue-800 transition-all duration-200 transform hover:scale-105"
                            style={{ animationDelay: `${index * 100}ms` }}
                          >
                            {workflow.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Confidence Score */}
                  <div className="bg-gradient-to-r from-green-50 to-emerald-50 p-4 rounded-xl border border-green-100">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-700">Simulation Confidence</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-gradient-to-r from-green-400 to-green-500 h-2 rounded-full transition-all duration-1000 ease-out"
                            style={{ width: `${simulationResults.simulation_confidence * 100}%` }}
                          ></div>
                        </div>
                        <span className="font-bold text-green-600">
                          {formatPercentage(simulationResults.simulation_confidence)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 bg-gradient-to-br from-gray-50 to-slate-50 rounded-2xl border border-gray-100">
                  <div className="text-8xl mb-4 opacity-20 animate-pulse">🔬</div>
                  <div className="text-gray-600 font-medium mb-2">Ready for Simulation</div>
                  <div className="text-gray-400 text-sm">Configure your scenario and run the simulation to see predictive insights</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Help Section */}
        <div className="bg-gradient-to-r from-blue-50 via-purple-50 to-pink-50 rounded-2xl p-8 border border-white/30 shadow-xl animate-slide-up">
          <div className="text-center mb-8">
            <div className="inline-flex items-center space-x-3 bg-white/50 rounded-full px-6 py-3 backdrop-blur-sm">
              <span className="text-2xl animate-bounce">🎯</span>
              <h3 className="text-2xl font-bold bg-gradient-to-r from-blue-800 to-purple-800 bg-clip-text text-transparent">
                Digital Twin Capabilities
              </h3>
            </div>
            <p className="text-gray-600 mt-4 max-w-2xl mx-auto">
              Experience the power of AI-driven business simulation and predictive analytics
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="group bg-white/60 backdrop-blur-sm rounded-2xl p-6 hover:bg-white/80 transition-all duration-300 transform hover:scale-105 border border-blue-100">
              <div className="text-center mb-4">
                <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center mx-auto mb-3 group-hover:animate-pulse">
                  <span className="text-white text-2xl">📊</span>
                </div>
                <h4 className="font-bold text-blue-800 text-lg">Workflow Analytics</h4>
              </div>
              <ul className="space-y-3 text-blue-700">
                <li className="flex items-center space-x-2 group-hover:animate-fade-in">
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                  <span>Performance metrics tracking</span>
                </li>
                <li className="flex items-center space-x-2 group-hover:animate-fade-in" style={{ animationDelay: '0.1s' }}>
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                  <span>Bottleneck identification</span>
                </li>
                <li className="flex items-center space-x-2 group-hover:animate-fade-in" style={{ animationDelay: '0.2s' }}>
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                  <span>Success rate monitoring</span>
                </li>
                <li className="flex items-center space-x-2 group-hover:animate-fade-in" style={{ animationDelay: '0.3s' }}>
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                  <span>Cost analysis per execution</span>
                </li>
              </ul>
            </div>
            
            <div className="group bg-white/60 backdrop-blur-sm rounded-2xl p-6 hover:bg-white/80 transition-all duration-300 transform hover:scale-105 border border-purple-100">
              <div className="text-center mb-4">
                <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-3 group-hover:animate-pulse">
                  <span className="text-white text-2xl">🎯</span>
                </div>
                <h4 className="font-bold text-purple-800 text-lg">Risk Pattern Detection</h4>
              </div>
              <ul className="space-y-3 text-purple-700">
                <li className="flex items-center space-x-2 group-hover:animate-fade-in">
                  <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></span>
                  <span>Document-driven risk patterns</span>
                </li>
                <li className="flex items-center space-x-2 group-hover:animate-fade-in" style={{ animationDelay: '0.1s' }}>
                  <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></span>
                  <span>Impact frequency analysis</span>
                </li>
                <li className="flex items-center space-x-2 group-hover:animate-fade-in" style={{ animationDelay: '0.2s' }}>
                  <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></span>
                  <span>Business process correlations</span>
                </li>
                <li className="flex items-center space-x-2 group-hover:animate-fade-in" style={{ animationDelay: '0.3s' }}>
                  <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse"></span>
                  <span>Predictive risk modeling</span>
                </li>
              </ul>
            </div>
            
            <div className="group bg-white/60 backdrop-blur-sm rounded-2xl p-6 hover:bg-white/80 transition-all duration-300 transform hover:scale-105 border border-green-100">
              <div className="text-center mb-4">
                <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full flex items-center justify-center mx-auto mb-3 group-hover:animate-pulse">
                  <span className="text-white text-2xl">🔬</span>
                </div>
                <h4 className="font-bold text-green-800 text-lg">What-If Simulation</h4>
              </div>
              <ul className="space-y-3 text-green-700">
                <li className="flex items-center space-x-2 group-hover:animate-fade-in">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  <span>Financial impact modeling</span>
                </li>
                <li className="flex items-center space-x-2 group-hover:animate-fade-in" style={{ animationDelay: '0.1s' }}>
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  <span>Operational delay predictions</span>
                </li>
                <li className="flex items-center space-x-2 group-hover:animate-fade-in" style={{ animationDelay: '0.2s' }}>
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  <span>Compliance risk assessment</span>
                </li>
                <li className="flex items-center space-x-2 group-hover:animate-fade-in" style={{ animationDelay: '0.3s' }}>
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  <span>Multi-workflow analysis</span>
                </li>
              </ul>
            </div>
          </div>
          
          {/* Call to Action */}
          <div className="text-center mt-8">
            <div className="inline-flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-3 rounded-full font-medium hover:from-blue-700 hover:to-purple-700 transition-all duration-200 transform hover:scale-105 shadow-lg hover:shadow-xl">
              <span className="animate-bounce">🚀</span>
              <span>Start Your Digital Twin Journey</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}