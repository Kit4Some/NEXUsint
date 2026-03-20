import { useCallback, useMemo } from 'react';
import type { LiveFlight, MilitaryFlight } from '@/types/livefeed';

interface FlightDetailPopupProps {
  flight: LiveFlight | MilitaryFlight | null;
  onClose: () => void;
}

interface FlightTypeConfig {
  title: string;
  colorClass: string;
  borderClass: string;
}

const FLIGHT_TYPE_CONFIG: Record<string, FlightTypeConfig> = {
  military_flight: {
    title: 'MILITARY BOGEY INTERCEPT',
    colorClass: 'text-red-400',
    borderClass: 'border-red-500/60',
  },
  tracked_flight: {
    title: 'TRACKED AIRCRAFT ALERT',
    colorClass: 'text-orange-400',
    borderClass: 'border-orange-500/60',
  },
  commercial_flight: {
    title: 'COMMERCIAL FLIGHT',
    colorClass: 'text-cyan-400',
    borderClass: 'border-cyan-500/40',
  },
  private_jet: {
    title: 'PRIVATE JET',
    colorClass: 'text-purple-400',
    borderClass: 'border-purple-500/40',
  },
};

const DEFAULT_CONFIG: FlightTypeConfig = {
  title: 'AIRCRAFT TRANSPONDER',
  colorClass: 'text-zinc-400',
  borderClass: 'border-zinc-700',
};

const MILITARY_TYPE_COLORS: Record<string, string> = {
  fighter: 'bg-red-500/80 text-red-100',
  bomber: 'bg-red-700/80 text-red-100',
  tanker: 'bg-amber-600/80 text-amber-100',
  cargo: 'bg-green-600/80 text-green-100',
  recon: 'bg-indigo-500/80 text-indigo-100',
  heli: 'bg-yellow-600/80 text-yellow-100',
};

function isMilitaryFlight(flight: LiveFlight | MilitaryFlight): flight is MilitaryFlight {
  return 'military_type' in flight && 'force' in flight;
}

function getNacpColor(nacp: number): string {
  if (nacp >= 8) return 'text-green-400';
  if (nacp >= 6) return 'text-yellow-400';
  return 'text-red-400';
}

function getNacpLabel(nacp: number): string {
  if (nacp >= 8) return 'HIGH';
  if (nacp >= 6) return 'MEDIUM';
  return 'LOW';
}

function DataField({
  label,
  value,
  unit,
  className,
}: {
  label: string;
  value: string | number | undefined | null;
  unit?: string;
  className?: string;
}) {
  const displayValue = value === undefined || value === null || value === '' ? '---' : value;
  return (
    <div className={className}>
      <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block">
        {label}
      </span>
      <span className="text-xs font-mono text-zinc-200">
        {displayValue}
        {unit && displayValue !== '---' && (
          <span className="text-zinc-500 ml-0.5">{unit}</span>
        )}
      </span>
    </div>
  );
}

