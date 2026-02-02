import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceArea
} from 'recharts';

export interface LabResult {
  name: string;
  value: number;
  unit: string;
  range_min?: number;
  range_max?: number;
  flag?: "H" | "L" | "LH" | null;
}

export interface AnalysisData {
  meta: { date_examination: string };
  examinations: {
    examination_name: string;
    results: LabResult[];
  }[];
}

export interface MedicalDocument {
  id: string;
  fileName: string;
  status: string;
  analysisJson: any; 
  uploadDate?: string; // Sometimes called uploadedAt in App.tsx
  uploadedAt?: string;
}

interface TrendsChartsProps {
  documents: MedicalDocument[];
}

interface ChartDataPoint {
  date: string;
  value: number;
  unit: string;
  min?: number;
  max?: number;
  flag?: string | null;
}

// --- KONFIGURACJA NORMALIZACJI (Port z Python) ---
const UNIT_NORMALIZATION_MAP: Record<string, string> = {
  "min/ul": "mln/ul",
  "f": "fl",
  "fi": "fl",
  "fI": "fl",
  "UI": "U/l",
  "UJ": "U/l",
  "pe": "pg",
  "pg*": "pg",
};

const PARAMETER_NAME_NORMALIZATION_MAP: Record<string, string> = {
  "NRBC$": "NRBC",
  "NRBCH": "NRBC",
  "NRBC #": "NRBC",
  "NRBC%": "NRBC",
  "NRBC %": "NRBC"
};

export const TrendsCharts = ({ documents }: TrendsChartsProps) => {
    const chartsData = useMemo(() => {
        const dataMap = new Map<string, ChartDataPoint[]>();

        documents.forEach(doc => {
            if (doc.status !== 'Completed' || !doc.analysisJson) return;

            let analysis: AnalysisData | null = null;
            try {
                analysis = typeof doc.analysisJson === 'string' ? JSON.parse(doc.analysisJson) : doc.analysisJson;
            } catch (e) {
                console.error("Error parsing JSON for doc", doc.id, e);
                return;
            }

            if (!analysis?.meta?.date_examination) return;
            const date = analysis.meta.date_examination;

            analysis.examinations?.forEach(exam => {
                // 1. Czyszczenie nazwy sekcji (usuwanie ICD-9)
                const sectionName = (exam.examination_name || 'Inne').replace(/\s*\(ICD-9:.*\)/, '').trim();

                exam.results?.forEach(res => {
                    // 2. Czyszczenie nazwy parametru (usuwanie jednostek w nawiasach)
                    let paramName = res.name.replace(/\s*[\[\(].*?[\]\)]$/, '').trim();
                    
                    // 3. Normalizacja nazwy parametru
                    paramName = PARAMETER_NAME_NORMALIZATION_MAP[paramName] || paramName;

                    // 4. Czyszczenie i normalizacja jednostki
                    let unit = res.unit;
                    if (unit) {
                        const cleanedUnit = unit.replace(/[\*$\s]/g, ''); // Usuwa *, $ i spacje
                        unit = UNIT_NORMALIZATION_MAP[cleanedUnit] || cleanedUnit;
                    }

                    // 5. Tworzenie unikalnego klucza: "Sekcja - Parametr [Jednostka]"
                    const baseKey = `${sectionName} - ${paramName}`;
                    const uniqueKey = unit ? `${baseKey} [${unit}]` : baseKey;

                    if (!dataMap.has(uniqueKey)) {
                        dataMap.set(uniqueKey, []);
                    }
                    dataMap.get(uniqueKey)!.push({
                        date,
                        value: res.value,
                        unit: unit,
                        min: res.range_min,
                        max: res.range_max,
                        flag: res.flag?.trim()
                    });
                });
            });
        });

        // Sort by date for each parameter
        dataMap.forEach((points) => {
            points.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
        });

        return dataMap;
    }, [documents]);

    const renderCustomDot = (props: any) => {
        const { cx, cy, payload } = props;
        const flag = payload.flag;
        
        // Kolory zgodne ze skryptem Python:
        // H -> Czerwony
        // L -> Niebieski
        // Norma -> Teal (Morski/Zielony)
        let fill = "#0d9488"; // teal-600 (W normie - domyślny)
        let r = 5;

        if (flag === "H") {
            fill = "#dc2626"; // red-600
            r = 6;
        }
        if (flag === "L") {
            fill = "#2563eb"; // blue-600
            r = 6;
        }

        return <circle cx={cx} cy={cy} r={r} fill={fill} stroke="white" strokeWidth={2} />;
    };

    if (chartsData.size === 0) {
        return <div className="text-center text-gray-500 py-10">Brak danych do wyświetlenia wykresów.</div>;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
            {Array.from(chartsData.entries()).map(([name, data]) => {
                const lastPoint = data[data.length - 1];
                
                // Find first available range (prefer latest)
                const validRangePoint = [...data].reverse().find(p => p.min !== undefined && p.max !== undefined && p.min !== null && p.max !== null);
                const min = validRangePoint?.min;
                const max = validRangePoint?.max;
                
                return (
                    <div key={name} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 min-w-0">
                        <div className="flex justify-between items-baseline mb-4">
                            <h3 className="text-lg font-bold text-gray-800">{name}</h3>
                            <span className="text-sm font-medium text-gray-500">{lastPoint.unit}</span>
                        </div>
                        
                        <div style={{ width: '100%', height: 300, minWidth: 0 }}>
                            <ResponsiveContainer width="99%" height="100%">
                                <LineChart data={data} margin={{ top: 10, right: 30, bottom: 5, left: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f3f4f6" />
                                    <XAxis 
                                        dataKey="date" 
                                        tick={{ fontSize: 11, fill: '#6b7280' }} 
                                        tickLine={false}
                                        axisLine={false}
                                        padding={{ left: 10, right: 10 }}
                                    />
                                    <YAxis 
                                        domain={['auto', 'auto']} 
                                        tick={{ fontSize: 11, fill: '#6b7280' }} 
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <Tooltip 
                                        contentStyle={{ 
                                            backgroundColor: '#fff', 
                                            borderRadius: '8px', 
                                            border: 'none', 
                                            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' 
                                        }}
                                        itemStyle={{ color: '#1f2937', fontWeight: 600 }}
                                        labelStyle={{ color: '#9ca3af', marginBottom: '0.25rem' }}
                                    />
                                    {min !== undefined && max !== undefined && (
                                         <ReferenceArea y1={min} y2={max} fill="#22c55e" fillOpacity={0.15} ifOverflow="extendDomain" />
                                    )}
                                    <Line 
                                        type="monotone" 
                                        dataKey="value" 
                                        stroke="#6b7280" // gray-500
                                        strokeWidth={2}
                                        dot={renderCustomDot}
                                        activeDot={{ r: 7, strokeWidth: 0 }}
                                        isAnimationActive={false}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                );
            })}
        </div>
    );
};
