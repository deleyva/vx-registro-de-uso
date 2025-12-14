import { Injectable, NotFoundException, ConflictException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { RegisterDeviceDto } from './dto/register-device.dto';
import { UpdateDeviceDto } from './dto/update-device.dto';

@Injectable()
export class DevicesService {
  constructor(private prisma: PrismaService) {}

  async register(dto: RegisterDeviceDto) {
    const existing = await this.prisma.device.findUnique({
      where: { hostname: dto.hostname },
    });

    if (existing) {
      return this.prisma.device.update({
        where: { id: existing.id },
        data: {
          ...dto,
          lastSeen: new Date(),
          isActive: true,
        },
      });
    }

    return this.prisma.device.create({
      data: {
        ...dto,
        isActive: true,
      },
    });
  }

  async findAll(isActive?: boolean) {
    return this.prisma.device.findMany({
      where: isActive !== undefined ? { isActive } : undefined,
      orderBy: { lastSeen: 'desc' },
    });
  }

  async findOne(id: string) {
    const device = await this.prisma.device.findUnique({
      where: { id },
      include: {
        usageLogs: {
          take: 10,
          orderBy: { timestamp: 'desc' },
        },
      },
    });

    if (!device) {
      throw new NotFoundException(`Device ${id} not found`);
    }

    return device;
  }

  async update(id: string, dto: UpdateDeviceDto) {
    try {
      return await this.prisma.device.update({
        where: { id },
        data: dto,
      });
    } catch (error) {
      throw new NotFoundException(`Device ${id} not found`);
    }
  }

  async remove(id: string) {
    try {
      return await this.prisma.device.delete({
        where: { id },
      });
    } catch (error) {
      throw new NotFoundException(`Device ${id} not found`);
    }
  }

  async heartbeat(id: string) {
    try {
      return await this.prisma.device.update({
        where: { id },
        data: {
          lastSeen: new Date(),
          isActive: true,
        },
      });
    } catch (error) {
      throw new NotFoundException(`Device ${id} not found`);
    }
  }

  async deactivateInactive(minutesInactive = 15) {
    const threshold = new Date(Date.now() - minutesInactive * 60 * 1000);
    
    return this.prisma.device.updateMany({
      where: {
        lastSeen: { lt: threshold },
        isActive: true,
      },
      data: { isActive: false },
    });
  }
}
