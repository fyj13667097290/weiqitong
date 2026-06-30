-- ============================================
-- 小程序工厂 - 多租户数据库 (SQLite)
-- 参考 drivingAppointPublic 数据模型改造
-- ============================================

-- 行业模板定义
CREATE TABLE IF NOT EXISTS industries (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  icon TEXT DEFAULT '🏭',
  is_active INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 租户(驾校)
CREATE TABLE IF NOT EXISTS tenants (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,                  -- 驾校全称
  short_name TEXT,                     -- 简称
  industry_id TEXT NOT NULL,           -- FK→industries
  contact_name TEXT,                   -- 联系人
  contact_phone TEXT,                  -- 联系电话
  status TEXT DEFAULT 'trial', -- trial/active/inactive
  plan TEXT DEFAULT 'basic',   -- basic/standard/pro
  trial_end DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (industry_id) REFERENCES industries(id)
);

-- 租户配置版本管理(核心：JSON驱动)
CREATE TABLE IF NOT EXISTS configs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL,
  version INTEGER DEFAULT 1,
  config TEXT NOT NULL,                -- 完整 school.config.json
  status TEXT DEFAULT 'draft', -- draft/generated/deployed/auditing/published
  mini_appid TEXT,                     -- 小程序AppID
  mini_appname TEXT,                   -- 小程序名称
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- 部署记录
CREATE TABLE IF NOT EXISTS deployments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL,
  config_version INTEGER,
  action TEXT NOT NULL,                -- preview/upload/submit_audit/release
  result TEXT DEFAULT 'pending',  -- success/failed/pending
  message TEXT,                        -- 微信返回的消息
  log TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- 微信第三方平台授权
CREATE TABLE IF NOT EXISTS wechat_auths (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL UNIQUE,
  authorizer_appid TEXT NOT NULL,      -- 授权方小程序AppID
  authorizer_access_token TEXT,
  authorizer_refresh_token TEXT,
  nick_name TEXT,                      -- 小程序昵称
  head_img TEXT,                       -- 小程序头像
  authorized_at TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- 模板市场(每个行业模板的元信息)
CREATE TABLE IF NOT EXISTS templates (
  id TEXT PRIMARY KEY,
  industry_id TEXT NOT NULL,
  name TEXT NOT NULL,
  version TEXT DEFAULT '1.0.0',
  description TEXT,
  thumbnail TEXT,                      -- 预览图URL
  is_active INTEGER DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (industry_id) REFERENCES industries(id)
);

-- 操作日志
CREATE TABLE IF NOT EXISTS operation_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT,
  action TEXT NOT NULL,
  detail TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============ 初始数据 ============
INSERT OR IGNORE INTO industries (id, name, slug, icon) VALUES
  ('drv001', '驾校', 'driving', '🚗');

INSERT OR IGNORE INTO templates (id, industry_id, name, version, description) VALUES
  ('tpl_driving_v1', 'drv001', '驾校通用模板 v1', '1.0.0', '品牌展示+在线报名+预约练车+题库练习');
