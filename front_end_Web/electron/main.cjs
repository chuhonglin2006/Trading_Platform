const { app, BrowserWindow } = require('electron')
const path = require('path')

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    autoHideMenuBar: true,
  })

  // 加载本地打包好的前端
  // win.loadFile(path.join(__dirname, '../dist/index.html'))

  // 直接加载线上网站
  win.loadURL('https://chuhlblog.top')
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => app.quit())