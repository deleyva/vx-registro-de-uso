import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateUsageLogDto } from './dto/create-usage-log.dto';

@Injectable()
export class UsageService {
  constructor(private prisma: PrismaService) {}

  async create(dto: CreateUsageLogDto) {
    const device = await this.prisma.device.findUnique({
      where: { id: dto.deviceId },
    });

    if (!device) {
      throw new NotFoundException(`Device ${dto.deviceId} not found`);
    }

    await this.prisma.device.update({
      where: { id: dto.deviceId },
      data: { lastSeen: new Date() },
    });

    return this.prisma.usageLog.create({
      data: dto,
    });
  }

  async findAll(deviceId?: string, limit = 100) {
    return this.prisma.usageLog.findMany({
      where: deviceId ? { deviceId } : undefined,
      take: limit,
      orderBy: { timestamp: 'desc' },
      include: {
        device: {
          select: {
            hostname: true,
            ipAddress: true,
          },
        },
      },
    });
  }

  async findByDevice(deviceId: string, limit = 50) {
    return this.prisma.usageLog.findMany({
      where: { deviceId },
      take: limit,
      orderBy: { timestamp: 'desc' },
    });
  }
}
