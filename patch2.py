import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Fix handlePublish confirmation
pub_pattern = r'''const handlePublish = async \(\) => \{
    if \(!previewData\?\.productos\?\.length\) return;
    setIsPublishing\(true\); setStep\(4\);'''
pub_repl = r'''const handlePublish = async () => {
    if (!previewData?.productos?.length) return;
    if (!window.confirm(¿Estás seguro de publicar  artículos?)) return;
    setIsPublishing(true); setStep(4);'''
code = re.sub(pub_pattern, pub_repl, code)

# Fix applyBulkExposicion and applyBulkEnvio
bulk_exp_pattern = r'''const applyBulkExposicion = \(\) => \{
    setRowData\(prev => \{'''
bulk_exp_repl = r'''const applyBulkExposicion = () => {
    if (!window.confirm(¿Aplicar exposición '' a  publicaciones?)) return;
    setRowData(prev => {'''
code = re.sub(bulk_exp_pattern, bulk_exp_repl, code)

bulk_env_pattern = r'''const applyBulkEnvio = \(\) => \{
    setRowData\(prev => \{'''
bulk_env_repl = r'''const applyBulkEnvio = () => {
    if (!window.confirm(¿Aplicar envío '' a  publicaciones?)) return;
    setRowData(prev => {'''
code = re.sub(bulk_env_pattern, bulk_env_repl, code)

# We need to add alert after bulk actions, but setRowData is async. We can just add setTimeout.
bulk_exp_repl2 = r'''return next;
    \}\);
  \};'''
bulk_exp_repl2_new = r'''return next;
    });
    setTimeout(() => alert("✅ Exposición masiva aplicada exitosamente."), 100);
  };'''
code = code.replace(bulk_exp_repl2, bulk_exp_repl2_new)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched handlePublish and bulk actions")
