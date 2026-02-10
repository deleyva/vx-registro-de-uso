import { Body, Controller, Get, NotFoundException, Param, Post, Query } from '@nestjs/common';
import { ApiOperation, ApiResponse, ApiTags } from '@nestjs/swagger';
import { ReportsService } from './reports.service';
import { CreateReportDto } from './dto/create-report.dto';

@ApiTags('reports')
@Controller('v1/report')
export class ReportsController {
  constructor(private readonly reportsService: ReportsService) { }

  @Post()
  @ApiOperation({ summary: 'Registrar un reporte de verificación' })
  @ApiResponse({ status: 201, description: 'Reporte registrado' })
  create(@Body() dto: CreateReportDto): Promise<any> {
    return this.reportsService.create(dto);
  }

  @Get()
  @ApiOperation({ summary: 'Listar reportes de verificación' })
  @ApiResponse({ status: 200, description: 'Lista de reportes' })
  findAll(
    @Query('limit') limit?: string,
    @Query('from') from?: string,
    @Query('to') to?: string,
    @Query('onlyErrors') onlyErrors?: string,
    @Query('component') component?: string,
  ): Promise<any> {
    const limitNum = limit ? parseInt(limit, 10) : 50;

    const fromDate = from ? new Date(from) : undefined;
    const toDate = to ? new Date(to) : undefined;
    const onlyErrorsBool = onlyErrors === 'true' ? true : onlyErrors === 'false' ? false : undefined;

    return this.reportsService.findAll(limitNum, {
      from: fromDate && !Number.isNaN(fromDate.getTime()) ? fromDate : undefined,
      to: toDate && !Number.isNaN(toDate.getTime()) ? toDate : undefined,
      onlyErrors: onlyErrorsBool,
      component,
    });
  }

  @Get(':id')
  @ApiOperation({ summary: 'Obtener un reporte por ID' })
  @ApiResponse({ status: 200, description: 'Reporte encontrado' })
  @ApiResponse({ status: 404, description: 'Reporte no encontrado' })
  async findOne(@Param('id') id: string): Promise<any> {
    const report = await this.reportsService.findOne(id);
    if (!report) throw new NotFoundException(`Report ${id} not found`);
    return report;
  }
}