export function FlightDetailPopup({ flight, onClose }: FlightDetailPopupProps) {
  const handleClose = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onClose();
    },
    [onClose],
  );

  const config = useMemo(() => {
    if (!flight) return DEFAULT_CONFIG;
    return FLIGHT_TYPE_CONFIG[flight.type] ?? DEFAULT_CONFIG;
  }, [flight]);

  const alertBorderClass = useMemo(() => {
    if (!flight) return '';
    if (flight.alert_color) {
      const colorMap: Record<string, string> = {
        red: 'border-red-500',
        orange: 'border-orange-500',
        yellow: 'border-yellow-500',
        green: 'border-green-500',
        blue: 'border-blue-500',
        purple: 'border-purple-500',
      };
      return colorMap[flight.alert_color] ?? '';
    }
    return '';
  }, [flight]);

  if (!flight) return null;

  const borderClass = alertBorderClass || config.borderClass;
  const isMilitary = isMilitaryFlight(flight);
  const hasRoute = flight.origin_name || flight.dest_name;
  const militaryTypeColor =
    isMilitary && flight.military_type
      ? MILITARY_TYPE_COLORS[flight.military_type] ?? 'bg-zinc-600 text-zinc-200'
      : '';

  return (
    <div
      className={`
        bg-zinc-900/95 backdrop-blur-md border ${borderClass}
        rounded-lg shadow-2xl w-[340px] font-mono text-xs
        select-none pointer-events-auto
      `}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
          <h3 className={`text-[11px] font-bold tracking-widest uppercase ${config.colorClass}`}>
            {config.title}
          </h3>
        </div>
        <button
          onClick={handleClose}
          className="w-5 h-5 flex items-center justify-center rounded hover:bg-zinc-700
                     text-zinc-500 hover:text-zinc-300 transition-colors"
          aria-label="Close"
        >
          <svg viewBox="0 0 12 12" className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M2 2l8 8M10 2l-8 8" />
          </svg>
        </button>
      </div>

      {/* Body */}
      <div className="px-3 py-2.5 space-y-3">
        {/* Tracked flight alert badge */}
        {flight.alert_category && (
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`
                px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider
                ${flight.alert_color === 'red' ? 'bg-red-500/20 text-red-400 ring-1 ring-red-500/40' : ''}
                ${flight.alert_color === 'orange' ? 'bg-orange-500/20 text-orange-400 ring-1 ring-orange-500/40' : ''}
                ${flight.alert_color === 'yellow' ? 'bg-yellow-500/20 text-yellow-400 ring-1 ring-yellow-500/40' : ''}
                ${!flight.alert_color || !['red', 'orange', 'yellow'].includes(flight.alert_color) ? 'bg-zinc-700 text-zinc-300' : ''}
              `}
            >
              {flight.alert_category}
            </span>
            {flight.alert_operator && (
              <span className="text-[10px] text-zinc-400">{flight.alert_operator}</span>
            )}
          </div>
        )}

        {/* Military type badge */}
        {isMilitary && (
          <div className="flex items-center gap-2 mb-1">
            {flight.military_type && (
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${militaryTypeColor}`}
              >
                {flight.military_type}
              </span>
            )}
            {flight.force && (
              <span className="text-[10px] text-zinc-400">
                <span className="text-zinc-600 mr-1">FORCE:</span>
                {flight.force}
              </span>
            )}
          </div>
        )}

        {/* Primary data grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2">
          <DataField label="Callsign" value={flight.callsign} />
          <DataField label="Registration" value={flight.registration} />
          <DataField label="Model" value={flight.model} />
          <DataField label="ICAO24" value={flight.icao24} />
          <DataField label="Altitude" value={flight.alt?.toLocaleString()} unit="ft" />
          <DataField label="Speed" value={flight.speed_knots} unit="kn" />
          <DataField label="Heading" value={flight.heading} unit="°" />
          <DataField label="Squawk" value={flight.squawk} />
        </div>

        {/* Route */}
        {hasRoute && (
          <div className="pt-1 border-t border-zinc-800">
            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block mb-0.5">
              Route
            </span>
            <span className="text-xs text-zinc-200">
              {flight.origin_name || '???'}
              <span className="text-zinc-600 mx-1.5">&rarr;</span>
              {flight.dest_name || '???'}
            </span>
          </div>
        )}

        {/* Airline */}
        {flight.airline_code && (
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500 block mb-0.5">
              Airline
            </span>
            <span className="text-xs text-zinc-200">{flight.airline_code}</span>
          </div>
        )}

        {/* Footer indicators */}
        <div className="flex items-center justify-between pt-1.5 border-t border-zinc-800">
          {/* GPS accuracy */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-zinc-500 uppercase">GPS</span>
            <span className={`text-[10px] font-bold ${getNacpColor(flight.nac_p)}`}>
              NACp {flight.nac_p}
            </span>
            <span className={`text-[9px] ${getNacpColor(flight.nac_p)}`}>
              ({getNacpLabel(flight.nac_p)})
            </span>
          </div>

          {/* Holding pattern warning */}
          {flight.holding && (
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
              <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">
                Holding
              </span>
            </div>
          )}
        </div>

        {/* Coordinates */}
        <div className="flex items-center gap-3 text-[10px] text-zinc-600">
          <span>{flight.lat.toFixed(5)}° N</span>
          <span>{flight.lng.toFixed(5)}° E</span>
          <span className="ml-auto">{flight.country}</span>
        </div>
      </div>
    </div>
  );
}
