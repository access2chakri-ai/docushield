"use client";

import { useState } from 'react';

interface DocumentTypeFilterProps {
  selectedDocumentTypes: string[];
  selectedIndustryTypes: string[];
  onDocumentTypesChange: (types: string[]) => void;
  onIndustryTypesChange: (types: string[]) => void;
  onClearFilters: () => void;
}

const DOCUMENT_TYPES = [
  { value: 'contract', label: 'Contracts' },
  { value: 'agreement', label: 'Agreements' },
  { value: 'invoice', label: 'Invoices' },
  { value: 'proposal', label: 'Proposals' },
  { value: 'report', label: 'Reports' },
  { value: 'policy', label: 'Policies' },
  { value: 'manual', label: 'Manuals' },
  { value: 'specification', label: 'Specifications' },
  { value: 'legal_document', label: 'Legal Documents' },
  { value: 'research_paper', label: 'Research Papers' },
  { value: 'whitepaper', label: 'Whitepapers' },
  { value: 'presentation', label: 'Presentations' },
  { value: 'memo', label: 'Memos' },
  { value: 'email', label: 'Emails' },
  { value: 'letter', label: 'Letters' },
  { value: 'form', label: 'Forms' }
];

const INDUSTRY_TYPES = [
  { value: 'Technology/SaaS', label: 'Technology/SaaS' },
  { value: 'Legal', label: 'Legal' },
  { value: 'Financial Services', label: 'Financial Services' },
  { value: 'Healthcare', label: 'Healthcare' },
  { value: 'Real Estate', label: 'Real Estate' },
  { value: 'Manufacturing', label: 'Manufacturing' },
  { value: 'Retail', label: 'Retail' },
  { value: 'Education', label: 'Education' },
  { value: 'Government', label: 'Government' },
  { value: 'Non-profit', label: 'Non-profit' },
  { value: 'Consulting', label: 'Consulting' },
  { value: 'Media', label: 'Media' }
];

export default function DocumentTypeFilter({
  selectedDocumentTypes,
  selectedIndustryTypes,
  onDocumentTypesChange,
  onIndustryTypesChange,
  onClearFilters
}: DocumentTypeFilterProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleDocumentTypeToggle = (type: string) => {
    if (selectedDocumentTypes.includes(type)) {
      onDocumentTypesChange(selectedDocumentTypes.filter(t => t !== type));
    } else {
      onDocumentTypesChange([...selectedDocumentTypes, type]);
    }
  };

  const handleIndustryTypeToggle = (type: string) => {
    if (selectedIndustryTypes.includes(type)) {
      onIndustryTypesChange(selectedIndustryTypes.filter(t => t !== type));
    } else {
      onIndustryTypesChange([...selectedIndustryTypes, type]);
    }
  };

  const totalFilters = selectedDocumentTypes.length + selectedIndustryTypes.length;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <h3 className="text-sm font-medium text-gray-900">Filters</h3>
          {totalFilters > 0 && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {totalFilters} active
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {totalFilters > 0 && (
            <button
              onClick={onClearFilters}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Clear all
            </button>
          )}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {isExpanded ? 'Hide' : 'Show'} filters
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="space-y-4">
          {/* Document Types */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Document Types</h4>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {DOCUMENT_TYPES.map((type) => (
                <label key={type.value} className="flex items-center space-x-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedDocumentTypes.includes(type.value)}
                    onChange={() => handleDocumentTypeToggle(type.value)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-gray-700">{type.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Industry Types */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">Industry Types</h4>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {INDUSTRY_TYPES.map((type) => (
                <label key={type.value} className="flex items-center space-x-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedIndustryTypes.includes(type.value)}
                    onChange={() => handleIndustryTypeToggle(type.value)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-gray-700">{type.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Active Filters Display */}
      {totalFilters > 0 && !isExpanded && (
        <div className="mt-2">
          <div className="flex flex-wrap gap-1">
            {selectedDocumentTypes.map((type) => (
              <span
                key={type}
                className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                {DOCUMENT_TYPES.find(t => t.value === type)?.label}
                <button
                  onClick={() => handleDocumentTypeToggle(type)}
                  className="ml-1 text-blue-600 hover:text-blue-800"
                >
                  ×
                </button>
              </span>
            ))}
            {selectedIndustryTypes.map((type) => (
              <span
                key={type}
                className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800"
              >
                {INDUSTRY_TYPES.find(t => t.value === type)?.label}
                <button
                  onClick={() => handleIndustryTypeToggle(type)}
                  className="ml-1 text-green-600 hover:text-green-800"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}