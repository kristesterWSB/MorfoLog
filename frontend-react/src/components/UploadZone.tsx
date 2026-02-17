import { useCallback, useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import axiosInstance from '../api/axios';

interface UploadZoneProps {
  onUploadSuccess: () => void;
}

export const UploadZone = ({ onUploadSuccess }: UploadZoneProps) => {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [uploadedExams, setUploadedExams] = useState<string[]>([]);

  useEffect(() => {
    if (uploadedExams.length > 0) {
      const timer = setTimeout(() => {
        setUploadedExams([]);
      }, 10000);
      return () => clearTimeout(timer);
    }
  }, [uploadedExams]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setUploading(true);
    setMessage(null);
    setUploadedExams([]);

    try {
      // Loop through files and upload each one
      const promises = acceptedFiles.map(file => {
        const formData = new FormData();
        formData.append('files', file);
        return axiosInstance.post(`/api/documents/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
      });

      const responses = await Promise.all(promises);
      
      const newExams: string[] = [];
      responses.forEach(res => {
          if (res.data && Array.isArray(res.data)) {
              res.data.forEach((doc: any) => {
                  if (doc.analysisJson) {
                      try {
                          const analysis = typeof doc.analysisJson === 'string' ? JSON.parse(doc.analysisJson) : doc.analysisJson;
                          if (analysis.examinations && Array.isArray(analysis.examinations)) {
                              analysis.examinations.forEach((exam: any) => {
                                  if (exam.examination_name) {
                                      newExams.push(exam.examination_name);
                                  }
                              });
                          }
                      } catch (e) {
                          console.error("Error parsing analysis JSON", e);
                      }
                  }
              });
          }
      });

      if (newExams.length > 0) {
          setUploadedExams(newExams);
      }

      setMessage(`Sukces! Wgrano ${acceptedFiles.length} plików.`);
      onUploadSuccess();
    } catch (error: any) {
      console.error(error);
      setMessage("Błąd podczas wgrywania: " + (error.message || "Nieznany błąd"));
    } finally {
      setUploading(false);
    }
  }, [onUploadSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop, 
    accept: { 'application/pdf': ['.pdf'] } 
  });

  return (
    <div 
      {...getRootProps()} 
      className={`
        p-8 border-2 border-dashed rounded-lg text-center cursor-pointer transition-colors
        ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:bg-gray-100'}
      `}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <p className="text-blue-600 font-semibold animate-pulse">Wgrywanie plików...</p>
      ) : isDragActive ? (
        <p className="text-blue-500 font-medium">Upuść pliki PDF tutaj...</p>
      ) : (
        <div className="space-y-2">
          <p className="text-gray-600 text-lg">Przeciągnij i upuść pliki PDF tutaj</p>
          <p className="text-gray-400 text-sm">lub kliknij, aby wybrać z dysku</p>
        </div>
      )}
      
      {message && (
        <p className={`mt-4 font-medium ${message.startsWith("Błąd") ? "text-red-500" : "text-green-600"}`}>
          {message}
        </p>
      )}

      {uploadedExams.length > 0 && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded text-green-800 text-sm animate-in fade-in slide-in-from-top-2 duration-300">
            <p className="font-bold mb-1">Dodano badania:</p>
            <ul className="list-disc list-inside">
                {uploadedExams.map((exam, i) => (
                    <li key={i}>{exam}</li>
                ))}
            </ul>
        </div>
      )}
    </div>
  );
};
