import { IsString, IsOptional, IsNumber, IsBoolean, Min } from 'class-validator';
import { ApiPropertyOptional } from '@nestjs/swagger';

export class UpdateDeviceDto {
  @ApiPropertyOptional({ example: '192.168.1.100' })
  @IsOptional()
  @IsString()
  ipAddress?: string;

  @ApiPropertyOptional({ example: '00:1B:44:11:3A:B7' })
  @IsOptional()
  @IsString()
  macAddress?: string;

  @ApiPropertyOptional({ example: 'macOS 14.1' })
  @IsOptional()
  @IsString()
  osInfo?: string;

  @ApiPropertyOptional({ example: '14.1' })
  @IsOptional()
  @IsString()
  osVersion?: string;

  @ApiPropertyOptional({ example: 'Apple M2 Pro' })
  @IsOptional()
  @IsString()
  cpuInfo?: string;

  @ApiPropertyOptional({ example: 32 })
  @IsOptional()
  @IsNumber()
  @Min(0)
  ramTotal?: number;

  @ApiPropertyOptional({ example: 1024 })
  @IsOptional()
  @IsNumber()
  @Min(0)
  diskTotal?: number;

  @ApiPropertyOptional({ example: true })
  @IsOptional()
  @IsBoolean()
  isActive?: boolean;
}
