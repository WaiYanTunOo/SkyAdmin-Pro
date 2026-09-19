/** Machines / records / housekeeping sections. */

export const getListsHtml = () => `
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
