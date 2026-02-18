import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowLeft, Save, AlertCircle, FileText, Trash2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { profileSchema, type ProfileSchema } from '../schemas/profile';
import axiosInstance from '../api/axios';
import { type MedicalDocument } from '../components/TrendsCharts';

export const ProfilePage = () => {
  const { setPage } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [documents, setDocuments] = useState<MedicalDocument[]>([]);
  const [docSuccess, setDocSuccess] = useState('');

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<ProfileSchema>({
    resolver: zodResolver(profileSchema),
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [profileRes, docsRes] = await Promise.all([
            axiosInstance.get('/api/profile'),
            axiosInstance.get('/api/documents')
        ]);
        
        reset(profileRes.data);

        const sortedDocs = (docsRes.data as MedicalDocument[]).sort((a, b) => {
            const dateA = a.uploadedAt ? new Date(a.uploadedAt).getTime() : 0;
            const dateB = b.uploadedAt ? new Date(b.uploadedAt).getTime() : 0;
            return dateB - dateA;
        });
        setDocuments(sortedDocs);

      } catch (err) {
        console.error('Failed to fetch data:', err);
        setError('Nie udało się pobrać danych.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [reset]);

  const handleDeleteDocument = async (id: string, fileName: string) => {
      if (!confirm(`Czy na pewno chcesz usunąć dokument "${fileName}"?`)) return;
      
      try {
          await axiosInstance.delete(`/api/documents/${id}`);
          setDocuments(prev => prev.filter(d => d.id !== id));
          setDocSuccess(`Dokument "${fileName}" został usunięty.`);
          setTimeout(() => setDocSuccess(''), 5000);
      } catch (err) {
          console.error("Failed to delete document", err);
          setError("Nie udało się usunąć dokumentu.");
          setTimeout(() => setError(''), 5000);
      }
  };

  const onSubmit = async (data: ProfileSchema) => {
    setError('');
    setSuccess('');
    setSaving(true);

    try {
      await axiosInstance.put('/api/profile', data);
      setSuccess('Zapisano zmiany.');
      reset(data); // Reset form state with new data
    } catch (err) {
      console.error('Failed to update profile:', err);
      setError('Błąd zapisu danych.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6 flex items-center gap-4">
          <button
            onClick={() => setPage('dashboard')}
            className="p-2 hover:bg-gray-200 rounded-full transition-colors"
          >
            <ArrowLeft className="w-6 h-6 text-gray-600" />
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Edycja Profilu</h1>
        </div>

        <div className="bg-white rounded-lg shadow-sm p-8">
          {error && (
            <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Imię
                </label>
                <input
                  {...register('firstName')}
                  type="text"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
                />
                {errors.firstName && (
                  <p className="text-xs text-red-500 mt-1">{errors.firstName.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nazwisko
                </label>
                <input
                  {...register('lastName')}
                  type="text"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
                />
                {errors.lastName && (
                  <p className="text-xs text-red-500 mt-1">{errors.lastName.message}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Adres
              </label>
              <input
                {...register('address')}
                type="text"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
              />
              {errors.address && (
                <p className="text-xs text-red-500 mt-1">{errors.address.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data Urodzenia
              </label>
              <input
                {...register('dateOfBirth')}
                type="date"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
              />
              {errors.dateOfBirth && (
                <p className="text-xs text-red-500 mt-1">{errors.dateOfBirth.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Email
              </label>
              <input
                {...register('email')}
                type="email"
                disabled
                className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500 cursor-not-allowed"
              />
              <p className="text-xs text-gray-500 mt-1">Adres email nie może być zmieniony.</p>
            </div>

            <div className="pt-4 flex justify-end">
              <button
                type="submit"
                disabled={saving || !isDirty}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Zapisywanie...' : 'Zapisz zmiany'}
              </button>
            </div>
          </form>
        </div>

        <div className="mt-8 bg-white rounded-lg shadow-sm p-8">
            <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                <FileText className="w-5 h-5 text-gray-500" />
                Twoje Dokumenty
            </h2>

            {docSuccess && (
                <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg mb-6 flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-300">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    {docSuccess}
                </div>
            )}
            
            {documents.length === 0 ? (
                <p className="text-gray-500 text-center py-4">Brak wgranych dokumentów.</p>
            ) : (
                <div className="space-y-3">
                    {documents.map(doc => (
                        <div key={doc.id} className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg border border-gray-100 transition-colors group">
                            <div className="flex items-center gap-3 overflow-hidden">
                                <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
                                    <FileText className="w-4 h-4" />
                                </div>
                                <div className="min-w-0">
                                    <p className="font-medium text-gray-900 truncate" title={doc.fileName}>{doc.fileName}</p>
                                    <p className="text-xs text-gray-500">
                                        Dodano: {doc.uploadedAt ? new Date(doc.uploadedAt).toLocaleString() : 'Brak daty'}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <span className={`px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap
                                    ${doc.status === 'Completed' ? 'bg-green-100 text-green-800' : 
                                    doc.status === 'Pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>
                                    {doc.status}
                                </span>
                                <button 
                                    onClick={() => handleDeleteDocument(doc.id, doc.fileName)}
                                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors opacity-0 group-hover:opacity-100"
                                    title="Usuń dokument"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
      </div>
    </div>
  );
};
