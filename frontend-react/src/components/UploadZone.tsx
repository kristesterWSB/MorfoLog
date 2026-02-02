import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';

const API_URL = 'https://localhost:7219';

interface UploadZoneProps {
  onUploadSuccess: () => void;
}

export const UploadZone = ({ onUploadSuccess }: UploadZoneProps) => {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setUploading(true);
    setMessage(null);

    try {
      // Loop through files and upload each one
      const promises = acceptedFiles.map(file => {
        const formData = new FormData();
        formData.append('file', file);
        return axios.post(`${API_URL}/api/documents/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
      });

      await Promise.all(promises);
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
    </div>
  );
};
