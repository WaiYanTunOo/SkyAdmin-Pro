export const viewerHtml = `
<div id="activate">
  <header style="position:static;border:0;background:transparent;padding:0 0 16px">
    <h1>SkyAdmin Viewer</h1>
    <p>Read-only groups, clients, tasks, contacts, and notebook. Paste your activation code from the desktop app.</p>
  </header>
  <label for="code">License key or passcode</label>
  <textarea id="code" placeholder="Paste SKYPASS1:… or license key"></textarea>
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
  </div>
  <main>
    <div id="panel-groups"></div>
    <div id="panel-clients" class="hidden"></div>
    <div id="panel-tasks" class="hidden"></div>
    <div id="panel-contacts" class="hidden"></div>
    <div id="panel-notebook" class="hidden"></div>
  </main>
</div>
`;
