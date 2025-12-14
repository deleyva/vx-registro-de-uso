import type { DeviceStats } from '@vx/types';
import { Server, Activity, HardDrive, Cpu, MemoryStick } from 'lucide-react';

interface StatsCardsProps {
  stats: DeviceStats;
}

export function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    {
      title: 'Total de Equipos',
      value: stats.totalDevices,
      icon: Server,
      color: 'text-blue-500',
      bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    },
    {
      title: 'Equipos Activos',
      value: stats.activeDevices,
      icon: Activity,
      color: 'text-green-500',
      bgColor: 'bg-green-100 dark:bg-green-900/30',
    },
    {
      title: 'CPU Promedio',
      value: `${stats.averageCpuUsage.toFixed(1)}%`,
      icon: Cpu,
      color: 'text-purple-500',
      bgColor: 'bg-purple-100 dark:bg-purple-900/30',
    },
    {
      title: 'RAM Promedio',
      value: `${stats.averageRamUsage.toFixed(1)} GB`,
      icon: MemoryStick,
      color: 'text-orange-500',
      bgColor: 'bg-orange-100 dark:bg-orange-900/30',
    },
    {
      title: 'Disco Promedio',
      value: `${stats.averageDiskUsage.toFixed(0)} GB`,
      icon: HardDrive,
      color: 'text-pink-500',
      bgColor: 'bg-pink-100 dark:bg-pink-900/30',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.title}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-border hover:shadow-lg transition-shadow"
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 rounded-lg ${card.bgColor}`}>
                <Icon className={`w-6 h-6 ${card.color}`} />
              </div>
            </div>
            <h3 className="text-sm font-medium text-muted-foreground mb-1">{card.title}</h3>
            <p className="text-2xl font-bold text-foreground">{card.value}</p>
          </div>
        );
      })}
    </div>
  );
}
