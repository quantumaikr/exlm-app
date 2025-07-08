'use client';

import { useWebSocket } from '@/hooks/useWebSocket';
import { cn } from '@/lib/utils';
import { Wifi, WifiOff } from 'lucide-react';

export function WebSocketIndicator() {
  const { isConnected } = useWebSocket();

  return (
    <div className="flex items-center space-x-2 text-sm">
      {isConnected ? (
        <>
          <Wifi className="h-4 w-4 text-green-500" />
          <span className="text-muted-foreground">실시간 연결됨</span>
        </>
      ) : (
        <>
          <WifiOff className="h-4 w-4 text-red-500" />
          <span className="text-muted-foreground">연결 끊김</span>
        </>
      )}
    </div>
  );
}