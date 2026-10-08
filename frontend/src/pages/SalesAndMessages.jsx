import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, ShoppingBag, Send, User, MapPin, Truck, RefreshCw, AlertCircle, Clock } from 'lucide-react';

export default function SalesAndMessages() {
  const [cuentas, setCuentas] = useState([]);
  const [cuentaActiva, setCuentaActiva] = useState('');
  const [ordenes, setOrdenes] = useState([]);
  const [totalOrdenes, setTotalOrdenes] = useState(0);
  const [loadingOrdenes, setLoadingOrdenes] = useState(false);
  const [offset, setOffset] = useState(0);
  const [userId, setUserId] = useState('');
  
  const [ordenSeleccionada, setOrdenSeleccionada] = useState(null);
  const [detalleOrden, setDetalleOrden] = useState(null);
  const [mensajes, setMensajes] = useState([]);
  const [loadingChat, setLoadingChat] = useState(false);
  const [chatError, setChatError] = useState(null);
  
  const [mensajeTexto, setMensajeTexto] = useState('');
  const [enviandoMensaje, setEnviandoMensaje] = useState(false);

  const mensajesEndRef = useRef(null);

  // Cargar cuentas
  useEffect(() => {
    fetch('/cuentas')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setCuentas(data);
          if (data.length > 0) setCuentaActiva(data[0].archivo);
        } else {
          if (data?.detail === "Credenciales invalidas" || data?.detail === "Not authenticated") {
            alert("Por favor, inicia sesión en la aplicación. La página se recargará.");
            window.location.reload();
          }
        }
      })
      .catch(err => console.error("Error cargando cuentas:", err));
  }, []);

  async function cargarOrdenes() {
    setLoadingOrdenes(true);
    try {
      const res = await fetch(`/api/ventas/ordenes?cuenta=${encodeURIComponent(cuentaActiva)}&offset=${offset}`);
      const data = await res.json();
      if (data?.error) {
        alert(data.error);
      } else if (data?.detail) {
        console.error("FastAPI Error:", data.detail);
      } else {
        const nuevasOrdenes = data?.ordenes || [];
        setOrdenes(offset === 0 ? nuevasOrdenes : [...ordenes, ...nuevasOrdenes]);
        setTotalOrdenes(data?.total || 0);
        setUserId(data?.user_id || '');
      }
    } catch (error) {
      console.error("Error cargando órdenes:", error);
    } finally {
      setLoadingOrdenes(false);
    }
  }

  // Cargar órdenes cuando cambia la cuenta
  useEffect(() => {
    if (!cuentaActiva) return;
    cargarOrdenes();
  }, [cuentaActiva, offset]); // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll automático en chat
  useEffect(() => {
    if (mensajesEndRef.current) {
      mensajesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [mensajes]);

  async function seleccionarOrden(orden) {
    setOrdenSeleccionada(orden);
    setDetalleOrden(null);
    setMensajes([]);
    setChatError(null);
    setLoadingChat(true);

    try {
      // Cargar detalle
      const resDet = await fetch(`/api/ventas/detalle/${orden.id}?cuenta=${encodeURIComponent(cuentaActiva)}`);
      const dataDet = await resDet.json();
      if (!dataDet?.error && !dataDet?.detail) setDetalleOrden(dataDet);

      // Cargar mensajes
      const resMsg = await fetch(`/api/ventas/mensajes/${orden.pack_id}?cuenta=${encodeURIComponent(cuentaActiva)}&user_id=${userId}`);
      const dataMsg = await resMsg.json();
      if (dataMsg?.error) {
        setChatError(dataMsg.error);
      } else if (dataMsg?.detail) {
        setChatError(dataMsg.detail);
      } else {
        setMensajes(dataMsg?.mensajes || []);
      }

    } catch (error) {
      console.error("Error cargando detalle/chat:", error);
      setChatError("Error de red al cargar el chat.");
    } finally {
      setLoadingChat(false);
    }
  }

  async function enviarMensaje(e) {
    e.preventDefault();
    if (!mensajeTexto.trim() || !ordenSeleccionada) return;

    setEnviandoMensaje(true);
    try {
      const res = await fetch(`/api/ventas/mensajes/${ordenSeleccionada.pack_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cuenta: cuentaActiva,
          user_id: userId,
          buyer_id: ordenSeleccionada.buyer_id,
          text: mensajeTexto
        })
      });
      const data = await res.json();
      
      if (data?.error) {
        alert(data.error);
      } else if (data?.detail) {
        alert(data.detail);
      } else {
        // Mensaje enviado, recargar chat
        setMensajeTexto('');
        const resMsg = await fetch(`/api/ventas/mensajes/${ordenSeleccionada.pack_id}?cuenta=${encodeURIComponent(cuentaActiva)}&user_id=${userId}`);
        const dataMsg = await resMsg.json();
        if (!dataMsg?.error && !dataMsg?.detail) setMensajes(dataMsg?.mensajes || []);
      }
    } catch (error) {
      console.error(error);
      alert("Error al enviar mensaje");
    } finally {
      setEnviandoMensaje(false);
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-VE', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  }

  const statusColors = {
    paid: 'bg-green-100 text-green-700',
    cancelled: 'bg-red-100 text-red-700',
    pending: 'bg-amber-100 text-amber-700'
  };

  return (
    <div className="flex h-full bg-slate-50 gap-6">
      
      {/* Panel Izquierdo: Órdenes */}
      <div className="w-1/3 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex flex-col gap-3 shrink-0">
          <h2 className="font-bold text-slate-800 flex items-center gap-2">
            <ShoppingBag size={20} className="text-blue-600" /> 
            Ventas y Órdenes
          </h2>
          <select 
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
            value={cuentaActiva}
            onChange={(e) => { setCuentaActiva(e.target.value); setOffset(0); setOrdenes([]); setOrdenSeleccionada(null); }}
          >
            {cuentas.map(c => (
              <option key={c.archivo} value={c.archivo}>{c.nombre}</option>
            ))}
          </select>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {loadingOrdenes && offset === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <RefreshCw className="animate-spin mx-auto mb-2" size={24} />
              Cargando órdenes...
            </div>
          ) : ordenes.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              No hay órdenes recientes.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {ordenes.map(orden => (
                <div 
                  key={orden.id} 
                  onClick={() => seleccionarOrden(orden)}
                  className={`p-3 rounded-lg cursor-pointer border transition-colors ${
                    ordenSeleccionada?.id === orden.id 
                      ? 'bg-blue-50 border-blue-200' 
                      : 'bg-white border-transparent hover:bg-slate-50 hover:border-slate-200'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <div className="font-bold text-slate-800 text-sm truncate pr-2">{orden.buyer_name}</div>
                    <div className="text-xs text-slate-500 shrink-0">{formatDate(orden.date_created)}</div>
                  </div>
                  <div className="text-xs text-slate-600 line-clamp-1 mb-2" title={orden.items}>{orden.items}</div>
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-blue-700 text-sm">{orden.currency_id} {orden.total_paid}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${statusColors[orden.status] || 'bg-slate-100 text-slate-700'}`}>
                      {orden.status}
                    </span>
                  </div>
                </div>
              ))}
              
              {ordenes.length < totalOrdenes && (
                <button 
                  onClick={() => setOffset(offset + 50)}
                  disabled={loadingOrdenes}
                  className="w-full py-2 mt-2 text-sm text-blue-600 font-medium hover:bg-blue-50 rounded disabled:opacity-50"
                >
                  {loadingOrdenes ? 'Cargando...' : 'Cargar más órdenes'}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Panel Derecho: Detalles y Chat */}
      <div className="w-2/3 bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden relative">
        {!ordenSeleccionada ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-8 text-center">
            <MessageSquare size={48} className="mb-4 opacity-50" />
            <h3 className="text-lg font-medium text-slate-600 mb-2">Selecciona una orden</h3>
            <p className="text-sm">Elige una orden de la lista para ver sus detalles y conversar con el comprador.</p>
          </div>
        ) : (
          <>
            {/* Header de la Orden */}
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex flex-col shrink-0">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-bold text-slate-800 text-lg">Orden #{ordenSeleccionada.id}</h3>
                <a href={`https://myaccount.mercadolibre.com.ve/sales/${ordenSeleccionada.pack_id}/detail`} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline">
                  Ver en MercadoLibre ↗
                </a>
              </div>
              
              {loadingChat && !detalleOrden ? (
                <div className="flex items-center text-slate-500 text-sm">
                  <RefreshCw className="animate-spin mr-2" size={14} /> Cargando detalles...
                </div>
              ) : detalleOrden && (
                <div className="flex flex-col gap-4 mt-2">
                  {/* Info de Productos */}
                  {detalleOrden.items && detalleOrden.items.length > 0 && (
                    <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
                      <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">Productos ({detalleOrden.items.length})</h4>
                      <div className="flex flex-col gap-2">
                        {detalleOrden.items.map((item, i) => (
                          <div key={i} className="flex gap-3 items-center">
                            {item.thumbnail ? (
                              <img src={item.thumbnail} alt={item.titulo} className="w-12 h-12 object-cover rounded border border-slate-200" />
                            ) : (
                              <div className="w-12 h-12 bg-slate-100 rounded border border-slate-200 flex items-center justify-center text-slate-400">
                                <ShoppingBag size={16} />
                              </div>
                            )}
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-slate-800 line-clamp-1" title={item.titulo}>{item.titulo}</p>
                              <div className="flex gap-3 text-xs text-slate-500 mt-1">
                                <span>Cant: <strong className="text-slate-700">{item.cantidad}</strong></span>
                                <span>Precio: <strong className="text-blue-600">{item.moneda} {item.precio_unit}</strong></span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Info de Comprador y Envío */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex gap-2 items-start text-sm text-slate-600">
                      <User size={16} className="text-slate-400 mt-0.5 shrink-0" />
                      <div>
                        <div className="font-medium text-slate-800">{ordenSeleccionada.buyer_name}</div>
                        {detalleOrden.buyer?.phone?.area_code && detalleOrden.buyer?.phone?.number && (
                          <div>{detalleOrden.buyer.phone.area_code} {detalleOrden.buyer.phone.number}</div>
                        )}
                      </div>
                    </div>
                    
                    {detalleOrden.envio && detalleOrden.envio.status !== "Sin envío" ? (
                      <div className="flex gap-2 items-start text-sm text-slate-600">
                        <Truck size={16} className="text-blue-500 mt-0.5 shrink-0" />
                        <div>
                          <div className="font-medium text-slate-800">{detalleOrden.envio.transportista} - <span className="uppercase text-blue-600 text-xs">{detalleOrden.envio.status}</span></div>
                          <div className="text-xs">Guía: {detalleOrden.envio.tracking}</div>
                          {detalleOrden.envio.receptor && (
                            <div className="text-xs mt-1 text-slate-500 line-clamp-1" title={detalleOrden.envio.direccion}>
                              A: {detalleOrden.envio.receptor} ({detalleOrden.envio.direccion}, {detalleOrden.envio.ciudad})
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-2 items-start text-sm text-slate-500">
                        <MapPin size={16} className="text-slate-400 mt-0.5 shrink-0" />
                        <div>Sin información de Mercado Envíos (Acordar con vendedor o Retiro)</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Historial de Chat */}
            <div className="flex-1 overflow-y-auto p-4 bg-slate-50/50 flex flex-col gap-3">
              {loadingChat ? (
                <div className="flex-1 flex items-center justify-center text-slate-400">
                  <RefreshCw className="animate-spin mr-2" size={20} /> Cargando chat...
                </div>
              ) : chatError ? (
                <div className="flex-1 flex flex-col items-center justify-center text-red-500 text-center">
                  <AlertCircle size={32} className="mb-2 opacity-50" />
                  <p className="text-sm font-medium mb-1">No se pudo cargar la conversación</p>
                  <p className="text-xs text-red-400 max-w-sm">{chatError}</p>
                </div>
              ) : mensajes.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                  <MessageSquare size={32} className="mb-2 opacity-50" />
                  <p className="text-sm">No hay mensajes en esta compra.</p>
                </div>
              ) : (
                mensajes.map((msg, idx) => {
                  const isMine = msg.es_mio;
                  return (
                    <div key={idx} className={`flex flex-col max-w-[80%] ${isMine ? 'self-end' : 'self-start'}`}>
                      <div className={`p-3 rounded-2xl ${
                        isMine 
                          ? 'bg-blue-600 text-white rounded-tr-sm' 
                          : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm shadow-sm'
                      }`}>
                        <div className="whitespace-pre-wrap text-sm">{msg.text}</div>
                      </div>
                      <div className={`text-[10px] text-slate-400 mt-1 flex items-center gap-1 ${isMine ? 'justify-end' : 'justify-start'}`}>
                        <Clock size={10} /> {formatDate(msg.date)}
                      </div>
                    </div>
                  );
                }).reverse() // Invertimos porque ML a veces los manda del más nuevo al más viejo
              )}
              <div ref={mensajesEndRef} />
            </div>

            {/* Input de Chat */}
            <div className="p-4 border-t border-slate-200 bg-white shrink-0">
              <form onSubmit={enviarMensaje} className="flex gap-3">
                <input 
                  type="text" 
                  className="flex-1 border border-slate-300 rounded-full px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="Escribe un mensaje al comprador..."
                  value={mensajeTexto}
                  onChange={(e) => setMensajeTexto(e.target.value)}
                  disabled={loadingChat || enviandoMensaje}
                />
                <button 
                  type="submit" 
                  disabled={loadingChat || enviandoMensaje || !mensajeTexto.trim()}
                  className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white w-10 h-10 rounded-full flex items-center justify-center transition-colors shrink-0"
                >
                  {enviandoMensaje ? <RefreshCw className="animate-spin" size={16} /> : <Send size={16} className="-ml-0.5" />}
                </button>
              </form>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
