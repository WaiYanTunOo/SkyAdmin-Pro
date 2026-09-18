export const viewerCss = `
:root{color-scheme:dark;--bg:#0f172a;--card:#1e293b;--muted:#94a3b8;--text:#f8fafc;--accent:#3b82f6;--border:#334155}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
header{position:sticky;top:0;z-index:10;background:#111827ee;backdrop-filter:blur(8px);border-bottom:1px solid var(--border);padding:12px 16px;padding-top:max(12px,env(safe-area-inset-top))}
header h1{margin:0;font-size:18px;font-weight:700}
header p{margin:4px 0 0;font-size:12px;color:var(--muted)}
.toolbar{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
input,select,button,textarea{font:inherit}
input,select{flex:1;min-width:0;padding:10px 12px;border:1px solid var(--border);border-radius:10px;background:#0b1220;color:var(--text)}
button{padding:10px 14px;border:0;border-radius:10px;background:var(--accent);color:#fff;font-weight:600;cursor:pointer}
button.secondary{background:#334155}
button:disabled{opacity:.5;cursor:not-allowed}
.tabs{display:flex;gap:4px;padding:8px 16px;border-bottom:1px solid var(--border);background:#111827;overflow-x:auto;-webkit-overflow-scrolling:touch}
.tab{flex:0 0 auto;min-width:72px;padding:10px 12px;border:0;border-radius:10px;background:transparent;color:var(--muted);font-weight:600;cursor:pointer;font-size:13px}
.tab.active{background:var(--card);color:var(--text)}
main{padding:12px 16px 24px;padding-bottom:max(24px,env(safe-area-inset-bottom))}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px;margin-bottom:10px}
.card h3{margin:0 0 6px;font-size:16px}
.meta{font-size:12px;color:var(--muted);line-height:1.5}
.body{margin-top:8px;font-size:14px;line-height:1.55;white-space:pre-wrap}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#1d4ed833;color:#93c5fd;font-size:11px;font-weight:600;margin-right:6px}
.swatch{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:middle;border:1px solid #ffffff44}
.pin{color:#fbbf24}
.empty{text-align:center;color:var(--muted);padding:48px 16px;font-size:14px;line-height:1.5}
.empty strong{display:block;color:var(--text);font-size:15px;margin-bottom:6px}
.row2{display:flex;gap:8px;flex-wrap:wrap;margin-top:4px}
.status{font-size:12px;color:var(--muted);margin-top:8px}
.error{color:#fca5a5}
#activate{padding:24px 16px;max-width:480px;margin:0 auto}
#activate textarea{width:100%;min-height:120px;padding:12px;border:1px solid var(--border);border-radius:12px;background:#0b1220;color:var(--text);resize:vertical}
#activate label{display:block;font-size:13px;color:var(--muted);margin:12px 0 6px}
.hidden{display:none!important}
.modal{position:fixed;inset:0;background:#00000099;display:flex;align-items:center;justify-content:center;padding:16px;z-index:40}
.modal-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px;width:100%;max-width:400px}
.modal-card h2{margin:0 0 8px;font-size:17px}
.modal-card input{width:100%;margin-top:10px;padding:10px 12px;border:1px solid var(--border);border-radius:10px;background:#0b1220;color:var(--text)}
.secret{font-family:ui-monospace,Consolas,monospace;letter-spacing:.04em}
.btn-row{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.btn-row button{padding:8px 12px;font-size:12px}
.lockbar{display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
.lockbar .status{margin:0}
`;
