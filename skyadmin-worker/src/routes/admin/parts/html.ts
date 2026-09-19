import { getGenerateHtml } from "./html_generate";
import { getListsHtml } from "./html_lists";

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

${getGenerateHtml()}

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

${getListsHtml()}
`;
