const { app, BrowserWindow } = require('electron')
const path = require('path')

// app.isPackaged: 打包成 exe 后为 true，开发时 (electron .) 为 false
const isDev = !app.isPackaged

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    autoHideMenuBar: true,
  })

  if (isDev) {
    // 开发 加载本地开发服务器 端口按你的实际情况改
    win.loadURL('http://localhost:5173')
    win.webContents.openDevTools() // 可选：开发时自动打开调试面板
  } else {
    // 打包后 加载线上网站
    win.loadURL('https://chuhlblog.top')
  }
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => app.quit())