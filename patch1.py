import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Add pagination and filtering states
state_pattern = r"const \[viewMode, setViewMode\] = useState\('categorias'\); // 'categorias' \| 'lineal'\n  const \[rowData, setRowData\] = useState\(\{\}\);"
state_repl = r'''const [viewMode, setViewMode] = useState('categorias');
  const [rowData, setRowData] = useState({});
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(50);
  const [hidePublished, setHidePublished] = useState(false);'''
code = re.sub(state_pattern, state_repl, code)

# Update handlePreview to pre-load rowData with ImagenLocal and confirm
prev_pattern = r'''const handlePreview = async \(\) => \{
    setShowCategoryModal\(false\); setLoadingPreview\(true\); setPreviewData\(null\); setRowData\(\{\}\);'''
prev_repl = r'''const handlePreview = async () => {
    if (!window.confirm("¿Estás seguro de generar la previsualización con estos ajustes?")) return;
    setShowCategoryModal(false); setLoadingPreview(true); setPreviewData(null); setRowData({});'''
code = re.sub(prev_pattern, prev_repl, code)

prev_pattern2 = r'''setPreviewData\(d\);
      setSelectedRows\(new Set\(\(d\.productos \|\| \[\]\)\.map\(\(_, i\) => i\)\)\);
      setStep\(3\);'''
prev_repl2 = r'''setPreviewData(d);
      
      const initialRowData = {};
      const newSelected = new Set();
      (d.productos || []).forEach((p, i) => {
        if (p.ImagenLocal) {
          initialRowData[i] = { localImages: [p.ImagenLocal] };
        }
        // by default select if not 'Ya publicado'
        if (!(p.EstadoPublicación || p["Estado Publicación"] || "").includes("Ya publicado")) {
           newSelected.add(i);
        }
      });
      setRowData(initialRowData);
      setSelectedRows(newSelected);
      setStep(3);
      setCurrentPage(1);'''
code = re.sub(prev_pattern2, prev_repl2, code)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched handlePreview and states")
