/** Generate License form (SKU entitlements). */

export const getGenerateHtml = () => `
<h2>Generate License</h2>
<label>Machine ID</label>
<input id="mid" placeholder="72FA00DC6B64525F" autocomplete="off" autocapitalize="characters" spellcheck="false">
<label>Package</label>
<select id="days">
<option value="7" selected>Loading packages…</option>
</select>
<div id="cWrap" style="display:none"><label>Custom days</label><input id="cDays" type="number" min="1" max="36500"></div>
<label>Org ID (optional)</label>
<input id="orgId" placeholder="leave blank for solo, or firm:acme for team" autocomplete="off" spellcheck="false">
<div class="sku-row">
<label class="sku"><input type="checkbox" id="skuSync" checked> Sync</label>
<label class="sku"><input type="checkbox" id="skuWeb"> Web</label>
<label class="sku"><input type="checkbox" id="skuDrive"> Drive files</label>
</div>
<label>Max devices (0 = unlimited)</label>
<input id="skuMaxDevices" type="number" min="0" max="10000" value="1" title="Fail-closed default 1; 0 = unlimited">
<div class="hint">Org ID: leave blank for solo (<code>m:MACHINE</code>). Same string (e.g. <code>firm:acme</code>) for every seat that should share team sync. Sync is on by default; tick Web / Drive only if needed. max_devices default 1; 0 = unlimited.</div>
<button type="button" id="genBtn">Generate</button>

<div id="result" style="display:none">
<label>License Key</label>
<div id="license" class="out"></div>
<div class="btns"><button type="button" id="copyKeyBtn" class="sm gray">Copy Key</button><button type="button" id="copyPassBtn" class="sm gray">Copy Passcode</button></div>
<label>Passcode</label>
<div id="passcode" class="out" style="font-size:18px;letter-spacing:3px;text-align:center"></div>
<div id="skuOut" class="hint"></div>
</div>
`;
