import React, { useState, useEffect } from 'react';
import { Upload, Trash2, Image as ImageIcon, CheckCircle, RefreshCw, Eye } from 'lucide-react';

export default function LocalGallery() {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');

  const fetchGallery = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/galeria-local');
      if (res.ok) {
        const data = await res.json();
        setImages(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGallery();
  }, []);

  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    setUploadMessage('Subiendo y optimizando imágenes...');
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const res = await fetch('/api/subir-lote-imagenes', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      setUploadMessage(data.mensaje || 'Imágenes subidas con éxito');
      fetchGallery();
    } catch (err) {
      setUploadMessage('Error al subir las imágenes');
    } finally {
      setUploading(false);
      setTimeout(() => setUploadMessage(''), 4000);
      e.target.value = '';
    }
  };

  const handleDelete = async (nombre) => {
    if (!window.confirm(`¿Eliminar ${nombre}?`)) return;
    try {
      // Nota: Asumiendo que existe una ruta en el backend, si no, se implementará luego
      const res = await fetch(`/api/eliminar-imagen-local?nombre=${encodeURIComponent(nombre)}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchGallery();
      } else {
        alert("El backend no soportó la eliminación todavía.");
      }
    } catch (e) {
      console.error('Error deleting image:', e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-50">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Galería de Imágenes Locales</h1>
          <p className="text-slate-500 text-sm">Gestiona el lote de imágenes para Mercado Libre.</p>
        </div>
        
        <div className="relative">
          <input 
            type="file" 
            multiple 
            accept="image/*"
            onChange={handleFileUpload}
            disabled={uploading}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed z-10"
          />
          <button 
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 shadow-sm transition-colors relative"
          >
            {uploading ? <RefreshCw className="animate-spin" size={18} /> : <Upload size={18} />}
            {uploading ? 'Subiendo...' : 'Subir Lote de Imágenes'}
          </button>
        </div>
      </div>

      {uploadMessage && (
        <div className="mb-6 p-4 bg-green-50 text-green-800 rounded-lg border border-green-200 flex items-center gap-3">
          <CheckCircle size={20} className="text-green-600" />
          <span className="font-medium">{uploadMessage}</span>
        </div>
      )}

      <div className="bg-white flex-1 rounded-xl shadow-sm border border-slate-200 p-6 overflow-y-auto">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <RefreshCw className="animate-spin mb-4" size={32} />
            <p>Cargando galería...</p>
          </div>
        ) : images.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400">
            <ImageIcon size={64} className="mb-4 opacity-50 text-slate-300" />
            <h3 className="text-xl font-medium text-slate-600 mb-2">No hay imágenes en el lote</h3>
            <p className="text-sm">Sube tus fotos para emparejarlas con los artículos del Excel.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
            {images.map((img, i) => (
              <div key={i} className="group flex flex-col bg-slate-50 rounded-lg overflow-hidden border border-slate-200 hover:border-blue-300 hover:shadow-md transition-all">
                <div className="aspect-square bg-slate-200 relative overflow-hidden flex items-center justify-center">
                  <img 
                    src={img.b64 || `/api/imagen-local/${img.nombre}`} 
                    alt={img.nombre}
                    className="w-full h-full object-contain bg-white"
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                    <button 
                      onClick={() => window.open(img.b64 || `/api/imagen-local/${img.nombre}`, '_blank')}
                      className="bg-white text-slate-700 p-2 rounded-full hover:bg-blue-50 hover:text-blue-600 hover:scale-110 transition-transform shadow-lg"
                      title="Ver grande"
                    >
                      <Eye size={20} />
                    </button>
                    <button 
                      onClick={() => handleDelete(img.nombre)}
                      className="bg-white text-red-600 p-2 rounded-full hover:bg-red-50 hover:scale-110 transition-transform shadow-lg"
                      title="Eliminar imagen"
                    >
                      <Trash2 size={20} />
                    </button>
                  </div>
                </div>
                <div className="p-3 text-center border-t border-slate-200">
                  <span className="text-xs font-medium text-slate-700 truncate block" title={img.nombre}>
                    {img.nombre}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

