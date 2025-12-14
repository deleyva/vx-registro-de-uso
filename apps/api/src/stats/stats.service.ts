import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class StatsService {
  constructor(private readonly prisma: PrismaService) {}

  async getDeviceStats() {
    const totalDevices = await this.prisma.device.count();
    const activeDevices = await this.prisma.device.count({
      where: { isActive: true },
    });

    // Estadísticas de uso promedio (últimos 7 días)
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    const recentLogs = await this.prisma.usageLog.aggregate({
      where: {
        timestamp: { gte: sevenDaysAgo },
      },
      _avg: {
        cpuUsage: true,
        ramUsage: true,
        diskUsage: true,
      },
    });

    return {
      totalDevices,
      activeDevices,
      inactiveDevices: totalDevices - activeDevices,
      averageCpuUsage: recentLogs._avg.cpuUsage || 0,
      averageRamUsage: recentLogs._avg.ramUsage || 0,
      averageDiskUsage: recentLogs._avg.diskUsage || 0,
    };
  }

  async getUsageStats() {
    // Top 10 dispositivos con mayor uso
    const devices = await this.prisma.device.findMany({
      take: 10,
      orderBy: { lastSeen: 'desc' },
    });

    const stats = await Promise.all(
      devices.map(async (device) => {
        const logs = await this.prisma.usageLog.aggregate({
          where: { deviceId: device.id },
          _avg: {
            cpuUsage: true,
            ramUsage: true,
            diskUsage: true,
            uptime: true,
          },
          _max: {
            cpuUsage: true,
            ramUsage: true,
            diskUsage: true,
          },
        });

        return {
          deviceId: device.id,
          hostname: device.hostname,
          avgCpuUsage: logs._avg.cpuUsage || 0,
          maxCpuUsage: logs._max.cpuUsage || 0,
          avgRamUsage: logs._avg.ramUsage || 0,
          maxRamUsage: logs._max.ramUsage || 0,
          avgDiskUsage: logs._avg.diskUsage || 0,
          maxDiskUsage: logs._max.diskUsage || 0,
          totalUptime: logs._avg.uptime || 0,
        };
      }),
    );

    return stats;
  }
}
