import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsISO8601, IsObject, IsOptional, IsString } from 'class-validator';

export class CreateReportDto {
  @ApiProperty({ example: '2025-12-14T07:59:26.463Z' })
  @IsISO8601()
  timestamp: string;

  @ApiProperty({ example: '12345' })
  @IsString()
  migrasfree_cid: string;

  @ApiProperty({ example: 'MOCK_USER_DELEYVA' })
  @IsString()
  usuario_grafico: string;

  @ApiPropertyOptional({ example: 'VITALINUX' })
  @IsOptional()
  @IsString()
  empresa?: string;

  @ApiPropertyOptional({ example: 'equipos_escritorio' })
  @IsOptional()
  @IsString()
  tipo_verificacion?: string;

  @ApiProperty({
    example: {
      pantalla: { estado: 'correcto', problema: null, obligatorio: true },
    },
  })
  @IsObject()
  verificacion_equipos: Record<string, unknown>;

  @ApiProperty({
    example: {
      total_componentes: 5,
      equipo_operativo: false,
    },
  })
  @IsObject()
  resumen: Record<string, unknown>;
}
