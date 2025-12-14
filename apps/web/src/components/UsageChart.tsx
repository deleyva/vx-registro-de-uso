'use client';

import type { DeviceResponse } from '@vx/types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface UsageChartProps {
  devices: DeviceResponse[];
}

export function UsageChart({ devices }: UsageChartProps) {
  // Tomar los 10 dispositivos más recientes
  const chartData = devices.slice(0, 10).map((device) => ({
    name: device.hostname,
    RAM: device.ramTotal || 0,
    Disco: Math.round((device.diskTotal || 0) / 10), // Escalar para visualización
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-border">
      <h2 className="text-xl font-bold text-foreground mb-6">Recursos por Equipo</h2>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis 
            dataKey="name" 
            className="text-sm text-muted-foreground"
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis className="text-sm text-muted-foreground" />
          <Tooltip 
            contentStyle={{
              backgroundColor: 'hsl(var(--background))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
          />
          <Legend />
          <Bar dataKey="RAM" fill="hsl(var(--primary))" name="RAM (GB)" />
          <Bar dataKey="Disco" fill="hsl(217.2 91.2% 59.8%)" name="Disco (x10 GB)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
