let currentTab = 'weekly';
let reportsData = { weekly: [], monthly: [], wordclouds: [] };
let selectedReport = null;

document.addEventListener('DOMContentLoaded', () => {
    fetchGitHubStats();
    loadReportsList();
    initTabs();
});

async function fetchGitHubStats() {
    try {
        const response = await fetch('https://api.github.com/repos/dw-dengwei/daily-arXiv-ai-enhanced');
        const data = await response.json();
        document.getElementById('starCount').textContent = data.stargazers_count;
        document.getElementById('forkCount').textContent = data.forks_count;
    } catch (error) {
        document.getElementById('starCount').textContent = '?';
        document.getElementById('forkCount').textContent = '?';
    }
}

async function loadReportsList() {
    try {
        const response = await fetch('assets/reports-list.json');
        if (!response.ok) {
            renderEmptyState();
            return;
        }
        reportsData = await response.json();
    } catch (e) {
        reportsData = { weekly: [], monthly: [], wordclouds: [] };
    }
    renderReportList();
}

function initTabs() {
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.tab === currentTab) return;
            currentTab = btn.dataset.tab;
            document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedReport = null;
            renderReportList();
            showPlaceholder();
        });
    });
}

function renderReportList() {
    const listScroll = document.getElementById('reportListScroll');
    const reports = reportsData[currentTab] || [];

    if (reports.length === 0) {
        const typeLabel = currentTab === 'weekly' ? 'weekly' : 'monthly';
        listScroll.innerHTML = `<div class="status-empty">No ${typeLabel} reports available yet.<br><br>Reports are generated automatically by GitHub Actions.</div>`;
        return;
    }

    listScroll.innerHTML = reports.map(filename => {
        const label = filename.replace('.md', '');
        const isWeekly = currentTab === 'weekly';
        const iconSvg = isWeekly
            ? '<svg class="report-item-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19 4H18V2H16V4H8V2H6V4H5C3.89 4 3.01 4.9 3.01 6L3 20C3 21.1 3.89 22 5 22H19C20.1 22 21 21.1 21 20V6C21 4.9 20.1 4 19 4ZM19 20H5V9H19V20ZM7 11H12V16H7V11Z" fill="currentColor"/></svg>'
            : '<svg class="report-item-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9 17H7V10H9V17ZM13 17H11V7H13V17ZM17 17H15V13H17V17ZM19 19H5V5H19V19.1V19ZM19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3Z" fill="currentColor"/></svg>';
        return `<div class="report-item" data-filename="${filename}" onclick="loadReport('${filename}')">${iconSvg}<span>${label}</span></div>`;
    }).join('');
}

async function loadReport(filename) {
    if (selectedReport === filename) return;
    selectedReport = filename;

    // Highlight selected item
    document.querySelectorAll('.report-item').forEach(item => {
        item.classList.toggle('active', item.dataset.filename === filename);
    });

    const viewer = document.getElementById('reportViewer');
    viewer.innerHTML = '<div class="status-loading">Loading report...</div>';

    try {
        const path = `data/${currentTab}/${filename}`;
        const response = await fetch(path);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        let markdown = await response.text();

        // Fix relative image paths from monthly reports (../../assets/ -> assets/)
        markdown = markdown.replace(/\(\.\.\/\.\.\/assets\//g, '(assets/');

        // Configure marked with GFM (GitHub Flavored Markdown) and tables
        marked.use({
            gfm: true,
            breaks: false
        });

        const html = marked.parse(markdown);
        viewer.innerHTML = `<div class="markdown-body">${html}</div>`;
    } catch (e) {
        viewer.innerHTML = '<div class="status-error">Failed to load report. The file may not be available yet.</div>';
    }
}

function showPlaceholder() {
    const viewer = document.getElementById('reportViewer');
    viewer.innerHTML = `
        <div class="report-viewer-placeholder">
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2ZM18 20H6V4H13V9H18V20ZM9 13H15V15H9V13ZM9 17H15V19H9V17ZM9 9H12V11H9V9Z" fill="currentColor"/>
            </svg>
            <p>Select a report from the list to view it</p>
        </div>`;
}

function renderEmptyState() {
    document.getElementById('reportListScroll').innerHTML =
        '<div class="status-empty">Reports index not found. Please generate reports first.</div>';
}