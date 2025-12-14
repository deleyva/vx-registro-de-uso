import { IsString, IsOptional, IsNumber, IsBoolean, Min, Max } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class CreateUsageLogDto {
  @ApiProperty({ example: 'clxxxx', description: 'ID del dispositivo' })
  @IsString()
  deviceId: string;

  @ApiPropertyOptional({ example: 45.5, description: 'Uso de CPU en porcentaje' })
  @IsOptional()
  @IsNumber()
  @Min(0)
  @Max(100)
  cpuUsage?: number;

  @ApiPropertyOptional({ example: 8.5, description: 'RAM usada en GB' })
  @IsOptional()
  @IsNumber()
  @Min(0)
  ramUsage?: number;

  @ApiPropertyOptional({ example: 250, description: 'Disco usado en GB' })
  @IsOptional()
  @IsNumber()
  @Min(0)
  diskUsage?: number;

  @ApiPropertyOptional({ example: 86400, description: 'Tiempo encendido en segundos' })
  @IsOptional()
  @IsNumber()
  @Min(0)
  uptime?: number;

  @ApiPropertyOptional({ example: 150, description: 'Número de procesos activos' })
  @IsOptional()
  @IsNumber()
  @Min(0)
  processCount?: number;

  @ApiPropertyOptional({ example: true, description: 'Usuario activo en el sistema' })
  @IsOptional()
  @IsBoolean()
  userActive?: boolean;
}
