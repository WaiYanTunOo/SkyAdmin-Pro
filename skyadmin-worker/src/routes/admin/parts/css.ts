export const loginCss = `
body{font-family:-apple-system,Helvetica,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#111827;color:#f9fafb}
.box{background:#1f2937;padding:32px;border-radius:16px;width:320px;text-align:center}
h2{margin:0 0 16px;font-size:18px}
input{width:100%;padding:12px;border:1px solid #374151;border-radius:10px;background:#111827;color:#f9fafb;font-size:16px;box-sizing:border-box;text-align:center;letter-spacing:4px}
button{margin-top:14px;width:100%;padding:12px;border:0;border-radius:10px;background:#2563eb;color:white;font-size:15px;font-weight:700}
button:active{background:#1d4ed8}
.err{color:#f87171;font-size:13px;margin-top:10px}
`;
export const adminCss = `
*{box-sizing:border-box}
body{font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:680px;margin:0 auto;padding:56px 16px 16px;background:#111827;color:#f9fafb;-webkit-text-size-adjust:100%}
.topbar{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;align-items:center;justify-content:flex-end;gap:12px;min-height:48px;padding:8px 16px;background:#111827;border-bottom:1px solid #374151}
.topbar .status{position:static;display:none;margin:0;margin-right:auto;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.logout-form{margin:0;padding:0;flex-shrink:0}
.topbar button.logout{width:auto;margin-top:0;padding:7px 14px;background:#374151;border:0;color:#e5e7eb;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer}
.topbar button.logout:active{background:#4b5563}
h1{font-size:20px;margin:0 0 4px} h2{font-size:16px;margin:22px 0 8px;color:#9ca3af}
.sub{color:#6b7280;font-size:12px;margin-bottom:16px}
label{font-weight:600;font-size:13px;display:block;margin:12px 0 5px;color:#d1d5db}
input,select{width:100%;padding:11px;border:1px solid #374151;border-radius:10px;background:#1f2937;color:#f9fafb;font-size:15px;-webkit-appearance:none}
button{margin-top:14px;width:100%;padding:13px;border:0;border-radius:10px;background:#2563eb;color:white;font-size:15px;font-weight:700}
button:active{background:#1d4ed8} button:disabled{background:#4b5563}
button.sm{width:auto;padding:7px 12px;font-size:12px;border-radius:8px;margin-top:0}
.gray{background:#374151;color:#e5e7eb;border:1px solid #4b5563}
.green{background:#059669}
.red{background:#dc2626}
.out{margin-top:8px;padding:12px;background:#1f2937;border-radius:10px;border:1px solid #374151;word-break:break-all;font-family:monospace;font-size:12px}
.hint{font-size:11px;color:#6b7280;margin-top:6px}
.rec{background:#1f2937;border:1px solid #374151;border-radius:10px;padding:10px;margin:6px 0;font-size:12px}
.rec.revoked{border-color:#991b1b;background:#450a0a}
.rec .row{margin:1px 0} .rec b{font-size:12px}
.tag{display:inline-block;padding:1px 6px;border-radius:99px;font-size:10px;font-weight:700}
.tag.ok{background:#064e3b;color:#6ee7b7}.tag.exp{background:#7f1d1d;color:#fca5a5}.tag.rev{background:#374151;color:#9ca3af}.tag.pend{background:#1e3a5f;color:#93c5fd}
.expiry{color:#6ee7b7;font-weight:600}.expiry.expired{color:#fca5a5}.expiry.pending{color:#93c5fd}
.mach{background:#1f2937;border:1px solid #374151;border-radius:10px;padding:10px;margin:6px 0;font-size:12px}
.mach .ttl{font-size:13px;font-weight:700}
.btns{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.chip{display:inline-flex;align-items:center;gap:4px;background:#7f1d1d;color:#fca5a5;padding:3px 8px;border-radius:99px;font-size:11px;font-weight:600;margin:3px 3px 0 0}
.chip button{background:none;border:0;color:#fca5a5;font-weight:800;padding:0 2px;margin:0;width:auto;font-size:12px}
.status{font-size:11px;padding:4px 10px;border-radius:8px;background:#064e3b;color:#6ee7b7}
.warn-banner{margin:0 0 12px;padding:10px 12px;border-radius:10px;background:#7f1d1d;color:#fecaca;font-size:12px;display:none}
.pkg-row{display:grid;grid-template-columns:1.2fr .6fr .6fr auto;gap:6px;align-items:center;margin:6px 0}
.pkg-row input,.pkg-row select{margin:0}
.pkg-head{font-size:11px;color:#9ca3af;font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin:8px 0 4px}
.pkg-head span{padding:0 2px}
.pkg-summary{background:#1f2937;border:1px solid #374151;border-radius:10px;padding:8px 12px;margin:0 0 10px;font-size:13px}
.pkg-summary .item{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid #374151}
.pkg-summary .item:last-child{border-bottom:0}
.pkg-summary .price{color:#6ee7b7;font-weight:600;white-space:nowrap}
.renew-days{width:76px;padding:7px 8px;font-size:12px;margin:0;border-radius:8px;border:1px solid #4b5563;background:#1f2937;color:#f9fafb}
.renew-custom{display:inline-flex;align-items:center;gap:6px;flex-wrap:wrap}
.housekeeping{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:8px}
.filt button.on{background:#2563eb;color:#fff;border-color:#2563eb}
`;
