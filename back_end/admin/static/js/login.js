'use strict';
const form = document.getElementById('login-form');
const errorBox = document.getElementById('error');
const submit = document.getElementById('submit');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorBox.textContent = '';
  submit.disabled = true;
  submit.textContent = '正在登录…';
  try {
    const response = await fetch('/api/admin/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username: document.getElementById('username').value.trim(), password: document.getElementById('password').value})
    });
    const result = await response.json();
    if (!response.ok || (result.code !== undefined && result.code !== 200)) {
      throw new Error(typeof result.detail === 'string' ? result.detail : result.message || '登录失败');
    }
    const data = result.data || result;
    if (!data.access_token) throw new Error('登录响应中缺少 access_token');
    sessionStorage.setItem('admin_token', data.access_token);
    sessionStorage.setItem('admin_profile', JSON.stringify(data.admin || data.user || {}));
    window.location.replace('/admin/');
  } catch (error) {
    errorBox.textContent = error.message || '网络异常，请稍后重试';
  } finally {
    submit.disabled = false;
    submit.textContent = '登录后台';
  }
});
