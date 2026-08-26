/**
 * JOBTRACK - Client-side Interactive Behaviors
 * Handles Theme Switching (Dark/Light), Mobile Sidebar, Chart.js,
 * Job Application Modals, Delete Confirmation, and Pipeline Actions.
 */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initMobileSidebar();
  initToastDismissal();
  initStatusChart();
  initDeleteModal();
  initJobApplyModal();
  initFormHelpers();
});

/* ==========================================
   THEME MANAGEMENT (DARK / LIGHT)
   ========================================== */
function initTheme() {
  const savedTheme = localStorage.getItem('jobtrack_theme') || 'light';
  applyTheme(savedTheme);

  // Bind all theme toggle buttons across pages (header and settings)
  const toggleBtns = document.querySelectorAll('.js-theme-toggle');
  toggleBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      applyTheme(newTheme);
      localStorage.setItem('jobtrack_theme', newTheme);
    });
  });

  // Settings radio switches if present
  const themeRadios = document.querySelectorAll('input[name="themePreference"]');
  themeRadios.forEach((radio) => {
    if (radio.value === savedTheme) radio.checked = true;
    radio.addEventListener('change', (e) => {
      const selected = e.target.value;
      applyTheme(selected);
      localStorage.setItem('jobtrack_theme', selected);
    });
  });
}

function applyTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }

  // Update theme toggle icons
  const toggleIcons = document.querySelectorAll('.js-theme-toggle i');
  toggleIcons.forEach((icon) => {
    if (theme === 'dark') {
      icon.className = 'fa-solid fa-sun';
    } else {
      icon.className = 'fa-solid fa-moon';
    }
  });
}

/* ==========================================
   MOBILE SIDEBAR TOGGLE
   ========================================== */
function initMobileSidebar() {
  const menuBtn = document.getElementById('mobileMenuBtn');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');

  if (menuBtn && sidebar && overlay) {
    menuBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('active');
    });

    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('active');
    });
  }
}

/* ==========================================
   TOAST NOTIFICATIONS
   ========================================== */
function initToastDismissal() {
  const toasts = document.querySelectorAll('.toast');

  toasts.forEach((toast) => {
    const timer = setTimeout(() => {
      dismissToast(toast);
    }, 4500);

    const closeBtn = toast.querySelector('.toast-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        clearTimeout(timer);
        dismissToast(toast);
      });
    }
  });
}

function dismissToast(toast) {
  toast.style.opacity = '0';
  toast.style.transform = 'translateX(100%)';
  setTimeout(() => {
    toast.remove();
  }, 300);
}

/* ==========================================
   DASHBOARD CHART.JS
   ========================================== */
