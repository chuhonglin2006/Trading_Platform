// 演示用的模拟数据。真正对接后端后，这些数据应改由接口返回：
// GET /api/products  -> seedProducts
// GET /api/users/:id -> seedUsers[id]

export const seedProducts = [
  { id: 1, name: '高等数学（同济第七版）上下册', price: 25, originalPrice: 89, category: 'book', campus: '关山校区', status: 'on_sale', views: 132, sellerId: 2, desc: '大一用完的教材，笔记不多，几乎全新，介意的勿拍。可以在图书馆门口面交。', createdAt: '3天前' },
  { id: 2, name: '罗技 M590 无线鼠标', price: 60, originalPrice: 149, category: 'digital', campus: '鲁巷校区', status: 'on_sale', views: 88, sellerId: 3, desc: '用了半年，功能完全正常，电池还很耐用，送一节备用电池。', createdAt: '1天前' },
  { id: 3, name: '宜家小型书桌 一米二', price: 120, originalPrice: 399, category: 'furniture', campus: '鲁巷校区', status: 'on_sale', views: 210, sellerId: 4, desc: '毕业急出，桌面有轻微划痕不影响使用，需要自取，宿舍楼下可搬。', createdAt: '5小时前' },
  { id: 4, name: 'Switch 健身环大冒险 全套', price: 280, originalPrice: 428, category: 'digital', campus: '关山校区', status: 'sold', views: 340, sellerId: 2, desc: '国行正版，配件齐全，玩了两个月，跳绳功能没怎么用。', createdAt: '1周前' },
  { id: 5, name: '北面抓绒外套 M码', price: 150, originalPrice: 599, category: 'clothes', campus: '鲁巷校区', status: 'on_sale', views: 56, sellerId: 5, desc: '尺码不合适，只试穿过一次，吊牌还在。', createdAt: '2天前' },
  { id: 6, name: '羽毛球拍 尤尼克斯 二手', price: 80, originalPrice: 320, category: 'sport', campus: '鲁巷校区', status: 'on_sale', views: 44, sellerId: 3, desc: '手胶换新，拍面完好，附赠一个拍套。', createdAt: '4天前' },
  { id: 7, name: '小米体重秤 + 台灯 一起出', price: 35, originalPrice: null, category: 'life', campus: '关山校区', status: 'on_sale', views: 19, sellerId: 4, desc: '两件一起卖更划算，都是正常使用没有问题。', createdAt: '刚刚' },
  { id: 8, name: '雅思写作真题解析（第16-18辑）', price: 20, originalPrice: 68, category: 'book', campus: '关山校区', status: 'on_sale', views: 27, sellerId: 5, desc: '考完试用不上了，里面有少量铅笔标注，可擦除。', createdAt: '6小时前' },
]

export const seedUsers = {
  2: { name: '林朝暮', campus: '关山校区', score: 118 },
  3: { name: '阿舟', campus: '鲁巷校区', score: 102 },
  4: { name: '木易', campus: '鲁巷校区', score: 95 },
  5: { name: '陈见山', campus: '关山校区', score: 130 },
}
