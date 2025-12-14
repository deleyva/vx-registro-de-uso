'use client';

import { useEffect, useState } from 'react';
import type { ReportResponse } from '@vx/types';
import { ReportsTable } from '@/components/ReportsTable';
import { Activity, ClipboardList, Filter, Server } from 'lucide-react';

export default function HomePage() {
  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [onlyErrors, setOnlyErrors] = useState(false);
  const [component, setComponent] = useState('');

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Actualizar cada 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchReports();
  }, [from, to, onlyErrors, component]);

  async function fetchData() {
    try {
      await fetchReports();
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  }

  async function fetchReports() {
    const params = new URLSearchParams();
    params.set('limit', '200');
    if (from) params.set('from', new Date(from).toISOString());
    if (to) params.set('to', new Date(to).toISOString());
    if (onlyErrors) params.set('onlyErrors', 'true');
    if (component) params.set('component', component);

    const res = await fetch(`${API_URL}/v1/report?${params.toString()}`);
    if (res.ok) {
      const data = await res.json();
      setReports(data);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-spin mx-auto text-primary" />
          <p className="mt-4 text-muted-foreground">Cargando datos...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border-b border-border sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Server className="w-8 h-8 text-primary" />
              <div>
                <h1 className="text-2xl font-bold text-foreground">VX Reportes</h1>
                <p className="text-sm text-muted-foreground">Verificación de equipos (app de escritorio → API)</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm text-muted-foreground">En vivo</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-border overflow-hidden">
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <ClipboardList className="w-6 h-6 text-primary" />
                <h2 className="text-xl font-bold text-foreground">Reportes</h2>
                <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-medium">
                  {reports.length}
                </span>
              </div>

              <div className="flex items-center gap-3 flex-wrap">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Filter className="w-4 h-4" />
                  Filtros
                </div>

                <label className="text-sm text-muted-foreground">
                  Desde
                  <input
                    type="date"
                    value={from}
                    onChange={(e) => setFrom(e.target.value)}
                    className="ml-2 px-3 py-2 rounded-lg border border-border bg-background text-foreground"
                  />
                </label>

                <label className="text-sm text-muted-foreground">
                  Hasta
                  <input
                    type="date"
                    value={to}
                    onChange={(e) => setTo(e.target.value)}
                    className="ml-2 px-3 py-2 rounded-lg border border-border bg-background text-foreground"
                  />
                </label>

                <label className="text-sm text-muted-foreground flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={onlyErrors}
                    onChange={(e) => setOnlyErrors(e.target.checked)}
                  />
                  Solo con errores
                </label>

                <select
                  value={component}
                  onChange={(e) => setComponent(e.target.value)}
                  aria-label="Filtrar por componente"
                  className="px-3 py-2 rounded-lg border border-border bg-background text-foreground"
                >
                  <option value="">Todos los componentes</option>
                  <option value="pantalla">Pantalla</option>
                  <option value="teclado">Teclado</option>
                  <option value="raton">Ratón</option>
                  <option value="bateria">Batería</option>
                  <option value="otros">Otros</option>
                </select>
              </div>
            </div>
          </div>

          <ReportsTable reports={reports} showHeader={false} />
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-16 py-6 border-t border-border bg-white/50 dark:bg-gray-800/50">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>VX Control Center - Stack T3N-P (TypeScript + Turborepo + NestJS + Next.js + Prisma)</p>
        </div>
      </footer>
    </div>
  );
}
