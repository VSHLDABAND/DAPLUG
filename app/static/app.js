const state = { user: null, view: 'overview', leads: [], properties: [], tasks: [], dashboard: null, search: '', selectedLead: '', selectedProperty: '', matchingMode: 'feed', feedGroup: '' };
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];

function esc(v) { return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function money(v, compact=false) {
  if (v === null || v === undefined || v === '') return '—';
  const n = Number(v);
  if (compact && n >= 10000000) return '₹' + (n/10000000).toFixed(2).replace(/\.00$/,'') + ' Cr';
  if (compact && n >= 100000) return '₹' + (n/100000).toFixed(1).replace(/\.0$/,'') + ' L';
  return '₹' + n.toLocaleString('en-IN', {maximumFractionDigits:0});
}
function dateLabel(value) {
  if (!value) return 'No due date';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString('en-IN', {day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'});
}
function badge(value) {
  const v = String(value || 'unknown').toLowerCase();
  const color = ['available','active','approved','shortlisted','closed','completed','received'].includes(v) ? 'green' :
    ['new','sale','buyer','tenant'].includes(v) ? 'blue' : ['on hold','hold','negotiation','qualifying','sent','normal','expected'].includes(v) ? 'amber' :
    ['sold','rented','lost','rejected','overdue','urgent'].includes(v) ? 'red' : 'gray';
  return `<span class="pill ${color}">${esc(v.replaceAll('_',' '))}</span>`;
}
function toast(message, bad=false) {
  const el = $('#toast'); el.textContent = message; el.style.borderColor = bad ? '#85414a' : '#3c6387';
  el.style.background = bad ? '#40252c' : '#1d354a'; el.classList.add('show');
  clearTimeout(toast._t); toast._t = setTimeout(()=>el.classList.remove('show'), 3000);
}
async function api(path, options={}) {
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
  const opts = {...options, headers: isFormData ? {...(options.headers||{})} : {'Content-Type':'application/json', ...(options.headers||{})}};
  if (options.body && typeof options.body !== 'string' && !isFormData) opts.body = JSON.stringify(options.body);
  const r = await fetch(path, opts);
  if (r.status === 204) return null;
  const type = r.headers.get('content-type') || '';
  const data = type.includes('application/json') ? await r.json() : await r.text();
  if (!r.ok) throw new Error(data?.detail || data?.message || `Request failed (${r.status})`);
  return data;
}
function setAuthScreen(mode) {
  $('#auth-screen').classList.remove('hidden'); $('#app-shell').classList.add('hidden');
  const setup = mode === 'setup';
  $('#auth-title').textContent = setup ? 'Create your workspace' : 'Welcome back';
  $('#auth-subtitle').textContent = setup ? 'Create the first administrator account. This account manages your brokerage team.' : 'Sign in to your local Property OS workspace.';
  $('#auth-fullname-wrap').classList.toggle('hidden', !setup);
  $('#auth-fullname').required = setup;
  $('#auth-password').autocomplete = setup ? 'new-password' : 'current-password';
  $('#auth-password').minLength = setup ? 10 : 1;
  $('#auth-password').placeholder = setup ? 'At least 10 characters' : '';
  $('#auth-submit').textContent = setup ? 'Create workspace' : 'Sign in';
  $('#auth-form').dataset.mode = mode;
}
async function boot() {
  try {
    try { state.user = await api('/api/me'); } catch { state.user = null; }
    if (!state.user) {
      const s = await api('/api/setup/status'); setAuthScreen(s.needs_setup ? 'setup' : 'login'); return;
    }
    $('#auth-screen').classList.add('hidden'); $('#app-shell').classList.remove('hidden');
    $('#user-name').textContent = state.user.full_name; $('#user-role').textContent = state.user.role;
    $('#user-avatar').textContent = state.user.full_name.split(/\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase();
    await loadView(state.view);
  } catch(e) { toast(e.message, true); }
}
$('#auth-form').addEventListener('submit', async e => {
  e.preventDefault(); const mode = e.currentTarget.dataset.mode;
  const payload = {username:$('#auth-username').value.trim(), password:$('#auth-password').value};
  if (mode === 'setup') { payload.full_name = $('#auth-fullname').value.trim(); }
  try { await api(mode === 'setup' ? '/api/setup' : '/api/login', {method:'POST', body:payload}); await boot(); }
  catch(err) { toast(err.message, true); }
});
$('#logout-btn').addEventListener('click', async()=>{ await api('/api/logout',{method:'POST'}); state.user=null; setAuthScreen('login'); });

const titles = {overview:'Overview', leads:'Leads & Clients', 'broker-feed':'WhatsApp Broker Feed', properties:'Verified Inventory', matching:'Property Match Engine', tasks:'Follow-ups & Tasks', projects:'Builder Projects', deals:'Deals & Negotiations', analytics:'Analytics & Reports', team:'Team', settings:'Settings'};
async function loadView(view) {
  state.view = view; state.search = ''; $('#global-search').value = ''; $('#page-crumb').textContent = titles[view] || 'Overview';
  $$('.nav-item').forEach(b=>b.classList.toggle('active', b.dataset.view===view));
  if (view==='overview') await renderOverview();
  else if (view==='leads') await renderLeads();
  else if (view==='properties') await renderProperties();
  else if (view==='broker-feed') await renderBrokerFeed();
  else if (view==='matching') await renderMatching();
  else if (view==='tasks') await renderTasks();
  else if (view==='team') await renderTeam();
  else if (view==='settings') renderSettings();
  else renderComingSoon(view);
}
$$('.nav-item').forEach(btn=>btn.addEventListener('click',()=>{loadView(btn.dataset.view); $('#sidebar').classList.remove('open');}));
$('#mobile-menu').addEventListener('click',()=>$('#sidebar').classList.toggle('open'));
$('#global-add').addEventListener('click',()=>openLeadModal());
$('#global-search').addEventListener('input', e=>{state.search=e.target.value; if(state.view==='leads') renderLeads(); if(state.view==='properties') renderProperties(); if(state.view==='tasks') renderTasks(); if(state.view==='broker-feed') renderBrokerFeed();});

function pageHead(kicker,title,desc,actions='') { return `<div class="page-head"><div><div class="section-kicker">${kicker}</div><h1>${title}</h1><p>${desc}</p></div><div class="page-head-actions">${actions}</div></div>`; }
function empty(title, desc, button='') { return `<div class="empty-state"><div class="empty-icon">⌁</div><strong>${title}</strong><p>${desc}</p>${button}</div>`; }

async function renderOverview() {
  const d = await api('/api/dashboard'); state.dashboard=d;
  const s=d.stats;
  $('#view-container').innerHTML = `${pageHead('COMMAND CENTRE','Good ' + greeting() + ', ' + esc(state.user.full_name.split(" " )[0]) + '.','Here is what is happening across your brokerage today.', '<button class="btn secondary" data-action="add-property">＋ Add Property</button><button class="btn primary" data-action="add-lead">＋ Add New Lead</button>')}
    <div class="stat-grid">
      ${stat('Active leads',s.active_leads,'↗','Across all stages', 'blue')}
      ${stat('Available properties',s.available_properties,'⌂',`${s.total_properties} total listings`, 'green')}
      ${stat('New matches',s.new_matches,'⤢','Awaiting your review', 'blue')}
      ${stat('Follow-ups due',s.open_tasks,'◷',`${s.overdue_tasks} overdue`, 'amber')}
    </div>
    <div class="dashboard-grid">
      <section class="panel"><div class="panel-head"><div><h3>Recently added leads</h3><p>Your latest client enquiries</p></div><button class="btn ghost small" data-action="go-leads">View all →</button></div>
      <div class="table-wrap">${d.recent_leads.length ? `<table class="data-table"><thead><tr><th>Client</th><th>Requirement</th><th>Priority</th><th>Status</th></tr></thead><tbody>${d.recent_leads.map(l=>`<tr><td><span class="primary-cell">${esc(l.name)}</span><span class="secondary-cell">${esc(l.lead_code)} · ${esc(l.phone||'No phone')}</span></td><td>${esc(requirementSummary(l.requirement))}</td><td>${priority(l.priority)}</td><td>${badge(l.status)}</td></tr>`).join('')}</tbody></table>`:empty('No leads yet','Add your first client enquiry to start building your pipeline.','<button class="btn primary small" data-action="add-lead">Add first lead</button>')}</div></section>
      <section class="panel"><div class="panel-head"><div><h3>Action queue</h3><p>Open follow-ups and tasks</p></div><button class="btn ghost small" data-action="go-tasks">All tasks →</button></div><div class="panel-body">${d.tasks.length?`<div class="task-list">${d.tasks.map(t=>`<div class="task-row"><button class="task-check" data-complete-task="${t.id}" title="Mark complete"></button><div><div class="task-title">${esc(t.title)}</div><div class="task-meta">${dateLabel(t.due_at)} · ${t.priority}</div></div></div>`).join('')}</div>`:empty('No pending tasks','Create a follow-up to keep your next action visible.','<button class="btn secondary small" data-action="add-task">Create task</button>')}</div></section>
    </div>
    <div class="notice" style="margin-top:16px"><strong>Broker sourcing:</strong> ${s.broker_feed_posts||0} broker posts captured · ${s.broker_feed_matches||0} live post-to-client opportunities · ${s.unreviewed_broker_posts||0} posts awaiting review. <button class="btn small secondary" data-action="go-matching">Open Property Matching →</button></div>
    <div class="notice"><strong>Workspace principle:</strong> Your data is stored locally. Manual lead entry, property management and the local matching engine work without WhatsApp connectivity or paid third-party services.</div>`;
}
function greeting(){const h=new Date().getHours();return h<12?'morning':h<17?'afternoon':'evening';}
function stat(label,value,ico,foot,color){return `<div class="stat-card"><div class="stat-top"><span>${label}</span><span class="stat-icon">${ico}</span></div><div class="stat-value">${value}</div><div class="stat-foot">${foot}</div></div>`;}
function priority(v){return `<span><i class="priority-dot ${esc(v||'normal')}"></i>${esc(v||'normal')}</span>`;}
function requirementSummary(r){if(!r)return 'Requirement not added';return `${esc(r.transaction_type)} · ${esc(r.category)} · ${esc(r.configuration||r.property_type||'Any type')} · ${r.max_budget?money(r.max_budget,true):'Budget TBD'}`;}

async function renderLeads() {
  const q=encodeURIComponent(state.search); state.leads=await api('/api/leads?q='+q);
  const rows=state.leads;
  $('#view-container').innerHTML=`${pageHead('CLIENT RELATIONSHIPS','Leads & Clients','Capture every enquiry, understand the requirement and manage the relationship.','<button class="btn secondary" data-action="export-leads">↓ Export CSV</button><button class="btn primary" data-action="add-lead">＋ Add New Lead</button>')}
    <div class="toolbar"><div class="toolbar-left"><select class="field-control" id="lead-status-filter"><option value="">All statuses</option><option>new</option><option>qualifying</option><option>active</option><option>paused</option><option>converted</option><option>lost</option></select><select class="field-control" id="lead-type-filter"><option value="">All lead types</option><option value="buyer">Buyer</option><option value="tenant">Tenant</option><option value="investor">Investor</option><option value="owner">Owner</option></select></div><div class="toolbar-right"><span class="muted" style="font-size:10px">${rows.length} records shown</span></div></div>
    <section class="panel"><div class="table-wrap"><table class="data-table"><thead><tr><th>Client / Lead ID</th><th>Requirement</th><th>Source</th><th>Assigned to</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead><tbody id="lead-rows">${leadRows(rows)}</tbody></table></div></section>`;
  $('#lead-status-filter').addEventListener('change', async e=>{const all=await api('/api/leads?status='+encodeURIComponent(e.target.value)+'&q='+encodeURIComponent(state.search)); $('#lead-rows').innerHTML=leadRows(all);});
  $('#lead-type-filter').addEventListener('change', async e=>{const all=await api('/api/leads?lead_type='+encodeURIComponent(e.target.value)+'&q='+encodeURIComponent(state.search)); $('#lead-rows').innerHTML=leadRows(all);});
}
function leadRows(rows){return rows.length?rows.map(l=>`<tr><td><span class="primary-cell">${esc(l.name)}</span><span class="secondary-cell">${esc(l.lead_code)} · ${esc(l.phone||'No phone')}</span></td><td>${esc(requirementSummary(l.requirement))}<span class="secondary-cell">${esc((l.requirement?.preferred_locations||[]).join(', ')||l.requirement?.city||'Location not set')}</span></td><td>${esc(l.source||'—')}</td><td>${esc(l.assigned_name||'Unassigned')}</td><td>${priority(l.priority)}</td><td><select class="field-control" style="height:27px;min-width:100px" data-lead-status="${l.id}">${['new','qualifying','active','paused','converted','lost'].map(x=>`<option value="${x}" ${l.status===x?'selected':''}>${x}</option>`).join('')}</select></td><td><button class="btn small secondary" data-match-lead="${l.id}">Find matches</button></td></tr>`).join(''): `<tr><td colspan="7">${empty('No leads found','Change the search or add a new lead.','<button class="btn primary small" data-action="add-lead">Add lead</button>')}</td></tr>`;}

async function renderProperties(){
  const q=encodeURIComponent(state.search);state.properties=await api('/api/properties?q='+q);
  $('#view-container').innerHTML=`${pageHead('SUPPLY DATABASE','Property Inventory','A single source of truth for residential and commercial listings.','<button class="btn secondary" data-action="export-properties">↓ Export CSV</button><button class="btn primary" data-action="add-property">＋ Add Property</button>')}
    <div class="toolbar"><div class="toolbar-left"><select id="property-status-filter" class="field-control"><option value="">All availability</option><option value="available">Available</option><option value="on_hold">On hold</option><option value="under_negotiation">Under negotiation</option><option value="sold">Sold</option><option value="rented">Rented</option><option value="archived">Archived</option></select><select id="property-category-filter" class="field-control"><option value="">All categories</option><option value="residential">Residential</option><option value="commercial">Commercial</option></select></div><div class="toolbar-right"><span class="muted" style="font-size:10px">${state.properties.length} records shown</span></div></div>
    <section class="panel"><div class="table-wrap"><table class="data-table"><thead><tr><th>Property</th><th>Type</th><th>Location</th><th>Price</th><th>Configuration / Area</th><th>Availability</th><th>Verified</th></tr></thead><tbody id="property-rows">${propertyRows(state.properties)}</tbody></table></div></section>`;
  $('#property-status-filter').addEventListener('change', async e=>{const all=await api('/api/properties?status='+encodeURIComponent(e.target.value)+'&q='+encodeURIComponent(state.search));$('#property-rows').innerHTML=propertyRows(all);});
  $('#property-category-filter').addEventListener('change', async e=>{const all=await api('/api/properties?category='+encodeURIComponent(e.target.value)+'&q='+encodeURIComponent(state.search));$('#property-rows').innerHTML=propertyRows(all);});
}
function propertyRows(rows){return rows.length?rows.map(p=>`<tr><td><span class="primary-cell">${esc(p.title)}</span><span class="secondary-cell">${esc(p.property_code)} · ${esc(p.transaction_type)}</span></td><td>${badge(p.category)}<span class="secondary-cell">${esc(p.property_type)}</span></td><td>${esc(p.locality||'—')}<span class="secondary-cell">${esc(p.city)}</span></td><td class="primary-cell">${money(p.price,true)}${p.transaction_type==='rent'?'<span class="secondary-cell">per month</span>':''}</td><td>${esc(p.bhk||'—')}<span class="secondary-cell">${p.area_sqft?Number(p.area_sqft).toLocaleString('en-IN')+' sq ft':'Area not set'}</span></td><td><select class="field-control" style="height:27px;min-width:120px" data-property-status="${p.id}">${['available','on_hold','under_negotiation','sold','rented','archived'].map(x=>`<option value="${x}" ${p.status===x?'selected':''}>${x.replaceAll('_',' ')}</option>`).join('')}</select></td><td>${p.verified_at?badge('verified'):'<span class="pill amber">Needs check</span>'}<button class="btn small ghost" data-verify-property="${p.id}">Verify now</button></td></tr>`).join(''):`<tr><td colspan="7">${empty('No properties yet','Add an available property to start matching it against your client requirements.','<button class="btn primary small" data-action="add-property">Add property</button>')}</td></tr>`;}

async function renderMatching(){
  if(state.matchingMode==='feed'){
    const [groups,posts]=await Promise.all([api('/api/broker-feed/groups'),api('/api/broker-feed/posts'+(state.feedGroup?'?group_id='+state.feedGroup:''))]);
    const matches=posts.reduce((n,p)=>n+p.match_count,0);
    const groupOptions=groups.map(g=>`<option value="${g.id}" ${String(state.feedGroup)===String(g.id)?'selected':''}>${esc(g.name)}</option>`).join('');
    $('#view-container').innerHTML=`${pageHead('PRIMARY SOURCING WORKFLOW','Property Matching','Your five broker-group feeds are compared against the requirements you entered manually. The best opportunities appear here first.','<button class="btn secondary" data-action="import-whatsapp-export">↥ Import group export</button><button class="btn primary" data-action="capture-broker-post">＋ Capture broker post</button>')}
      <div class="notice warn"><strong>Live group monitoring is not connected.</strong> This build matches locally captured posts and imported chat exports. The official WhatsApp API cannot simply attach to your existing broker groups; we are avoiding unofficial scraping that could put your personal number at risk.</div>
      <div class="stat-grid">${stat('Captured property posts',posts.length,'▤','Across your source groups','blue')}${stat('Client opportunities',matches,'⤢','Post-to-lead matches','green')}${stat('Matched posts',posts.filter(p=>p.match_count>0).length,'✓','At least one lead matched','green')}${stat('Needs review',posts.filter(p=>p.status==='needs_review').length,'!','Unclear transaction/details','amber')}</div>
      <div class="filter-tabs" style="margin-bottom:13px"><button class="tab-btn active" data-match-mode="feed">WhatsApp → Lead Matches</button><button class="tab-btn" data-match-mode="client">Verified inventory → Client</button><button class="tab-btn" data-match-mode="property">Verified property → Leads</button></div>
      <div class="toolbar"><div class="toolbar-left"><select class="field-control" id="match-feed-group"><option value="">All five groups</option>${groupOptions}</select></div><span class="muted" style="font-size:10px">Broker posts remain candidates until verified</span></div>
      <div id="match-feed-results">${posts.length?posts.map(brokerPostCard).join(''):empty('No broker opportunities yet','Capture a post or import a WhatsApp chat export. New posts are automatically compared with your active lead requirements.','<button class="btn primary small" data-action="import-whatsapp-export">Import first group export</button>')}</div>`;
    $$('[data-match-mode]').forEach(b=>b.addEventListener('click',()=>{state.matchingMode=b.dataset.matchMode;renderMatching();}));
    $('#match-feed-group').addEventListener('change',e=>{state.feedGroup=e.target.value;renderMatching();});
    return;
  }
  const [leads, properties] = await Promise.all([api('/api/leads'), api('/api/properties?status=available')]);
  state.leads=leads; state.properties=properties;
  const leadOptions=state.leads.map(l=>`<option value="${l.id}" ${String(state.selectedLead)===String(l.id)?'selected':''}>${esc(l.name)} · ${esc(l.lead_code)}</option>`).join('');
  const propertyOptions=state.properties.map(p=>`<option value="${p.id}" ${String(state.selectedProperty)===String(p.id)?'selected':''}>${esc(p.title)} · ${esc(p.property_code)} · ${money(p.price,true)}</option>`).join('');
  $('#view-container').innerHTML=`${pageHead('SECONDARY MATCHING WORKSPACE','Verified Inventory Matching','Match approved inventory records against leads, or find existing demand for a verified listing.','<button class="btn secondary" data-action="go-leads">Manage leads</button>')}
   <div class="filter-tabs" style="margin-bottom:13px"><button class="tab-btn" data-match-mode="feed">WhatsApp → Lead Matches</button><button class="tab-btn ${state.matchingMode==='client'?'active':''}" data-match-mode="client">Client → Properties</button><button class="tab-btn ${state.matchingMode==='property'?'active':''}" data-match-mode="property">Property → Clients</button></div>
   <div class="notice">This section matches verified inventory. New raw broker posts are matched in WhatsApp → Lead Matches without being added to inventory first.</div>
   <div class="match-layout"><section class="panel lead-picker"><h3>${state.matchingMode==='client'?'Select a client':'Select a property'}</h3><p>${state.matchingMode==='client'?'Find suitable inventory for a client requirement.':'Discover existing leads that fit a verified listing.'}</p>
   ${state.matchingMode==='client'?`<select class="field-control" id="match-lead-select"><option value="">Select a client</option>${leadOptions}</select>`:`<select class="field-control" id="match-property-select"><option value="">Select an available property</option>${propertyOptions}</select>`}
   <div style="height:12px"></div><button class="btn primary full" id="run-matching" ${(state.matchingMode==='client'?state.leads.length:state.properties.length)?'':'disabled'}>⤢ ${state.matchingMode==='client'?'Find compatible properties':'Find interested clients'}</button><div style="height:17px"></div><div class="section-kicker">Matching rules</div><p style="margin-top:7px">• Sale/rent must match<br>• Hard requirements are respected<br>• Missing post details are flagged<br>• Preferences influence ranking</p></section>
   <section class="panel"><div class="panel-head"><div><h3 id="match-result-title">${state.matchingMode==='client'?'Recommended properties':'Potential clients'}</h3><p id="match-caption">Select a record and run matching.</p></div><span class="pill blue" id="match-count">0 results</span></div><div class="panel-body" id="match-results">${empty('Ready to match',state.matchingMode==='client'?'Choose a client on the left and run the matching engine.':'Choose a property on the left and find compatible leads.')}</div></section></div>`;
  $$('[data-match-mode]').forEach(b=>b.addEventListener('click',()=>{state.matchingMode=b.dataset.matchMode;renderMatching();}));
  $('#run-matching').addEventListener('click',state.matchingMode==='client'?runMatching:runReverseMatching);
  if(state.matchingMode==='client') $('#match-lead-select').addEventListener('change',e=>state.selectedLead=e.target.value);
  else $('#match-property-select').addEventListener('change',e=>state.selectedProperty=e.target.value);
  if(state.matchingMode==='client'&&state.selectedLead)runMatching();
  if(state.matchingMode==='property'&&state.selectedProperty)runReverseMatching();
}
async function runMatching(){
  const id=$('#match-lead-select').value;if(!id){toast('Select a client first',true);return;}state.selectedLead=id;
  const box=$('#match-results');box.innerHTML='<div class="empty-state">Calculating compatibility…</div>';
  try{const matches=await api('/api/matches?lead_id='+id);$('#match-count').textContent=matches.length+' results';$('#match-caption').textContent='Ranked by compatibility. Review the reasons before sharing.';
    box.innerHTML=matches.length?matches.map(m=>`<article class="match-card"><div class="match-card-top"><div><h4>${esc(m.property.title)}</h4><div class="match-code">${esc(m.property.property_code)} · ${esc(m.property.locality||m.property.city)} · ${money(m.property.price,true)}${m.property.transaction_type==='rent'?'/mo':''}</div></div><div class="score">${m.score}<small>/100</small></div></div><div class="reason-list">${m.reasons.map(r=>`<span class="reason">${esc(r)}</span>`).join('')}</div><div class="match-card-top"><div>${badge(m.status)} <span class="muted" style="font-size:9px">${esc(m.property.category)} · ${esc(m.property.property_type)}</span></div><div class="match-actions"><button class="btn small secondary" data-match-status="${m.id}" data-status="shortlisted">Shortlist</button><button class="btn small primary" data-match-status="${m.id}" data-status="approved">Approve</button></div></div></article>`).join('') : empty('No current matches','No available listing passed the current hard filters. Try relaxing a non-essential requirement or add inventory.');
  }catch(e){box.innerHTML=empty('Could not calculate matches',esc(e.message));}
}
async function runReverseMatching(){
  const id=$('#match-property-select').value;if(!id){toast('Select a property first',true);return;}state.selectedProperty=id;
  const box=$('#match-results');box.innerHTML='<div class="empty-state">Searching existing demand…</div>';
  try{const matches=await api('/api/matches/by-property?property_id='+id);$('#match-count').textContent=matches.length+' results';$('#match-caption').textContent='Existing leads ranked by compatibility with this listing.';
    box.innerHTML=matches.length?matches.map(m=>`<article class="match-card"><div class="match-card-top"><div><h4>${esc(m.lead.name)}</h4><div class="match-code">${esc(m.lead.lead_code)} · ${esc(m.lead.lead_type)} · ${esc(m.lead.phone||'No phone')}</div></div><div class="score">${m.score}<small>/100</small></div></div><div class="reason-list">${m.reasons.map(r=>`<span class="reason">${esc(r)}</span>`).join('')}</div><div class="match-card-top"><div>${badge(m.status)} ${badge(m.lead.status)}</div><div class="match-actions"><button class="btn small secondary" data-match-status="${m.id}" data-status="shortlisted">Shortlist</button><button class="btn small primary" data-match-status="${m.id}" data-status="approved">Approve</button></div></div></article>`).join('') : empty('No compatible leads found','No active client requirement passed the current hard filters.');
  }catch(e){box.innerHTML=empty('Could not calculate matches',esc(e.message));}
}


async function renderBrokerFeed(){
  const [groups, posts] = await Promise.all([api('/api/broker-feed/groups'), api('/api/broker-feed/posts'+(state.feedGroup?'?group_id='+state.feedGroup:''))]);
  const selectedGroup = state.feedGroup || '';
  const matchedPosts = posts.filter(p=>p.match_count>0).length;
  const groupOptions = groups.map(g=>`<option value="${g.id}" ${String(selectedGroup)===String(g.id)?'selected':''}>${esc(g.name)} · ${g.post_count} posts</option>`).join('');
  $('#view-container').innerHTML = `${pageHead('SUPPLY NETWORK','WhatsApp Broker Feed','Capture broker posts from your five groups, extract property details and match them directly against your saved client requirements.','<button class="btn secondary" data-action="import-whatsapp-export">↥ Import WhatsApp export</button><button class="btn primary" data-action="capture-broker-post">＋ Capture post</button>')}
    <div class="notice warn"><strong>Live group monitoring is not connected.</strong> This workspace currently supports local post capture and WhatsApp .txt export imports. Meta's official API does not provide a supported way to silently monitor your existing broker groups; we will not risk your personal WhatsApp number with an unofficial scraper. See the integration note in the project documentation.</div>
    <div class="stat-grid">
      ${stat('Captured posts',posts.length,'▤','Broker messages in this view','blue')}
      ${stat('Posts with matches',matchedPosts,'⤢','At least one compatible client','green')}
      ${stat('Needs review',posts.filter(p=>p.status==='needs_review').length,'!','Missing or unclear details','amber')}
      ${stat('Configured groups',groups.filter(g=>g.is_active).length,'◉','Five source slots','blue')}
    </div>
    <section class="panel" style="margin-bottom:15px"><div class="panel-head"><div><h3>Your source groups</h3><p>Rename these five source slots to match your actual WhatsApp groups.</p></div><span class="pill blue">Local configuration</span></div><div class="panel-body"><div class="group-chip-grid">${groups.map(g=>`<div class="group-chip"><div><strong>${esc(g.name)}</strong><small>${g.post_count} captured posts · ${g.is_active?'Active':'Paused'}</small></div><button class="btn small ghost" data-edit-feed-group="${g.id}" data-group-name="${esc(g.name)}">Rename</button></div>`).join('')}</div></div></section>
    <div class="toolbar"><div class="toolbar-left"><select class="field-control" id="feed-group-filter"><option value="">All five groups</option>${groupOptions}</select><select class="field-control" id="feed-status-filter"><option value="">All post statuses</option><option value="matched">Matched</option><option value="needs_review">Needs review</option><option value="parsed">Parsed · no client match</option><option value="reviewed">Reviewed</option><option value="ignored">Ignored</option></select></div><span class="muted" style="font-size:10px">Newest captured opportunities first</span></div>
    <div id="broker-post-list">${posts.length?posts.map(brokerPostCard).join(''):empty('No broker posts captured yet','Start by capturing a message or importing a WhatsApp chat export from one of your five groups.','<button class="btn primary small" data-action="capture-broker-post">Capture first post</button>')}</div>`;
  $('#feed-group-filter').addEventListener('change',e=>{state.feedGroup=e.target.value;renderBrokerFeed();});
  $('#feed-status-filter').addEventListener('change',async e=>{const params=new URLSearchParams();if(state.feedGroup)params.set('group_id',state.feedGroup);if(e.target.value)params.set('status',e.target.value);const rows=await api('/api/broker-feed/posts?'+params.toString());$('#broker-post-list').innerHTML=rows.length?rows.map(brokerPostCard).join(''):empty('No posts in this filter','Try another group or status filter.');});
}
function brokerPostCard(p){
  const x=p.parsed_data||{};
  const details=[x.transaction_type, x.category, x.property_type, x.configuration, x.locality, x.price?money(x.price,true):null, x.area_sqft?Number(x.area_sqft).toLocaleString('en-IN')+' sq ft':null].filter(Boolean).join(' · ');
  const attachments=(p.attachments||[]).map((a,i)=>a.content_type?.startsWith('image/')?`<a class="feed-image-link" href="/api/broker-feed/posts/${p.id}/attachments/${i}" target="_blank"><img class="feed-image-thumb" src="/api/broker-feed/posts/${p.id}/attachments/${i}" alt="Broker property image"><small>${esc(a.filename||'Image')}</small></a>`:`<a class="attachment-link" href="/api/broker-feed/posts/${p.id}/attachments/${i}" target="_blank">▧ ${esc(a.filename||'Attachment')}</a>`).join('');
  const ocrBlock=p.ocr_text?`<details class="feed-ocr-details"><summary>Locally extracted image/PDF text</summary><div class="feed-ocr-text">${esc(p.ocr_text)}</div></details>`:(p.ocr_status&&p.ocr_status!=='pending'?`<small class="feed-ocr-status">Local OCR: ${esc(p.ocr_status.replaceAll('_',' '))}${p.ocr_detail?' · '+esc(p.ocr_detail):''}</small>`:'');
  const matches=(p.matches||[]).map(m=>`<div class="feed-match-row"><div class="feed-match-main"><strong>${esc(m.lead.name)}</strong><small>${esc(m.lead.lead_code)} · ${esc(m.lead.phone||'No phone')} · ${esc(m.lead.lead_type)}</small><span>${(m.reasons||[]).slice(0,3).map(esc).join(' · ')}</span></div><div class="feed-match-score">${m.score}<small>/100</small></div><div class="feed-match-actions">${badge(m.status)}<button class="btn small ghost" data-feed-match-status="${m.id}" data-status="shortlisted">Shortlist</button><button class="btn small secondary" data-feed-match-status="${m.id}" data-status="contacted">Contacted</button><button class="btn small ghost danger-text" data-feed-match-status="${m.id}" data-status="rejected">Reject</button></div></div>`).join('');
  return `<article class="feed-post-card"><div class="feed-post-head"><div><div class="feed-post-source">${esc(p.group_name)} · ${esc(p.sender_name||'Unknown sender')} ${(p.sender_phone||p.broker_phone_candidates?.[0])?'· '+esc(p.sender_phone||p.broker_phone_candidates[0]):''}</div><h3>${esc(x.title||'Broker property post')}</h3><div class="feed-post-meta">${dateLabel(p.received_at||p.created_at)} · ${esc(p.source_type.replaceAll('_',' '))} · extraction confidence ${p.parse_confidence}%</div></div><div class="feed-post-status">${badge(p.status)}<strong>${p.match_count} client matches</strong></div></div>
    <div class="feed-raw-text">${esc(p.raw_text)}</div>
    ${attachments?`<div class="feed-attachments">${attachments}</div>`:''}
    <div class="feed-extracted"><div class="section-kicker">EXTRACTED DETAILS · VERIFY BEFORE CONTACTING</div><div class="feed-extracted-line">${esc(details||'Not enough structured details extracted yet')}</div>${p.parse_notes?`<small>${esc(p.parse_notes)}</small>`:''}${ocrBlock}</div>
    ${matches?`<div class="feed-matches"><div class="section-kicker">MATCHED CLIENT REQUIREMENTS</div>${matches}</div>`:`<div class="feed-no-match">${p.status==='needs_review'?'More information is needed before reliable matching.':'No active client requirement matched this post yet.'}</div>`}
    <div class="feed-post-actions"><button class="btn small secondary" data-action="reprocess-feed-post" data-post-id="${p.id}">Re-extract & re-match</button>${p.status!=='reviewed'?`<button class="btn small ghost" data-feed-post-status="${p.id}" data-status="reviewed">Mark reviewed</button>`:''}<button class="btn small ghost danger-text" data-feed-post-status="${p.id}" data-status="ignored">Ignore post</button></div>
  </article>`;
}
function openBrokerPostModal(){
  api('/api/broker-feed/groups').then(groups=>{
    const options=groups.filter(g=>g.is_active).map(g=>[String(g.id),g.name]);
    const body=`<div class="form-grid">${selectField('Source WhatsApp group','feed_group_id',options,options[0]?.[0]||'')}${field('Broker / sender name','feed_sender','Optional')}${field('Broker phone number','feed_phone','Optional','tel')}${areaField('Paste broker property message *','feed_raw_text','Paste the complete WhatsApp message here. Preserve price, location, configuration and broker contact details.')}</div><div class="form-field" style="margin-top:12px"><label for="feed_attachments">Property photos / PDF (optional)</label><input id="feed_attachments" type="file" multiple accept="image/jpeg,image/png,image/webp,image/gif,image/heic,image/tiff,application/pdf"><small class="field-hint">Files stay on this Mac. On macOS with the free Swift command-line tools installed, Property OS runs Apple Vision OCR locally and re-matches the extracted text.</small></div>`;
    openModal('Capture broker post','Save the raw post first; the local parser extracts fields and searches your existing lead requirements.',body,'Capture and match');
    $('#modal-form').addEventListener('submit',async e=>{e.preventDefault();const files=[...($('#feed_attachments').files||[])];const raw=$('#feed_raw_text').value.trim()||(files.length?'Photo-only broker post; property details are in the attached media.':'');if(raw.length<3){toast('Paste the broker message or attach at least one photo/PDF',true);return;}try{const post=await api('/api/broker-feed/posts',{method:'POST',body:{group_id:Number($('#feed_group_id').value),sender_name:$('#feed_sender').value,sender_phone:$('#feed_phone').value,raw_text:raw}});if(files.length){const fd=new FormData();files.forEach(f=>fd.append('files',f));await api(`/api/broker-feed/posts/${post.id}/attachments`,{method:'POST',body:fd});}closeModal();toast(post.duplicate?'This message was already captured':'Broker post captured, extracted and matched');renderBrokerFeed();}catch(err){toast(err.message,true);}});
  }).catch(e=>toast(e.message,true));
}
function openWhatsAppExportModal(){
  api('/api/broker-feed/groups').then(groups=>{
    const options=groups.filter(g=>g.is_active).map(g=>[String(g.id),g.name]);
    const body=`<div class="form-grid">${selectField('WhatsApp group','export_group_id',options,options[0]?.[0]||'')}<div class="form-field"><label for="whatsapp_export_file">WhatsApp exported chat (.txt)</label><input id="whatsapp_export_file" type="file" accept=".txt,.zip,text/plain,application/zip" required><small class="field-hint">Export chat → Without media (.txt) or Include media (.zip). ZIP exports can attach matching images/PDFs to their original messages.</small></div></div><div class="notice" style="margin-top:12px">The importer filters ordinary chat/system messages, keeps photo-only messages when their media is present in the ZIP, attaches referenced images/PDFs, runs optional on-device macOS Vision OCR, then matches extracted candidates against active saved requirements. The original broker message is preserved.</div>`;
    openModal('Import WhatsApp chat export','A zero-subscription way to bring messages and exported media from an existing group into the local broker feed.',body,'Import property posts',false);
    $('#modal-form').addEventListener('submit',async e=>{e.preventDefault();const file=$('#whatsapp_export_file').files[0];if(!file){toast('Choose a .txt export first',true);return;}const fd=new FormData();fd.append('group_id',$('#export_group_id').value);fd.append('file',file);try{const result=await api('/api/broker-feed/import-export',{method:'POST',body:fd});closeModal();toast(`Imported ${result.imported} posts · ${result.duplicates} duplicates · ${result.skipped_demand||0} requirements skipped · ${result.multi_listing_messages_split||0} bulk messages split`);state.feedGroup=$('#feed-group-filter')?.value||'';renderBrokerFeed();}catch(err){toast(err.message,true);}});
  }).catch(e=>toast(e.message,true));
}

async function renderTasks(){state.tasks=await api('/api/tasks');const list=state.tasks.filter(t=>!state.search||t.title.toLowerCase().includes(state.search.toLowerCase()));
  $('#view-container').innerHTML=`${pageHead('DAILY OPERATIONS','Follow-ups & Tasks','Keep every call, reminder and next action visible.','<button class="btn primary" data-action="add-task">＋ Create Task</button>')}
  <div class="toolbar"><div class="filter-tabs"><button class="tab-btn active" data-task-filter="all">All tasks</button><button class="tab-btn" data-task-filter="open">Open</button><button class="tab-btn" data-task-filter="completed">Completed</button></div><span class="muted" style="font-size:10px">${list.length} records</span></div>
  <section class="panel"><div class="table-wrap"><table class="data-table"><thead><tr><th>Task</th><th>Due</th><th>Priority</th><th>Linked lead</th><th>Status</th><th>Action</th></tr></thead><tbody id="task-rows">${taskRows(list)}</tbody></table></div></section>`;
  $$('[data-task-filter]').forEach(b=>b.addEventListener('click',()=>{$$('[data-task-filter]').forEach(x=>x.classList.toggle('active',x===b));const f=b.dataset.taskFilter;$('#task-rows').innerHTML=taskRows(list.filter(t=>f==='all'||t.status===f));}));
}
function taskRows(rows){return rows.length?rows.map(t=>`<tr><td><span class="primary-cell">${esc(t.title)}</span><span class="secondary-cell">${esc(t.description||'')}</span></td><td>${dateLabel(t.due_at)}</td><td>${priority(t.priority)}</td><td>${t.lead_id?'Lead #'+t.lead_id:'—'}</td><td>${badge(t.status)}</td><td>${t.status==='open'?`<button class="btn small secondary" data-complete-task="${t.id}">Mark done</button>`:'—'}</td></tr>`).join(''):`<tr><td colspan="6">${empty('Nothing in this view','Create a task or change the selected filter.','<button class="btn primary small" data-action="add-task">Create task</button>')}</td></tr>`;}

async function renderTeam(){const users=await api('/api/users');$('#view-container').innerHTML=`${pageHead('WORKSPACE ACCESS','Team','Manage the small brokerage team using this local workspace.',state.user.role==='admin'?'<button class="btn primary" data-action="add-user">＋ Add Team Member</button>':'')}
  <div class="notice">Team access is available on the same trusted local network when the server is configured to bind to 0.0.0.0. Each person signs in with their own account. This first version has admin, manager and agent roles; fine-grained permissions are planned.</div>
  <section class="panel"><div class="panel-head"><div><h3>Workspace members</h3><p>${users.length} user accounts</p></div></div><div class="panel-body">${users.map(u=>`<div class="team-row"><div class="team-id"><div class="avatar">${esc(u.full_name.split(/\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase())}</div><div><strong>${esc(u.full_name)}</strong><small>@${esc(u.username)}</small></div></div><div>${badge(u.role)} ${u.is_active?badge('active'):badge('disabled')}</div></div>`).join('')}</div></section>`;}
function renderSettings(){$('#view-container').innerHTML=`${pageHead('PREFERENCES & DATA','Settings','Local workspace configuration, data portability and cost policy.')}
  <div class="settings-grid"><section class="panel setting-card"><h3>Data portability</h3><p>Download your business records in open CSV format. Database backup tooling is included with the project.</p><div class="toolbar-left"><a class="btn secondary" href="/api/export/leads.csv">↓ Leads CSV</a><a class="btn secondary" href="/api/export/properties.csv">↓ Properties CSV</a></div></section>
  <section class="panel setting-card"><h3>Local-first storage</h3><p>SQLite database stored in the project's <code>data/</code> directory. No remote database is required.</p><span class="pill green">Enabled</span></section>
  <section class="panel setting-card"><h3>Lifetime-free policy</h3><p>No paid API, subscription, cloud hosting, paid AI model or usage-based dependency is required for core workflows.</p><span class="pill green">Core app: no recurring service fees</span></section>
  <section class="panel setting-card"><h3>Optional integrations</h3><p>WhatsApp and external messaging are deliberately decoupled. Third-party pricing or access can change, so no integration is mandatory.</p><span class="pill amber">Not connected in this foundation</span></section></div>`;}
function renderComingSoon(view){const descriptions={projects:'Builder and developer projects, configuration-wise inventory, RERA references and channel-partner commissions.',deals:'A transaction pipeline from negotiation to closure, with agreed and received commission tracking.',analytics:'Lead-source conversion, inventory performance, locality demand, agent activity and commission reports.'};$('#view-container').innerHTML=`${pageHead('PRODUCT ROADMAP',titles[view],descriptions[view]||'Planned module.')}
  <section class="panel coming-soon"><div><div class="icon">◇</div><h3>Designed into the architecture</h3><p>This module is in the V2 roadmap. The underlying data model is being prepared, but this screen is intentionally not presented as a completed feature.</p><div style="margin-top:15px"><span class="pill amber">Planned module</span></div></div></section>`;}

function openModal(title,subtitle,body,submitLabel='Save record',wide=true){
 const root=$('#modal-root');root.innerHTML=`<div class="modal-backdrop" data-close-backdrop><div class="modal ${wide?'wide':''}" role="dialog" aria-modal="true"><div class="modal-head"><div><h2>${title}</h2><p>${subtitle}</p></div><button class="icon-button" data-close-modal aria-label="Close">✕</button></div><form id="modal-form"><div class="modal-body">${body}</div><div class="modal-foot"><button type="button" class="btn secondary" data-close-modal>Cancel</button><button type="submit" class="btn primary">${submitLabel}</button></div></form></div></div>`;
 root.querySelectorAll('[data-close-modal]').forEach(b=>b.addEventListener('click',closeModal));root.querySelector('[data-close-backdrop]').addEventListener('click',e=>{if(e.target===e.currentTarget)closeModal();});
}
function closeModal(){$('#modal-root').innerHTML='';}
function field(label,id,placeholder='',type='text',extra=''){return `<div class="form-field"><label for="${id}">${label}</label><input id="${id}" name="${id}" type="${type}" placeholder="${placeholder}" ${extra}></div>`;}
function selectField(label,id,opts,selected=''){return `<div class="form-field"><label for="${id}">${label}</label><select id="${id}" name="${id}">${opts.map(([v,l])=>`<option value="${v}" ${v===selected?'selected':''}>${l}</option>`).join('')}</select></div>`;}
function areaField(label,id,placeholder=''){return `<div class="form-field full-span"><label for="${id}">${label}</label><textarea id="${id}" name="${id}" placeholder="${placeholder}"></textarea></div>`;}
function openLeadModal(){
 const body=`<div class="form-section"><h4>01 · Contact information</h4><div class="form-grid">${field('Full name *','name','Client name','text','required')}${field('Phone number','phone','+91…','tel')}${field('Email','email','name@example.com','email')}${field('Company','company','Company name')}</div></div>
 <div class="form-section"><h4>02 · Lead classification</h4><div class="form-grid three">${selectField('Lead type','lead_type',[['buyer','Buyer'],['tenant','Tenant'],['investor','Investor'],['owner','Owner']],'buyer')}${selectField('Transaction','transaction_type',[['sale','Purchase / Sale'],['rent','Rental']],'sale')}${selectField('Property category','category',[['residential','Residential'],['commercial','Commercial']],'residential')}${selectField('Lead status','status',[['new','New'],['qualifying','Qualifying'],['active','Active'],['paused','Paused']],'new')}${selectField('Priority','priority',[['low','Low'],['normal','Normal'],['high','High'],['urgent','Urgent']],'normal')}${field('Lead source','source','Referral, portal, walk-in…')}</div></div>
 <div class="form-section"><h4>03 · Property requirement</h4><div class="form-grid">${field('Property type','property_type','Apartment, office, shop, plot…')}${field('City','city','Ahmedabad','text','value="Ahmedabad"')}${field('Preferred localities','preferred_locations','South Bopal, Shela, SG Highway…')}${field('Configuration','configuration','3 BHK / 1200 sq ft office…')}${field('Minimum budget (₹)','min_budget','e.g. 5000000','number','min="0"')}${field('Maximum budget (₹)','max_budget','e.g. 7500000','number','min="0"')}${field('Stretch budget (₹)','stretch_budget','Optional absolute ceiling','number','min="0"')}${field('Minimum area (sq ft)','min_area_sqft','Optional','number','min="0"')}${field('Maximum area (sq ft)','max_area_sqft','Optional','number','min="0"')}${selectField('Furnishing','furnishing',[['','No preference'],['unfurnished','Unfurnished'],['semi-furnished','Semi-furnished'],['furnished','Furnished']])}${selectField('Parking required?','parking_required',[['','No preference'],['true','Yes'],['false','No']])}${selectField('Timeline','move_timeline',[['','Not specified'],['immediate','Immediate'],['30_days','Within 30 days'],['3_months','Within 3 months'],['6_months','Within 6 months'],['flexible','Flexible']])}${field('Amenities (comma-separated)','amenities','Gym, lift, security, power backup…')}</div><div style="display:flex;gap:18px;margin-top:12px;flex-wrap:wrap"><label class="check-line"><input type="checkbox" id="strict_location"> Location is mandatory</label><label class="check-line"><input type="checkbox" id="strict_configuration"> Configuration is mandatory</label></div></div>
 <div class="form-section"><h4>04 · Assignment & notes</h4><div class="form-grid">${areaField('Internal notes','notes','Context, budget flexibility, decision-maker, preferences…')}${areaField('Requirement notes','requirement_notes','Must-haves and additional details…')}</div></div>`;
 openModal('Add new lead','Manual entry is always available. Incomplete requirements can be updated later.',body,'Save lead');
 $('#modal-form').addEventListener('submit',async e=>{e.preventDefault();const val=id=>$('#'+id)?.value||'';const num=id=>val(id)===''?null:Number(val(id));
 const payload={name:val('name').trim(),phone:val('phone'),email:val('email'),company:val('company'),lead_type:val('lead_type'),status:val('status'),priority:val('priority'),source:val('source'),transaction_type:val('transaction_type'),category:val('category'),property_type:val('property_type')||null,city:val('city'),preferred_locations:val('preferred_locations').split(',').map(x=>x.trim()).filter(Boolean),min_budget:num('min_budget'),max_budget:num('max_budget'),stretch_budget:num('stretch_budget'),configuration:val('configuration')||null,min_area_sqft:num('min_area_sqft'),max_area_sqft:num('max_area_sqft'),furnishing:val('furnishing')||null,parking_required:val('parking_required')===''?null:val('parking_required')==='true',move_timeline:val('move_timeline')||null,amenities:val('amenities').split(',').map(x=>x.trim()).filter(Boolean),strict_location:$('#strict_location').checked,strict_configuration:$('#strict_configuration').checked,notes:val('notes'),requirement_notes:val('requirement_notes')};
 try{await api('/api/leads',{method:'POST',body:payload});closeModal();toast('Lead saved successfully');if(state.view==='leads')renderLeads();else loadView('overview');}catch(err){toast(err.message,true);}
 });
}
function openPropertyModal(){const body=`<div class="form-section"><h4>01 · Listing details</h4><div class="form-grid">${field('Listing title *','title','3 BHK apartment in South Bopal','text','required')}${selectField('Transaction','transaction_type',[['sale','For sale'],['rent','For rent']],'sale')}${selectField('Category','category',[['residential','Residential'],['commercial','Commercial']],'residential')}${field('Property type *','property_type','Apartment, villa, office, shop…','text','required')}${field('City','city','Ahmedabad','text','value="Ahmedabad"')}${field('Locality','locality','South Bopal')}${field('Full address','address','Building, road, landmark')}${field('Price / monthly rent (₹) *','price','e.g. 7200000','number','required min="1"')}${field('Configuration','bhk','3 BHK / 1200 sq ft office')}${field('Area (sq ft)','area_sqft','1650','number','min="0"')}${selectField('Furnishing','furnishing',[['','Not specified'],['unfurnished','Unfurnished'],['semi-furnished','Semi-furnished'],['furnished','Furnished']])}${field('Floor','floor','7th floor')}${selectField('Parking','parking',[['','Not specified'],['true','Available'],['false','Not available']])}${field('Amenities (comma-separated)','amenities','Lift, gym, security…')}</div></div>
 <div class="form-section"><h4>02 · Sourcing & ownership</h4><div class="form-grid">${selectField('Listing source','source_type',[['direct','Direct owner'],['broker','Broker'],['builder','Builder'],['portal','Property portal'],['network','Network / referral']])}${selectField('Availability','status',[['available','Available'],['on_hold','On hold'],['under_negotiation','Under negotiation'],['sold','Sold'],['rented','Rented'],['archived','Archived']],'available')}${field('Owner name','owner_name','Owner / landlord')}${field('Owner phone','owner_phone','+91…','tel')}${field('Source broker name','source_name','Broker / channel partner')}${field('Source broker phone','source_phone','+91…','tel')}${field('Expected commission (₹)','asking_commission','Optional','number','min="0"')}</div></div>
 <div class="form-section"><h4>03 · Internal information</h4><div class="form-grid">${areaField('Private notes','notes','Verification notes, negotiation context, source reliability…')}</div></div>`;
 openModal('Add property','Store residential or commercial supply in your central inventory.',body,'Save property');
 $('#modal-form').addEventListener('submit',async e=>{e.preventDefault();const val=id=>$('#'+id)?.value||'';const num=id=>val(id)===''?null:Number(val(id));const payload={title:val('title'),transaction_type:val('transaction_type'),category:val('category'),property_type:val('property_type'),city:val('city'),locality:val('locality'),address:val('address'),price:num('price'),bhk:val('bhk'),area_sqft:num('area_sqft'),furnishing:val('furnishing')||null,floor:val('floor'),parking:val('parking')===''?null:val('parking')==='true',amenities:val('amenities').split(',').map(x=>x.trim()).filter(Boolean),source_type:val('source_type'),status:val('status'),owner_name:val('owner_name'),owner_phone:val('owner_phone'),source_name:val('source_name'),source_phone:val('source_phone'),asking_commission:num('asking_commission'),notes:val('notes')};
 try{await api('/api/properties',{method:'POST',body:payload});closeModal();toast('Property added to inventory');if(state.view==='properties')renderProperties();else loadView('overview');}catch(err){toast(err.message,true);}
 });}
function openTaskModal(){const leadOptions=state.leads.length?state.leads.map(l=>`<option value="${l.id}">${esc(l.name)} · ${esc(l.lead_code)}</option>`).join(''):'';const body=`<div class="form-grid">${field('Task title *','task_title','Call client, verify listing…','text','required')}${field('Due date & time','due_at','','datetime-local')}${selectField('Priority','task_priority',[['low','Low'],['normal','Normal'],['high','High'],['urgent','Urgent']],'normal')}<div class="form-field"><label for="task_lead">Link to lead (optional)</label><select id="task_lead" class="field-control"><option value="">No linked lead</option>${leadOptions}</select></div>${areaField('Description','task_description','What needs to happen?')}</div>`;
 openModal('Create follow-up task','Make the next action visible and assignable.',body,'Create task',false);
 $('#modal-form').addEventListener('submit',async e=>{e.preventDefault();const due=$('#due_at').value;const payload={title:$('#task_title').value,description:$('#task_description').value,priority:$('#task_priority').value,lead_id:$('#task_lead').value?Number($('#task_lead').value):null,due_at:due?new Date(due).toISOString():null};try{await api('/api/tasks',{method:'POST',body:payload});closeModal();toast('Task created');if(state.view==='tasks')renderTasks();else loadView('overview');}catch(err){toast(err.message,true);}});}
function openUserModal(){const body=`<div class="form-grid">${field('Full name *','new_full_name','Team member','text','required')}${field('Username *','new_username','username','text','required minlength="3"')}${field('Temporary password *','new_password','At least 10 characters','password','required minlength="10"')}${selectField('Role','new_role',[['agent','Agent'],['manager','Manager']],'agent')}</div>`;openModal('Add team member','Create an individual sign-in for a colleague.',body,'Create account',false);$('#modal-form').addEventListener('submit',async e=>{e.preventDefault();try{await api('/api/users',{method:'POST',body:{full_name:$('#new_full_name').value,username:$('#new_username').value,password:$('#new_password').value,role:$('#new_role').value}});closeModal();toast('Team member created');renderTeam();}catch(err){toast(err.message,true);}});}

$('#view-container').addEventListener('click',async e=>{
 const act=e.target.closest('[data-action]')?.dataset.action;
 const editGroup=e.target.closest('[data-edit-feed-group]');if(editGroup){const next=prompt('Rename this source group:',editGroup.dataset.groupName);if(next&&next.trim()){try{await api('/api/broker-feed/groups/'+editGroup.dataset.editFeedGroup,{method:'PATCH',body:{name:next.trim()}});toast('Group renamed');renderBrokerFeed();}catch(err){toast(err.message,true);}}}
 const reprocess=e.target.closest('[data-post-id]');if(reprocess&&reprocess.dataset.action==='reprocess-feed-post'){try{await api('/api/broker-feed/posts/'+reprocess.dataset.postId+'/reprocess',{method:'POST'});toast('Post re-extracted and matches refreshed');renderBrokerFeed();}catch(err){toast(err.message,true);}}
 const feedPostStatus=e.target.closest('[data-feed-post-status]');if(feedPostStatus){try{await api('/api/broker-feed/posts/'+feedPostStatus.dataset.feedPostStatus,{method:'PATCH',body:{status:feedPostStatus.dataset.status}});toast('Broker post updated');renderBrokerFeed();}catch(err){toast(err.message,true);}}
 const feedMatchStatus=e.target.closest('[data-feed-match-status]');if(feedMatchStatus){try{await api('/api/broker-feed/matches/'+feedMatchStatus.dataset.feedMatchStatus,{method:'PATCH',body:{status:feedMatchStatus.dataset.status}});toast('Lead opportunity updated');renderBrokerFeed();}catch(err){toast(err.message,true);}}

 if(act==='add-lead')openLeadModal(); if(act==='add-property')openPropertyModal();if(act==='add-task')openTaskModal();if(act==='add-user')openUserModal();if(act==='capture-broker-post')openBrokerPostModal();if(act==='import-whatsapp-export')openWhatsAppExportModal();
 if(act==='go-leads')loadView('leads');if(act==='go-tasks')loadView('tasks');if(act==='go-matching'){state.matchingMode='feed';loadView('matching');}
 if(act==='export-leads')location.href='/api/export/leads.csv';if(act==='export-properties')location.href='/api/export/properties.csv';
 const matchBtn=e.target.closest('[data-match-lead]');if(matchBtn){state.selectedLead=matchBtn.dataset.matchLead;await loadView('matching');}
 const taskBtn=e.target.closest('[data-complete-task]');if(taskBtn){try{await api('/api/tasks/'+taskBtn.dataset.completeTask,{method:'PATCH',body:{status:'completed'}});toast('Task completed');loadView(state.view);}catch(err){toast(err.message,true);}}
 const verify=e.target.closest('[data-verify-property]');if(verify){try{await api('/api/properties/'+verify.dataset.verifyProperty,{method:'PATCH',body:{verified:true}});toast('Listing verification date updated');renderProperties();}catch(err){toast(err.message,true);}}
 const matchAction=e.target.closest('[data-match-status]');if(matchAction){try{await api('/api/matches/'+matchAction.dataset.matchStatus,{method:'PATCH',body:{status:matchAction.dataset.status}});toast('Match updated');runMatching();}catch(err){toast(err.message,true);}}
});
$('#view-container').addEventListener('change',async e=>{
 const lead=e.target.closest('[data-lead-status]');if(lead){try{await api('/api/leads/'+lead.dataset.leadStatus,{method:'PATCH',body:{status:lead.value}});toast('Lead status updated');}catch(err){toast(err.message,true);}}
 const prop=e.target.closest('[data-property-status]');if(prop){try{await api('/api/properties/'+prop.dataset.propertyStatus,{method:'PATCH',body:{status:prop.value}});toast('Property availability updated');}catch(err){toast(err.message,true);}}
});

// Keyboard shortcuts: N opens manual lead entry; Cmd/Ctrl+K focuses section search.
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('#global-search').focus();}if(!e.metaKey&&!e.ctrlKey&&e.key.toLowerCase()==='n'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)&&!$('#app-shell').classList.contains('hidden')){e.preventDefault();openLeadModal();}if(e.key==='Escape')closeModal();});
boot();