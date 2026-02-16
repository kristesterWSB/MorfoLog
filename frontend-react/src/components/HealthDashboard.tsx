import { useEffect, useState, useCallback } from 'react';
import { LogOut } from 'lucide-react';
import axiosInstance from '../api/axios';
import { useAuth } from '../context/AuthContext';
import { UploadZone } from './UploadZone';
import { TrendsCharts, type MedicalDocument } from './TrendsCharts';

export const HealthDashboard = () => {
  const [docs, setDocs] = useState<MedicalDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const { email, logout, setPage } = useAuth();

  const fetchDocuments = useCallback(async () => {
    setLoading(true);
    axiosInstance.get(`/api/documents`)
      .then(res => {
        setDocs(res.data);
        setError("");
      })
      .catch(err => {
        console.error(err);
        setError("Błąd pobierania danych: " + err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans text-gray-900">
      <div className="max-w-7xl mx-auto">
        <header className="mb-10 pb-4 border-b border-gray-200 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">
              🏥 MorfoLog
            </h1>
            <p className="text-gray-500 mt-2">Dashboard labs</p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-600">👤 {email}</span>
            <button
              onClick={() => {
                logout();
                setPage('login');
              }}
              className="flex items-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Wyloguj
            </button>
          </div>
        </header>

        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6 rounded-md" role="alert">
            <p className="font-bold text-red-700">Błąd</p>
            <p className="text-red-600">{error}</p>
          </div>
        )}

        <div className="space-y-8">
            <section className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <h2 className="text-lg font-bold mb-4 text-gray-800">Wgraj wyniki (PDF)</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div className="md:col-span-2">
                         <UploadZone onUploadSuccess={fetchDocuments} />
                    </div>
                    
                    <div className="md:col-span-1 border-l border-gray-100 pl-8">
                        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">Ostatnie dokumenty</h3>
                        <div className="space-y-2">
                            {docs.slice(0, 5).map(doc => (
                                <div key={doc.id} className="flex justify-between items-center text-sm p-2 hover:bg-gray-50 rounded">
                                    <span className="truncate max-w-[180px]" title={doc.fileName}>{doc.fileName}</span>
                                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium 
                                        ${doc.status === 'Completed' ? 'bg-green-100 text-green-800' : 
                                          doc.status === 'Pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>
                                        {doc.status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </section>

            <section>
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-gray-800">Trendy Parametrów</h2>
                    <button 
                        onClick={fetchDocuments}
                        className="px-3 py-1 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                        Odśwież
                    </button>
                </div>
                
                {loading && docs.length === 0 ? (
                    <div className="flex justify-center items-center h-64 bg-white rounded-xl shadow-sm border border-gray-200">
                        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
                    </div>
                ) : (
                    <TrendsCharts documents={docs} />
                )}
            </section>
        </div>
      </div>
    </div>
  );
};
