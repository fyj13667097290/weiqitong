// 小程序工厂 - API工具
// 从 school.config.json 读取 tenantId，调用后端公开API
const config = require('../school.config.json');

const API_BASE = 'https://jiaxiao.t-hub.cc/api/public';
const TENANT_ID = config._meta ? config._meta.tenantId : '';

function fetchAPI(path) {
  return new Promise((resolve) => {
    uni.request({
      url: API_BASE + '/' + TENANT_ID + '/' + path,
      method: 'GET',
      success: res => resolve(res.data),
      fail: () => resolve([])
    });
  });
}

module.exports = {
  getAnnouncements() { return fetchAPI('announcements'); },
  getCourses() { return fetchAPI('courses'); },
  getCoaches() { return fetchAPI('coaches'); },
  API_BASE,
  TENANT_ID
};
