export const viewerHtml = `
<div id="activate">
  <header style="position:static;border:0;background:transparent;padding:0 0 16px">
    <h1>SkyAdmin Viewer</h1>
    <p>Read-only groups, clients, tasks, contacts, notebook, and passwords. Paste a client passcode only (not a license key).</p>
  </header>
  <label for="code">Client passcode</label>
  <textarea id="code" placeholder="Paste SKYPASS1:… passcode"></textarea>
  <div class="toolbar" style="margin-top:12px">
    <button id="btnActivate" type="button">Activate</button>
  </div>
  <p id="activateStatus" class="status"></p>
</div>

<div id="app" class="hidden">
  <header>
    <h1>SkyAdmin Viewer</h1>
    <p id="machineLabel">Read-only · synced from desktop</p>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Search this tab…" autocomplete="off" enterkeyhint="search">
      <button id="btnRefresh" type="button">Refresh</button>
      <button id="btnLogout" type="button" class="secondary">Sign out</button>
    </div>
    <p id="syncStatus" class="status"></p>
  </header>
  <div class="tabs">
    <button class="tab active" data-tab="groups" type="button">Groups</button>
    <button class="tab" data-tab="clients" type="button">Clients</button>
    <button class="tab" data-tab="tasks" type="button">Tasks</button>
    <button class="tab" data-tab="contacts" type="button">Contacts</button>
    <button class="tab" data-tab="notebook" type="button">Notebook</button>
    <button class="tab" data-tab="passwords" type="button">Passwords</button>
  </div>
  <main>
    <div id="panel-groups"></div>
    <div id="panel-clients" class="hidden"></div>
    <div id="panel-tasks" class="hidden"></div>
    <div id="panel-contacts" class="hidden"></div>
    <div id="panel-notebook" class="hidden"></div>
    <div id="panel-passwords" class="hidden"></div>
  </main>
</div>

<div id="vaultUnlock" class="modal hidden" role="dialog" aria-modal="true">
  <div class="modal-card">
    <h2>Unlock Mobile Vault</h2>
    <p class="meta">Enter the Mobile Vault Passphrase from desktop Settings. Sync token alone cannot decrypt passwords.</p>
    <input id="vaultPhrase" type="password" placeholder="Passphrase" autocomplete="current-password">
    <div class="toolbar" style="margin-top:12px">
      <button id="btnVaultUnlock" type="button">Unlock</button>
      <button id="btnVaultCancel" type="button" class="secondary">Cancel</button>
    </div>
    <p id="vaultUnlockStatus" class="status"></p>
  </div>
</div>
`;
