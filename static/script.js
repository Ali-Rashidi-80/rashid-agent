// ارسال فرم و دریافت پاسخ
let currentData = null;

document.getElementById('dataForm').addEventListener('submit', async function(event) {
  event.preventDefault();
  const text = document.getElementById('textInput').value;
  const outputDiv = document.getElementById('output');

  outputDiv.innerHTML = '<p style="color: #b0b0b0;">در حال پردازش...</p>';

  try {
    const response = await fetch('http://127.0.0.1:8000/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();

    // ذخیره پاسخ در متغیر گلوبال
    currentData = data; 

    outputDiv.innerHTML = formatJsonToItems(data);
    document.getElementById('applyChangesBtn').style.display = 'block';
    attachApplyChangesListener();
  } catch (error) {
    console.error('Error:', error);
    outputDiv.innerHTML = `<p style="color: #ff6f61;">خطا در ارسال داده‌ها: ${error.message}</p>`;
  }
});





// تابع برای تبدیل JSON به آیتم‌ها با استفاده از Markdown

function formatJsonToItems(data) {

  let markdown = '';



  if (data.message) {

    markdown += `## پیام:\n${data.message}\n\n`;

  }



  if (data.pip && data.pip.trim() !== '') {

    markdown += `## کتاب‌خونه‌ها:\n${data.pip}\n\n<button id="install-lib-button" style="display:block; margin-top: 10px;">نصب کتابخانه‌ها</button>\n\n`;

  }



  if (data.log) {

    markdown += `## گزارش:\n${data.log}\n\n`;

  }



  if (data.edits && Array.isArray(data.edits)) {

    data.edits.forEach((edit, index) => {

      markdown += `### ویرایش ${index + 1}:\n- **مسیر:** ${edit.path || 'نامشخص'}\n- **گزارش:** ${edit.log || 'بدون گزارش'}\n- **توضیحات:** ${edit.info || 'بدون توضیحات'}\n\n`;

      if (edit.edits && Array.isArray(edit.edits)) {

        edit.edits.forEach((subEdit, subIndex) => {

          markdown += `#### ویرایش ${subIndex + 1}:\n- **خطوط:** ${subEdit.start_number_line || '؟'} تا ${subEdit.end_number_line || '؟'}\n- **نوع:** ${subEdit.type || 'نامشخص'}\n\n**کد جدید:**\n\n\`\`\`auto\n${subEdit.new_code || 'بدون کد'}\n\`\`\`\n\n`;

        });

      }

    });

  }



  let html = marked.parse(markdown);



  // اعمال syntax highlighting با Prism

  html = html.replace(/<pre><code class="language-auto">([\s\S]*?)<\/code><\/pre>/g, (match, code) => {

    let language = detectLanguage(code);

    return `<div class="code-container"><button class="copy-btn" onclick="copyToClipboard(this)">کپی</button><pre><code class="language-${language}">${code}</code></pre></div>`;

  });



  html = `<div class="item">${html}</div>`;



  setTimeout(() => {

    attachInstallButtonListener();

    Prism.highlightAll();

  }, 0);



  return html;

}



// تابع کمکی برای تشخیص زبان

function detectLanguage(code) {

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
    installButton.addEventListener('click', async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/pip');
        const data = await response.json();
        alert(data.status === 'success' ? 'کتابخانه‌ها با موفقیت نصب شدند.' : `خطا در نصب کتابخانه‌ها: ${data.error || 'نامشخص'}`);
      } catch (error) {
        console.error('Error:', error);
        alert('مشکلی در برقراری ارتباط با سرور پیش آمده.');
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
  try {
    const response = await fetch('http://127.0.0.1:8000/set_json', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(getEditsFromPage())
    });

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();

    alert('تغییرات با موفقیت اعمال شد.');
    await populateBackupVersions();
    console.log('پاسخ از سرور:', data);
  } catch (error) {
    console.error('خطا در ارسال درخواست:', error);
    alert(`خطا در ارسال درخواست اعمال تغییرات: ${error.message}`);
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
    const response = await fetch('http://127.0.0.1:8000/list_versions');
    const data = await response.json();
    const versionDropdown = document.getElementById('backupVersion');
    if (versionDropdown) {
      versionDropdown.innerHTML = data.versions.map(version =>
        `<option value="${version}">Version ${version}</option>`
      ).join('');
    }
  } catch (error) {
    console.error('Error fetching backup versions:', error);
  }
}

function showRestoreDialog() {
  const version = document.getElementById('backupVersion').value;
  if (confirm(`آیا مطمئن هستید که می‌خواهید نسخه ${version} را بازیابی کنید؟`)) {
    restoreBackup(version);
  }
}

async function restoreBackup(version) {
  try {
    const response = await fetch(`http://127.0.0.1:8000/restore_version/${version}`, { method: 'POST' });
    const data = await response.json();
    alert(data.message || 'نسخه با موفقیت بازیابی شد.');
  } catch (error) {
    console.error('Error restoring version:', error);
    alert('خطا در بازیابی نسخه.');
  }
}

function createBackupRestoreElements() {
  const formContainer = document.querySelector('.form-container') || document.body;

  formContainer.insertAdjacentHTML('beforeend', `
    <label for="backupVersion">انتخاب نسخه بکاپ:</label>
    <select id="backupVersion" name="backupVersion"></select>
    <button type="button" id="restoreBackupBtn" style="background-color: #dc3545; border-color: #dc3545; color: white;">بازیابی بکاپ</button>
  `);

  document.getElementById('restoreBackupBtn').addEventListener('click', showRestoreDialog);
  populateBackupVersions();
}

// حذف خطای await در سطح بالا
(function() {
  createBackupRestoreElements();
})();

async function requestNewPathFromServer() {
  try {
    const response = await fetch('http://127.0.0.1:8000/set_path');
    const data = await response.json();
    if (data.status === 'success' && data.path) {
      displaySelectedPath(data.path);
      console.log('✅ مسیر جدید:', data.path);
      await populateBackupVersions();
    } else {
      console.error('❌ خطا در دریافت مسیر:', data.error || data.message);
    }
  } catch (error) {
    console.error('⚠️ خطا:', error);
  }
}

function displaySelectedPath(path) {
  let displayDiv = document.getElementById('selectedPathDisplay');
  if (!displayDiv) {
    displayDiv = document.createElement('div');
    displayDiv.id = 'selectedPathDisplay';
    document.body.appendChild(displayDiv);
  }
  displayDiv.innerHTML = `📂 <strong>مسیر انتخاب شده:</strong> ${path}`;
  displayDiv.style.cursor = 'pointer';
  displayDiv.onclick = requestNewPathFromServer;
}

async function checkAndSelectPath() {
  try {
    const response = await fetch('http://127.0.0.1:8000/path');
    const data = await response.json();
    if (data.path) {
      displaySelectedPath(data.path);
    } else {
      await requestNewPathFromServer();
    }
  } catch (error) {
    console.error('⚠️ خطا در دریافت مسیر:', error);
  }
}

// اجرای تابع به صورت غیرهمزمان
(async () => {
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


// تابع کپی به کلیپ‌بورد
function copyToClipboard(button) {
  const codeElement = button.nextElementSibling.querySelector('code');
  const text = codeElement.textContent || codeElement.innerText;
  navigator.clipboard.writeText(text).then(() => {
    button.textContent = 'کپی شد!';
    setTimeout(() => {
      button.textContent = 'کپی';
    }, 2000);
  }).catch(err => {
    console.error('خطا در کپی: ', err);
    alert('کپی ناموفق بود.');
  });
}
