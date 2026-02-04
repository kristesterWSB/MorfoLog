import { useMemo, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
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
  range?: [number, number];
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

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        const data = payload[0].payload;
        return (
            <div className="bg-white p-3 border border-gray-200 shadow-lg rounded-lg outline-none">
                <p className="text-gray-500 text-sm mb-2">{label}</p>
                <p className="text-gray-800 font-bold text-sm">
                    Wynik: <span className="text-black">{data.value}</span> <span className="text-gray-600 font-normal">{data.unit}</span>
                </p>
                {data.min !== undefined && data.max !== undefined && (
                    <p className="text-gray-500 text-xs mt-1">
                        Zakres: {data.min} - {data.max} {data.unit}
                    </p>
                )}
            </div>
        );
    }
    return null;
};

const ChartGroup = ({ sectionName, sectionCharts }: { sectionName: string, sectionCharts: Map<string, ChartDataPoint[]> }) => {
    const [isExpanded, setIsExpanded] = useState(true);

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
             <button 
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 transition-colors border-b border-gray-200"
            >
                <h2 className="text-lg font-bold text-gray-800">{sectionName}</h2>
                {isExpanded ? <ChevronDown className="w-5 h-5 text-gray-500" /> : <ChevronRight className="w-5 h-5 text-gray-500" />}
            </button>
            
            {isExpanded && (
                <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {Array.from(sectionCharts.entries()).map(([name, data]) => {
                        const lastPoint = data[data.length - 1];
                        const displayName = name.replace(/\s*\[.*?\]$/, '');
                        
                        return (
                            <div key={name} className="bg-white p-4 rounded-lg border border-gray-100 min-w-0">
                                <div className="flex flex-col items-center mb-4">
                                    <h3 className="text-base font-semibold text-gray-700 text-center">{displayName}</h3>
                                    <span className="text-xs font-medium text-gray-500">{lastPoint.unit}</span>
                                </div>
                                
                                <div style={{ width: '100%', height: 250, minWidth: 0 }}>
                                    <ResponsiveContainer width="99%" height="100%">
                                        <ComposedChart data={data} margin={{ top: 10, right: 10, bottom: 5, left: 0 }}>
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
                                            <Tooltip content={<CustomTooltip />} />
                                            <Bar 
                                                dataKey="range" 
                                                fill="#22c55e" 
                                                fillOpacity={0.15} 
                                                barSize={30}
                                                isAnimationActive={false}
                                            />
                                            <Line 
                                                type="monotone" 
                                                dataKey="value" 
                                                stroke="#6b7280" 
                                                strokeWidth={2}
                                                dot={renderCustomDot}
                                                activeDot={{ r: 7, strokeWidth: 0 }}
                                                isAnimationActive={false}
                                            />
                                        </ComposedChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export const TrendsCharts = ({ documents }: TrendsChartsProps) => {
    const chartsData = useMemo(() => {
        const dataMap = new Map<string, Map<string, ChartDataPoint[]>>();

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

                if (!dataMap.has(sectionName)) {
                    dataMap.set(sectionName, new Map());
                }
                const sectionCharts = dataMap.get(sectionName)!;

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

                    // 5. Tworzenie klucza wykresu: "Parametr [Jednostka]"
                    const uniqueKey = unit ? `${paramName} [${unit}]` : paramName;

                    if (!sectionCharts.has(uniqueKey)) {
                        sectionCharts.set(uniqueKey, []);
                    }

                    const range: [number, number] | undefined = 
                        (typeof res.range_min === 'number' && typeof res.range_max === 'number') 
                        ? [res.range_min, res.range_max] 
                        : undefined;

                    sectionCharts.get(uniqueKey)!.push({
                        date,
                        value: res.value,
                        unit: unit,
                        min: res.range_min,
                        max: res.range_max,
                        range,
                        flag: res.flag?.trim()
                    });
                });
            });
        });

        // Sort by date for each parameter
        dataMap.forEach((sectionCharts) => {
            sectionCharts.forEach((points) => {
                points.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
            });
        });

        return dataMap;
    }, [documents]);

    if (chartsData.size === 0) {
        return <div className="text-center text-gray-500 py-10">Brak danych do wyświetlenia wykresów.</div>;
    }

    return (
        <div className="mt-8 space-y-6">
            {Array.from(chartsData.entries()).map(([sectionName, sectionCharts]) => (
                <ChartGroup key={sectionName} sectionName={sectionName} sectionCharts={sectionCharts} />
            ))}
        </div>
    );
};
