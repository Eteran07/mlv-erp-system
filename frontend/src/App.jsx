import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Home, ShoppingCart, Settings, Users, Image as ImageIcon, LayoutGrid } from 'lucide-react';

function Sidebar() {
  const location = useLocation();
  
  const menuItems = [
    { path: '/', icon: <Home size={20} />, text: 'Inicio' },
    { path: '/sync', icon: <LayoutGrid size={20} />, text: 'Sincronización' },
    { path: '/ventas', icon: <ShoppingCart size={20} />, text: 'Ventas y Mensajes' },
    { path: '/manager', icon: <Settings size={20} />, text: 'Manager Matrix' },
    { path: '/multicuenta', icon: <Users size={20} />, text: 'Acción Multicuenta' },
    { path: '/galeria', icon: <ImageIcon size={20} />, text: 'Galería' },
  ];

  return (
    <div className="w-64 bg-slate-900 text-white flex flex-col h-screen fixed">
      <div className="p-6 border-b border-slate-800">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <span className="text-blue-400">🚀</span> MLV ERP
        </h1>
      </div>
      <nav className="flex-1 py-4">
        {menuItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`flex items-center gap-3 px-6 py-3 transition-colors ${
              location.pathname === item.path 
                ? 'bg-blue-600 border-r-4 border-blue-400' 
                : 'hover:bg-slate-800 text-slate-300 hover:text-white'
            }`}
          >
            {item.icon}
            <span className="font-medium">{item.text}</span>
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-slate-800 text-sm text-slate-400 text-center">
        Versión React (Preview)
      </div>
    </div>
  );
}

function Welcome() {
  return (
    <div className="p-10">
      <h1 className="text-3xl font-bold text-slate-800 mb-4">Bienvenido al Nuevo MLV ERP</h1>
      <p className="text-slate-600 mb-8">Esta es una vista previa del rediseño usando React y Tailwind CSS.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center text-center">
          <div className="bg-blue-100 p-4 rounded-full text-blue-600 mb-4">
            <LayoutGrid size={32} />
          </div>
          <h3 className="font-bold text-lg mb-2">Diseño Ultra Rápido</h3>
          <p className="text-slate-500 text-sm">Navegación instantánea entre módulos sin recargar la página.</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center text-center">
          <div className="bg-green-100 p-4 rounded-full text-green-600 mb-4">
            <ShoppingCart size={32} />
          </div>
          <h3 className="font-bold text-lg mb-2">Ventas Avanzadas</h3>
          <p className="text-slate-500 text-sm">El nuevo panel de ventas y mensajería se sentirá como una app móvil.</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center text-center">
          <div className="bg-purple-100 p-4 rounded-full text-purple-600 mb-4">
            <Users size={32} />
          </div>
          <h3 className="font-bold text-lg mb-2">Multicuenta Fluida</h3>
          <p className="text-slate-500 text-sm">Gestiona todo tu ecosistema de Mercado Libre desde un solo lugar de forma elegante.</p>
        </div>
      </div>
    </div>
  );
}

import ManagerMatrix from './pages/ManagerMatrix';
import MultiAccountAction from './pages/MultiAccountAction';
import SalesAndMessages from './pages/SalesAndMessages';
import ExcelSync from './pages/ExcelSync';
import LocalGallery from './pages/LocalGallery';

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-slate-50">
        <Sidebar />
        <main className="flex-1 ml-64 flex flex-col h-screen">
          <header className="bg-white h-16 border-b border-slate-200 flex items-center px-8 justify-between sticky top-0 z-10 shrink-0">
            <h2 className="text-lg font-semibold text-slate-700">Dashboard</h2>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                ED
              </div>
              <span className="text-sm font-medium text-slate-600">Edgar Admin</span>
            </div>
          </header>
          
          <div className="p-6 flex-1 overflow-hidden">
            <Routes>
              <Route path="/" element={<Welcome />} />
              <Route path="/sync" element={<ExcelSync />} />
              <Route path="/ventas" element={<SalesAndMessages />} />
              <Route path="/manager" element={<ManagerMatrix />} />
              <Route path="/multicuenta" element={<MultiAccountAction />} />
              <Route path="/galeria" element={<LocalGallery />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
