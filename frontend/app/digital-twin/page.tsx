"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getUserData, isAuthenticated, authenticatedFetch, type User } from '@/utils/auth';
import { config } from '@/utils/config';

interface SystemState {
  total_documents: number;
  processing_capacity: number;
  average_processing_time: number;
  accuracy_rate: number;
  risk_distribution: Record<string, number>;
  compliance_rate: number;
  knowledge_coverage: number;
  system_health: number;
}

interface SimulationResult {
  simulation_id: string;
  scenario_name: string;
  baseline_state: SystemState;
  simulated_state: SystemState;
  impact_analysis: any;
  recommendations: string[];
  confidence_score: number;
  execution_time_ms: number;
}

interface Scenario {
  scenario_type: string;
  name: string;
  description: string;
  expected_impacts: Record<string, number>;
}

export default function DigitalTwinPage() {
  const [user, setUser] = useState<User | null>(null);
  const [systemState, setSystemState] = useState<SystemState | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState('');
  const [customParameters, setCustomParameters] = useState<Record<string, any>>({});
  const router = useRouter();

  useEffect(() => {
    // Check authentication
    if (!isAuthenticated()) {
      router.push('/auth');
      return;
    }

    const currentUser = getUserData();
    if (currentUser) {
      setUser(currentUser);
      loadSystemState();
      loadScenarios();
    }
  }, [router]);

  const loadSystemState = async () => {
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/digital-twin/system-state`);
      
      if (response.ok) {
        const data = await response.json();
        setSystemState(data.system_state);
      }
    } catch (error) {
      console.error('Failed to load system state:', error);
    }
  };

  const loadScenarios = async () => {
    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/digital-twin/scenarios`);
      
      if (response.ok) {
        const data = await response.json();
        setScenarios(data.scenarios || []);
      }
    } catch (error) {
      console.error('Failed to load scenarios:', error);
    }
  };

  const runSimulation = async () => {
    if (!selectedScenario) return;

    setIsLoading(true);
    setSimulationResult(null);

    try {
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/digital-twin/simulate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          scenario_name: selectedScenario,
          parameter_changes: Object.keys(customParameters).length > 0 ? customParameters : null
        })
      });

      if (response.ok) {
        const result = await response.json();
        setSimulationResult(result);
      } else {
        throw new Error(`Simulation failed: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Simulation error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatMetric = (value: number, type: 'percentage' | 'time' | 'number' | 'capacity') => {
    switch (type) {
      case 'percentage':
        return `${(value * 100).toFixed(1)}%`;
      case 'time':
        return `${value.toFixed(1)}s`;
      case 'capacity':
        return `${value.toFixed(0)} docs/hr`;
      default:
        return value.toFixed(0);
    }
  };

  const getHealthColor = (health: number) => {
    if (health >= 0.8) return 'text-green-600';
    if (health >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getImpactColor = (impact: string) => {
    return impact === 'positive' ? 'text-green-600' : 'text-red-600';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 relative overflow-hidden">
      {/* Floating digital twin elements */}
      <div className="floating-document top-20 left-10 text-6xl">🔮</div>
      <div className="floating-document top-32 right-16 text-5xl">⚡</div>
      <div className="floating-document bottom-40 left-1/4 text-4xl">📊</div>
      <div className="floating-document bottom-24 right-1/3 text-5xl">🎯</div>
      
      <div className="container mx-auto px-4 py-8 max-w-7xl relative z-10">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Document Intelligence Digital Twin</h1>
            <p className="text-gray-600 mt-2">
              Simulate document processing scenarios and predict system behavior
            </p>
          </div>
          <div className="flex space-x-4">
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

        {/* System State Overview */}
        {systemState && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">📊 Current System State</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{systemState.total_documents}</div>
                <div className="text-sm text-gray-600">Total Documents</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {formatMetric(systemState.processing_capacity, 'capacity')}
                </div>
                <div className="text-sm text-gray-600">Processing Capacity</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {formatMetric(systemState.accuracy_rate, 'percentage')}
                </div>
                <div className="text-sm text-gray-600">Accuracy Rate</div>
              </div>
              <div className="text-center">
                <div className={`text-2xl font-bold ${getHealthColor(systemState.system_health)}`}>
                  {formatMetric(systemState.system_health, 'percentage')}
                </div>
                <div className="text-sm text-gray-600">System Health</div>
              </div>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Simulation Controls */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">🎯 Run Simulation</h2>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Simulation Scenario
                </label>
                <select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={isLoading}
                >
                  <option value="">Select a scenario...</option>
                  {scenarios.map((scenario) => (
                    <option key={scenario.scenario_type} value={scenario.scenario_type}>
                      {scenario.name}
                    </option>
                  ))}
                </select>
              </div>

              {selectedScenario && (
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-medium text-blue-900 mb-2">Scenario Description</h3>
                  <p className="text-blue-700 text-sm">
                    {scenarios.find(s => s.scenario_type === selectedScenario)?.description}
                  </p>
                </div>
              )}

              <button
                onClick={runSimulation}
                disabled={isLoading || !selectedScenario}
                className={`w-full py-3 px-4 rounded-lg font-medium ${
                  isLoading || !selectedScenario
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                } text-white`}
              >
                {isLoading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Running Simulation...
                  </span>
                ) : (
                  '🚀 Run Simulation'
                )}
              </button>
            </div>
          </div>

          {/* Available Scenarios */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">📋 Available Scenarios</h2>
            
            <div className="space-y-3">
              {scenarios.map((scenario) => (
                <div 
                  key={scenario.scenario_type} 
                  className={`border rounded-lg p-4 cursor-pointer transition-colors ${
                    selectedScenario === scenario.scenario_type 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedScenario(scenario.scenario_type)}
                >
                  <h3 className="font-medium text-gray-900">{scenario.name}</h3>
                  <p className="text-sm text-gray-600 mt-1">{scenario.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Simulation Results */}
        {simulationResult && (
          <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-semibold mb-4">📈 Simulation Results</h2>
            
            <div className="grid md:grid-cols-2 gap-6 mb-6">
              {/* Baseline vs Simulated */}
              <div>
                <h3 className="font-medium text-gray-900 mb-3">System Metrics Comparison</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Processing Time:</span>
                    <div className="text-right">
                      <div className="text-sm">
                        {formatMetric(simulationResult.baseline_state.average_processing_time, 'time')} → {formatMetric(simulationResult.simulated_state.average_processing_time, 'time')}
                      </div>
                      <div className={`text-xs ${getImpactColor(simulationResult.impact_analysis.processing_time_change.impact)}`}>
                        {simulationResult.impact_analysis.processing_time_change.change_percent.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Accuracy Rate:</span>
                    <div className="text-right">
                      <div className="text-sm">
                        {formatMetric(simulationResult.baseline_state.accuracy_rate, 'percentage')} → {formatMetric(simulationResult.simulated_state.accuracy_rate, 'percentage')}
                      </div>
                      <div className={`text-xs ${getImpactColor(simulationResult.impact_analysis.accuracy_change.impact)}`}>
                        {simulationResult.impact_analysis.accuracy_change.change_percent.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">System Health:</span>
                    <div className="text-right">
                      <div className="text-sm">
                        {formatMetric(simulationResult.baseline_state.system_health, 'percentage')} → {formatMetric(simulationResult.simulated_state.system_health, 'percentage')}
                      </div>
                      <div className={`text-xs ${getImpactColor(simulationResult.impact_analysis.system_health_change.impact)}`}>
                        {simulationResult.impact_analysis.system_health_change.change_percent.toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              <div>
                <h3 className="font-medium text-gray-900 mb-3">Recommendations</h3>
                <div className="space-y-2">
                  {simulationResult.recommendations.slice(0, 5).map((recommendation, index) => (
                    <div key={index} className="text-sm text-gray-700 flex items-start">
                      <span className="text-blue-500 mr-2">•</span>
                      <span>{recommendation}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="border-t pt-4">
              <div className="flex justify-between items-center text-sm text-gray-600">
                <span>Confidence Score: {(simulationResult.confidence_score * 100).toFixed(1)}%</span>
                <span>Execution Time: {simulationResult.execution_time_ms.toFixed(0)}ms</span>
              </div>
            </div>
          </div>
        )}

        {/* Information Cards */}
        <div className="mt-8 grid md:grid-cols-3 gap-6">
          <div className="bg-blue-50 rounded-lg p-6">
            <div className="text-blue-600 text-2xl mb-3">🎯</div>
            <h3 className="font-semibold text-blue-900 mb-2">Scenario Modeling</h3>
            <p className="text-blue-700 text-sm">
              Model different document processing scenarios like volume surges, quality changes, and system optimizations.
            </p>
          </div>
          
          <div className="bg-green-50 rounded-lg p-6">
            <div className="text-green-600 text-2xl mb-3">📊</div>
            <h3 className="font-semibold text-green-900 mb-2">Impact Analysis</h3>
            <p className="text-green-700 text-sm">
              Analyze the potential impact of changes on processing time, accuracy, compliance, and system health.
            </p>
          </div>
          
          <div className="bg-purple-50 rounded-lg p-6">
            <div className="text-purple-600 text-2xl mb-3">⚡</div>
            <h3 className="font-semibold text-purple-900 mb-2">Predictive Insights</h3>
            <p className="text-purple-700 text-sm">
              Get predictive insights and actionable recommendations to optimize your document processing workflows.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}