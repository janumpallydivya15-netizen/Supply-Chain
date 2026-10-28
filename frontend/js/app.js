/**
 * Supply Chain Disruption Command Center
 * Phase 3: Client-Side Dashboard Controller, SQLite Recovery Plan Management, & Human Approval
 */

// Application State
const state = {
  activeSection: 'overview',
  metrics: null,
  shipments: [],
  disruptions: [],
  inventory: [],
  recoveryPlans: [],
  auditEvents: [],
  auditTotal: 0,
  auditPage: 1,
  auditPages: 1,
  auditLimit: 15,
  auditFilters: {
    eventType: '',
    shipmentId: '',
    search: ''
  },
  selectedDisruption: null,
  latestAnalysis: null,
  currentStatusFilter: 'All',
  isLoading: false,
  isAnalyzing: false
};

// API Base configuration
const API_ENDPOINTS = {
  health: '/api/health',
  dashboard: '/api/dashboard',
  shipments: '/api/shipments',
  disruptions: '/api/disruptions',
  inventory: '/api/inventory',
  analyze: '/api/analyze-disruption',
  recoveryPlans: '/api/recovery-plans',
  auditEvents: '/api/audit-events'
};

// DOM Elements Cache
const elements = {
  // Navigation
  navItems: document.querySelectorAll('.sidebar-nav .nav-item'),
  sidebar: document.getElementById('sidebar'),
  sidebarToggleBtn: document.getElementById('sidebarToggleBtn'),
  sidebarCloseBtn: document.getElementById('sidebarCloseBtn'),
  pageHeading: document.getElementById('pageHeading'),

  // Header & Controls
  apiStatusBadge: document.getElementById('apiStatusBadge'),
  apiStatusText: document.getElementById('apiStatusText'),
  refreshBtn: document.getElementById('refreshBtn'),
  refreshIcon: document.getElementById('refreshIcon'),
  alertContainer: document.getElementById('alertContainer'),
  executionModeNotice: document.getElementById('executionModeNotice'),

  // Metrics
  metricTotalShipments: document.getElementById('metricTotalShipments'),
  metricDelayedShipments: document.getElementById('metricDelayedShipments'),
  metricLowStockItems: document.getElementById('metricLowStockItems'),
  metricOpenDisruptions: document.getElementById('metricOpenDisruptions'),

  // Sections
  disruptionsGrid: document.getElementById('disruptionsGrid'),
  disruptionCountBadge: document.getElementById('disruptionCountBadge'),
  shipmentsTableBody: document.getElementById('shipmentsTableBody'),
  shipmentStatusFilter: document.getElementById('shipmentStatusFilter'),
  inventoryList: document.getElementById('inventoryList'),
  recoveryPlansContent: document.getElementById('recoveryPlansContent'),
  recoveryPlanStatusBadge: document.getElementById('recoveryPlanStatusBadge'),
  auditTrailTableBody: document.getElementById('auditTrailTableBody'),
  auditEventCountBadge: document.getElementById('auditEventCountBadge'),
  auditRefreshBtn: document.getElementById('auditRefreshBtn'),
  auditEventTypeFilter: document.getElementById('auditEventTypeFilter'),
  auditShipmentFilter: document.getElementById('auditShipmentFilter'),
  auditSearchFilter: document.getElementById('auditSearchFilter'),
  auditApplyFiltersBtn: document.getElementById('auditApplyFiltersBtn'),
  auditClearFiltersBtn: document.getElementById('auditClearFiltersBtn'),
  auditPaginationInfo: document.getElementById('auditPaginationInfo'),
  auditPrevPageBtn: document.getElementById('auditPrevPageBtn'),
  auditNextPageBtn: document.getElementById('auditNextPageBtn'),

  // Modal
  disruptionModal: document.getElementById('disruptionModal'),
  modalTitle: document.getElementById('modalTitle'),
  modalBody: document.getElementById('modalBody'),
  modalCloseBtn: document.getElementById('modalCloseBtn'),
  modalDismissBtn: document.getElementById('modalDismissBtn'),
  modalAnalyzeBtn: document.getElementById('modalAnalyzeBtn'),

  // Phase 4: Audit Event Detail Modal
  auditEventModal: document.getElementById('auditEventModal'),
  auditEventModalTitle: document.getElementById('auditEventModalTitle'),
  auditEventModalBody: document.getElementById('auditEventModalBody'),
  auditEventModalCloseBtn: document.getElementById('auditEventModalCloseBtn'),
  auditEventModalDismissBtn: document.getElementById('auditEventModalDismissBtn')
};

/**
 * Initialize application listeners and load initial data
 */
document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  setupFilterHandlers();
  setupModalHandlers();
  setupAuditTrailHandlers();
  setupGlobalControls();
  fetchInitialData();
});

/**
 * Configure Sidebar & Section Navigation
 */
function setupNavigation() {
  elements.navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const targetSection = item.getAttribute('data-section');
      switchSection(targetSection);

      if (elements.sidebar.classList.contains('mobile-open')) {
        elements.sidebar.classList.remove('mobile-open');
      }
    });
  });

  if (elements.sidebarToggleBtn) {
    elements.sidebarToggleBtn.addEventListener('click', () => {
      elements.sidebar.classList.toggle('mobile-open');
    });
  }

  if (elements.sidebarCloseBtn) {
    elements.sidebarCloseBtn.addEventListener('click', () => {
      elements.sidebar.classList.remove('mobile-open');
    });
  }
}

/**
 * Smoothly scroll or focus to the selected section
 */
function switchSection(sectionId) {
  state.activeSection = sectionId;

  elements.navItems.forEach(item => {
    if (item.getAttribute('data-section') === sectionId) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  const titles = {
    'overview': 'Operations Overview',
    'disruptions': 'Active Disruption Incidents',
    'shipments': 'Shipment Monitoring',
    'inventory': 'Inventory Health & Safety Stocks',
    'recovery-plans': 'AI Recovery Playbooks & Approvals',
    'audit-trail': 'Audit Trail & Governance Logs'
  };
  elements.pageHeading.textContent = titles[sectionId] || 'Command Center';

  if (sectionId === 'overview') {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } else {
    const targetElement = document.getElementById(`section-${sectionId}`);
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}

/**
 * Setup Shipment Filtering
 */
function setupFilterHandlers() {
  if (elements.shipmentStatusFilter) {
    elements.shipmentStatusFilter.addEventListener('change', async (e) => {
      const selectedStatus = e.target.value;
      state.currentStatusFilter = selectedStatus;
      await fetchFilteredShipments(selectedStatus);
    });
  }
}

/**
 * Setup Disruption Detail & Analysis Modal
 */
function setupModalHandlers() {
  const closeModal = (reason = 'direct_close') => {
    console.log(`[Modal] Closing modal (Reason: ${reason})`);
    elements.disruptionModal.classList.remove('active');
  };

  if (elements.modalCloseBtn) {
    elements.modalCloseBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      closeModal('close_x_button');
    });
  }

  if (elements.modalDismissBtn) {
    elements.modalDismissBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      closeModal('dismiss_button');
    });
  }

  if (elements.disruptionModal) {
    elements.disruptionModal.addEventListener('click', (e) => {
      if (e.target === elements.disruptionModal) {
        closeModal('backdrop_click');
      }
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && elements.disruptionModal.classList.contains('active')) {
      closeModal('escape_key');
    }
  });

  if (elements.modalAnalyzeBtn) {
    elements.modalAnalyzeBtn.addEventListener('click', handleAnalyzeDisruption);
  }
}

/**
 * Setup Refresh button and global controls
 */
function setupGlobalControls() {
  if (elements.refreshBtn) {
    elements.refreshBtn.addEventListener('click', () => {
      fetchInitialData(true);
    });
  }
}

/**
 * Handle "Analyze Disruption" button click
 * Phase 2 & 3: Dispatches POST /api/analyze-disruption, persists in SQLite, and updates UI
 */
