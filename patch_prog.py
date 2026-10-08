import re

with open('frontend/src/pages/ExcelSync.jsx', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update handlePreview to start progress tracking
prev_pattern = r'''  const handlePreview = async \(\) => \{
    setShowCategoryModal\(false\); setLoadingPreview\(true\); setPreviewData\(null\); setRowData\(\{\}\);
    const fd = new FormData\(\);'''
prev_repl = r'''  const handlePreview = async () => {
    setShowCategoryModal(false); setLoadingPreview(true); setPreviewData(null); setRowData({});
    setProgress(null);
    const iv = startProgressTracking();
    const fd = new FormData();'''
code = re.sub(prev_pattern, prev_repl, code)

prev_finally_pattern = r'''    \} catch \(e\) \{ alert\('Error generando vista previa'\); \}
    finally \{ setLoadingPreview\(false\); \}'''
prev_finally_repl = r'''    } catch (e) { alert('Error generando vista previa'); }
    finally { setLoadingPreview(false); clearInterval(iv); }'''
code = re.sub(prev_finally_pattern, prev_finally_repl, code)

with open('frontend/src/pages/ExcelSync.jsx', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched handlePreview progress")
