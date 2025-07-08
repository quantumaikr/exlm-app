'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Activity, Cpu, HardDrive, MemoryStick, Wifi, WifiOff } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SystemMetrics {
  system: {
    cpu: {
      percent: number;
      count: number;
    };
    memory: {
      total_mb: number;
      available_mb: number;
      percent: number;
    };
    disk: {
      total_gb: number;
      free_gb: number;
      percent: number;
    };
  };
  process: {
    cpu_percent: number;
    memory_mb: number;
    num_threads: number;
  };
}

interface HealthStatus {
  status: string;
  checks?: {
    database: boolean;
    redis: boolean;
    disk_space: boolean;
    memory: boolean;
  };
}

export function SystemStatus() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchSystemStatus = async () => {
    try {
      const [metricsRes, healthRes] = await Promise.all([
        fetch('/api/v1/health/metrics'),
        fetch('/api/v1/health/ready')
      ]);

      if (metricsRes.ok) {
        const metricsData = await metricsRes.json();
        setMetrics(metricsData);
      }

      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealth(healthData);
      }
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            시스템 상태
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="animate-pulse">
              <div className="h-4 bg-muted rounded w-1/3 mb-2"></div>
              <div className="h-2 bg-muted rounded"></div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const isHealthy = health?.status === 'ready' && Object.values(health.checks || {}).every(v => v);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            시스템 상태
          </CardTitle>
          <Badge variant={isHealthy ? 'success' : 'destructive'}>
            {isHealthy ? (
              <>
                <Wifi className="h-3 w-3 mr-1" />
                정상
              </>
            ) : (
              <>
                <WifiOff className="h-3 w-3 mr-1" />
                문제 발생
              </>
            )}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* CPU Usage */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sm">
                <Cpu className="h-4 w-4" />
                <span>CPU 사용률</span>
              </div>
              <span className="text-sm font-medium">
                {metrics?.system.cpu.percent.toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={metrics?.system.cpu.percent || 0} 
              className={cn(
                "h-2",
                metrics?.system.cpu.percent && metrics.system.cpu.percent > 80 && "bg-red-100"
              )}
            />
          </div>

          {/* Memory Usage */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sm">
                <MemoryStick className="h-4 w-4" />
                <span>메모리 사용률</span>
              </div>
              <span className="text-sm font-medium">
                {metrics?.system.memory.percent.toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={metrics?.system.memory.percent || 0} 
              className={cn(
                "h-2",
                metrics?.system.memory.percent && metrics.system.memory.percent > 80 && "bg-red-100"
              )}
            />
            <p className="text-xs text-muted-foreground mt-1">
              {((metrics?.system.memory.total_mb || 0) - (metrics?.system.memory.available_mb || 0)).toFixed(0)} MB / {metrics?.system.memory.total_mb.toFixed(0)} MB
            </p>
          </div>

          {/* Disk Usage */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-sm">
                <HardDrive className="h-4 w-4" />
                <span>디스크 사용률</span>
              </div>
              <span className="text-sm font-medium">
                {metrics?.system.disk.percent.toFixed(1)}%
              </span>
            </div>
            <Progress 
              value={metrics?.system.disk.percent || 0} 
              className={cn(
                "h-2",
                metrics?.system.disk.percent && metrics.system.disk.percent > 90 && "bg-red-100"
              )}
            />
            <p className="text-xs text-muted-foreground mt-1">
              {((metrics?.system.disk.total_gb || 0) - (metrics?.system.disk.free_gb || 0)).toFixed(1)} GB / {metrics?.system.disk.total_gb.toFixed(1)} GB
            </p>
          </div>

          {/* Service Status */}
          {health?.checks && (
            <div className="pt-2 border-t">
              <h4 className="text-sm font-medium mb-2">서비스 상태</h4>
              <div className="grid grid-cols-2 gap-2">
                <div className="flex items-center gap-2">
                  <div className={cn(
                    "h-2 w-2 rounded-full",
                    health.checks.database ? "bg-green-500" : "bg-red-500"
                  )} />
                  <span className="text-xs">Database</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={cn(
                    "h-2 w-2 rounded-full",
                    health.checks.redis ? "bg-green-500" : "bg-red-500"
                  )} />
                  <span className="text-xs">Redis</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}