async function handleAnalyzeDisruption(e) {
  if (e && typeof e.preventDefault === 'function') e.preventDefault();
  if (e && typeof e.stopPropagation === 'function') e.stopPropagation();

  console.log('[Analyze Button] Click event received. Executing multi-agent analysis handler.');

  const disruption = state.selectedDisruption;
  const shipmentId = disruption?.affected_shipment || disruption?.id;

  if (!shipmentId) {
    console.error('[Analyze Button] Error: No shipment ID could be resolved:', disruption);
    showAlert('danger', 'Unable to resolve shipment ID for this incident.');
    return;
  }

  console.log(`[Analyze Button] Initiating LangGraph analysis for shipment ID: "${shipmentId}"`);

  elements.disruptionModal.classList.add('active');
  setAnalyzingState(true);

  const modalNoticeArea = document.getElementById('modalAnalysisNotice');
  if (modalNoticeArea) {
    modalNoticeArea.innerHTML = `
      <div style="background-color: var(--blue-light); border: 1px solid var(--blue-border); padding: 12px; border-radius: 6px; color: var(--blue-primary); font-size: 0.85rem; display: flex; align-items: center; gap: 10px;">
        <span class="spinner spinner-dark" style="border-top-color: var(--blue-primary);"></span>
        <span>Orchestrating multi-agent investigation fleet for <strong>${escapeHtml(shipmentId)}</strong> across supplier, inventory, and logistics channels...</span>
      </div>
    `;
  }

  try {
    console.log(`[Analyze Button] Sending POST ${API_ENDPOINTS.analyze} with shipment_id=${shipmentId}...`);
    const response = await fetch(API_ENDPOINTS.analyze, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ shipment_id: shipmentId })
    });

    const data = await response.json();
    console.log('[Analyze Button] Received API response:', response.status, data);

    if (!response.ok || data.status !== 'success') {
      throw new Error(data.message || `Analysis endpoint returned HTTP ${response.status}`);
    }

    state.latestAnalysis = data;
    renderAnalysisResultInModal(data);

    // Refresh persisted plans and audit trail from SQLite
    await Promise.all([
      fetchRecoveryPlans(),
      fetchAuditEvents()
    ]);

    elements.disruptionModal.classList.add('active');
    const modalBodyEl = elements.modalBody;
    if (modalBodyEl) modalBodyEl.scrollTop = 0;

    const modeLabel = data.execution_mode === 'live_llm' ? 'Live LLM Reasoning' : 'Deterministic Mock Mode';
    showAlert(
      'success',
      `<strong>Multi-Agent Analysis Persisted (${escapeHtml(modeLabel)}):</strong> Plan <code>${escapeHtml(data.plan_id || 'PLAN')}</code> saved to SQLite with ${data.recovery_options?.length || 0} recovery options.`
    );
  } catch (err) {
    console.error('[Analyze Button] Multi-Agent Analysis Failure:', err);
    showAlert('danger', `<strong>Multi-Agent Investigation Failed:</strong> ${escapeHtml(err.message)}`);
    
    const errorNoticeArea = document.getElementById('modalAnalysisNotice');
    if (errorNoticeArea) {
      errorNoticeArea.innerHTML = `
        <div style="background-color: var(--danger-bg); border: 1px solid var(--danger-border); padding: 12px; border-radius: 6px; color: var(--danger); font-size: 0.85rem;">
          <strong>Analysis Error:</strong> ${escapeHtml(err.message)}
        </div>
      `;
    }
  } finally {
    setAnalyzingState(false);
    elements.disruptionModal.classList.add('active');
  }
}

/**
 * Set visual state during analysis execution
 */
function setAnalyzingState(isAnalyzing) {
  state.isAnalyzing = isAnalyzing;
  if (elements.modalAnalyzeBtn) {
    elements.modalAnalyzeBtn.disabled = isAnalyzing;
    elements.modalAnalyzeBtn.innerHTML = isAnalyzing
      ? `<span class="spinner spinner-dark" style="border-top-color: #fff; margin-right: 6px;"></span> Orchestrating Agents...`
      : `<span>⚡ Run Multi-Agent Analysis</span>`;
  }
}

/**
 * Display User Notification Alerts
 */
function showAlert(type, message) {
  const alertEl = document.createElement('div');
  alertEl.className = `alert alert-${type}`;
  alertEl.innerHTML = `
    <div>${message}</div>
    <button class="alert-close" aria-label="Dismiss alert">&times;</button>
  `;

  alertEl.querySelector('.alert-close').addEventListener('click', () => {
    alertEl.remove();
  });

  elements.alertContainer.innerHTML = '';
  elements.alertContainer.appendChild(alertEl);

  if (type !== 'danger') {
    setTimeout(() => {
      if (alertEl.parentNode) alertEl.remove();
    }, 9000);
  }
}

/**
 * Set visual API Connection Badge State
 */
function setApiStatus(status, label) {
  elements.apiStatusBadge.className = `api-status-badge ${status}`;
  elements.apiStatusText.textContent = label;
}

/**
 * Helper to execute fetch with a sensible timeout (default 8000ms)
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 8000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error(`Request timed out after ${timeoutMs / 1000}s while calling ${url}`);
    }
    throw err;
  }
}

/**
 * Fetch complete dashboard payload from Flask backend (Phase 1, 2, & 3)
 */
async function fetchInitialData(isManualRefresh = false) {
  setLoadingState(true);
  setApiStatus('loading', 'Syncing API...');

  try {
    // 1. Check actual backend health
    const healthRes = await fetchWithTimeout(API_ENDPOINTS.health, {}, 6000);
    if (!healthRes.ok) throw new Error(`Health check returned status ${healthRes.status}`);
    const healthData = await healthRes.json();
    if (healthData.status !== 'ok') throw new Error('Backend health reported non-ok status');

    // 2. Fetch Dashboard Telemetry
    const dashRes = await fetchWithTimeout(API_ENDPOINTS.dashboard, {}, 8000);
    if (!dashRes.ok) throw new Error(`Dashboard API returned status ${dashRes.status}`);

    const payload = await dashRes.json();
    if (payload.status !== 'success') throw new Error(payload.message || 'Invalid server response');

    state.metrics = payload.metrics;
    state.shipments = payload.shipments;
    state.disruptions = payload.disruptions;
    state.inventory = payload.inventory;

    renderMetrics(state.metrics);
    renderDisruptions(state.disruptions);
    renderShipments(state.shipments);
    renderInventory(state.inventory);

    // 3. Fetch Phase 3 Persisted Recovery Plans & Audit Events safely
    await Promise.allSettled([
      fetchRecoveryPlans(),
      fetchAuditEvents()
    ]);

    setApiStatus('connected', 'API Connected (Phase 5: Intelligence & SQLite)');
    if (elements.executionModeNotice) {
      elements.executionModeNotice.textContent = 'Multi-Agent Intelligence & SQLite Active';
    }

    if (isManualRefresh) {
      showAlert('success', 'Dashboard telemetry and SQLite state successfully refreshed.');
    }
  } catch (error) {
    console.error('API Sync Error:', error);
    setApiStatus('error', 'API Offline / Error');
    renderErrorPlaceholders(error.message);
    showAlert(
      'danger',
      `<strong>Backend Communication Failure:</strong> ${escapeHtml(error.message)}. <button class="btn btn-sm btn-outline" style="margin-left: 10px; padding: 2px 8px;" onclick="fetchInitialData(true)">Retry Connection</button>`
    );
  } finally {
    setLoadingState(false);
  }
}

/**
 * Render graceful error placeholders if API sync fails so indicators never hang indefinitely
 */
function renderErrorPlaceholders(errorMessage) {
  if (elements.metricTotalShipments) elements.metricTotalShipments.textContent = 'Err';
  if (elements.metricDelayedShipments) elements.metricDelayedShipments.textContent = 'Err';
  if (elements.metricLowStockItems) elements.metricLowStockItems.textContent = 'Err';
  if (elements.metricOpenDisruptions) elements.metricOpenDisruptions.textContent = 'Err';

  if (elements.disruptionsGrid && (!state.disruptions || state.disruptions.length === 0)) {
    elements.disruptionsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 24px; text-align: center; color: var(--danger); background: var(--bg-card); border-radius: 8px; border: 1px dashed var(--danger);">
        <strong>Failed to load disruption incidents:</strong> ${escapeHtml(errorMessage)}<br>
        <button class="btn btn-sm btn-primary" style="margin-top: 10px;" onclick="fetchInitialData(true)">⟳ Retry</button>
      </div>`;
  }

  if (elements.shipmentsTableBody && (!state.shipments || state.shipments.length === 0)) {
    elements.shipmentsTableBody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; padding: 24px; color: var(--danger);">
          Failed to load shipment records. <button class="btn btn-sm btn-outline" onclick="fetchInitialData(true)">Retry</button>
        </td>
      </tr>`;
  }

  if (elements.inventoryList && (!state.inventory || state.inventory.length === 0)) {
    elements.inventoryList.innerHTML = `
      <div style="padding: 24px; text-align: center; color: var(--danger);">
        Failed to load warehouse stock records. <button class="btn btn-sm btn-outline" onclick="fetchInitialData(true)">Retry</button>
      </div>`;
  }
}

/**
 * Fetch Persisted Recovery Plans from SQLite
 */
async function fetchRecoveryPlans() {
  try {
    const res = await fetchWithTimeout(API_ENDPOINTS.recoveryPlans, {}, 6000);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.recoveryPlans = data.recovery_plans || [];
    renderRecoveryPlans(state.recoveryPlans);
  } catch (err) {
    console.error('Failed to load recovery plans:', err);
    if (elements.recoveryPlansContent && (!state.recoveryPlans || state.recoveryPlans.length === 0)) {
      elements.recoveryPlansContent.innerHTML = `
        <div class="placeholder-card" style="border: 1px dashed var(--danger);">
          <div class="placeholder-icon" aria-hidden="true">⚠️</div>
          <h3>Unable to Load Recovery Plans</h3>
          <p>${escapeHtml(err.message)}</p>
          <button class="btn btn-sm btn-outline" onclick="fetchRecoveryPlans()">⟳ Retry Loading Plans</button>
        </div>`;
    }
  }
}

/**
 * Fetch Immutable Audit Events from SQLite (Phase 4 Filtered & Paginated)
 */
