import { Controller, Get, Post, Body, Query, Param } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiQuery } from '@nestjs/swagger';
import { UsageService } from './usage.service';
import { CreateUsageLogDto } from './dto/create-usage-log.dto';

@ApiTags('usage')
@Controller('usage')
export class UsageController {
  constructor(private readonly usageService: UsageService) {}

  @Post()
  @ApiOperation({ summary: 'Registrar un log de uso' })
  @ApiResponse({ status: 201, description: 'Log creado exitosamente' })
  @ApiResponse({ status: 404, description: 'Dispositivo no encontrado' })
  create(@Body() createUsageLogDto: CreateUsageLogDto) {
    return this.usageService.create(createUsageLogDto);
  }

  @Get()
  @ApiOperation({ summary: 'Obtener logs de uso' })
  @ApiQuery({ name: 'deviceId', required: false })
  @ApiQuery({ name: 'limit', required: false, type: Number })
  @ApiResponse({ status: 200, description: 'Lista de logs' })
  findAll(
    @Query('deviceId') deviceId?: string,
    @Query('limit') limit?: string,
  ) {
    const limitNum = limit ? parseInt(limit, 10) : 100;
    return this.usageService.findAll(deviceId, limitNum);
  }

  @Get('device/:deviceId')
  @ApiOperation({ summary: 'Obtener logs de un dispositivo específico' })
  @ApiResponse({ status: 200, description: 'Logs del dispositivo' })
  findByDevice(
    @Param('deviceId') deviceId: string,
    @Query('limit') limit?: string,
  ) {
    const limitNum = limit ? parseInt(limit, 10) : 50;
    return this.usageService.findByDevice(deviceId, limitNum);
  }
}
