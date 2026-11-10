'use strict';
const form = document.getElementById('login-form');
const errorBox = document.getElementById('error');
const submit = document.getElementById('submit');
const captchaInput = document.getElementById('captcha');
const captchaImage = document.getElementById('captcha-image');
let captchaId = '';

// 每张验证码只能校验一次（对错都作废），所以每次提交后都要换一张
async function loadCaptcha() {
  captchaInput.value = '';
  captchaId = '';
  try {
    const response = await fetch('/api/captcha', {cache: 'no-store'});
    const data = await response.json();
    if (!response.ok || !data.captcha_id) throw new Error('captcha');
    captchaId = data.captcha_id;
    captchaImage.src = data.image;
  } catch (error) {
    captchaImage.removeAttribute('src');
    errorBox.textContent = '图片验证码加载失败，请点击图片重试';
  }
}
document.getElementById('captcha-btn').addEventListener('click', loadCaptcha);
loadCaptcha();
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorBox.textContent = '';
  submit.disabled = true;
  submit.textContent = '正在登录…';
  try {
    const response = await fetch('/api/admin/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({username: document.getElementById('username').value.trim(), password: document.getElementById('password').value, captcha_id: captchaId, captcha_code: captchaInput.value.trim()})
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
    await loadCaptcha();
  } finally {
    submit.disabled = false;
    submit.textContent = '登录后台';
  }
});