async function fetchAuditEvents() {
  try {
    const params = new URLSearchParams();
    params.set('page', state.auditPage);
    params.set('limit', state.auditLimit);

    if (state.auditFilters.eventType) {
      params.set('event_type', state.auditFilters.eventType);
    }
    if (state.auditFilters.shipmentId) {
      params.set('shipment_id', state.auditFilters.shipmentId);
    }
    if (state.auditFilters.search) {
      params.set('search', state.auditFilters.search);
    }

    const res = await fetchWithTimeout(`${API_ENDPOINTS.auditEvents}?${params.toString()}`, {}, 6000);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    state.auditEvents = data.audit_events || [];
    state.auditTotal = data.total || 0;
    state.auditPages = data.pages || 1;
    state.auditPage = data.page || 1;

    renderAuditTrail(state.auditEvents);
    updateAuditPaginationControls();
  } catch (err) {
    console.error('Failed to load audit events:', err);
    if (elements.auditTrailTableBody && (!state.auditEvents || state.auditEvents.length === 0)) {
      elements.auditTrailTableBody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 24px; color: var(--danger);">
            Failed to load audit trail: ${escapeHtml(err.message)} <button class="btn btn-sm btn-outline" style="margin-left: 8px;" onclick="fetchAuditEvents()">Retry</button>
          </td>
        </tr>`;
    }
  }
}

/**
 * Update Audit Trail Pagination Controls
 */
function updateAuditPaginationControls() {
  if (elements.auditEventCountBadge) {
    elements.auditEventCountBadge.textContent = `${state.auditTotal} Total Event(s)`;
  }

  if (elements.auditPaginationInfo) {
    const startIdx = state.auditTotal === 0 ? 0 : (state.auditPage - 1) * state.auditLimit + 1;
    const endIdx = Math.min(state.auditPage * state.auditLimit, state.auditTotal);
    elements.auditPaginationInfo.textContent = `Showing ${startIdx}-${endIdx} of ${state.auditTotal} events (Page ${state.auditPage} of ${state.auditPages})`;
  }

  if (elements.auditPrevPageBtn) {
    elements.auditPrevPageBtn.disabled = state.auditPage <= 1;
  }
  if (elements.auditNextPageBtn) {
    elements.auditNextPageBtn.disabled = state.auditPage >= state.auditPages;
  }
}

/**
 * Configure Phase 4 Audit Trail Interactive Filters & Pagination Handlers
 */
function setupAuditTrailHandlers() {
  if (elements.auditApplyFiltersBtn) {
    elements.auditApplyFiltersBtn.addEventListener('click', () => {
      state.auditFilters.eventType = elements.auditEventTypeFilter ? elements.auditEventTypeFilter.value : '';
      state.auditFilters.shipmentId = elements.auditShipmentFilter ? elements.auditShipmentFilter.value.trim().toUpperCase() : '';
      state.auditFilters.search = elements.auditSearchFilter ? elements.auditSearchFilter.value.trim() : '';
      state.auditPage = 1; // Reset to page 1 on filter
      fetchAuditEvents();
    });
  }

  if (elements.auditClearFiltersBtn) {
    elements.auditClearFiltersBtn.addEventListener('click', () => {
      if (elements.auditEventTypeFilter) elements.auditEventTypeFilter.value = '';
      if (elements.auditShipmentFilter) elements.auditShipmentFilter.value = '';
      if (elements.auditSearchFilter) elements.auditSearchFilter.value = '';
      state.auditFilters.eventType = '';
      state.auditFilters.shipmentId = '';
      state.auditFilters.search = '';
      state.auditPage = 1;
      fetchAuditEvents();
    });
  }

  if (elements.auditRefreshBtn) {
    elements.auditRefreshBtn.addEventListener('click', () => {
      fetchAuditEvents();
    });
  }

  if (elements.auditPrevPageBtn) {
    elements.auditPrevPageBtn.addEventListener('click', () => {
      if (state.auditPage > 1) {
        state.auditPage--;
        fetchAuditEvents();
      }
    });
  }

  if (elements.auditNextPageBtn) {
    elements.auditNextPageBtn.addEventListener('click', () => {
      if (state.auditPage < state.auditPages) {
        state.auditPage++;
        fetchAuditEvents();
      }
    });
  }

  // Audit Event Detail Modal handlers
  if (elements.auditEventModalCloseBtn) {
    elements.auditEventModalCloseBtn.addEventListener('click', closeAuditEventModal);
  }
  if (elements.auditEventModalDismissBtn) {
    elements.auditEventModalDismissBtn.addEventListener('click', closeAuditEventModal);
  }
  if (elements.auditEventModal) {
    elements.auditEventModal.addEventListener('click', (e) => {
      if (e.target === elements.auditEventModal) closeAuditEventModal();
    });
  }
}

function closeAuditEventModal() {
  if (elements.auditEventModal) {
    elements.auditEventModal.classList.remove('active');
  }
}

/**
 * Open Audit Event Detail Modal by ID
 */
window.viewAuditEventDetail = async function(eventId) {
  try {
    const res = await fetch(`/api/audit-events/${eventId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const ev = data.audit_event;

    if (!elements.auditEventModalBody) return;

    let outcomeBadge = 'badge-healthy';
    if (ev.outcome === 'FAILED') outcomeBadge = 'badge-critical';
    else if (ev.outcome === 'WARNING') outcomeBadge = 'badge-warning';

    elements.auditEventModalBody.innerHTML = `
      <div style="display: flex; gap: 8px; margin-bottom: 14px; align-items: center;">
        <span class="code-cell" style="font-size: 0.95rem;">EVENT #${ev.id}</span>
        <span class="badge badge-transit">${escapeHtml(ev.event_type)}</span>
        <span class="badge ${outcomeBadge}">${escapeHtml(ev.outcome)}</span>
      </div>

      <div class="detail-field">
        <div class="detail-label">Action Description</div>
        <div class="detail-value" style="font-weight: 500; line-height: 1.5;">${escapeHtml(ev.description)}</div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 14px 0;">
        <div class="detail-field">
          <div class="detail-label">Associated Shipment</div>
          <div class="detail-value" style="font-family: monospace;">${escapeHtml(ev.associated_shipment || 'N/A')}</div>
        </div>
        <div class="detail-field">
          <div class="detail-label">Associated Plan / Incident</div>
          <div class="detail-value" style="font-family: monospace;">${escapeHtml(ev.associated_plan || ev.associated_disruption || 'N/A')}</div>
        </div>
        <div class="detail-field">
          <div class="detail-label">Actor</div>
          <div class="detail-value">${escapeHtml(ev.actor_name)} <span style="font-size: 0.74rem; color: var(--text-muted);">(${escapeHtml(ev.actor_type)})</span></div>
        </div>
        <div class="detail-field">
          <div class="detail-label">Timestamp (UTC)</div>
          <div class="detail-value" style="font-size: 0.8rem;">${ev.timestamp ? new Date(ev.timestamp).toUTCString() : 'N/A'}</div>
        </div>
      </div>

      ${ev.previous_status || ev.new_status ? `
        <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 14px; margin-bottom: 14px;">
          <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Status Transition</div>
          <div style="margin-top: 4px; font-size: 0.84rem; display: flex; align-items: center; gap: 8px;">
            <span class="badge badge-transit">${escapeHtml(ev.previous_status || 'Initial')}</span>
            <span>&rarr;</span>
            <span class="badge badge-healthy">${escapeHtml(ev.new_status || 'Updated')}</span>
          </div>
        </div>
      ` : ''}

      <div class="detail-field">
        <div class="detail-label">Structured Governance Details (JSON)</div>
        <pre style="background: #0f172a; color: #38bdf8; padding: 12px; border-radius: 6px; font-size: 0.76rem; overflow-x: auto; max-height: 220px;">${escapeHtml(JSON.stringify(ev.details || {}, null, 2))}</pre>
      </div>
    `;

    if (elements.auditEventModal) {
      elements.auditEventModal.classList.add('active');
    }
  } catch (err) {
    console.error('Failed to load audit event details:', err);
    showAlert('danger', `Failed to load audit event #${eventId}: ${escapeHtml(err.message)}`);
  }
};

/**
 * Fetch shipments filtered by status
 */
async function fetchFilteredShipments(status) {
  setLoadingState(true);

  try {
    const url = status && status !== 'All'
      ? `${API_ENDPOINTS.shipments}?status=${encodeURIComponent(status)}`
      : API_ENDPOINTS.shipments;

    const res = await fetch(url);
    if (!res.ok) throw new Error(`Shipments API returned status ${res.status}`);

    const data = await res.json();
    renderShipments(data.shipments || []);
  } catch (err) {
    console.error('Shipment filter error:', err);
    showAlert('danger', `Failed to filter shipments: ${escapeHtml(err.message)}`);
  } finally {
    setLoadingState(false);
  }
}

/**
 * Toggle visual loading indicators
 */
function setLoadingState(isLoading) {
  state.isLoading = isLoading;
  if (elements.refreshBtn) elements.refreshBtn.disabled = isLoading;
  if (elements.refreshIcon) elements.refreshIcon.textContent = isLoading ? '⏳' : '🔄';
}

/**
 * Render Metric Cards
 */
function renderMetrics(metrics) {
  if (!metrics) return;
  elements.metricTotalShipments.textContent = metrics.total_shipments ?? 0;
  elements.metricDelayedShipments.textContent = metrics.delayed_shipments ?? 0;
  elements.metricLowStockItems.textContent = metrics.low_stock_items ?? 0;
  elements.metricOpenDisruptions.textContent = metrics.open_disruptions ?? 0;
}

/**
 * Safely parse or evaluate numeric risk score (0-100) with robust fallback
 */
function getNumericRiskScore(item) {
  if (!item) return 0.0;
  if (typeof item.risk_score === 'number' && !isNaN(item.risk_score)) {
    return item.risk_score;
  }
  const parsed = parseFloat(item.risk_score);
  if (!isNaN(parsed)) return parsed;

  const sev = String(item.calculated_severity || item.severity || '').toLowerCase().trim();
  if (sev === 'critical') return 85.0;
  if (sev === 'high') return 60.0;
  if (sev === 'medium') return 40.0;
  if (sev === 'low') return 15.0;
  return 0.0;
}

/**
 * Sort disruptions by numeric risk score in descending order,
 * keeping completed/resolved incidents separated after active ones.
 */
function sortDisruptionsByRisk(disruptions) {
  if (!Array.isArray(disruptions)) return { active: [], resolved: [], all: [] };

  const isResolvedOrCompleted = (d) => {
    const st = String(d.status || d.resolution_status || '').toLowerCase().trim();
    return st === 'resolved' || st === 'completed' || st === 'closed';
  };

  const active = disruptions.filter(d => !isResolvedOrCompleted(d));
  const resolved = disruptions.filter(isResolvedOrCompleted);

  active.sort((a, b) => getNumericRiskScore(b) - getNumericRiskScore(a));
  resolved.sort((a, b) => getNumericRiskScore(b) - getNumericRiskScore(a));

  return { active, resolved, all: [...active, ...resolved] };
}

/**
 * Generate concise operational risk intelligence explanation from actual backend attributes
 */
function generateDisruptionRiskExplanation(item) {
  if (!item) return { summary: 'Standard operational evaluation.', attentionNote: 'Monitor operational parameters.' };

  const parts = [];
  const sev = item.calculated_severity || item.severity || 'Medium';
  const daysToStockout = typeof item.days_to_stockout === 'number' ? item.days_to_stockout : null;
  const revAtRisk = typeof item.revenue_at_risk_usd === 'number' ? item.revenue_at_risk_usd : null;
  const shipmentId = item.affected_shipment;

  if (daysToStockout !== null && daysToStockout <= 2.0) {
    parts.push(`Warehouse buffer depletion is imminent with only ${daysToStockout.toFixed(1)} days of stock remaining.`);
  } else if (daysToStockout !== null && daysToStockout <= 5.0) {
    parts.push(`Warehouse stock will breach safety threshold in ${daysToStockout.toFixed(1)} days unless replenishment arrives.`);
  }

  if (revAtRisk && revAtRisk > 0) {
    parts.push(`Projected enterprise revenue exposure stands at $${revAtRisk.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} due to potential fulfillment delays.`);
  }

  if (Array.isArray(item.top_contributing_factors) && item.top_contributing_factors.length > 0) {
    const topDriver = item.top_contributing_factors[0];
    parts.push(`Primary risk driver is ${topDriver.factor} (${topDriver.detail}).`);
  }

  const attentionNote = shipmentId
    ? `Operational action required: Evaluate expedited carrier re-routing or secondary supplier PO for shipment ${shipmentId} before stockout occurs.`
    : `Operational action required: Formulate alternative sourcing or emergency stock re-balancing immediately.`;

  return {
    summary: parts.join(' ') || `Incident evaluated under composite risk model with priority level '${sev}'.`,
    attentionNote
  };
}

// Expose on global window object for testability
if (typeof window !== 'undefined') {
  window.getNumericRiskScore = getNumericRiskScore;
  window.sortDisruptionsByRisk = sortDisruptionsByRisk;
  window.generateDisruptionRiskExplanation = generateDisruptionRiskExplanation;
  window.renderDisruptions = renderDisruptions;
  window.openDisruptionModal = openDisruptionModal;
}

/**
 * Render Priority Disruption Cards Sorted by Descending Risk Score
 */
function renderDisruptions(disruptions) {
  if (!elements.disruptionsGrid) return;

  if (!disruptions || disruptions.length === 0) {
    elements.disruptionsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 20px; text-align: center; color: var(--text-muted);">
        No active disruptions flagged. All supply routes operating within normal parameters.
      </div>`;
    return;
  }

  // Sort active disruptions dynamically by descending risk score
  const { active, resolved, all } = sortDisruptionsByRisk(disruptions);

  elements.disruptionCountBadge.textContent = resolved.length > 0
    ? `${active.length} Active Incidents (${resolved.length} Resolved)`
    : `${active.length} Active Incidents`;

  elements.disruptionsGrid.innerHTML = all.map((item) => {
    const sev = (item.calculated_severity || item.severity || 'Medium');
    const sevClass = sev.toLowerCase();
    const badgeClass = sevClass === 'critical' ? 'badge-critical' : (sevClass === 'high' ? 'badge-warning' : 'badge-medium');
    const numericScore = getNumericRiskScore(item);
    const riskScore = numericScore.toFixed(1);
    const isResolved = String(item.status || item.resolution_status || '').toLowerCase() === 'resolved';
    const explanation = generateDisruptionRiskExplanation(item);

    return `
      <div class="disruption-card severity-${sevClass} ${isResolved ? 'status-resolved' : ''}" data-id="${item.id}" tabindex="0" role="button" aria-label="View details for ${escapeHtml(item.title)}">
        <div class="disruption-head">
          <span class="disruption-id">${escapeHtml(item.id)}</span>
          <div style="display: flex; gap: 6px; align-items: center;">
            ${isResolved ? `<span class="badge badge-healthy">Resolved</span>` : ''}
            <span class="badge ${badgeClass}" title="Dynamic Normalized Risk Score (0-100)">Risk: ${riskScore}/100</span>
            <span class="badge ${badgeClass}">${escapeHtml(sev)}</span>
          </div>
        </div>

        <div class="risk-meter-bar" title="Risk Score: ${riskScore}/100">
          <div class="risk-meter-fill ${sevClass}" style="width: ${Math.min(100, Math.max(8, numericScore))}%;"></div>
        </div>

        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.description)}</p>
        
        ${item.top_contributing_factors && item.top_contributing_factors.length > 0 ? `
          <div style="margin: 8px 0; font-size: 0.72rem; color: var(--text-muted); background: rgba(0,0,0,0.025); border: 1px solid var(--border-subtle); padding: 8px 10px; border-radius: 4px;">
            <div><strong style="color: var(--text-secondary);">Top Risk Driver:</strong> ${escapeHtml(item.top_contributing_factors[0].factor)} (${escapeHtml(item.top_contributing_factors[0].detail)})</div>
            <div style="margin-top: 3px; color: ${sevClass === 'critical' ? '#b91c1c' : (sevClass === 'high' ? '#b45309' : '#0284c7')}; font-weight: 500;">
              ⚡ ${escapeHtml(explanation.summary)}
            </div>
          </div>
        ` : ''}

        <div class="disruption-meta">
          <span>📦 ${escapeHtml(item.affected_shipment || 'Inventory')} &bull; ${escapeHtml(item.affected_item ? item.affected_item.split('(')[0].trim() : 'Active SKU')}</span>
          <span style="color: var(--blue-primary); font-weight: 600;">Investigate &rarr;</span>
        </div>
      </div>
    `;
  }).join('');

  elements.disruptionsGrid.querySelectorAll('.disruption-card').forEach(card => {
    const clickHandler = () => {
      const disruptionId = card.getAttribute('data-id');
      const item = all.find(d => d.id === disruptionId) || disruptions.find(d => d.id === disruptionId);
      if (item) openDisruptionModal(item);
    };
    card.addEventListener('click', clickHandler);
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        clickHandler();
      }
    });
  });
}

/**
 * Render Shipments Table
 */
function renderShipments(shipments) {
  if (!elements.shipmentsTableBody) return;

  if (!shipments || shipments.length === 0) {
    elements.shipmentsTableBody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; padding: 24px; color: var(--text-muted);">
          No shipment records found matching filter criteria.
        </td>
      </tr>`;
    return;
  }

  elements.shipmentsTableBody.innerHTML = shipments.map(s => {
    let statusBadgeClass = 'badge-transit';
    if (s.status === 'Delayed') statusBadgeClass = 'badge-critical';
    else if (s.status === 'Rerouted') statusBadgeClass = 'badge-warning';
    else if (s.status === 'Delivered') statusBadgeClass = 'badge-healthy';

    let riskBadgeClass = 'badge-low';
    if (s.risk_level === 'Critical') riskBadgeClass = 'badge-critical';
    else if (s.risk_level === 'High') riskBadgeClass = 'badge-warning';
    else if (s.risk_level === 'Medium') riskBadgeClass = 'badge-medium';

    return `
      <tr>
        <td class="code-cell">
          <button class="btn btn-sm btn-outline" style="font-family: monospace; font-size: 0.75rem; padding: 2px 6px;" onclick="inspectShipment('${escapeHtml(s.id)}')">
            ${escapeHtml(s.id)}
          </button>
        </td>
        <td><strong>${escapeHtml(s.supplier)}</strong></td>
        <td>
          <div>${escapeHtml(s.product)}</div>
          <div style="font-size: 0.72rem; color: var(--text-muted);">${escapeHtml(s.sku || '')}</div>
        </td>
        <td>${s.quantity.toLocaleString()}</td>
        <td>${escapeHtml(s.destination)}</td>
        <td>
          ${escapeHtml(s.expected_arrival)}
          ${s.delay_days > 0 ? `<div style="color: var(--danger); font-size: 0.72rem; font-weight: 600;">+${s.delay_days} days delay</div>` : ''}
        </td>
        <td><span class="badge ${statusBadgeClass}">${escapeHtml(s.status)}</span></td>
        <td><span class="badge ${riskBadgeClass}">${escapeHtml(s.risk_level)}</span></td>
      </tr>
    `;
  }).join('');
}

