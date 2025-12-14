import { Controller, Get } from '@nestjs/common';
import { ApiTags, ApiOperation } from '@nestjs/swagger';
import { StatsService } from './stats.service';

@ApiTags('stats')
@Controller('stats')
export class StatsController {
  constructor(private readonly statsService: StatsService) {}

  @Get('devices')
  @ApiOperation({ summary: 'Estadísticas generales de equipos' })
  async getDeviceStats() {
    return this.statsService.getDeviceStats();
  }

  @Get('usage')
  @ApiOperation({ summary: 'Estadísticas de uso por equipo' })
  async getUsageStats() {
    return this.statsService.getUsageStats();
  }
}
