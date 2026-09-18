export const getAdminHtml = (adminPath: string, csrfToken: string) => `
<div class="topbar">
  <div id="status" class="status"></div>
  <form class="logout-form" method="POST" action="${adminPath}/logout">
    <input type="hidden" name="csrf_token" value="${csrfToken}">
    <button class="logout" type="submit">Logout</button>
  </form>
</div>
<h1>SkyAdmin Pro</h1>
<div class="sub">Sky Creation Innovations</div>
<div class="hint">This desk issues licenses and app updates. It does not edit client companies, tasks, or bills.</div>
<div id="keyBanner" class="warn-banner"></div>
<div id="apiBanner" class="warn-banner"></div>
<h2>License packages</h2>
<div class="hint">License packages (days/baht) for the activation page and iPhone generator — not the desktop client fee matrix.</div>
<div id="pkgSummary" class="pkg-summary"></div>
<div id="pkgStatus" class="hint"></div>
<div class="pkg-head pkg-row"><span>Label</span><span>Days</span><span>Baht</span><span></span></div>
<div id="pkgEditor"></div>
<label>Over 1-year message</label>
<input id="overYear" placeholder="Over 1 Year — discuss on WhatsApp">
<div class="btns" style="margin-top:8px">
<button type="button" id="addPkgBtn" class="sm green">Add package</button>
<button type="button" id="savePkgBtn" class="sm gray">Save packages</button>
<button type="button" id="reloadPkgBtn" class="sm gray">Reload</button>
</div>

<h2>Generate License</h2>
<label>Machine ID</label>
<input id="mid" placeholder="72FA00DC6B64525F" autocomplete="off" autocapitalize="characters" spellcheck="false">
<label>Package</label>
<select id="days">
<option value="7" selected>Loading packages…</option>
</select>
<div id="cWrap" style="display:none"><label>Custom days</label><input id="cDays" type="number" min="1" max="36500"></div>
<button type="button" id="genBtn">Generate</button>

<div id="result" style="display:none">
<label>License Key</label>
<div id="license" class="out"></div>
<div class="btns"><button type="button" id="copyKeyBtn" class="sm gray">Copy Key</button><button type="button" id="copyPassBtn" class="sm gray">Copy Passcode</button></div>
<label>Passcode</label>
<div id="passcode" class="out" style="font-size:18px;letter-spacing:3px;text-align:center"></div>
</div>

<h2>App Update</h2>
<div class="hint">URL must be the installer <code>SkyAdminPro-Setup-*.exe</code>, not a portable exe. Desktop apps show Settings → Download.</div>
<label>Version (e.g. 0.3.1)</label>
<input id="updVer" placeholder="0.3.1">
<label>Download URL</label>
<input id="updUrl" placeholder="https://your-cdn/SkyAdminPro-Setup-0.3.1.exe">
<div class="btns" style="margin-top:8px">
<button type="button" id="publishBtn" class="sm green">Publish update</button>
<button type="button" id="reloadUpdBtn" class="sm gray">Reload</button>
</div>
<div id="updStatus" class="hint"></div>

<h2>Remote Control</h2>
<label>Ban machine</label>
<div style="display:flex;gap:6px">
<input id="banIn" placeholder="Machine ID" spellcheck="false" style="flex:1">
<button type="button" id="banBtn" class="sm red" style="margin:0">Ban</button>
</div>
<div id="banList"></div>

<h2>Machines <span id="machCnt" style="color:#6b7280;font-size:12px"></span></h2>
<div class="hint">License keys, not visas or company documents. Timed packages: <b>24h to activate</b> — period starts on desktop activation. Use <b>Use ID</b> to fill Generate License, or renew with package buttons / custom days.</div>
<div class="btns filt" style="margin:8px 0">
<button type="button" class="sm gray" data-mf="all">All</button>
<button type="button" class="sm gray" data-mf="active">Active</button>
<button type="button" class="sm gray" data-mf="expiring" title="License keys, not visas or company documents">License keys &lt;7d</button>
<button type="button" class="sm gray" data-mf="pending">Pending</button>
<button type="button" class="sm gray" data-mf="expired">Expired</button>
</div>
<input id="machSearch" placeholder="Search machine ID…">
<div id="machines"></div>

<h2>Records <span id="cnt" style="color:#6b7280;font-size:12px"></span></h2>
<div class="hint">Issued license keys, not visas or company documents. Copy, quick-renew, revoke, or unrevoke.</div>
<div class="btns filt" style="margin:8px 0">
<button type="button" class="sm gray" data-rf="all">All</button>
<button type="button" class="sm gray" data-rf="active">Active</button>
<button type="button" class="sm gray" data-rf="expiring" title="License keys, not visas or company documents">License keys &lt;7d</button>
<button type="button" class="sm gray" data-rf="pending">Pending</button>
<button type="button" class="sm gray" data-rf="expired">Expired</button>
</div>
<input id="search" placeholder="Search...">
<div id="records"></div>

<h2>Housekeeping</h2>
<div class="hint">Archive and remove expired, revoked, or never-activated keys older than N days. Active licenses are kept.</div>
<div class="housekeeping">
  <label for="purgeDays" style="margin:0">Older than</label>
  <input id="purgeDays" type="number" min="1" max="365" value="30" class="renew-days" style="width:80px">
  <span style="font-size:12px;color:#9ca3af">days</span>
  <button type="button" id="purgeBtn" class="sm red">Clear old licenses</button>
</div>
<div id="purgeResult" class="hint"></div>
`;
