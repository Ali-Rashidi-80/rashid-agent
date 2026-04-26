// ارسال فرم و دریافت پاسخ
let currentData = null;
const API_BASE = window.location.origin;
const ui = {
  form: document.getElementById('dataForm'),
  input: document.getElementById('textInput'),
  output: document.getElementById('output'),
  submitBtn: document.getElementById('submitBtn'),
  applyBtn: document.getElementById('applyChangesBtn'),
  statusBar: document.getElementById('statusBar'),
  pathDisplay: document.getElementById('selectedPathDisplay'),
  choosePathBtn: document.getElementById('choosePathBtn'),
  refreshPathBtn: document.getElementById('refreshPathBtn'),
  clearOutputBtn: document.getElementById('clearOutputBtn')
};
const STORAGE_KEYS = {
  prompt: 'maho_prompt',
  selectedPath: 'maho_selected_path'
};

function setStatus(message, type = 'default') {
  if (!ui.statusBar) return;
  ui.statusBar.textContent = message;
  ui.statusBar.classList.remove('ok', 'warn', 'error');
  if (type === 'ok' || type === 'warn' || type === 'error') {
    ui.statusBar.classList.add(type);
  }
}

function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (_) {
    // ignore storage failure
  }
}

function readFromStorage(key) {
  try {
    return localStorage.getItem(key);
  } catch (_) {
    return null;
  }
}

function renderLoadingSkeleton() {
  return `
    <div class="item output-card">
      <section class="result-section skeleton-card">
        <div class="skeleton-line w-40"></div>
        <div class="skeleton-line w-90"></div>
        <div class="skeleton-line w-80"></div>
      </section>
      <section class="result-section skeleton-card">
        <div class="skeleton-line w-55"></div>
        <div class="skeleton-code"></div>
      </section>
    </div>
  `;
}

function setLoading(loading, message = 'در حال پردازش...', resetStatusOnFinish = false) {
  if (ui.submitBtn) {
    ui.submitBtn.disabled = loading;
    ui.submitBtn.textContent = loading ? 'در حال ارسال...' : 'ارسال';
  }
  if (ui.applyBtn && loading) {
    ui.applyBtn.disabled = true;
  }
  if (ui.choosePathBtn) ui.choosePathBtn.disabled = loading;
  if (ui.refreshPathBtn) ui.refreshPathBtn.disabled = loading;
  if (loading) {
    setStatus(message, 'warn');
  } else if (resetStatusOnFinish) {
    setStatus('آماده');
  }
}

function escapeForMarkdown(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(/[&<>]/g, (ch) => (
    ch === '&' ? '&amp;' : ch === '<' ? '&lt;' : '&gt;'
  ));
}

function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[ch]));
}

function getPrettyLanguage(lang) {
  const map = {
    js: 'JavaScript',
    javascript: 'JavaScript',
    ts: 'TypeScript',
    typescript: 'TypeScript',
    py: 'Python',
    python: 'Python',
    cpp: 'C++',
    c: 'C',
    css: 'CSS',
    html: 'HTML',
    json: 'JSON',
    md: 'Markdown',
    markdown: 'Markdown',
    text: 'Text',
    jsx: 'JSX'
  };
  return map[(lang || '').toLowerCase()] || (lang || 'Code');
}

function countCodeLines(code) {
  if (!code) return 0;
  return String(code).split('\n').length;
}

async function parseErrorResponse(response) {
  try {
    const body = await response.json();
    if (body?.detail) return body.detail;
    if (body?.message) return body.message;
  } catch (_) {
    // Ignore JSON parsing error and fallback to HTTP status
  }
  return `HTTP error! status: ${response.status}`;
}

