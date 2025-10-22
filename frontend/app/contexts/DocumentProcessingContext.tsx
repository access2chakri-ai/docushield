"use client";

import { createContext, useContext, useState, useEffect, ReactNode, useRef } from 'react';
import { authenticatedFetch, isAuthenticated } from '../../utils/auth';
import { config } from '../../utils/config';

interface ProcessingDocument {
  contract_id: string;
  filename: string;
  status: 'processing' | 'completed' | 'failed';
}

interface Notification {
  id: string;
  type: 'success' | 'info' | 'warning' | 'error';
  title: string;
  message: string;
  duration?: number;
  persistent?: boolean;
  category?: 'upload' | 'general'; // Add category to filter notifications
}

interface DocumentProcessingContextType {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  dismissNotification: (id: string) => void;
  startPolling: (contractId: string, filename: string) => void;
  stopPolling: (contractId: string) => void;
  testNotification: () => void; // For debugging
}

const DocumentProcessingContext = createContext<DocumentProcessingContextType | undefined>(undefined);

export function DocumentProcessingProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [processingDocuments, setProcessingDocuments] = useState<ProcessingDocument[]>([]);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);
  const processingDocumentsRef = useRef<ProcessingDocument[]>([]);

  // Keep ref in sync with state
  useEffect(() => {
    processingDocumentsRef.current = processingDocuments;
  }, [processingDocuments]);

  const addNotification = (notification: Omit<Notification, 'id'>) => {
    const id = Date.now().toString() + Math.random().toString(36).substring(2, 11);
    console.log('🔔 Adding notification:', notification.title);
    setNotifications(prev => [...prev, { ...notification, id }]);
  };

  const dismissNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const startPolling = (contractId: string, filename: string) => {
    console.log('🚀 Starting polling for document:', filename, contractId);
    setProcessingDocuments(prev => {
      // Don't add if already exists
      if (prev.some(doc => doc.contract_id === contractId)) {
        console.log('📋 Document already being polled:', contractId);
        return prev;
      }
      console.log('📋 Adding document to polling list:', contractId);
      return [...prev, { contract_id: contractId, filename, status: 'processing' }];
    });
  };

  const stopPolling = (contractId: string) => {
    console.log('🛑 Stopping polling for document:', contractId);
    setProcessingDocuments(prev => prev.filter(doc => doc.contract_id !== contractId));
  };

  const testNotification = () => {
    console.log('🧪 Testing notification system');
    addNotification({
      type: 'success',
      title: 'Test Notification',
      message: 'This is a test to verify the global notification system is working!',
      duration: 5000,
      category: 'general'
    });
  };

  // Poll document status for all processing documents
  const pollDocumentStatus = async (contractId: string) => {
    if (!isAuthenticated()) return;

    try {
      console.log('🔄 Polling status for document:', contractId);
      const response = await authenticatedFetch(`${config.apiBaseUrl}/api/documents/${contractId}/status`);
      if (response.ok) {
        const statusData = await response.json();
        console.log('📊 Status response for', contractId, ':', statusData.status);

        // Update document status and get the current document info
        let currentDoc: ProcessingDocument | undefined;
        setProcessingDocuments(prev => {
          const updated = prev.map(doc => {
            if (doc.contract_id === contractId) {
              currentDoc = { ...doc, status: statusData.status };
              return currentDoc;
            }
            return doc;
          });
          return updated;
        });

        // Handle completion or failure
        if (statusData.status === 'completed' || statusData.status === 'failed') {
          // Use the current document info we just captured
          if (currentDoc && statusData.status === 'completed') {
            console.log('🎉 Global notification: Document processing completed for', currentDoc.filename);
            
            // Show completion notification
            addNotification({
              type: 'success',
              title: 'Analysis Complete!',
              message: `${currentDoc.filename} is now ready! We've extracted all the key information and made it searchable. You can now ask questions about it or search through its content.`,
              duration: 15000, // Increased by 3 seconds (12000 + 3000)
              persistent: false,
              category: 'upload'
            });
          } else if (currentDoc && statusData.status === 'failed') {
            console.log('❌ Document processing failed for', currentDoc.filename);
            addNotification({
              type: 'error',
              title: 'Processing Failed',
              message: `${currentDoc.filename} could not be processed. Please try uploading again.`,
              duration: 13000, // Increased by 3 seconds (10000 + 3000)
              persistent: false,
              category: 'upload'
            });
          }

          // Remove from processing list
          console.log('🛑 Stopping polling for completed document:', contractId);
          stopPolling(contractId);
        }
      } else {
        console.error('Failed to get document status:', response.status, response.statusText);
      }
    } catch (error) {
      console.error('Failed to poll document status:', error);
    }
  };

  // Set up polling interval
  useEffect(() => {
    if (processingDocuments.length > 0) {
      console.log(`📊 Global polling started for ${processingDocuments.length} documents:`, processingDocuments.map(d => d.filename));
      
      const interval = setInterval(() => {
        const currentDocs = processingDocumentsRef.current;
        console.log('⏰ Polling tick - checking', currentDocs.length, 'documents');
        currentDocs.forEach(doc => {
          if (doc.status === 'processing') {
            console.log('🔄 Polling document:', doc.filename, doc.contract_id);
            pollDocumentStatus(doc.contract_id);
          } else {
            console.log('⏸️ Skipping non-processing document:', doc.filename, doc.status);
          }
        });
      }, 3000); // Poll every 3 seconds

      setPollingInterval(interval);

      return () => {
        console.log('🛑 Global polling stopped');
        clearInterval(interval);
      };
    } else if (pollingInterval) {
      console.log('🛑 Clearing polling interval - no documents to poll');
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
  }, [processingDocuments.length]); // Only depend on length to avoid stale closures

  // Auto-dismiss notifications
  useEffect(() => {
    notifications.forEach(notification => {
      if (!notification.persistent && notification.duration !== 0) {
        const timer = setTimeout(() => {
          dismissNotification(notification.id);
        }, notification.duration || 5000);

        return () => clearTimeout(timer);
      }
    });
  }, [notifications]);

  return (
    <DocumentProcessingContext.Provider value={{
      notifications,
      addNotification,
      dismissNotification,
      startPolling,
      stopPolling,
      testNotification
    }}>
      {children}
    </DocumentProcessingContext.Provider>
  );
}

export function useDocumentProcessing() {
  const context = useContext(DocumentProcessingContext);
  if (context === undefined) {
    throw new Error('useDocumentProcessing must be used within a DocumentProcessingProvider');
  }
  return context;
}