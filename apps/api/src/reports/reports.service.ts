import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateReportDto } from './dto/create-report.dto';
import { Prisma } from '@vx/database';

type ReportFilters = {
  from?: Date;
  to?: Date;
  onlyErrors?: boolean;
  component?: string;
  onlyOperativo?: boolean;
};

@Injectable()
export class ReportsService {
  constructor(private readonly prisma: PrismaService) {}

  async create(dto: CreateReportDto) {
    return this.prisma.report.create({
      data: {
        timestamp: new Date(dto.timestamp),
        migrasfreeCid: dto.migrasfree_cid,
        usuarioGrafico: dto.usuario_grafico,
        verificacionEquipos: dto.verificacion_equipos as unknown as Prisma.InputJsonValue,
        resumen: dto.resumen as unknown as Prisma.InputJsonValue,
      },
    });
  }

  async findAll(limit = 50, filters: ReportFilters = {}) {
    const take = Math.min(Math.max(limit, 1), 500);

    const reports = await this.prisma.report.findMany({
      take,
      orderBy: { createdAt: 'desc' },
    });

    const filtered = reports.filter((r) => {
      if (filters.from && new Date(r.timestamp) < filters.from) return false;
      if (filters.to && new Date(r.timestamp) > filters.to) return false;

      if (filters.onlyErrors) {
        const resumen = r.resumen as unknown as Record<string, unknown>;
        const requiere = Boolean(resumen?.requiere_atencion);
        if (!requiere) return false;
      }

      if (filters.component) {
        const ve = r.verificacionEquipos as unknown as Record<string, any>;
        const entry = ve?.[filters.component];
        if (!entry) return false;
        // Always filter by defectuoso when component is selected
        if (entry?.estado !== 'defectuoso') return false;
      }

      if (filters.onlyOperativo !== undefined) {
        const resumen = r.resumen as unknown as Record<string, unknown>;
        const operativo = Boolean(resumen?.equipo_operativo);
        if (filters.onlyOperativo !== operativo) return false;
      }

      return true;
    });

    return filtered;
  }

  async findOne(id: string) {
    return this.prisma.report.findUnique({
      where: { id },
    });
  }
}
