import { IsString, IsOptional, IsNumber, Min } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class RegisterDeviceDto {
  @ApiProperty({ example: 'laptop-001', description: 'Nombre del host' })
  @IsString()
  hostname: string;

  @ApiPropertyOptional({ example: '192.168.1.100', description: 'Dirección IP' })
  @IsOptional()
  @IsString()
  ipAddress?: string;

  @ApiPropertyOptional({ example: '00:1B:44:11:3A:B7', description: 'Dirección MAC' })
  @IsOptional()
  @IsString()
  macAddress?: string;

  @ApiPropertyOptional({ example: 'macOS 14.0', description: 'Sistema operativo' })
  @IsOptional()
  @IsString()
  osInfo?: string;

  @ApiPropertyOptional({ example: '14.0', description: 'Versión del SO' })
  @IsOptional()
  @IsString()
  osVersion?: string;

  @ApiPropertyOptional({ example: 'Apple M2 Pro', description: 'Información del CPU' })
  @IsOptional()
  @IsString()
  cpuInfo?: string;

  @ApiPropertyOptional({ example: 16, description: 'RAM total en GB' })
  @IsOptional()
  @IsNumber()
  @Min(0)
  ramTotal?: number;

  @ApiPropertyOptional({ example: 512, description: 'Disco total en GB' })
  @IsOptional()
  @IsNumber()
  @Min(0)
  diskTotal?: number;
}