function initStatusChart() {
  const chartCanvas = document.getElementById('statusChart');
  if (!chartCanvas) return;

  const saved = parseInt(chartCanvas.dataset.saved || '0', 10);
  const applied = parseInt(chartCanvas.dataset.applied || '0', 10);
  const screening = parseInt(chartCanvas.dataset.screening || '0', 10);
  const interview = parseInt(chartCanvas.dataset.interview || '0', 10);
  const offer = parseInt(chartCanvas.dataset.offer || '0', 10);
  const rejected = parseInt(chartCanvas.dataset.rejected || '0', 10);
  const withdrawn = parseInt(chartCanvas.dataset.withdrawn || '0', 10);

  const total = saved + applied + screening + interview + offer + rejected + withdrawn;
  const chartContainer = chartCanvas.parentElement;

  if (total === 0) {
    if (chartContainer) {
      chartContainer.innerHTML = `
        <div class="empty-state" style="padding: 24px;">
          <div class="empty-state-icon" style="width: 48px; height: 48px; font-size: 1.25rem;">
            <i class="fa-solid fa-chart-pie"></i>
          </div>
          <div class="empty-state-title" style="font-size: 1rem;">No Application Data</div>
          <p class="empty-state-text" style="font-size: 0.85rem; margin-bottom: 0;">
            Add applications to visualize your hiring pipeline breakdown.
          </p>
        </div>
      `;
    }
    return;
  }

  if (typeof Chart !== 'undefined') {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const textColor = isDark ? '#94A3B8' : '#64748B';

    new Chart(chartCanvas, {
      type: 'doughnut',
      data: {
        labels: ['Saved', 'Applied', 'Screening', 'Interview', 'Offer', 'Rejected', 'Withdrawn'],
        datasets: [{
          data: [saved, applied, screening, interview, offer, rejected, withdrawn],
          backgroundColor: [
            '#64748B', // Saved - Slate Gray
            '#2563EB', // Applied - Blue
            '#8B5CF6', // Screening - Purple
            '#F59E0B', // Interview - Amber
            '#16A34A', // Offer - Green
            '#DC2626', // Rejected - Red
            '#94A3B8'  // Withdrawn - Gray
          ],
          borderWidth: 2,
          borderColor: isDark ? '#1E293B' : '#FFFFFF',
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 10,
              boxHeight: 10,
              borderRadius: 3,
              useBorderRadius: true,
              padding: 12,
              font: {
                family: "'Inter', sans-serif",
                size: 11,
                weight: '500'
              },
              color: textColor
            }
          },
          tooltip: {
            backgroundColor: '#0F172A',
            padding: 12,
            cornerRadius: 8,
            titleFont: {
              family: "'Inter', sans-serif",
              size: 13,
              weight: '600'
            },
            bodyFont: {
              family: "'Inter', sans-serif",
              size: 12
            },
            callbacks: {
              label: function(context) {
                const value = context.raw || 0;
                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                return ` ${context.label}: ${value} (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  }
}

/* ==========================================
   "I'VE APPLIED" CONFIRMATION MODAL (FIND JOBS)
   ========================================== */
function initJobApplyModal() {
  const modal = document.getElementById('jobApplyModal');
  if (!modal) return;

  const cancelBtn = document.getElementById('cancelJobApplyBtn');
  const companyInput = document.getElementById('applyModalCompany');
  const positionInput = document.getElementById('applyModalPosition');
  const locationInput = document.getElementById('applyModalLocation');
  const jobTypeInput = document.getElementById('applyModalJobType');
  const urlInput = document.getElementById('applyModalJobUrl');
  const appDateInput = document.getElementById('applyModalAppDate');
  const followupInput = document.getElementById('applyModalFollowup');

  // Trigger buttons on job cards
  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('.js-apply-confirm-trigger');
    if (trigger) {
      e.preventDefault();

      const company = trigger.dataset.company || '';
      const position = trigger.dataset.position || '';
      const location = trigger.dataset.location || '';
      const jobType = trigger.dataset.jobType || 'Full-time';
      const url = trigger.dataset.url || '';

      if (companyInput) companyInput.value = company;
      if (positionInput) positionInput.value = position;
      if (locationInput) locationInput.value = location;
      if (jobTypeInput) jobTypeInput.value = jobType;
      if (urlInput) urlInput.value = url;

      const today = new Date();
      const todayStr = today.toISOString().split('T')[0];
      if (appDateInput) appDateInput.value = todayStr;

      // Suggest follow up date 7 days later
      const followupDate = new Date(today);
      followupDate.setDate(followupDate.getDate() + 7);
      if (followupInput) followupInput.value = followupDate.toISOString().split('T')[0];

      modal.classList.add('active');
    }
  });

  const closeModal = () => {
    modal.classList.remove('active');
  };

  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) closeModal();
  });
}

/* ==========================================
   DELETE CONFIRMATION MODAL
   ========================================== */
function initDeleteModal() {
  const modal = document.getElementById('deleteModal');
  const confirmForm = document.getElementById('deleteConfirmForm');
  const companySpan = document.getElementById('deleteModalCompany');
  const cancelBtn = document.getElementById('cancelDeleteBtn');

  if (!modal) return;

  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('.js-delete-trigger');
    if (trigger) {
      e.preventDefault();
      const deleteUrl = trigger.dataset.deleteUrl;
      const company = trigger.dataset.company || 'this application';

      if (confirmForm) confirmForm.action = deleteUrl;
      if (companySpan) companySpan.textContent = company;

      modal.classList.add('active');
    }
  });

  const closeModal = () => {
    modal.classList.remove('active');
  };

  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) closeModal();
  });
}

/* ==========================================
   FORM HELPERS
   ========================================== */
function initFormHelpers() {
  const statusSelect = document.getElementById('status');
  const interviewDateField = document.getElementById('interviewDateField');
  const interviewInput = document.getElementById('interview_date');

  if (statusSelect && interviewDateField) {
    const handleStatusChange = () => {
      if (statusSelect.value === 'Interview') {
        interviewDateField.classList.add('highlight-field');
        if (interviewInput && !interviewInput.value) {
          interviewInput.focus();
        }
      } else {
        interviewDateField.classList.remove('highlight-field');
      }
    };

    statusSelect.addEventListener('change', handleStatusChange);
  }
}
