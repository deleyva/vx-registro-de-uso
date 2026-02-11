import type { ReportResponse } from '@vx/types';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { ClipboardList, CheckCircle2, XCircle, Info } from 'lucide-react';
import { useMemo, useState } from 'react';

type VerificationItem = {
  estado?: string | null;
  problema?: string | null;
  obligatorio?: boolean | null;
};

const COMPONENT_LABELS: Record<string, string> = {
  pantalla: 'Pantalla',
  teclado: 'Teclado',
  raton: 'Ratón',
  bateria: 'Batería',
  otros: 'Otros',
};

interface ReportsTableProps {
  reports: ReportResponse[];
  showHeader?: boolean;
}

export function ReportsTable({ reports, showHeader = true }: ReportsTableProps) {
  const [details, setDetails] = useState<{
    report: ReportResponse;
    component: string;
    item: VerificationItem;
  } | null>(null);

  const components = useMemo(() => {
    const found = new Set<string>();
    for (const r of reports) {
      const ve = r.verificacionEquipos as unknown as Record<string, unknown>;
      for (const k of Object.keys(ve || {})) found.add(k);
    }
    const preferred = ['pantalla', 'teclado', 'raton', 'bateria', 'otros'];
    const rest = [...found].filter((k) => !preferred.includes(k)).sort();
    return [...preferred.filter((k) => found.has(k)), ...rest];
  }, [reports]);

  function getItem(r: ReportResponse, component: string): VerificationItem | null {
    const ve = r.verificacionEquipos as unknown as Record<string, any>;
    const item = ve?.[component];
    if (!item || typeof item !== 'object') return null;
    return item as VerificationItem;
  }

  function renderStatusIcon(r: ReportResponse, component: string) {
    const item = getItem(r, component);
    if (!item) return <span className="text-xs text-muted-foreground">—</span>;

    const ok = item.estado === 'correcto';
    const label = COMPONENT_LABELS[component] || component;
    const problema = item.problema ? String(item.problema) : null;
    const obligatorio = item.obligatorio === true ? 'Obligatorio' : item.obligatorio === false ? 'Opcional' : null;
    const tooltipParts = [label, obligatorio, item.estado].filter(Boolean);
    if (problema) tooltipParts.push(problema);
    const tooltip = tooltipParts.join(' · ');

    const Icon = ok ? CheckCircle2 : XCircle;
    const className = ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';

    return (
      <button
        type="button"
        className={`inline-flex items-center justify-center ${className}`}
        title={tooltip}
        aria-label={tooltip}
        onClick={() => setDetails({ report: r, component, item })}
      >
        <Icon className="w-5 h-5" />
      </button>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-border overflow-hidden">
      {showHeader && (
        <div className="p-6 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ClipboardList className="w-6 h-6 text-primary" />
            <h2 className="text-xl font-bold text-foreground">Reportes Recientes</h2>
            <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-medium">
              {reports.length}
            </span>
          </div>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Fecha</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">CID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Usuario</th>
              {components.map((c) => (
                <th
                  key={c}
                  className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider"
                >
                  {COMPONENT_LABELS[c] || c}
                </th>
              ))}
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Operativo</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Creado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {reports.length === 0 ? (
              <tr>
                <td colSpan={5 + components.length} className="px-6 py-12 text-center text-muted-foreground">
                  No hay reportes aún
                </td>
              </tr>
            ) : (
              reports.map((r) => (
                <tr key={r.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">
                    {new Date(r.timestamp).toLocaleString('es-ES')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">{r.migrasfreeCid}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-foreground">{r.usuarioGrafico}</td>
                  {components.map((c) => (
                    <td key={c} className="px-6 py-4 whitespace-nowrap">
                      {renderStatusIcon(r, c)}
                    </td>
                  ))}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        r.resumen?.equipo_operativo ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                      }`}
                    >
                      {r.resumen?.equipo_operativo ? 'Sí' : 'No'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-muted-foreground">
                    {formatDistanceToNow(new Date(r.createdAt), { addSuffix: true, locale: es })}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {details && (
        <div
          className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Detalles del componente"
          onClick={() => setDetails(null)}
        >
          <div
            className="w-full max-w-lg bg-white dark:bg-gray-900 rounded-xl shadow-xl border border-border"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-5 border-b border-border flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Info className="w-5 h-5 text-primary" />
                <div>
                  <div className="text-sm text-muted-foreground">{details.report.migrasfreeCid}</div>
                  <h3 className="text-lg font-bold text-foreground">
                    {COMPONENT_LABELS[details.component] || details.component}
                  </h3>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setDetails(null)}
                className="px-3 py-1 rounded-lg border border-border text-sm text-foreground hover:bg-muted/30"
              >
                Cerrar
              </button>
            </div>

            <div className="p-5 space-y-3">
              <div className="text-sm">
                <span className="text-muted-foreground">Estado:</span>{' '}
                <span className="font-medium text-foreground">{details.item.estado || 'N/A'}</span>
              </div>
              <div className="text-sm">
                <span className="text-muted-foreground">Obligatorio:</span>{' '}
                <span className="font-medium text-foreground">
                  {details.item.obligatorio === true ? 'Sí' : details.item.obligatorio === false ? 'No' : 'N/A'}
                </span>
              </div>
              <div className="text-sm">
                <span className="text-muted-foreground">Problema:</span>{' '}
                <span className="font-medium text-foreground">{details.item.problema || '—'}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