ui.form.addEventListener('submit', async function(event) {
  event.preventDefault();
  const text = ui.input.value.trim();
  const outputDiv = ui.output;
  if (!text) {
    setStatus('متن درخواست خالی است.', 'warn');
    return;
  }

  setLoading(true, 'در حال تولید پاسخ...');
  outputDiv.innerHTML = renderLoadingSkeleton();

  try {
    const response = await fetch(`${API_BASE}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    if (!response.ok) throw new Error(await parseErrorResponse(response));
    const data = await response.json();

    // ذخیره پاسخ در متغیر گلوبال
    currentData = data; 

    outputDiv.innerHTML = formatJsonToItems(data);
    ui.applyBtn.disabled = !(Array.isArray(data.edits) && data.edits.length > 0);
    setStatus('پاسخ دریافت شد. در صورت نیاز می‌توانید تغییرات را اعمال کنید.', 'ok');
    attachApplyChangesListener();
  } catch (error) {
    console.error('Error:', error);
    outputDiv.innerHTML = `<p style="color: #ff6b6b;">خطا در ارسال داده‌ها: ${error.message}</p>`;
    setStatus(`خطا در تولید پاسخ: ${error.message}`, 'error');
  } finally {
    setLoading(false);
  }
});

ui.input.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    event.preventDefault();
    ui.form.requestSubmit();
  }
});

let savePromptTimer = null;
ui.input.addEventListener('input', () => {
  clearTimeout(savePromptTimer);
  savePromptTimer = setTimeout(() => {
    saveToStorage(STORAGE_KEYS.prompt, ui.input.value);
  }, 250);
});

if (ui.choosePathBtn) {
  ui.choosePathBtn.addEventListener('click', () => {
    requestNewPathFromServer();
  });
}

if (ui.refreshPathBtn) {
  ui.refreshPathBtn.addEventListener('click', () => {
    checkAndSelectPath();
  });
}

if (ui.clearOutputBtn) {
  ui.clearOutputBtn.addEventListener('click', () => {
    ui.output.innerHTML = '';
    currentData = null;
    if (ui.applyBtn) ui.applyBtn.disabled = true;
    setStatus('خروجی پاک شد.', 'ok');
  });
}





// تابع برای تبدیل JSON به آیتم‌ها با استفاده از Markdown

function renderCodeBlock(code, language, title) {
  const codeText = code || 'بدون کد';
  const safeId = `code-${Math.random().toString(36).slice(2, 10)}`;
  const safeLanguage = escapeHtml(language || 'text');
  const lineCount = countCodeLines(codeText);
  const headerTitle = title || 'کد جدید';
  return `
    <section class="code-container">
      <div class="code-header">
        <span class="code-title">${escapeHtml(headerTitle)}</span>
        <span class="code-meta">${escapeHtml(getPrettyLanguage(language))} • ${lineCount} خط</span>
        <button class="copy-btn" type="button" data-copy-target="${safeId}" aria-label="کپی کد">
          <span class="copy-btn-text">کپی</span>
        </button>
      </div>
      <pre><code id="${safeId}" class="language-${safeLanguage}">${escapeHtml(codeText)}</code></pre>
    </section>
  `;
}

function formatJsonToItems(data) {
  const sections = [];

  if (data.message) {
    sections.push(`
      <section class="result-section">
        <h3>پیام</h3>
        <p>${escapeHtml(data.message)}</p>
      </section>
    `);
  }

  if (data.pip && data.pip.trim() !== '') {
    sections.push(`
      <section class="result-section">
        <h3>کتاب‌خونه‌ها</h3>
        <div class="pip-box">${escapeHtml(data.pip)}</div>
        <button id="install-lib-button" class="inline-action-btn" type="button">نصب کتابخانه‌ها</button>
      </section>
    `);
  }

  if (data.log) {
    sections.push(`
      <section class="result-section">
        <h3>گزارش</h3>
        <p>${escapeHtml(data.log)}</p>
      </section>
    `);
  }

  if (Array.isArray(data.edits) && data.edits.length > 0) {
    const editsHtml = data.edits.map((edit, index) => {
      const path = edit?.path || 'نامشخص';
      const info = edit?.info || 'بدون توضیحات';
      const log = edit?.log || 'بدون گزارش';
      const subEdits = Array.isArray(edit?.edits) ? edit.edits : [];
      const subEditsHtml = subEdits.map((subEdit, subIndex) => {
        let language = 'text';
        if (typeof path === 'string' && path.endsWith('.md')) {
          language = 'markdown';
        } else if (path === '.gitignore') {
          language = 'text';
        } else {
          language = detectLanguage(subEdit?.new_code || '');
        }
        return `
          <article class="sub-edit-card">
            <div class="sub-edit-meta">
              <span>ویرایش ${subIndex + 1}</span>
              <span>خطوط ${escapeHtml(subEdit?.start_number_line || '؟')} تا ${escapeHtml(subEdit?.end_number_line || '؟')}</span>
              <span>نوع: ${escapeHtml(subEdit?.type || 'نامشخص')}</span>
            </div>
            ${renderCodeBlock(subEdit?.new_code || 'بدون کد', language, 'کد جدید')}
          </article>
        `;
      }).join('');

      return `
        <article class="edit-card">
          <header class="edit-card-header">
            <h4>ویرایش ${index + 1}</h4>
            <code class="path-chip">${escapeHtml(path)}</code>
          </header>
          <div class="edit-details">
            <p><strong>گزارش:</strong> ${escapeHtml(log)}</p>
            <p><strong>توضیحات:</strong> ${escapeHtml(info)}</p>
          </div>
          <div class="sub-edits">${subEditsHtml || '<p class="empty-subedits">ویرایشی ثبت نشده است.</p>'}</div>
        </article>
      `;
    }).join('');

    sections.push(`
      <section class="result-section">
        <h3>تغییرات پیشنهادی</h3>
        <div class="edits-grid">${editsHtml}</div>
      </section>
    `);
  }

  if (sections.length === 0) {
    sections.push('<section class="result-section"><p>خروجی قابل نمایشی دریافت نشد.</p></section>');
  }

  const html = `<div class="item output-card">${sections.join('')}</div>`;

  setTimeout(() => {
    attachInstallButtonListener();
    Prism.highlightAll();
  }, 0);

  return html;
}



// تابع کمکی برای تشخیص زبان

function detectLanguage(code) {
  if (typeof code !== 'string' || code.trim() === '') {
    return 'text';
  }

  // React/JSX

  if (code.includes('import React') || code.includes('export default') || /<[^>]+>/.test(code) && code.includes('className')) {

    return 'jsx';

  }

  // Next.js

  if (code.includes('import {') && (code.includes("from 'next/") || code.includes('useRouter') || code.includes('useState'))) {

    return 'jsx';

  }

  // C++

  if (code.includes('#include') || code.includes('std::') || code.includes('cout') || code.includes('cin')) {

    return 'cpp';

  }

  // Python

  if (code.includes('import ') || code.includes('def ') || code.includes('class ') || code.includes('print(')) {

    return 'python';

  }

  // JavaScript

  if (code.includes('function ') || code.includes('const ') || code.includes('let ') || code.includes('var ')) {

    return 'javascript';

  }

  // HTML

  if (code.includes('<') && code.includes('>') && !code.includes('className')) {

    return 'html';

  }

  // CSS

  if (code.includes(':') && code.includes(';') && !code.includes('<') && !code.includes('function ') && !code.includes('const ')) {

    return 'css';

  }

  return 'python';

}


function attachInstallButtonListener() {
  const installButton = document.getElementById('install-lib-button');
  if (installButton) {
    installButton.replaceWith(installButton.cloneNode(true));
    const installButtonFresh = document.getElementById('install-lib-button');
    if (!installButtonFresh) return;

    installButtonFresh.addEventListener('click', async () => {
      try {
        const response = await fetch(`${API_BASE}/pip`);
        if (!response.ok) throw new Error(await parseErrorResponse(response));
        const data = await response.json();
        alert(data.status === 'success' ? 'کتابخانه‌ها با موفقیت نصب شدند.' : `خطا در نصب کتابخانه‌ها: ${data.detail || data.error || 'نامشخص'}`);
      } catch (error) {
        console.error('Error:', error);
        alert(`مشکلی در نصب کتابخانه‌ها پیش آمد: ${error.message}`);
      }
    });
  }
}



// اتصال رویداد به دکمه اعمال تغییرات
function attachApplyChangesListener() {
  const applyChangesBtn = document.getElementById('applyChangesBtn');
  if (applyChangesBtn) {
    applyChangesBtn.removeEventListener('click', handleApplyChanges); // حذف رویداد قبلی
    applyChangesBtn.addEventListener('click', handleApplyChanges);
  }
}


async function handleApplyChanges() {
  if (!currentData || !Array.isArray(currentData.edits) || currentData.edits.length === 0) {
    alert('تغییری برای اعمال وجود ندارد.');
    return;
  }

  try {
    setLoading(true, 'در حال اعمال تغییرات...');
    const response = await fetch(`${API_BASE}/set_json`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(getEditsFromPage())
    });

    if (!response.ok) throw new Error(await parseErrorResponse(response));
    const data = await response.json();

    setStatus('تغییرات با موفقیت اعمال شد.', 'ok');
    await populateBackupVersions();
    console.log('پاسخ از سرور:', data);
  } catch (error) {
    console.error('خطا در ارسال درخواست:', error);
    setStatus(`خطا در اعمال تغییرات: ${error.message}`, 'error');
  } finally {
    setLoading(false);
    ui.applyBtn.disabled = !(currentData && Array.isArray(currentData.edits) && currentData.edits.length > 0);
  }
}


function getEditsFromPage() {
  // اگر داده‌ای دریافت شده باشد، آن را برمی‌گردانیم، در غیر این صورت یک پیام وضعیت
  if (currentData) {
    return currentData;
  } else {
    console.warn("هیچ داده‌ای برای اعمال تغییرات یافت نشد.");
    return { message: 'خطا: داده‌ای برای اعمال تغییرات وجود ندارد.' };
  }
}



async function populateBackupVersions() {
  try {
    const response = await fetch(`${API_BASE}/list_versions`);
    if (!response.ok) throw new Error(await parseErrorResponse(response));
    const data = await response.json();
    const versionDropdown = document.getElementById('backupVersion');
    if (versionDropdown) {
      const versions = Array.isArray(data.versions) ? data.versions : [];
      versionDropdown.innerHTML = versions.map(version =>
        `<option value="${version}">Version ${version}</option>`
      ).join('');
    }
  } catch (error) {
    console.error('Error fetching backup versions:', error);
    setStatus(`خطا در دریافت نسخه‌های بکاپ: ${error.message}`, 'warn');
  }
}

function showRestoreDialog() {
  const versionDropdown = document.getElementById('backupVersion');
  const version = versionDropdown?.value;
  if (!version) {
    setStatus('نسخه‌ای برای بازیابی پیدا نشد.', 'warn');
    return;
  }
  if (confirm(`آیا مطمئن هستید که می‌خواهید نسخه ${version} را بازیابی کنید؟`)) {
    restoreBackup(version);
  }
}

async function restoreBackup(version) {
  try {
    const response = await fetch(`${API_BASE}/restore_version/${version}`, { method: 'POST' });
    if (!response.ok) throw new Error(await parseErrorResponse(response));
    const data = await response.json();
    setStatus(data.message || 'نسخه با موفقیت بازیابی شد.', 'ok');
  } catch (error) {
    console.error('Error restoring version:', error);
    setStatus('خطا در بازیابی نسخه.', 'error');
  }
}

function createBackupRestoreElements() {
  const formContainer = document.querySelector('.form-container') || document.body;

  formContainer.insertAdjacentHTML('beforeend', `
    <div class="backup-tools">
      <label for="backupVersion">انتخاب نسخه بکاپ:</label>
      <select id="backupVersion" name="backupVersion"></select>
      <button type="button" id="restoreBackupBtn" class="danger-btn">بازیابی بکاپ</button>
    </div>
  `);

  document.getElementById('restoreBackupBtn').addEventListener('click', showRestoreDialog);
  populateBackupVersions();
}

// اجرای اولیه
(function() {
  createBackupRestoreElements();
})();


async function requestNewPathFromServer() {
  try {
    setLoading(true, 'در حال انتخاب مسیر پروژه...');
    const response = await fetch(`${API_BASE}/set_path`, { method: 'POST' });
    if (!response.ok) throw new Error(await parseErrorResponse(response));
    const data = await response.json();
    if (data.status === 'success' && data.path) {
      displaySelectedPath(data.path);
      setStatus('مسیر پروژه با موفقیت به‌روزرسانی شد.', 'ok');
      await populateBackupVersions();
    } else {
      throw new Error(data.error || data.message || 'خطا در به‌روزرسانی مسیر');
    }
  } catch (error) {
    console.error('⚠️ خطا:', error);
    setStatus(`خطا در انتخاب مسیر: ${error.message}`, 'error');
  } finally {
    setLoading(false);
  }
}

function displaySelectedPath(path) {
  let displayDiv = document.getElementById('selectedPathDisplay');
  if (!displayDiv) {
    displayDiv = document.createElement('div');
    displayDiv.id = 'selectedPathDisplay';
    document.body.appendChild(displayDiv);
  }
  displayDiv.innerHTML = `📂 <strong>مسیر فعال پروژه:</strong> ${escapeForMarkdown(path)}`;
  if (path) saveToStorage(STORAGE_KEYS.selectedPath, String(path));
}

async function checkAndSelectPath() {
  try {
    const response = await fetch(`${API_BASE}/path`);
    if (!response.ok) throw new Error(await parseErrorResponse(response));
    const data = await response.json();
    if (data.path) {
      displaySelectedPath(data.path);
      setStatus('مسیر پروژه آماده است.', 'ok');
    } else {
      await requestNewPathFromServer();
    }
  } catch (error) {
    console.error('⚠️ خطا در دریافت مسیر:', error);
    setStatus(`خطا در دریافت مسیر: ${error.message}`, 'warn');
  }
}

// اجرای تابع به صورت غیرهمزمان
(async () => {
  const savedPrompt = readFromStorage(STORAGE_KEYS.prompt);
  if (savedPrompt && ui.input && !ui.input.value) {
    ui.input.value = savedPrompt;
  }
  const savedPath = readFromStorage(STORAGE_KEYS.selectedPath);
  if (savedPath) {
    displaySelectedPath(savedPath);
  }
  await checkAndSelectPath();
})();

// افزودن ستاره‌ها
const colors = ['#6d1e78', '#155950', '#9370db', '#ffffff', '#add8e6'];
for (let i = 0; i < 200; i++) {
  const star = document.createElement('div');
  star.classList.add('star');
  Object.assign(star.style, {
    left: `${Math.random() * 100}vw`,
    top: `${Math.random() * 100}vh`,
    animationDelay: `${Math.random() * 2}s`,
    backgroundColor: colors[Math.floor(Math.random() * colors.length)]
  });
  document.body.appendChild(star);
}


document.addEventListener('click', (event) => {
  const button = event.target.closest('.copy-btn');
  if (!button) return;
  copyToClipboard(button);
});

async function writeClipboardText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.style.position = 'fixed';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const copied = document.execCommand('copy');
  document.body.removeChild(textarea);
  if (!copied) {
    throw new Error('copy-fallback-failed');
  }
}

// تابع کپی به کلیپ‌بورد
function copyToClipboard(button) {
  const targetId = button.dataset.copyTarget;
  const codeElement = targetId ? document.getElementById(targetId) : null;
  if (!codeElement) {
    setStatus('کد برای کپی یافت نشد.', 'warn');
    return;
  }

  const text = codeElement.textContent || codeElement.innerText;
  writeClipboardText(text).then(() => {
    const label = button.querySelector('.copy-btn-text');
    if (label) label.textContent = 'کپی شد';
    button.classList.add('copied');
    setTimeout(() => {
      if (label) label.textContent = 'کپی';
      button.classList.remove('copied');
    }, 1600);
  }).catch(err => {
    console.error('خطا در کپی: ', err);
    setStatus('کپی ناموفق بود.', 'error');
  });
}