/**
 * Directly inspect and trigger analysis for a specific shipment
 */
window.inspectShipment = function(shipmentId) {
  const shipment = state.shipments.find(s => s.id === shipmentId);
  const disruption = state.disruptions.find(d => d.affected_shipment === shipmentId) || {
    id: `DIS-${shipmentId}`,
    title: `Shipment Analysis: ${shipmentId}`,
    type: shipment?.status === 'Delayed' ? 'Supplier Delay' : 'Standard In-Transit Tracking',
    severity: shipment?.risk_level || 'Medium',
    affected_item: `${shipment?.product} (${shipment?.sku})`,
    affected_shipment: shipmentId,
    facility: shipment?.destination,
    reported_date: 'Active',
    description: shipment?.notes || 'No notes filed.',
    impact_summary: 'Under investigation.',
    future_agent_task: 'Multi-agent LangGraph workflow execution.'
  };

  openDisruptionModal(disruption);
};

/**
 * Render Inventory Health Rows
 */
function renderInventory(inventory) {
  if (!elements.inventoryList) return;

  if (!inventory || inventory.length === 0) {
    elements.inventoryList.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--text-muted);">
        No warehouse inventory records available.
      </div>`;
    return;
  }

  elements.inventoryList.innerHTML = inventory.map(item => {
    let statusClass = 'healthy';
    let badgeClass = 'badge-healthy';

    if (item.stock_status === 'Critical') {
      statusClass = 'critical';
      badgeClass = 'badge-critical';
    } else if (item.stock_status === 'Low Stock') {
      statusClass = 'warning';
      badgeClass = 'badge-warning';
    }

    const pct = Math.min(Math.max(item.percentage || 0, 8), 100);

    return `
      <div class="inventory-row">
        <div>
          <div class="inv-prod-name">${escapeHtml(item.product_name)}</div>
          <div class="inv-sku">${escapeHtml(item.sku)} &bull; ${escapeHtml(item.location || 'Central Facility')}</div>
        </div>

        <div>
          <span class="badge ${badgeClass}">${escapeHtml(item.stock_status)}</span>
        </div>

        <div>
          <div class="inv-stock-count">${item.available_stock.toLocaleString()} / ${item.reorder_threshold.toLocaleString()} ${item.unit || 'units'}</div>
          <div class="progress-track" aria-label="Inventory buffer level: ${pct}%">
            <div class="progress-bar ${statusClass}" style="width: ${pct}%;"></div>
          </div>
        </div>

        <div style="font-size: 0.78rem; color: var(--text-secondary);">
          Reorder Threshold: <strong>${item.reorder_threshold}</strong>
        </div>

        <div style="text-align: right; font-size: 0.75rem; color: var(--text-muted);">
          ${item.notes ? escapeHtml(item.notes) : 'Standard safety stock'}
        </div>
      </div>
    `;
  }).join('');
}

/**
 * Open Disruption Detail Modal with Phase 5 Risk Intelligence & Top Drivers
 */
function openDisruptionModal(item) {
  state.selectedDisruption = item;
  elements.modalTitle.textContent = `${item.id}: ${item.title}`;

  const sev = (item.calculated_severity || item.severity || 'Medium');
  const sevClass = sev.toLowerCase();
  let sevBadgeClass = 'badge-medium';
  if (sev === 'Critical') sevBadgeClass = 'badge-critical';
  else if (sev === 'High') sevBadgeClass = 'badge-warning';

  const numericScore = getNumericRiskScore(item);
  let riskBadgeClass = 'badge-transit';
  if (numericScore >= 70) riskBadgeClass = 'badge-critical';
  else if (numericScore >= 50) riskBadgeClass = 'badge-warning';

  const factors = Array.isArray(item.top_contributing_factors) ? item.top_contributing_factors : [];
  const explanation = generateDisruptionRiskExplanation(item);
  const formula = item.scoring_formula || 'Composite 6-factor index: Shortage (25%) + Delay (20%) + Stockout Time (20%) + Criticality (15%) + Revenue (10%) + Mitigation Scarcity (10%). Scale 0-100.';

  if (elements.modalAnalyzeBtn) {
    elements.modalAnalyzeBtn.disabled = false;
    elements.modalAnalyzeBtn.innerHTML = `<span>⚡ Run Multi-Agent Analysis</span>`;
  }

  elements.modalBody.innerHTML = `
    <!-- Hero Risk Score & Severity Header Card -->
    <div style="background: #ffffff; border: 1px solid var(--border-color); border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; box-shadow: var(--shadow-sm);">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
        <div>
          <div style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; color: var(--text-muted); margin-bottom: 4px;">
            Dynamic Disruption Risk Score
          </div>
          <div style="display: flex; align-items: baseline; gap: 6px;">
            <span style="font-size: 2.1rem; font-weight: 800; color: ${sevClass === 'critical' ? '#dc2626' : (sevClass === 'high' ? '#d97706' : '#0284c7')}; line-height: 1;">
              ${numericScore.toFixed(1)}
            </span>
            <span style="font-size: 0.95rem; font-weight: 600; color: var(--text-muted);">/ 100</span>
          </div>
        </div>

        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
          <div style="display: flex; gap: 6px; align-items: center;">
            <span class="badge ${sevBadgeClass}" style="font-size: 0.82rem; font-weight: 700; padding: 4px 10px;">
              ${escapeHtml(sev)} Priority
            </span>
            <span class="badge badge-transit" style="font-size: 0.78rem;">${escapeHtml(item.type)}</span>
          </div>
          <div style="font-size: 0.74rem; color: var(--text-muted);">
            Shipment: <code style="color: var(--blue-primary); font-weight: 700;">${escapeHtml(item.affected_shipment || 'N/A')}</code>
          </div>
        </div>
      </div>

      <!-- Risk Meter Visual Track -->
      <div class="risk-meter-bar" style="height: 8px; margin: 12px 0 6px 0;" title="Dynamic Risk Score: ${numericScore.toFixed(1)}/100">
        <div class="risk-meter-fill ${sevClass}" style="width: ${Math.min(100, Math.max(6, numericScore))}%;"></div>
      </div>
      <div style="display: flex; justify-content: space-between; font-size: 0.68rem; color: var(--text-muted);">
        <span>Low (0–29)</span>
        <span>Medium (30–54)</span>
        <span>High (55–79)</span>
        <span>Critical (80–100)</span>
      </div>
    </div>

    <!-- Phase 5 Dynamic Risk Intelligence & Contributing Factors Panel -->
    <div style="background: rgba(30, 41, 59, 0.03); border: 1px solid var(--border-color); border-radius: 6px; padding: 14px; margin-bottom: 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px;">
        <div style="font-weight: 700; font-size: 0.85rem; color: var(--blue-primary); display: flex; align-items: center; gap: 6px;">
          <span>📈</span> Contributing Risk Factors & Prioritization Rationale
        </div>
        <span class="badge badge-transit" style="font-size: 0.68rem;">6-Factor Dynamic Model</span>
      </div>

      <!-- Concise Operational Risk Explanation -->
      <div style="background: #fff; border: 1px solid #fecaca; border-left: 4px solid #ef4444; padding: 10px 12px; border-radius: 4px; font-size: 0.80rem; line-height: 1.45; margin-bottom: 10px;">
        <strong>Prioritization Rationale:</strong> ${escapeHtml(explanation.summary)}
        <div style="margin-top: 5px; color: #991b1b; font-weight: 600;">
          ⚠️ ${escapeHtml(explanation.attentionNote)}
        </div>
      </div>

      <!-- Top Contributing Risk Factors Grid -->
      ${factors.length > 0 ? `
        <div style="font-size: 0.76rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px;">
          Top Contributing Risk Factors (Score Breakdown):
        </div>
        <div class="risk-factor-grid">
          ${factors.map(f => `
            <div class="risk-factor-item">
              <div class="risk-factor-top">
                <span class="risk-factor-title">${escapeHtml(f.factor)}</span>
                <span class="risk-factor-badge ${f.score >= (f.max * 0.7) ? 'badge-critical' : 'badge-warning'}">
                  +${f.score}/${f.max} pts
                </span>
              </div>
              <div class="risk-factor-desc">
                ${escapeHtml(f.detail)}
              </div>
            </div>
          `).join('')}
        </div>
      ` : ''}

      <div style="font-size: 0.70rem; color: var(--text-muted); margin-top: 8px; font-style: italic;">
        Scoring Formula: ${escapeHtml(formula)}
      </div>
    </div>

    <div class="detail-field">
      <div class="detail-label">Incident Description</div>
      <div class="detail-value" style="font-weight: 400; line-height: 1.5;">${escapeHtml(item.description)}</div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0;">
      <div class="detail-field">
        <div class="detail-label">Affected SKU / Product</div>
        <div class="detail-value">${escapeHtml(item.affected_item)}</div>
      </div>
      <div class="detail-field">
        <div class="detail-label">Target Shipment ID</div>
        <div class="detail-value" style="color: var(--blue-primary); font-family: monospace; font-weight: 700;">
          ${escapeHtml(item.affected_shipment || 'N/A')}
        </div>
      </div>
      <div class="detail-field">
        <div class="detail-label">Target Facility</div>
        <div class="detail-value">${escapeHtml(item.facility || 'Central DC')}</div>
      </div>
      <div class="detail-field">
        <div class="detail-label">Reported Timestamp</div>
        <div class="detail-value">${escapeHtml(item.reported_date || 'Recent')}</div>
      </div>
    </div>

    <div class="detail-field">
      <div class="detail-label">Estimated Baseline Business Impact</div>
      <div class="detail-value" style="color: #991b1b; background-color: #fef2f2; padding: 10px; border-radius: 6px; border: 1px solid #fecaca;">
        ${escapeHtml(item.impact_summary)}
      </div>
    </div>

    <div class="modal-ai-notice" id="modalAnalysisNotice">
      <span style="font-size: 1.3rem;">🧠</span>
      <div>
        <strong>Dynamic Risk Intelligence & Prioritization (Phase 5 Active):</strong><br>
        The disruption risk score evaluates 6 operational factors: inventory shortage severity (25%), expected shipment delay (20%), stockout urgency (20%), shipment criticality (15%), revenue exposure (10%), and mitigation scarcity (10%). All metrics, carrier lead times, and financial projections are deterministic benchmark simulations within the Command Center sandbox. Click <strong>"Run Multi-Agent Analysis"</strong> to orchestrate parallel LangGraph agents and generate audited recovery playbooks.
      </div>
    </div>
  `;

  elements.disruptionModal.classList.add('active');
}

/**
 * Render structured multi-agent results inside the modal
 */
function renderAnalysisResultInModal(data) {
  const isMock = data.execution_mode !== 'live_llm';
  const modeTag = isMock
    ? `<span class="badge badge-warning">Deterministic Benchmark Reasoning (Mock Mode)</span>`
    : `<span class="badge badge-healthy">Live LLM Agent Reasoning</span>`;

  const findings = data.agent_findings || {};
  const supplier = findings.supplier || {};
  const inventory = findings.inventory || {};
  const logistics = findings.logistics || {};
  const impact = findings.impact || {};

  elements.modalBody.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
      <h4 style="font-size: 1rem; color: var(--text-main);">Multi-Agent Orchestration Findings</h4>
      <div style="display: flex; gap: 8px; align-items: center;">
        ${data.risk_score ? `<span class="badge badge-transit" style="font-weight: 700;">Risk Score: ${Number(data.risk_score).toFixed(1)}/100</span>` : ''}
        ${modeTag}
      </div>
    </div>

    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid var(--blue-primary); padding: 12px; border-radius: 6px; margin-bottom: 16px; font-size: 0.84rem; line-height: 1.5;">
      <strong>Executive Synthesis:</strong><br>
      ${escapeHtml(data.executive_summary || 'Analysis complete.')}
    </div>

    <!-- Phase 4 Multi-Agent Execution Timeline -->
    ${data.execution_timeline && data.execution_timeline.length > 0 ? `
      <div style="margin-bottom: 16px; background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px 14px;">
        <div style="font-size: 0.82rem; font-weight: 700; color: var(--blue-primary); margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
          <span>⚡</span> Multi-Agent LangGraph Execution Pipeline & Timeline
        </div>
        <div style="display: flex; flex-direction: column; gap: 6px;">
          ${data.execution_timeline.map(t => `
            <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.76rem; background: #f8fafc; padding: 6px 10px; border-radius: 4px; border-left: 3px solid #10b981;">
              <div>
                <strong>Step ${t.step}: ${escapeHtml(t.agent)}</strong> 
                <span style="color: var(--text-muted); font-size: 0.72rem;">(${escapeHtml(t.phase)})</span>
                <div style="color: var(--text-secondary); margin-top: 2px;">${escapeHtml(t.findings_summary)}</div>
              </div>
              <span class="badge badge-healthy" style="font-size: 0.68rem;">${escapeHtml(t.status)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    ` : ''}

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
      <!-- Supplier Agent -->
      <div style="border: 1px solid var(--border-subtle); border-radius: 6px; padding: 12px; font-size: 0.8rem;">
        <div style="font-weight: 700; color: var(--blue-primary); margin-bottom: 6px;">🏭 Supplier Investigation Agent</div>
        <div>Primary: <strong>${escapeHtml(supplier.primary_supplier || 'N/A')}</strong> (+${supplier.delay_days || 0}d delay)</div>
        <div style="margin-top: 4px; color: var(--text-secondary);">${escapeHtml(supplier.reported_delay_cause || '')}</div>
        <div style="margin-top: 6px; font-weight: 600;">
          Alternatives found: ${supplier.alternative_suppliers_found || 0}
          ${supplier.recommended_alternative ? `(Rec: ${escapeHtml(supplier.recommended_alternative.supplier_name)}, ${supplier.recommended_alternative.lead_time_days}d lead)` : ''}
        </div>
      </div>

      <!-- Inventory Agent -->
      <div style="border: 1px solid var(--border-subtle); border-radius: 6px; padding: 12px; font-size: 0.8rem;">
        <div style="font-weight: 700; color: var(--warning); margin-bottom: 6px;">📦 Inventory Shortage Agent</div>
        <div>Current Stock: <strong>${inventory.current_stock ?? 'N/A'}</strong> (Threshold: ${inventory.reorder_threshold ?? 'N/A'})</div>
        <div>Buffer Remaining: <strong>${inventory.days_of_stock_remaining ?? 'N/A'} days</strong> (${inventory.estimated_hours_to_stockout ?? 0} hrs)</div>
        <div style="margin-top: 4px; color: ${inventory.will_stockout_before_arrival ? 'var(--danger)' : 'var(--text-secondary)'}; font-weight: 600;">
          ${inventory.will_stockout_before_arrival ? '⚠️ Stockout anticipated before shipment arrives' : 'Buffer sufficient'}
        </div>
      </div>

      <!-- Logistics Agent -->
      <div style="border: 1px solid var(--border-subtle); border-radius: 6px; padding: 12px; font-size: 0.8rem;">
        <div style="font-weight: 700; color: var(--info); margin-bottom: 6px;">🚢 Logistics Routing Agent</div>
        <div>Current Route: <strong>${escapeHtml(logistics.current_route || 'Standard')}</strong></div>
        <div>Available options: ${logistics.available_routes_count || 0}</div>
        <div style="margin-top: 4px; color: var(--text-secondary);">${escapeHtml(logistics.recommendation_summary || 'Evaluating routes...')}</div>
      </div>

      <!-- Impact Agent -->
      <div style="border: 1px solid var(--border-subtle); border-radius: 6px; padding: 12px; font-size: 0.8rem;">
        <div style="font-weight: 700; color: var(--danger); margin-bottom: 6px;">📊 Impact Analysis Agent</div>
        <div>Revenue at Risk: <strong style="color: var(--danger); font-size: 0.95rem;">$${(impact.revenue_at_risk_usd || 0).toLocaleString()}</strong></div>
        <div>Batch Asset Value: $${(impact.batch_value_usd || 0).toLocaleString()}</div>
        <div style="margin-top: 4px; font-weight: 600;">Recommended: ${escapeHtml(impact.recommended_plan || 'N/A')}</div>
      </div>
    </div>

    <!-- Recovery Options Table -->
    <div style="margin-bottom: 14px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div style="font-weight: 700; font-size: 0.88rem; color: var(--text-main);">
          Mitigation Playbooks Saved to SQLite (Plan: <code>${escapeHtml(data.plan_id || 'PLAN')}</code>):
        </div>
        <a href="#recovery-plans" onclick="elements.disruptionModal.classList.remove('active'); switchSection('recovery-plans');" style="font-size: 0.78rem; color: var(--blue-primary); font-weight: 600; text-decoration: none;">
          View in Recovery Center &rarr;
        </a>
      </div>
      <div class="table-responsive">
        <table class="enterprise-table" style="font-size: 0.78rem;">
          <thead>
            <tr>
              <th>Option</th>
              <th>Action Plan</th>
              <th>Indicative Cost</th>
              <th>Resolution Time</th>
              <th>Feasibility</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${(data.recovery_options || []).map(opt => `
              <tr>
                <td><strong>${escapeHtml(opt.option_id)}</strong>: ${escapeHtml(opt.type || opt.option_type || 'Playbook')}</td>
                <td>${escapeHtml(opt.action)}</td>
                <td><strong>$${(opt.indicative_cost_usd || 0).toLocaleString()}</strong></td>
                <td>${opt.expected_time_to_resolve_days} day(s)</td>
                <td><span class="badge ${opt.feasibility === 'High' ? 'badge-healthy' : 'badge-warning'}">${escapeHtml(opt.feasibility)}</span></td>
                <td><span class="badge ${getStatusBadgeClass(opt.status)}">${escapeHtml(opt.status || 'Proposed')}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Assumptions -->
    <div style="background-color: #f1f5f9; padding: 10px 14px; border-radius: 6px; font-size: 0.74rem; color: var(--text-secondary);">
      <strong>Model Assumptions & Disclaimers:</strong>
      <ul style="margin-top: 4px; padding-left: 18px;">
        ${(data.assumptions || []).map(a => `<li>${escapeHtml(a)}</li>`).join('')}
      </ul>
    </div>
  `;
}

/**
 * Phase 5: Render Persisted Recovery Plans & Advanced Intelligence Panel
 */
function renderRecoveryPlans(plans) {
  if (!elements.recoveryPlansContent) return;

  if (!plans || plans.length === 0) {
    if (elements.recoveryPlanStatusBadge) elements.recoveryPlanStatusBadge.textContent = '0 Plans';
    elements.recoveryPlansContent.innerHTML = `
      <div class="placeholder-card">
        <div class="placeholder-icon" aria-hidden="true">🤖</div>
        <h3>No Persisted Recovery Plans</h3>
        <p>
          Click <strong>"Analyze Disruption"</strong> on an incident (e.g. SH-101) to run the multi-agent investigation. The resulting mitigation options, business impact metrics, and trade-off comparisons will persist in SQLite for human approval and safe simulation.
        </p>
      </div>`;
    return;
  }

  if (elements.recoveryPlanStatusBadge) {
    elements.recoveryPlanStatusBadge.textContent = `${plans.length} Persisted Plan(s)`;
  }

  elements.recoveryPlansContent.innerHTML = plans.map(plan => {
    const risk = plan.risk_assessment || {};
    const intel = plan.recommendation_intelligence || {};
    const riskScore = plan.risk_score || risk.risk_score || 0;
    const revAtRisk = risk.revenue_at_risk_usd || 0;
    const daysToStockout = risk.days_to_stockout || 0;

    return `
      <div style="padding: 24px; border-bottom: 2px solid #e2e8f0; background: var(--bg-card); margin-bottom: 20px; border-radius: 8px; border: 1px solid var(--border-color);">
        <!-- Plan Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; flex-wrap: wrap; gap: 10px;">
          <div>
            <div style="display: flex; align-items: center; gap: 10px;">
              <span class="code-cell" style="font-size: 1.05rem; font-weight: 700;">${escapeHtml(plan.id)}</span>
              <span class="badge ${getStatusBadgeClass(plan.status)}">${escapeHtml(plan.status)}</span>
              <span class="badge ${plan.severity === 'Critical' ? 'badge-critical' : 'badge-warning'}">${escapeHtml(plan.severity)}</span>
              <span class="badge badge-transit" style="font-weight: 700;">Risk Score: ${riskScore.toFixed(1)}/100</span>
            </div>
            <div style="font-size: 0.92rem; font-weight: 600; color: var(--text-main); margin-top: 6px;">
              Shipment Target: <code>${escapeHtml(plan.shipment_id)}</code> &bull; Product: <strong>${escapeHtml(plan.product)}</strong>
            </div>
            <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 3px;">
              Created: ${plan.created_at ? new Date(plan.created_at).toLocaleString() : 'Recent'} &bull; Primary Recommendation: <em>${escapeHtml(plan.recommended_plan || 'N/A')}</em>
            </div>
          </div>
        </div>

        <!-- Phase 5 Recovery Intelligence Panel -->
        <div style="background: rgba(30, 41, 59, 0.03); border: 1px solid var(--border-color); border-radius: 6px; padding: 16px; margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">
            <div style="font-weight: 700; font-size: 0.88rem; color: var(--blue-primary); display: flex; align-items: center; gap: 6px;">
              <span>🧠</span> Multi-Agent Recommendation Intelligence & Decision Rationale
            </div>
            <span class="badge badge-healthy" style="font-size: 0.72rem;">Evidence-Based Ranking</span>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 14px;">
            <div style="background: #fff; padding: 10px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
              <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Time Until Stockout</div>
              <div style="font-size: 1.15rem; font-weight: 700; color: ${daysToStockout <= 2 ? '#b91c1c' : '#d97706'}; margin-top: 2px;">
                ${daysToStockout.toFixed(1)} Days
              </div>
            </div>
            <div style="background: #fff; padding: 10px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
              <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Revenue at Risk Exposure</div>
              <div style="font-size: 1.15rem; font-weight: 700; color: #b91c1c; margin-top: 2px;">
                $${revAtRisk.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
              </div>
            </div>
            <div style="background: #fff; padding: 10px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
              <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Expected Net Benefit</div>
              <div style="font-size: 1.15rem; font-weight: 700; color: #15803d; margin-top: 2px;">
                +$${(intel.expected_net_benefit_usd || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
              </div>
            </div>
            <div style="background: #fff; padding: 10px 12px; border-radius: 6px; border: 1px solid #e2e8f0;">
              <div style="font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600;">Resolution Velocity</div>
              <div style="font-size: 1.15rem; font-weight: 700; color: var(--text-main); margin-top: 2px;">
                ${intel.expected_resolution_days || 1} Day(s)
              </div>
            </div>
          </div>

          <!-- Rationale -->
          <div style="font-size: 0.82rem; line-height: 1.5; color: var(--text-main); margin-bottom: 8px;">
            <strong>Selection Rationale:</strong> ${escapeHtml(intel.selection_rationale || 'Ranked highest by composite ROI, shortage mitigation speed, and residual risk reduction.')}
          </div>

          ${intel.tradeoff_note ? `
            <div style="background: #fffbeb; border: 1px solid #fef3c7; color: #92400e; padding: 8px 12px; border-radius: 4px; font-size: 0.78rem; margin-bottom: 8px;">
              <strong>Trade-Off Analysis:</strong> ${escapeHtml(intel.tradeoff_note)}
            </div>
          ` : ''}

          <!-- Considered Alternatives -->
          ${intel.considered_alternatives && intel.considered_alternatives.length > 0 ? `
            <div style="margin-top: 10px; font-size: 0.78rem;">
              <strong style="color: var(--text-secondary);">Other Playbooks Evaluated:</strong>
              <ul style="margin: 4px 0 0 18px; padding: 0; color: var(--text-muted);">
                ${intel.considered_alternatives.map(ca => `
                  <li><strong>${escapeHtml(ca.option_id)} (${escapeHtml(ca.name)}):</strong> ${escapeHtml((ca.reasons_ranked_lower || []).join('; '))}</li>
                `).join('')}
              </ul>
            </div>
          ` : ''}
        </div>

        <!-- Options Comparison Table with Approval & Simulation Controls -->
        <div class="table-responsive" style="margin-top: 10px;">
          <table class="enterprise-table" style="font-size: 0.82rem;">
            <thead>
              <tr>
                <th style="width: 75px;">Option</th>
                <th>Mitigation Playbook</th>
                <th style="width: 100px;">Indicative Cost</th>
                <th style="width: 85px;">Turnaround</th>
                <th style="width: 110px;">Shortage Relief</th>
                <th style="width: 110px;">Avoided Loss</th>
                <th style="width: 110px;">Net Benefit</th>
                <th style="width: 80px;">Feasibility</th>
                <th style="width: 105px;">Approval State</th>
                <th style="width: 210px; text-align: right;">Human Governance</th>
              </tr>
            </thead>
            <tbody>
              ${(plan.options || []).map(opt => {
                const isApproved = opt.status === 'Approved';
                const isSimulated = opt.status === 'Simulated';
                const isRejected = opt.status === 'Rejected';

                return `
                  <tr>
                    <td class="code-cell"><strong>${escapeHtml(opt.option_id)}</strong></td>
                    <td>
                      <div><strong>${escapeHtml(opt.name)}</strong></div>
                      <div style="font-size: 0.74rem; color: var(--text-secondary); margin-top: 2px;">${escapeHtml(opt.action)}</div>
                      ${opt.tradeoff_summary ? `
                        <div style="font-size: 0.70rem; color: #0284c7; margin-top: 2px;">${escapeHtml(opt.tradeoff_summary)}</div>
                      ` : ''}
                      ${opt.latest_decision ? `
                        <div style="font-size: 0.72rem; color: #475569; margin-top: 4px; background: #f8fafc; padding: 2px 6px; border-radius: 4px; display: inline-block;">
                          Decision: <strong>${escapeHtml(opt.latest_decision.decision)}</strong> by ${escapeHtml(opt.latest_decision.decided_by)} (${escapeHtml(opt.latest_decision.reason || 'No notes')})
                        </div>
                      ` : ''}
                    </td>
                    <td><strong style="color: var(--text-main);">$${(opt.indicative_cost_usd || 0).toLocaleString()}</strong></td>
                    <td>${opt.expected_time_to_resolve_days} day(s)</td>
                    <td><span style="color: #15803d; font-weight: 600;">+${(opt.shortage_reduction_units || 0)} units</span></td>
                    <td>$${(opt.avoided_revenue_loss_usd || 0).toLocaleString()}</td>
                    <td><strong style="color: ${(opt.net_indicative_benefit_usd || 0) >= 0 ? '#15803d' : '#b91c1c'};">+$${(opt.net_indicative_benefit_usd || 0).toLocaleString()}</strong></td>
                    <td><span class="badge ${opt.feasibility === 'High' ? 'badge-healthy' : 'badge-warning'}">${escapeHtml(opt.feasibility)}</span></td>
                    <td><span class="badge ${getStatusBadgeClass(opt.status)}">${escapeHtml(opt.status)}</span></td>
                    <td style="text-align: right;">
                      <div style="display: flex; gap: 6px; justify-content: flex-end; align-items: center;">
                        ${!isApproved && !isSimulated ? `
                          <button class="btn btn-sm btn-outline" style="color: #15803d; border-color: #bbf7d0;" onclick="handleOptionDecision(${opt.id}, '${escapeHtml(opt.option_id)}', '${escapeHtml(opt.name)}', ${(opt.indicative_cost_usd || 0)}, 'Approved')">
                            ✓ Approve
                          </button>
                        ` : ''}

                        ${!isRejected && !isSimulated ? `
                          <button class="btn btn-sm btn-outline" style="color: #b91c1c; border-color: #fecaca;" onclick="handleOptionDecision(${opt.id}, '${escapeHtml(opt.option_id)}', '${escapeHtml(opt.name)}', ${(opt.indicative_cost_usd || 0)}, 'Rejected')">
                            ✕ Reject
                          </button>
                        ` : ''}

                        ${isApproved ? `
                          <button class="btn btn-sm btn-primary" onclick="handleSimulateOption(${opt.id}, '${escapeHtml(opt.option_id)}', '${escapeHtml(opt.name)}', ${(opt.indicative_cost_usd || 0)})">
                            ⚡ Simulate Execution
                          </button>
                        ` : ''}

                        ${isSimulated ? `
                          <span style="font-size: 0.74rem; color: #15803d; font-weight: 600;">
                            ✓ Simulated
                          </span>
                        ` : ''}
                      </div>
                    </td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>

        <!-- Assumptions & Limitations Accordion / Notes -->
        <details style="margin-top: 14px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 12px; font-size: 0.76rem; color: var(--text-secondary);">
          <summary style="cursor: pointer; font-weight: 600; color: var(--text-main);">
            View Calculation Assumptions & Data Limitations (${(plan.assumptions || []).length} Recorded)
          </summary>
          <div style="margin-top: 8px; line-height: 1.5;">
            <strong>Underlying Assumptions:</strong>
            <ul style="margin: 4px 0 8px 18px;">
              ${(plan.assumptions || []).map(a => `<li>${escapeHtml(a)}</li>`).join('')}
            </ul>
            <strong>Known Data Limitations:</strong>
            <ul style="margin: 4px 0 0 18px;">
              <li>Carrier spot rates reflect deterministic regional tariffs; no binding commercial contracts committed.</li>
              <li>Warehouse stock burn rate assumes continuous linear production demand.</li>
            </ul>
          </div>
        </details>
      </div>
    `;
  }).join('');
}

/**
 * Handle Human Approval / Rejection Decision with Confirmation & Prompt
 */
window.handleOptionDecision = async function(optionDbId, optionCode, optionName, cost, decision) {
  const actionText = decision === 'Approved' ? 'APPROVE' : 'REJECT';
  const confirmMsg = `Confirm Human Governance Decision:\n\nAre you sure you want to ${actionText} playbook ${optionCode} ("${optionName}") with an indicative budget of $${cost.toLocaleString()}?\n\n(Simulated Operator: Supply Chain Director)`;

  if (!confirm(confirmMsg)) return;

  const reason = prompt(`Enter optional governance sign-off notes for ${decision.toLowerCase()}ing ${optionCode}:`, `${decision} by operator for inventory mitigation.`);
  if (reason === null) return; // User cancelled prompt

  try {
    const res = await fetch(`/api/recovery-options/${optionDbId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        decision: decision,
        reason: reason || `Operator sign-off: ${decision}`,
        decided_by: 'Simulated Operator (Supply Chain Director)'
      })
    });

    const data = await res.json();
    if (!res.ok || data.status !== 'success') {
      throw new Error(data.message || `HTTP ${res.status}`);
    }

    showAlert('success', `<strong>Human Decision Recorded:</strong> Playbook <code>${escapeHtml(optionCode)}</code> has been marked as <strong>${escapeHtml(decision)}</strong> in SQLite.`);

    // Refresh recovery plans & audit trail to show updated status
    await Promise.all([fetchRecoveryPlans(), fetchAuditEvents()]);
  } catch (err) {
    console.error('Approval decision error:', err);
    showAlert('danger', `<strong>Decision Failed:</strong> ${escapeHtml(err.message)}`);
  }
};

/**
 * Handle Safe Simulation Execution for Approved Options
 */
window.handleSimulateOption = async function(optionDbId, optionCode, optionName, cost) {
  const confirmMsg = `Safe Action Simulation:\n\nExecute sandbox simulation for approved playbook ${optionCode} ("${optionName}")?\n\nAllocated Indicative Budget: $${cost.toLocaleString()}\n\nNote: This is a safe simulation. Zero actual supplier orders or carrier bookings will be placed.`;

  if (!confirm(confirmMsg)) return;

  try {
    const res = await fetch(`/api/recovery-options/${optionDbId}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const data = await res.json();
    if (!res.ok || data.status !== 'success') {
      throw new Error(data.message || `HTTP ${res.status}`);
    }

    showAlert('success', `<strong>Simulation Succeeded:</strong> Playbook <code>${escapeHtml(optionCode)}</code> safely executed in sandbox. Status updated to <strong>Simulated</strong>.`);

    // Refresh views
    await Promise.all([fetchRecoveryPlans(), fetchAuditEvents()]);
  } catch (err) {
    console.error('Simulation error:', err);
    showAlert('danger', `<strong>Simulation Blocked:</strong> ${escapeHtml(err.message)}`);
  }
};

/**
 * Phase 4: Render Immutable Audit Trail from SQLite with State Transitions & Details
 */
function renderAuditTrail(events) {
  if (!elements.auditTrailTableBody) return;

  if (!events || events.length === 0) {
    elements.auditTrailTableBody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; padding: 24px; color: var(--text-muted);">
          No audit records found matching current filter criteria.
        </td>
      </tr>`;
    return;
  }

  elements.auditTrailTableBody.innerHTML = events.map(ev => {
    let typeBadge = 'badge-transit';
    if (ev.event_type.includes('APPROVED')) typeBadge = 'badge-healthy';
    else if (ev.event_type.includes('REJECTED') || ev.event_type.includes('FAILED')) typeBadge = 'badge-critical';
    else if (ev.event_type.includes('SIMULATION') || ev.event_type.includes('CHANGED')) typeBadge = 'badge-warning';

    let outcomeBadge = 'badge-healthy';
    if (ev.outcome === 'FAILED') outcomeBadge = 'badge-critical';
    else if (ev.outcome === 'WARNING') outcomeBadge = 'badge-warning';

    const dateStr = ev.timestamp ? new Date(ev.timestamp).toLocaleString() : 'N/A';

    return `
      <tr>
        <td style="font-size: 0.74rem; color: var(--text-muted); font-family: monospace;">
          ${escapeHtml(dateStr)}
        </td>
        <td>
          <span class="badge ${typeBadge}" style="font-size: 0.68rem;">${escapeHtml(ev.event_type)}</span>
        </td>
        <td class="code-cell" style="font-size: 0.75rem;">
          ${escapeHtml(ev.associated_shipment || ev.associated_plan || 'SYSTEM')}
        </td>
        <td>
          <div style="font-weight: 600; font-size: 0.76rem;">${escapeHtml(ev.actor_name)}</div>
          <div style="font-size: 0.68rem; color: var(--text-muted);">${escapeHtml(ev.actor_type)}</div>
        </td>
        <td style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.4;">
          ${escapeHtml(ev.description)}
          ${ev.previous_status || ev.new_status ? `
            <div style="margin-top: 3px; font-size: 0.70rem; color: var(--text-muted);">
              State: <code>${escapeHtml(ev.previous_status || 'Init')}</code> &rarr; <code>${escapeHtml(ev.new_status || 'New')}</code>
            </div>
          ` : ''}
        </td>
        <td style="text-align: center;">
          <span class="badge ${outcomeBadge}" style="font-size: 0.66rem; padding: 2px 6px;">${escapeHtml(ev.outcome || 'SUCCESS')}</span>
        </td>
        <td style="text-align: center;">
          <button class="btn btn-sm btn-outline" style="font-size: 0.7rem; padding: 2px 6px;" onclick="viewAuditEventDetail(${ev.id})" title="View Audit Payload">
            Inspect
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

/**
 * Utility helper for status badge CSS classes
 */
function getStatusBadgeClass(status) {
  switch (status) {
    case 'Approved':
    case 'Completed':
      return 'badge-healthy';
    case 'Rejected':
    case 'Cancelled':
      return 'badge-critical';
    case 'Simulated':
    case 'Pending Approval':
      return 'badge-warning';
    case 'Proposed':
    default:
      return 'badge-transit';
  }
}

/**
 * Safe HTML escaping utility
 */
function escapeHtml(str) {
  if (typeof str !== 'string') return str ?? '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
