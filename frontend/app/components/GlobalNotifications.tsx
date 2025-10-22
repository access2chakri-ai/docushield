"use client";

import { useDocumentProcessing } from '../contexts/DocumentProcessingContext';
import NotificationSystem from './NotificationSystem';

export default function GlobalNotifications() {
  const { notifications, dismissNotification } = useDocumentProcessing();

  // Filter for upload-related notifications only
  const uploadNotifications = notifications.filter(n => n.category === 'upload');

  console.log('🔔 GlobalNotifications render - upload notifications count:', uploadNotifications.length);

  return (
    <NotificationSystem
      notifications={uploadNotifications}
      onDismiss={dismissNotification}
    />
  );
}