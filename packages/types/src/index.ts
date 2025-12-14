export interface DeviceResponse {
  id: string;
  hostname: string;
  ipAddress?: string | null;
  macAddress?: string | null;
  osInfo?: string | null;
  osVersion?: string | null;
  cpuInfo?: string | null;
  ramTotal?: number | null;
  diskTotal?: number | null;
  isActive: boolean;
  lastSeen: string | Date;
  createdAt?: string | Date;
  updatedAt?: string | Date;
}

export interface DeviceStats {
  totalDevices: number;
  activeDevices: number;
  averageCpuUsage: number;
  averageRamUsage: number;
  averageDiskUsage: number;
}

export interface ReportResumen {
  equipo_operativo?: boolean;
  requiere_atencion?: boolean;
  [key: string]: unknown;
}

export interface ReportResponse {
  id: string;
  timestamp: string | Date;
  migrasfreeCid: string;
  usuarioGrafico: string;
  verificacionEquipos: Record<string, unknown>;
  resumen: ReportResumen;
  createdAt: string | Date;
}
