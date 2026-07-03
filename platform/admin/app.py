"""
小程序工厂 - 管理后台 API v2
多租户 + JSON配置驱动 + 行业模板可插拔
"""
import sqlite3, json, uuid, os
from datetime import date, datetime, timedelta
from flask import Flask, request, jsonify, redirect, render_template_string, make_response
import requests as _requests
import time as _time
from wechatpy.crypto import WeChatCrypto

app = Flask(__name__)
DB = "/opt/jiaxiao/platform/admin/data.db"
ADMIN_PW_FILE = "/opt/jiaxiao/platform/admin/.admin_password"

# ==================== 微信第三方平台 ====================
WX_COMPONENT_APPID = "wxf1d537dba4c5f6e9"
WX_COMPONENT_SECRET = "56fd5df8a938e85447e2a8eb54bac7a1"
WX_TOKEN = "weiqitong2026"
WX_ENCODING_KEY = "FYJ3601211994062939321827089906115179196692"

WX_CRYPTO = WeChatCrypto(WX_TOKEN, WX_ENCODING_KEY, WX_COMPONENT_APPID)
WX_TICKET_FILE = "/opt/jiaxiao/platform/admin/.wx_ticket"
WX_ACCESS_TOKEN_FILE = "/opt/jiaxiao/platform/admin/.wx_access_token"
import tempfile as _tempfile
WX_MAP_DIR = "/opt/jiaxiao/platform/admin/wx_auth_map"
os.makedirs(WX_MAP_DIR, exist_ok=True)

def wx_get_stored(key, default=""):
    try: return open(key).read().strip()
    except: return default

def wx_store(key, value):
    with open(key, "w") as f: f.write(value)

def wx_get_component_token():
    """获取 component_access_token，有效期2小时，缓存到文件"""
    cached = wx_get_stored(WX_ACCESS_TOKEN_FILE)
    if cached:
        parts = cached.split("|")
        if len(parts)==2 and _time.time() < int(parts[1]):
            return parts[0]
    ticket = wx_get_stored(WX_TICKET_FILE)
    if not ticket: return None
    resp = _requests.post("https://api.weixin.qq.com/cgi-bin/component/api_component_token", json={
        "component_appid": WX_COMPONENT_APPID,
        "component_appsecret": WX_COMPONENT_SECRET,
        "component_verify_ticket": ticket
    }).json()
    token = resp.get("component_access_token","")
    if token:
        wx_store(WX_ACCESS_TOKEN_FILE, token + "|" + str(int(_time.time())+7000))
    return token

def wx_get_pre_auth_code():
    """获取预授权码"""
    token = wx_get_component_token()
    if not token: return None
    resp = _requests.post(f"https://api.weixin.qq.com/cgi-bin/component/api_create_preauthcode?component_access_token={token}", json={
        "component_appid": WX_COMPONENT_APPID
    }).json()
    return resp.get("pre_auth_code","")

def wx_get_authorizer_info(authorizer_appid):
    """获取授权方信息"""
    token = wx_get_component_token()
    if not token: return None
    resp = _requests.post(f"https://api.weixin.qq.com/cgi-bin/component/api_get_authorizer_info?component_access_token={token}", json={
        "component_appid": WX_COMPONENT_APPID,
        "authorizer_appid": authorizer_appid
    }).json()
    return resp

def wx_get_authorizer_token(tid):
    """获取可用的 authorizer_access_token（过期自动刷新）"""
    d = db()
    auth = d.execute("SELECT * FROM wechat_auths WHERE tenant_id=?", [tid]).fetchone()
    if not auth: d.close(); return None
    token = auth["authorizer_access_token"]
    # 测试 token 是否可用，不可用则刷新
    test = _requests.post(f"https://api.weixin.qq.com/wxa/get_latest_auditstatus?access_token={token}", json={}).json()
    if test.get("errcode") == 42001:
        comp_token = wx_get_component_token()
        if comp_token:
            refresh = _requests.post(f"https://api.weixin.qq.com/cgi-bin/component/api_authorizer_token?component_access_token={comp_token}", json={
                "component_appid": WX_COMPONENT_APPID,
                "authorizer_appid": auth["authorizer_appid"],
                "authorizer_refresh_token": auth["authorizer_refresh_token"]
            }).json()
            new_token = refresh.get("authorizer_access_token","")
            new_refresh = refresh.get("authorizer_refresh_token","")
            if new_token:
                d.execute("UPDATE wechat_auths SET authorizer_access_token=?,authorizer_refresh_token=? WHERE tenant_id=?",
                          [new_token, new_refresh or auth["authorizer_refresh_token"], tid])
                d.commit()
                token = new_token
    d.close()
    return token

# ==================== 微信回调 ====================

@app.route("/wechat/callback", methods=["GET","POST"])
def wechat_callback():
    """接收微信推送"""
    if request.method == "GET":
        return request.args.get("echostr","")
    body = request.get_data(as_text=True)
    try:
        # 用wechatpy解密
        sig = request.args.get("msg_signature","")
        ts = request.args.get("timestamp","")
        nonce = request.args.get("nonce","")
        decrypted = WX_CRYPTO.decrypt_message(body, sig, ts, nonce)
        # 用xml解析（import在函数内避免循环依赖）
        import xml.etree.ElementTree as ET
        # 保存原始解密内容用于调试
        with open("/tmp/wx_debug.xml", "w") as f: f.write(decrypted)
        xml = ET.fromstring(decrypted)
        info_type = xml.findtext("InfoType")
        if info_type == "component_verify_ticket":
            ticket = xml.findtext("ComponentVerifyTicket")
            if ticket:
                wx_store(WX_TICKET_FILE, ticket)
                wx_store(WX_ACCESS_TOKEN_FILE, "")
        elif info_type == "authorized":
            authorizer_appid = xml.findtext("AuthorizerAppid")
            auth_code = xml.findtext("AuthorizationCode")
            pre_code = xml.findtext("PreAuthCode")
            token = wx_get_component_token()
            if token and auth_code:
                resp = _requests.post(f"https://api.weixin.qq.com/cgi-bin/component/api_query_auth?component_access_token={token}", json={
                    "component_appid": WX_COMPONENT_APPID,
                    "authorization_code": auth_code
                }).json()
                info = resp.get("authorization_info",{})
                if info:
                    d = db()
                    # 通过PreAuthCode映射找到租户（从文件读）
                    map_key = pre_code.split("@@@")[-1][:20] if "@@@" in (pre_code or "") else (pre_code or "")[:20]
                    tid = wx_get_stored(os.path.join(WX_MAP_DIR, map_key), "")
                    if tid:
                        d.execute("INSERT OR REPLACE INTO wechat_auths (tenant_id,authorizer_appid,authorizer_access_token,authorizer_refresh_token,authorized_at) VALUES (?,?,?,?,datetime('now'))",
                                  [tid, authorizer_appid, info.get("authorizer_access_token",""), info.get("authorizer_refresh_token","")])
                        d.commit()
                    d.close()
        elif info_type == "unauthorized":
            authorizer_appid = xml.findtext("AuthorizerAppid")
            d = db()
            d.execute("DELETE FROM wechat_auths WHERE authorizer_appid=?", [authorizer_appid])
            d.commit(); d.close()
        elif info_type == "notify_third_fastregisterweapp":
            # 快速注册小程序成功回调，自动拿到AppID
            appid = xml.findtext("appid")
            status = xml.findtext("status")
            legal_name = xml.findtext("info/name") or ""
            if appid and status == "0":
                d2 = db()
                # 用法人姓名匹配租户
                tenant = d2.execute("SELECT id FROM tenants WHERE contact_name=? AND status!='inactive' ORDER BY created_at DESC LIMIT 1", [legal_name]).fetchone()
                if tenant:
                    latest = d2.execute("SELECT * FROM configs WHERE tenant_id=? ORDER BY version DESC LIMIT 1", [tenant["id"]]).fetchone()
                    if latest:
                        cfg = json.loads(latest["config"])
                        cfg["school"]["appId"] = appid
                        new_ver = latest["version"] + 1
                        d2.execute("INSERT INTO configs (tenant_id,version,config,status,mini_appid) VALUES (?,?,?,?,?)",
                                  [tenant["id"], new_ver, json.dumps(cfg, ensure_ascii=False), "draft", appid])
                    # 自动授权
                    d2.execute("INSERT OR REPLACE INTO wechat_auths (tenant_id,authorizer_appid,authorized_at) VALUES (?,?,datetime('now'))",
                              [tenant["id"], appid])
                    d2.commit()
                d2.close()
        elif info_type == "weapp_audit_success":
            appid = xml.findtext("ToAppid")
            app.logger.info(f"WX_AUDIT_SUCCESS: {appid}")
        elif info_type == "weapp_audit_fail":
            appid = xml.findtext("ToAppid")
            reason = xml.findtext("Reason") or "未知原因"
            app.logger.info(f"WX_AUDIT_FAIL: {appid} - {reason}")
    except Exception as e:
        app.logger.error(f"WX_CALLBACK_ERROR: {e}")
    return "success"
def get_admin_pw():
    try: return open(ADMIN_PW_FILE).read().strip()
    except: return "admin"

def require_admin(f):
    """装饰器：保护管理后台路由"""
    from functools import wraps
    @wraps(f)
    def wrapped(*a,**kw):
        if request.cookies.get("admin_token") != get_admin_pw():
            if request.path.startswith("/api/"):
                return jsonify({"error":"unauthorized"}), 401
            return redirect("/login?next="+request.path)
        return f(*a,**kw)
    return wrapped


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def row2dict(row):
    return dict(row) if row else None

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ==================== 首页 ====================

HTML_INDEX = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>小程序工厂</title>
<style>:root{--primary:#1890ff;--success:#52c41a;--warning:#fa8c16;--bg:#f0f2f5;--card:#fff}
*{margin:0;padding:0;box-sizing:border-box} body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg);color:#333}
.header{background:#1a1a2e;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:20px}.header .badge{background:#ffffff22;padding:4px 12px;border-radius:12px;font-size:13px}
.container{max-width:1200px;margin:0 auto;padding:20px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:20px}
.stat{background:var(--card);padding:20px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.stat .num{font-size:30px;font-weight:700;color:var(--primary)} .stat .label{color:#999;margin-top:4px;font-size:14px}
.card{background:var(--card);border-radius:8px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:20px}
.card h2{font-size:17px;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #f0f0f0}
.btn{display:inline-block;padding:8px 18px;border-radius:4px;text-decoration:none;font-size:14px;cursor:pointer;border:none;font-weight:500}
.btn-primary{background:var(--primary);color:#fff}.btn-success{background:var(--success);color:#fff}.btn-sm{padding:4px 10px;font-size:12px;border-radius:3px}
table{width:100%;border-collapse:collapse} th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #f0f0f0}
th{color:#999;font-weight:500;font-size:13px;background:#fafafa}
.badge{padding:2px 10px;border-radius:10px;font-size:12px;font-weight:500}
.badge-active{background:#f6ffed;color:#52c41a}.badge-trial{background:#fff7e6;color:#fa8c16}
.badge-published{background:#e6f7ff;color:#1890ff}.badge-draft{background:#f5f5f5;color:#999}
.empty{text-align:center;color:#bbb;padding:40px}</style></head><body>
<div class="header"><h1>🏭 小程序工厂</h1><span class="badge">驾校行业 v1.0</span></div>
<div class="container">
<div class="stats">
<div class="stat"><div class="num">{{stats.tenants}}</div><div class="label">总客户</div></div>
<div class="stat"><div class="num">{{stats.active}}</div><div class="label">活跃客户</div></div>
<div class="stat"><div class="num">{{stats.deployed}}</div><div class="label">已部署</div></div>
<div class="stat"><div class="num">{{stats.industries}}</div><div class="label">行业模板</div></div>
</div>
<div class="card">
<h2>🏫 客户列表 <a href="/new" class="btn btn-primary" style="float:right">+ 添加客户</a></h2>
<table><thead><tr><th>驾校名称</th><th>行业</th><th>套餐</th><th>状态</th><th>小程序</th><th>创建时间</th><th>操作</th></tr></thead>
<tbody>{% if tenants %}{% for t in tenants %}<tr>
<td><strong>{{t.name}}</strong></td><td>{{t.industry_name or '-'}}</td>
<td><span class="badge badge-draft">{{t.plan}}</span></td>
<td><span class="badge {% if t.status=='active' %}badge-active{% else %}badge-trial{% endif %}">{{t.status}}</span></td>
<td><span class="badge badge-draft">未部署</span></td>
<td>{{t.created_at[:10] if t.created_at else '-'}}</td>
<td><a href="/tenants/{{t.id}}/config" class="btn btn-primary btn-sm">配置</a></td>
</tr>{% endfor %}{% else %}<tr><td colspan="7" class="empty">还没有客户，点击右上角添加客户</td></tr>{% endif %}</tbody></table>
</div></div></body></html>"""

HTML_NEW = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>添加客户</title>
<style>:root{--primary:#1890ff;--bg:#f0f2f5} *{margin:0;padding:0;box-sizing:border-box} body{font-family:-apple-system,sans-serif;background:var(--bg)}
.container{max-width:600px;margin:40px auto;padding:20px} .card{background:#fff;border-radius:8px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
h2{margin-bottom:20px} .form-group{margin-bottom:16px} label{display:block;margin-bottom:6px;font-weight:500;font-size:14px;color:#555}
input,select,textarea{width:100%;padding:10px 12px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px} input:focus,select:focus{border-color:var(--primary);outline:none;box-shadow:0 0 0 2px rgba(24,144,255,.2)}
.btn{padding:10px 24px;border-radius:4px;border:none;font-size:14px;cursor:pointer;font-weight:500} .btn-primary{background:var(--primary);color:#fff;width:100%}
.back{color:#999;text-decoration:none;font-size:13px;margin-bottom:16px;display:inline-block}</style></head><body>
<div class="container"><a href="/admin" class="back">← 返回</a><div class="card"><h2>+ 添加驾校客户</h2>
<form method="POST" action="/api/tenants"><div class="form-group"><label>驾校全称 *</label><input name="name" required placeholder="如：鑫达机动车驾驶培训学校"></div>
<div class="form-group"><label>简称</label><input name="short_name" placeholder="如：鑫达驾校" maxlength="10"></div>
<div class="form-group"><label>联系人</label><input name="contact_name" placeholder="驾校老板姓名"></div>
<div class="form-group"><label>联系电话</label><input name="contact_phone" placeholder="手机号"></div>
<div class="form-group"><label>行业</label><select name="industry_id">{% for ind in industries %}<option value="{{ind.id}}">{{ind.icon}} {{ind.name}}</option>{% endfor %}</select></div>
<div class="form-group"><label>套餐</label><select name="plan"><option value="trial">试用版（免费14天）</option><option value="basic">基础版 999元/年</option><option value="standard">标准版 1999元/年</option><option value="pro">专业版 2999元/年</option></select></div>
<div class="form-group"><label>推广人</label><select name="referrer_id"><option value="">无</option>{% for r in referrers %}<option value="{{r.id}}" {% if preselected_ref==r.id %}selected{% endif %}>{{r.name}} ({{r.phone or ''}})</option>{% endfor %}</select></div>
<button type="submit" class="btn btn-primary">创建客户</button></form></div></div></body></html>"""

HTML_CONFIG = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>驾校配置</title>
<style>:root{--primary:#1890ff;--danger:#ff4d4f;--bg:#f0f2f5} *{margin:0;padding:0;box-sizing:border-box} body{font-family:-apple-system,sans-serif;background:var(--bg)}
.container{max-width:800px;margin:20px auto;padding:20px} .card{background:#fff;border-radius:8px;padding:24px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
h2{font-size:18px;margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid #f0f0f0}
h3{font-size:15px;color:#555;margin:20px 0 12px;padding-left:8px;border-left:3px solid var(--primary)}
.form-group{margin-bottom:14px} label{display:block;margin-bottom:5px;font-weight:500;font-size:13px;color:#555}
input,select,textarea{width:100%;padding:9px 12px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;font-family:inherit}
input:focus,select:focus,textarea:focus{border-color:var(--primary);outline:none;box-shadow:0 0 0 2px rgba(24,144,255,.2)}
textarea{resize:vertical;min-height:80px}
.btn{padding:10px 20px;border-radius:4px;border:none;font-size:14px;cursor:pointer;font-weight:500;display:inline-flex;align-items:center;gap:6px}
.btn-primary{background:var(--primary);color:#fff} .btn-success{background:#52c41a;color:#fff} .btn-warn{background:#fa8c16;color:#fff} .btn-sm{padding:4px 10px;font-size:12px} .btn-danger{background:var(--danger);color:#fff}
.btn-group{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap}
.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.row3{display:grid;grid-template-columns:2fr 1fr 80px;gap:12px;align-items:end;margin-bottom:8px}
.back{color:#999;text-decoration:none;font-size:13px;display:inline-block;margin-bottom:16px}
.tab-bar{display:flex;border-bottom:2px solid #f0f0f0;margin-bottom:20px}
.tab-item{padding:10px 20px;color:#999;cursor:pointer;font-size:14px;border-bottom:2px solid transparent;margin-bottom:-2px;user-select:none}
.tab-item.active{color:var(--primary);border-bottom-color:var(--primary);font-weight:500}
.tab-content{display:none} .tab-content.active{display:block}
.item-row{display:grid;grid-template-columns:1fr 100px 60px;gap:10px;align-items:start;margin-bottom:8px;padding:10px;background:#fafafa;border-radius:6px}
.item-row-coach{grid-template-columns:1fr 100px 100px 60px}
.log-box{background:#1e293b;color:#4ade80;padding:16px;border-radius:8px;font-size:13px;max-height:300px;overflow-y:auto;white-space:pre-wrap;font-family:monospace}
.empty{text-align:center;color:#bbb;padding:20px}</style></head><body>
<div class="container">
<a href="/admin" class="back">← 返回管理后台</a>
<div class="tab-bar">
  <div class="tab-item active" onclick="switchTab('tab-basic',this)">基本信息</div>
  <div class="tab-item" onclick="switchTab('tab-courses',this)">课程套餐</div>
  <div class="tab-item" onclick="switchTab('tab-coaches',this)">教练团队</div>
  <div class="tab-item" onclick="switchTab('tab-deploy',this)">部署上线</div>
</div>

<form id="configForm">
<!-- 基本信息 -->
<div class="tab-content active" id="tab-basic">
  <div class="card">
    <h3>驾校信息</h3>
    <div class="row"><div class="form-group"><label>驾校全称 *</label><input id="f_school_name" required value="{{tenant.name}}"></div>
    <div class="form-group"><label>简称</label><input id="f_school_shortName" value="{{tenant.short_name or ''}}"></div></div>
    <div class="row"><div class="form-group"><label>联系电话 *</label><input id="f_school_phone" required value="{{tenant.contact_phone or ''}}"></div>
    <div class="form-group"><label>Logo URL</label><input id="f_school_logo" placeholder="https://..."></div></div>
    <div class="form-group"><label>地址</label><input id="f_school_address"></div>
    <div class="form-group"><label>驾校简介</label><textarea id="f_school_description" maxlength="500"></textarea></div>
    <div class="row"><div class="form-group"><label>主题色</label><input type="color" id="f_primaryColor" value="#1890ff" style="width:60px;height:40px;padding:2px"></div>
    <div class="form-group"><label>小程序 AppID</label><input id="f_mini_appid" placeholder="wx开头（部署时必填）"></div></div>
  </div>
</div>

<!-- 课程套餐 -->
<div class="tab-content" id="tab-courses">
  <div class="card">
    <h3>培训课程</h3>
    <div id="courses-list"></div>
    <p class="empty" id="courses-empty" style="display:none">暂无课程，点击下方按钮添加</p>
    <button type="button" class="btn btn-primary btn-sm" onclick="addCourse()" style="margin-top:12px">+ 添加课程</button>
  </div>
</div>

<!-- 教练团队 -->
<div class="tab-content" id="tab-coaches">
  <div class="card">
    <h3>教练团队</h3>
    <div id="coaches-list"></div>
    <p class="empty" id="coaches-empty" style="display:none">暂无教练，点击下方按钮添加</p>
    <button type="button" class="btn btn-primary btn-sm" onclick="addCoach()" style="margin-top:12px">+ 添加教练</button>
  </div>
</div>

<!-- 部署 -->
<div class="tab-content" id="tab-deploy">
  <div class="card">
    <h3>部署状态</h3>
    <div id="deploy-status">加载中...</div>
  </div>
  <div class="card">
    <h3>部署日志</h3>
    <div class="log-box" id="deploy-log">等待部署...</div>
  </div>
</div>
</form>

<div class="btn-group">
  <button type="button" class="btn btn-primary" onclick="save()">💾 保存配置</button>
  <button type="button" class="btn btn-success" onclick="generate()">⚙️ 生成代码</button>
  <button type="button" class="btn btn-warn" onclick="deploy()">🚀 部署到微信</button>
  <button type="button" class="btn" onclick="submitAudit()" style="background:#722ed1;color:#fff">📝 提交审核</button>
  <button type="button" class="btn" onclick="undoAudit()" style="background:#ff7875;color:#fff">↩ 撤回审核</button>
  <button type="button" class="btn" onclick="releaseWx()" style="background:#13c2c2;color:#fff">🎉 发布上线</button>
</div>
</div>

<script>
const tid = window.location.pathname.split('/')[2];
// 安全读取服务端预填值
function gv(id){ var el=document.getElementById(id); return el?el.value:''; }
let cfg = {school:{name:gv('f_school_name'),shortName:gv('f_school_shortName'),logo:'',phone:gv('f_school_phone'),address:'',description:'',photos:[],theme:{primaryColor:'#1890ff'}},courses:[],coaches:[],locations:[],features:{appointment:true,examPrep:true,onlinePayment:false}};

// === TAB ===
function switchTab(tabId, el){
  document.querySelectorAll('.tab-item').forEach(function(e){e.classList.remove('active')});
  document.querySelectorAll('.tab-content').forEach(function(e){e.classList.remove('active')});
  el.classList.add('active');
  var tab = document.getElementById(tabId);
  if(tab){ tab.classList.add('active'); if(tabId==='tab-deploy') loadDeployments(); }
}
load();

// === LOAD ===
async function load(){
  try {
    const r = await fetch('/api/tenants/'+tid+'/config');
    const d = await r.json();
    if(d.config) cfg = d.config;
    renderAll();
  } catch(e){ console.error(e); }
}
function renderAll(){
  // basic
  const s = cfg.school || {};
  document.getElementById('f_school_name').value = s.name || '';
  document.getElementById('f_school_shortName').value = s.shortName || '';
  document.getElementById('f_school_phone').value = s.phone || '';
  document.getElementById('f_school_logo').value = s.logo || '';
  document.getElementById('f_school_address').value = s.address || '';
  document.getElementById('f_school_description').value = s.description || '';
  document.getElementById('f_primaryColor').value = (s.theme && s.theme.primaryColor) || '#1890ff';
  // courses
  const cl = document.getElementById('courses-list');
  cl.innerHTML = (cfg.courses||[]).map((c,i) => `<div class="item-row">
    <input value="${esc(c.name||'')}" onchange="cfg.courses[${i}].name=this.value" placeholder="套餐名称">
    <input type="number" value="${c.price||''}" onchange="cfg.courses[${i}].price=parseInt(this.value)||0" placeholder="价格">
    <button type="button" class="btn btn-danger btn-sm" onclick="cfg.courses.splice(${i},1);renderAll()">删除</button>
  </div>`).join('');
  document.getElementById('courses-empty').style.display = (cfg.courses||[]).length ? 'none' : '';
  // coaches
  const chl = document.getElementById('coaches-list');
  chl.innerHTML = (cfg.coaches||[]).map((c,i) => `<div class="item-row item-row-coach">
    <input value="${esc(c.name||'')}" onchange="cfg.coaches[${i}].name=this.value" placeholder="姓名">
    <input type="number" value="${c.experience||''}" onchange="cfg.coaches[${i}].experience=parseInt(this.value)||0" placeholder="教龄">
    <input value="${esc(c.phone||'')}" onchange="cfg.coaches[${i}].phone=this.value" placeholder="电话">
    <button type="button" class="btn btn-danger btn-sm" onclick="cfg.coaches.splice(${i},1);renderAll()">删除</button>
  </div>`).join('');
  document.getElementById('coaches-empty').style.display = (cfg.coaches||[]).length ? 'none' : '';
}
function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;') }

// === COLLECT ===
function collect(){
  cfg.school = cfg.school || {};
  cfg.school.name = document.getElementById('f_school_name').value;
  cfg.school.shortName = document.getElementById('f_school_shortName').value;
  cfg.school.phone = document.getElementById('f_school_phone').value;
  cfg.school.logo = document.getElementById('f_school_logo').value;
  cfg.school.address = document.getElementById('f_school_address').value;
  cfg.school.description = document.getElementById('f_school_description').value;
  cfg.school.theme = {primaryColor: document.getElementById('f_primaryColor').value};
  cfg.courses = cfg.courses || [];
  cfg.coaches = cfg.coaches || [];
  return cfg;
}

// === ACTIONS ===
function addCourse(){ cfg.courses.push({name:'',price:0}); renderAll(); }
function addCoach(){ cfg.coaches.push({name:'',experience:0,phone:''}); renderAll(); }

async function save(){
  const config = collect();
  const r = await fetch('/api/tenants/'+tid+'/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({config,mini_appid:document.getElementById('f_mini_appid').value})});
  const d = await r.json();
  log('✅ 配置已保存 (版本 v'+d.version+')');
}

async function submitAudit(){
  await save();
  var r=await fetch('/api/wechat/submit-audit/'+tid,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  var d=await r.json();
  log(d.error||d.message||'提交审核请求已发出');
  loadDeployments();
}
async function undoAudit(){
  var r=await fetch('/api/wechat/undocodeaudit/'+tid,{method:'POST'});
  var d=await r.json();
  log(d.error||d.message||'撤回请求已发出');
  loadDeployments();
}
async function releaseWx(){
  var r=await fetch('/api/wechat/release/'+tid,{method:'POST'});
  var d=await r.json();
  log(d.error||d.message||'发布请求已发出');
  loadDeployments();
}
async function generate(){
  await save();
  log('⚙️ 正在生成小程序代码...');
  const r = await fetch('/api/tenants/'+tid+'/deploy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'generate'})});
  const d = await r.json();
  log('📦 '+d.message);
  setTimeout(loadDeployments, 2000);
}

async function deploy(){
  await save();
  log('🚀 正在触发部署...');
  const r = await fetch('/api/tenants/'+tid+'/deploy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'upload'})});
  const d = await r.json();
  log('📤 '+d.message);
  // 触发 GitHub Actions（通过服务端代理，不暴露Token）
  try {
    const gr = await fetch('/api/tenants/'+tid+'/trigger-deploy',{method:'POST'});
    const gd = await gr.json();
    log('🔗 GitHub Actions '+gd.message);
  } catch(e){ log('⚠️ 触发失败: '+e.message) }
  setTimeout(loadDeployments, 3000);
}

async function loadDeployments(){
  try {
    const r = await fetch('/api/tenants/'+tid+'/deployments');
    const list = await r.json();
    var ds = document.getElementById('deploy-status');
    if(list.length){
      var a = list[0].action, re = list[0].result, t = list[0].created_at;
      ds.innerHTML = '<p>最近部署：<strong>'+a+'</strong> — <span style="color:'+(re==='success'?'#52c41a':'#fa8c16')+'">'+re+'</span> ('+t+')</p>';
    } else { ds.innerHTML = '<p style="color:#999">还没有部署记录</p>'; }
    var lines = []; for(var i=0;i<list.length;i++){ var d=list[i]; lines.push('['+d.created_at+'] '+d.action+': '+d.result); }
    document.getElementById('deploy-log').textContent = lines.join('\\n') || '暂无日志';
  } catch(e){}
}

function log(msg){
  var el = document.getElementById('deploy-log');
  el.textContent = '['+new Date().toLocaleTimeString()+'] '+msg+'\\n' + el.textContent;
}

</script></body></html>"""

LANDING_PAGE = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微企通 - 中小企业小程序解决方案</title>
<style>:root{--primary:#2563eb;--dark:#1e293b;--light:#f8fafc}
*{margin:0;padding:0;box-sizing:border-box} body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;color:#334155;line-height:1.6}
.hero{background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);color:#fff;padding:80px 20px;text-align:center}
.hero h1{font-size:42px;font-weight:800;margin-bottom:16px} .hero p{font-size:20px;opacity:.9;max-width:600px;margin:0 auto}
.features{max-width:1000px;margin:-40px auto 0;padding:0 20px;display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
.feature{background:#fff;padding:30px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.08);text-align:center}
.feature .icon{font-size:48px;margin-bottom:12px}
.feature h3{font-size:18px;margin-bottom:8px}
.feature p{font-size:14px;color:#64748b}
.how{max-width:1000px;margin:60px auto;padding:0 20px}
.how h2{text-align:center;font-size:32px;margin-bottom:40px}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:24px}
.step{text-align:center;padding:24px}
.step .num{width:48px;height:48px;background:var(--primary);color:#fff;border-radius:24px;display:inline-flex;align-items:center;justify-content:center;font-size:24px;font-weight:700;margin-bottom:12px}
.cta{text-align:center;padding:60px 20px;background:var(--light)}
.cta h2{font-size:28px;margin-bottom:12px} .cta p{color:#64748b;margin-bottom:24px}
.btn{display:inline-block;padding:12px 32px;background:var(--primary);color:#fff;border-radius:8px;text-decoration:none;font-weight:600;font-size:16px}
.footer{text-align:center;padding:30px;color:#94a3b8;font-size:13px}</style></head><body>
<div class="hero"><h1>🏭 微企通</h1><p>为中小企业提供微信小程序一站式解决方案，批量生成、自动部署、快速上线</p></div>
<div class="features">
<div class="feature"><div class="icon">🚗</div><h3>驾校行业</h3><p>品牌展示 · 在线报名 · 预约练车 · 题库练习</p></div>
<div class="feature"><div class="icon">🍜</div><h3>餐饮行业</h3><p>在线点餐 · 外卖配送 · 排队叫号 · 会员管理</p></div>
<div class="feature"><div class="icon">💇</div><h3>美业服务</h3><p>服务展示 · 在线预约 · 技师介绍 · 会员储值</p></div>
</div>
<div class="how"><h2>三步上线</h2><div class="steps">
<div class="step"><div class="num">1</div><h3>填写资料</h3><p>提供您的店铺信息、Logo、服务项目</p></div>
<div class="step"><div class="num">2</div><h3>自动生成</h3><p>系统10秒生成您的专属小程序</p></div>
<div class="step"><div class="num">3</div><h3>审核上线</h3><p>提交微信审核，1-7天正式上线</p></div>
</div></div>
<div class="cta"><h2>让您的生意拥有专属小程序</h2><p>免费试用14天，满意再付费</p><a href="mailto:547178675@qq.com" class="btn">联系我们</a></div>
<div class="footer"><p>© 2026 微企通 weiqitong | 为中小企业提供微信小程序解决方案</p></div>
</body></html>"""

ADMIN_PAGE = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微企通 · 管理后台</title>
<style>:root{--primary:#1890ff;--bg:#f0f2f5} *{margin:0;padding:0;box-sizing:border-box} body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:var(--bg)}
.header{background:#1e293b;color:#fff;padding:14px 24px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:18px} .container{max-width:1200px;margin:0 auto;padding:20px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:20px}
.stat{background:#fff;padding:20px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.stat .num{font-size:30px;font-weight:700;color:var(--primary)} .stat .label{color:#999;margin-top:4px;font-size:14px}
.card{background:#fff;border-radius:8px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:20px}
.card h2{font-size:17px;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #f0f0f0}
.btn{display:inline-block;padding:8px 18px;border-radius:4px;text-decoration:none;font-size:14px;cursor:pointer;border:none;font-weight:500}
.btn-primary{background:var(--primary);color:#fff}.btn-sm{padding:4px 10px;font-size:12px}
table{width:100%;border-collapse:collapse} th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #f0f0f0}
th{color:#999;font-weight:500;font-size:13px;background:#fafafa}
.badge{padding:2px 10px;border-radius:10px;font-size:12px;font-weight:500}
.badge-active{background:#f6ffed;color:#52c41a}.badge-trial{background:#fff7e6;color:#fa8c16}
.badge-draft{background:#f5f5f5;color:#999}
.empty{text-align:center;color:#bbb;padding:40px}
.industry-bar{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}
.ind-item{padding:8px 16px;border-radius:20px;background:#fff;color:#666;text-decoration:none;font-size:13px;font-weight:500;box-shadow:0 1px 2px rgba(0,0,0,.06);transition:all .2s}
.ind-item:hover{color:var(--primary)}
.ind-item.active{background:var(--primary);color:#fff}
.filter-bar{display:flex;gap:8px;margin-bottom:16px}
.filter-item{padding:6px 14px;border-radius:16px;background:#fff;color:#666;text-decoration:none;font-size:12px;font-weight:500;box-shadow:0 1px 2px rgba(0,0,0,.05)}
.filter-item.active{background:#1e293b;color:#fff}</style></head><body>
<div class="header"><h1>🏭 微企通 · 管理后台</h1><div><a href="/admin/partners" style="color:#94a3b8;text-decoration:none;font-size:13px">推广人管理</a></div></div>
<div class="container">
<div class="industry-bar">
  <a href="/admin" class="ind-item {% if not current_industry %}active{% endif %}">📊 全部</a>
  {% for ind in industries %}
  <a href="/admin?industry={{ind.id}}" class="ind-item {% if current_industry==ind.id %}active{% endif %}">{{ind.icon}} {{ind.name}}</a>
  {% endfor %}
</div>
<div class="filter-bar">
  <a href="/admin?status=active{% if current_industry %}&industry={{current_industry}}{% endif %}" class="filter-item {% if filter_status=='active' %}active{% endif %}">🟢 活跃</a>
  <a href="/admin?status=all{% if current_industry %}&industry={{current_industry}}{% endif %}" class="filter-item {% if filter_status=='all' %}active{% endif %}">📋 全部</a>
  <a href="/admin?status=deleted{% if current_industry %}&industry={{current_industry}}{% endif %}" class="filter-item {% if filter_status=='deleted' %}active{% endif %}">🗑️ 已删除 ({{stats.deleted}})</a>
</div>
<div class="stats">
<div class="stat"><div class="num">{{stats.tenants}}</div><div class="label">总客户</div></div>
<div class="stat"><div class="num">{{stats.active}}</div><div class="label">活跃客户</div></div>
<div class="stat"><div class="num">{{stats.deployed}}</div><div class="label">已部署</div></div>
<div class="stat"><div class="num">{{stats.industries}}</div><div class="label">行业模板</div></div>
</div>
<div class="card">
<h2>客户列表 <a href="/new" class="btn btn-primary" style="float:right">+ 添加客户</a></h2>
<table><thead><tr><th>名称</th><th>行业</th><th>套餐</th><th>状态</th><th>推广人</th><th>创建</th><th>操作</th></tr></thead>
<tbody>{% if tenants %}{% for t in tenants %}<tr>
<td><strong>{{t.name}}</strong></td><td>{{t.industry_name or '-'}}</td>
<td><span class="badge badge-trial">{{t.plan}}</span></td>
<td><span class="badge {% if t.status=='active' %}badge-active{% else %}badge-trial{% endif %}">{{t.status}}</span></td>
<td>{{t.referrer_name or '-'}}</td>
<td>{{t.created_at[:10] if t.created_at else '-'}}</td>
<td>{% if t.status=='inactive' %}
  <a href="#" onclick="restoreTenant('{{t.id}}')" class="btn btn-sm" style="background:#52c41a;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">恢复</a>
  <a href="#" onclick="hardDelTenant('{{t.id}}','{{t.name}}')" class="btn btn-sm" style="background:#ff4d4f;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">彻底删除</a>
{% else %}
  <a href="/tenants/{{t.id}}/config" class="btn btn-primary btn-sm">① 配置</a>
  <a href="#" onclick="regWx('{{t.id}}','{{t.name}}')" class="btn btn-sm" style="background:#eb2f96;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">② 注册小程序</a>
  <a href="#" onclick="authWx('{{t.id}}')" class="btn btn-sm" style="background:#722ed1;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">② 授权</a>
  <a href="/school/{{t.id}}/impersonate" class="btn btn-sm" style="background:#fa8c16;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">③ 管理</a>
  <a href="/school/{{t.id}}/login" target="_blank" class="btn btn-sm" style="background:#52c41a;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">③ 自助后台</a>
  <a href="#" onclick="copyLink('{{t.id}}')" class="btn btn-sm" style="background:#1890ff;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">🔗</a>
  <a href="/pay/{{t.id}}" target="_blank" class="btn btn-sm" style="background:#ff9800;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">付费</a>
  <a href="#" onclick="if(confirm('确认已收到该客户的付款？')){location.href='/admin/tenant/{{t.id}}/mark-paid'}" class="btn btn-sm" style="background:#4caf50;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">已收款</a>
  <a href="#" onclick="delTenant('{{t.id}}','{{t.name}}')" class="btn btn-sm" style="background:#ff4d4f;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">删除</a>
{% endif %}</td>
</tr>{% endfor %}{% else %}<tr><td colspan="7" class="empty">{% if filter_status=='deleted' %}没有已删除的客户{% else %}还没有客户{% endif %}</td></tr>{% endif %}</tbody></table>
</div></div>
<script>
function delTenant(id,name){
  if(!confirm('确定要删除客户「'+name+'」吗？\\n此操作不可恢复。')) return;
  fetch('/api/tenants/'+id,{method:'DELETE'}).then(function(r){ return r.json(); }).then(function(d){
    if(d.ok){ alert('已删除'); location.reload(); } else { alert('删除失败'); }
  });
}
function authWx(id){
  fetch('/api/wechat/auth-url/'+id).then(function(r){return r.json()}).then(function(d){
    if(d.url) prompt('复制此链接发给客户，在微信中打开授权：', d.url);
    else alert('获取失败');
  });
}
function regWx(id,name){
  var data = {};
  data.mp_name = prompt('小程序名称（如：'+name.replace('培训','')+'）', name);
  if(!data.mp_name) return;
  data.legal_name = prompt('法人姓名：');
  if(!data.legal_name) return;
  data.legal_wechat = prompt('法人微信号：');
  if(!data.legal_wechat) return;
  data.license_code = prompt('统一社会信用代码（营业执照18位）：');
  if(!data.license_code) return;
  data.phone = prompt('联系电话（审核通知用）：', '');
  fetch('/api/wechat/fast-register/'+id, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
    .then(function(r){return r.json()}).then(function(d){
      if(d.qrcode_base64){
        var w = window.open('','_blank','width=400,height=500');
        w.document.write('<div style=\"text-align:center;padding:20px;font-family:sans-serif\"><h3>请法人扫码确认</h3><img src=\"data:image/png;base64,'+d.qrcode_base64+'\" style=\"width:280px\"/><p style=\"color:#999;font-size:13px\">用微信扫码后，在手机端确认创建小程序</p></div>');
      } else { alert('失败: '+(d.error||'未知错误')); }
    });
}
function copyLink(id){
  var url = 'https://jiaxiao.t-hub.cc/school/'+id+'/login';
  var ta = document.createElement('textarea');
  ta.value = url; ta.style.position = 'fixed'; ta.style.left = '-9999px';
  document.body.appendChild(ta); ta.select();
  try { document.execCommand('copy'); alert('已复制！\\n'+url); } catch(e) { prompt('手动复制', url); }
  document.body.removeChild(ta);
}
function restoreTenant(id){
  if(!confirm('确定恢复此客户？')) return;
  fetch('/api/tenants/'+id+'/restore',{method:'POST'}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){ alert('已恢复'); location.reload(); } else { alert('恢复失败'); }
  });
}
function hardDelTenant(id,name){
  if(!confirm('⚠️ 确定彻底删除「'+name+'」？\\n所有配置、公告、课程、教练数据将被永久清除，不可恢复！')) return;
  if(!confirm('再次确认：彻底删除「'+name+'」？')) return;
  fetch('/api/tenants/'+id+'/hard-delete',{method:'DELETE'}).then(function(r){return r.json()}).then(function(d){
    if(d.ok){ alert('已彻底删除'); location.reload(); } else { alert('删除失败'); }
  });
}
</script></body></html>"""

LANDING_V2 = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微企通 - 中小企业小程序解决方案</title>
<style>:root{--primary:#2563eb}*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#f5f5f5}
.hero{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:60px 20px;text-align:center}
.hero h1{font-size:36px;font-weight:800;margin-bottom:8px}.hero p{font-size:16px;opacity:.85}
.container{max-width:600px;margin:-30px auto 0;padding:0 20px}
.card{background:#fff;border-radius:16px;padding:24px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.06)}
.card h3{font-size:18px;margin-bottom:16px;text-align:center}
.industry-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:12px}
.ind-card{text-align:center;padding:16px 8px;border:2px solid #eee;border-radius:12px;cursor:pointer;transition:all .2s}
.ind-card:hover,.ind-card.active{border-color:var(--primary);background:#f0f5ff}
.ind-icon{font-size:36px;display:block;margin-bottom:4px}.ind-name{font-size:14px;font-weight:600}
.form-section{display:none}.form-section.show{display:block}
input,select{width:100%;padding:12px;border:1px solid #d9d9d9;border-radius:8px;font-size:15px;margin-bottom:12px}
.btn{width:100%;padding:14px;background:var(--primary);color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;font-weight:600}
.msg{text-align:center;font-size:15px;padding:20px;color:#52c41a}.msg-err{color:#ff4d4f}
.back{text-align:center;color:#999;font-size:13px;margin-top:12px;cursor:pointer}
.footer{text-align:center;padding:30px 20px;color:#999;font-size:12px}
</style></head><body>
<div class="hero"><h1>🏭 微企通</h1><p>为中小企业提供微信小程序一站式解决方案</p></div>
<div class="container" id="app">
<div class="card" id="step-industry"><h3>选择你的行业</h3>
<div class="industry-grid" id="industry-list"></div>
</div>
<div class="card form-section" id="step-form"><h3 id="form-title">填写信息</h3>
<form id="signup-form"><input type="hidden" id="industry-slug" name="industry_id">
<input name="name" placeholder="商家名称" required>
<input name="phone" placeholder="联系电话" required>
<button class="btn" type="submit">提交申请 · 免费试用14天</button></form>
<div class="back" onclick="backToIndustry()">← 重新选择行业</div>
</div>
<div class="card form-section" id="step-done"><div class="msg"></div></div>
</div>
<div class="footer">14天免费试用 · 满意再付费 · 从 ¥999/年 起</div>
<script>
var industries=INDPLACEHOLDER;
var list=document.getElementById('industry-list');
industries.forEach(function(ind){
  var d=document.createElement('div');d.className='ind-card';
  d.innerHTML='<span class="ind-icon">'+ind.icon+'</span><span class="ind-name">'+ind.name+'</span>';
  d.onclick=function(){selectIndustry(ind.id,ind.name,ind.icon)};
  list.appendChild(d);
});
function selectIndustry(id,name,icon){
  document.getElementById('industry-slug').value=id;
  document.getElementById('form-title').innerHTML=icon+' '+name+' · 填写信息';
  document.getElementById('step-industry').style.display='none';
  document.getElementById('step-form').classList.add('show');
  location.hash='form';
}
function backToIndustry(){
  document.getElementById('step-industry').style.display='block';
  document.getElementById('step-form').classList.remove('show');
  location.hash='';
}
window.onhashchange=function(){
  if(!location.hash){ backToIndustry(); }
};
document.getElementById('signup-form').onsubmit=function(e){
  e.preventDefault();
  var f=e.target,data=new FormData(f);
  fetch('/api/signup',{method:'POST',body:new URLSearchParams(data)}).then(function(r){return r.json()}).then(function(d){
    document.getElementById('step-form').classList.remove('show');
    document.getElementById('step-done').classList.add('show');
    var msg=document.querySelector('#step-done .msg');
    if(d.ok){msg.textContent='✅ 提交成功！我们将在24小时内联系您开通试用。';msg.className='msg'}
    else{msg.textContent='❌ '+(d.error||'提交失败');msg.className='msg msg-err'}
  });
  return false;
};
</script></body></html>"""

@app.route("/")
def landing():
    d = db()
    industries = d.execute("SELECT id,name,slug,icon FROM industries WHERE is_active=1 ORDER BY sort_order").fetchall()
    d.close()
    ind_json = json.dumps([{"id":r["id"],"name":r["name"],"icon":r["icon"]} for r in industries], ensure_ascii=False)
    return LANDING_V2.replace("INDPLACEHOLDER", ind_json)

@app.route("/api/signup", methods=["POST"])
def api_signup():
    """首页注册：自动创建试用客户并关联推广人"""
    industry_id = request.form.get("industry_id","drv001")
    name = request.form.get("name","")
    phone = request.form.get("phone","")
    if not name or not phone:
        return jsonify({"ok":False,"error":"请填写商家名称和联系电话"})
    d = db()
    tid = f"t{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
    # 读推广人cookie
    ref_code = request.cookies.get("ref_code","")
    ref_id = None
    if ref_code:
        ref = d.execute("SELECT id FROM referrers WHERE code=? AND role='agent' AND is_active=1",[ref_code]).fetchone()
        if ref: ref_id = ref["id"]
    d.execute("INSERT INTO tenants (id,name,contact_phone,industry_id,status,plan,referrer_id,trial_end) VALUES (?,?,?,?,?,?,?,?)",
              [tid, name, phone, industry_id, "trial", "trial", ref_id, (date.today()+timedelta(days=14)).isoformat()])
    d.commit(); d.close()
    return jsonify({"ok":True,"tenant_id":tid})

ADMIN_LOGIN_HTML = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微企通 · 管理员登录</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#1e3a5f,#2563eb);min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border-radius:16px;padding:40px 30px;width:90%;max-width:380px;box-shadow:0 20px 60px rgba(0,0,0,.2);text-align:center}
h2{font-size:22px;margin-bottom:4px}.sub{color:#999;font-size:13px;margin-bottom:24px}
input{width:100%;padding:12px;border:1px solid #d9d9d9;border-radius:8px;font-size:16px;margin-bottom:16px;text-align:center}
.btn{width:100%;padding:12px;background:#2563eb;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;font-weight:600}
.err{color:#ff4d4f;font-size:13px;margin-bottom:12px}</style></head><body>
<div class="card"><h2>🏭 微企通</h2><p class="sub">管理后台登录</p>
<form method="POST"><input type="password" name="password" placeholder="请输入管理员密码" required>
{% if error %}<p class="err">{{error}}</p>{% endif %}
<button class="btn" type="submit">登录</button></form></div></body></html>"""

@app.route("/clear", methods=["GET"])
def clear_cookies():
    resp = redirect("/login")
    resp.delete_cookie("admin_token")
    resp.delete_cookie("school_admin")
    return resp

@app.route("/login", methods=["GET","POST"])
def admin_login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == get_admin_pw():
            resp = redirect(request.args.get("next","/admin"))
            resp.set_cookie("admin_token", get_admin_pw(), max_age=86400*30)
            return resp
        error = "密码错误"
    return render_template_string(ADMIN_LOGIN_HTML, error=error)

@app.route("/admin")
@require_admin
def index():
    d = db()
    stats = {
        "tenants": d.execute("SELECT COUNT(*) as c FROM tenants").fetchone()["c"],
        "active": d.execute("SELECT COUNT(*) as c FROM tenants WHERE status='active'").fetchone()["c"],
        "deployed": d.execute("SELECT COUNT(*) as c FROM configs WHERE status IN ('deployed','published')").fetchone()["c"],
        "industries": d.execute("SELECT COUNT(*) as c FROM industries WHERE is_active=1").fetchone()["c"],
    }
    industry = request.args.get("industry", "")
    filter_status = request.args.get("status", "active")  # active / all / deleted
    base_sql = "SELECT t.*, i.name as industry_name, r.name as referrer_name, (SELECT d2.result FROM deployments d2 WHERE d2.tenant_id=t.id ORDER BY d2.created_at DESC LIMIT 1) as deploy_status FROM tenants t LEFT JOIN industries i ON t.industry_id=i.id LEFT JOIN referrers r ON t.referrer_id=r.id"
    conditions = []
    params = []
    if industry: conditions.append("t.industry_id=?"); params.append(industry)
    if filter_status == "active": conditions.append("t.status!='inactive'")
    elif filter_status == "deleted": conditions.append("t.status='inactive'")
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    tenants = d.execute(base_sql + where + " ORDER BY t.created_at DESC", params).fetchall()
    # 更新统计
    stats["active"] = d.execute("SELECT COUNT(*) as c FROM tenants WHERE status!='inactive'").fetchone()["c"]
    stats["deleted"] = d.execute("SELECT COUNT(*) as c FROM tenants WHERE status='inactive'").fetchone()["c"]
    industries = d.execute("SELECT * FROM industries WHERE is_active=1 ORDER BY sort_order,id").fetchall()
    d.close()
    return render_template_string(ADMIN_PAGE, stats=stats, tenants=tenants, industries=industries, current_industry=industry, filter_status=filter_status)

@app.route("/new")
@require_admin
def new_tenant():
    d = db()
    industries = d.execute("SELECT * FROM industries WHERE is_active=1 ORDER BY sort_order,id").fetchall()
    referrers = d.execute("SELECT * FROM referrers WHERE role='agent' AND is_active=1").fetchall()
    ref_code = request.cookies.get("ref_code","")
    preselected = None
    if ref_code:
        ref = d.execute("SELECT id FROM referrers WHERE code=? AND role='agent' AND is_active=1",[ref_code]).fetchone()
        if ref: preselected = ref["id"]
    d.close()
    return render_template_string(HTML_NEW, industries=industries, referrers=referrers, preselected_ref=preselected)

@app.route("/tenants/<tid>/config")
@require_admin
def config_page(tid):
    d = db()
    t = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    d.close()
    return render_template_string(HTML_CONFIG, tenant=row2dict(t)) if t else ("Not found", 404)

# ==================== API: 租户 ====================

@app.route("/api/tenants", methods=["GET"])
def api_list_tenants():
    d = db()
    rows = d.execute("SELECT t.*, i.name as industry_name FROM tenants t LEFT JOIN industries i ON t.industry_id=i.id ORDER BY t.created_at DESC").fetchall()
    d.close()
    return jsonify([row2dict(r) for r in rows])

@app.route("/api/tenants", methods=["POST"])
@require_admin
def api_create_tenant():
    data = request.form
    tid = f"t{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
    d = db()
    rid = data.get("referrer_id","") or None
    d.execute("INSERT INTO tenants (id,name,short_name,industry_id,contact_name,contact_phone,status,plan,trial_end,referrer_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
              [tid, data["name"], data.get("short_name",""), data.get("industry_id","drv001"),
               data.get("contact_name",""), data.get("contact_phone",""),
               "trial", data.get("plan","trial"),
               (date.today() + timedelta(days=14)).isoformat(), rid])
    d.commit(); d.close()
    return render_template_string("""<html><body><script>alert('客户创建成功！');location.href='/admin'</script></body></html>"""), 201

@app.route("/api/tenants/<tid>", methods=["GET"])
def api_get_tenant(tid):
    d = db()
    r = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    d.close()
    return jsonify(row2dict(r)) if r else (jsonify({"error":"not found"}), 404)

@app.route("/api/tenants/<tid>", methods=["DELETE"])
@require_admin
def api_delete_tenant(tid):
    d = db()
    d.execute("UPDATE tenants SET status='inactive' WHERE id=?", [tid])
    d.commit(); d.close()
    return jsonify({"ok":True})

@app.route("/api/tenants/<tid>/restore", methods=["POST"])
@require_admin
def api_restore_tenant(tid):
    d = db()
    d.execute("UPDATE tenants SET status='active' WHERE id=?", [tid])
    d.commit(); d.close()
    return jsonify({"ok":True})

@app.route("/api/tenants/<tid>/hard-delete", methods=["DELETE"])
@require_admin
def api_hard_delete_tenant(tid):
    d = db()
    # 级联删除所有关联数据
    for table in ["configs","deployments","wechat_auths","customer_admins","announcements","dynamic_courses","dynamic_coaches","appointments","operation_logs"]:
        d.execute("DELETE FROM " + table + " WHERE tenant_id=?", [tid])
    d.execute("DELETE FROM tenants WHERE id=?", [tid])
    d.commit(); d.close()
    return jsonify({"ok":True})

# ==================== API: 配置 ====================

@app.route("/api/tenants/<tid>/config", methods=["GET"])
def api_get_config(tid):
    d = db()
    config = d.execute("SELECT * FROM configs WHERE tenant_id=? ORDER BY version DESC LIMIT 1", [tid]).fetchone()
    if config:
        r = row2dict(config)
        r["config"] = json.loads(r["config"])
        d.close()
        return jsonify(r)
    default = {
        "school": {"name":"","shortName":"","logo":"","phone":"","address":"","description":"","photos":[],"theme":{"primaryColor":"#1890ff"}},
        "courses": [], "coaches": [], "locations": [], "features": {"appointment":True,"examPrep":True,"onlinePayment":False}
    }
    # 没有配置时，从租户信息预填充
    tenant = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    if tenant:
        default["school"]["name"] = tenant["name"] or ""
        default["school"]["shortName"] = tenant["short_name"] or ""
        default["school"]["phone"] = tenant["contact_phone"] or ""
    d.close()
    return jsonify({"tenant_id":tid, "version":0, "config":default, "status":"draft"})

@app.route("/api/tenants/<tid>/config", methods=["POST"])
@require_admin
def api_save_config(tid):
    data = request.get_json()
    d = db()
    latest = d.execute("SELECT MAX(version) as v FROM configs WHERE tenant_id=?", [tid]).fetchone()
    new_ver = (latest["v"] or 0) + 1
    mini_appid = data.get("mini_appid","") or data.get("config",{}).get("school",{}).get("appId","")
    d.execute("INSERT INTO configs (tenant_id,version,config,status,mini_appid,mini_appname) VALUES (?,?,?,?,?,?)",
              [tid, new_ver, json.dumps(data.get("config",{}), ensure_ascii=False),
               data.get("status","draft"), mini_appid, data.get("mini_appname","")])
    d.commit(); d.close()
    return jsonify({"ok":True, "version":new_ver})

# ==================== API: 部署 ====================

@app.route("/api/tenants/<tid>/deploy", methods=["POST"])
@require_admin
def api_deploy(tid):
    action = request.json.get("action", "upload")
    d = db()
    config = d.execute("SELECT * FROM configs WHERE tenant_id=? ORDER BY version DESC LIMIT 1", [tid]).fetchone()
    if not config: d.close(); return jsonify({"error":"请先保存配置"}), 400

    cfg = row2dict(config)
    cfg["config"] = json.loads(cfg["config"])
    result = "pending"
    message = ""

    # 1. 生成小程序代码
    try:
        import subprocess
        cfg_json = json.dumps(cfg["config"], ensure_ascii=False)
        tmp_cfg = f"/tmp/deploy_{tid}.json"
        with open(tmp_cfg, "w") as f: f.write(cfg_json)
        out_dir = f"/opt/jiaxiao/dist/{tid}"
        subprocess.run(["node", "/opt/jiaxiao/scripts/generate.js", tmp_cfg, out_dir], check=True, capture_output=True, timeout=30)
        result = "generated"
        message = "代码已生成"
    except Exception as e:
        result = "failed"
        message = f"生成失败: {str(e)}"

    # 2. 如果有微信授权，通过模板上传代码
    if result == "generated" and action == "upload":
        token = wx_get_authorizer_token(tid)
        if token:
            try:
                # 用ext_json方式直接提交（不需要预存模板）
                ext = {"extEnable": True, "extAppid": config["mini_appid"] or cfg["config"]["school"]["appId"] or "", "directCommit": True}
                resp = _requests.post(f"https://api.weixin.qq.com/wxa/commit?access_token={token}", json={
                    "template_id": 0,
                    "ext_json": json.dumps(ext, ensure_ascii=False),
                    "user_version": f"v{config['version']}",
                    "user_desc": "小程序工厂自动部署 v"+str(config['version'])
                }, timeout=30).json()
                if resp.get("errcode",0) == 0:
                    result = "uploaded"
                    message = "代码已上传到微信"
                else:
                    # 如果模板不存在，需要先创建模板
                    if "template not exist" in str(resp.get("errmsg","")):
                        message = "需要在微信开发者工具中先上传一次代码建立模板，之后即可自动部署"
                    else:
                        message = resp.get("errmsg", "上传失败")
                    result = "upload_failed"
            except Exception as e:
                result = "upload_failed"
                message = str(e)

    # 更新状态
    status_map = {"generated":"deployed","uploaded":"deployed","failed":"draft","upload_failed":"draft"}
    d.execute("INSERT INTO deployments (tenant_id,config_version,action,result,message) VALUES (?,?,?,?,?)",
              [tid, config["version"], action, result, message])
    new_status = status_map.get(result, "draft")
    if new_status == "deployed":
        d.execute("UPDATE configs SET status=? WHERE id=?", ["deployed", config["id"]])
    d.commit()
    d.close()
    return jsonify({"ok":result!="failed","result":result,"message":message})

@app.route("/api/tenants/<tid>/deployments", methods=["GET"])
def api_deployments(tid):
    d = db()
    rows = d.execute("SELECT * FROM deployments WHERE tenant_id=? ORDER BY created_at DESC LIMIT 20", [tid]).fetchall()
    d.close()
    return jsonify([row2dict(r) for r in rows])

@app.route("/api/tenants/<tid>/trigger-deploy", methods=["POST"])
@require_admin
def api_trigger_github(tid):
    """服务端代理触发 GitHub Actions"""
    import urllib.request
    token = open("/opt/jiaxiao/platform/admin/.github_token").read().strip()
    data = json.dumps({"event_type": "deploy_tenant", "client_payload": {"tenant_id": tid}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/repos/fyj13667097290/weiqitong/dispatches",
        data=data,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        urllib.request.urlopen(req)
        return jsonify({"ok": True, "message": "已触发"})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500

# ==================== API: 健康检查 ====================

# ==================== 付费页面 ====================

PAY_PAGE = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>升级套餐</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#f0f2f5;min-height:100vh}
.header{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;text-align:center;padding:40px 20px}
.header h1{font-size:28px}.header p{font-size:14px;opacity:.8;margin-top:8px}
.container{max-width:500px;margin:-20px auto 0;padding:0 20px}
.card{background:#fff;border-radius:12px;padding:24px;margin-bottom:16px;box-shadow:0 2px 12px rgba(0,0,0,.06);text-align:center}
.plan-name{font-size:24px;font-weight:800;color:#1e3a5f}.plan-desc{font-size:13px;color:#999;margin:8px 0}
.price{font-size:48px;font-weight:800;color:#ff4d4f}.price span{font-size:16px;font-weight:400}.price .yen{font-size:28px}
.plan-features{text-align:left;margin:16px 0;font-size:14px;color:#666;line-height:2}
.plan-features li{list-style:none}.plan-features li::before{content:'✅ '}
.qr-section{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}
.qr-card{flex:1;min-width:140px;max-width:200px;text-align:center;background:#fafafa;padding:16px;border-radius:8px}
.qr-card img{width:160px;height:160px;border-radius:4px;background:#fff;object-fit:contain}
.qr-label{font-size:14px;font-weight:600;margin:8px 0 4px;color:#333}
.qr-tip{font-size:12px;color:#999}
.note{font-size:12px;color:#ff4d4f;margin-top:8px}
.btn{display:block;width:100%;padding:12px;background:#2563eb;color:#fff;border:none;border-radius:8px;font-size:15px;cursor:pointer;font-weight:600;margin-top:12px;text-align:center;text-decoration:none}
.btn-wx{background:#07c160}.btn-ali{background:#1677ff}
.back{text-align:center;padding:20px;font-size:13px}.back a{color:#999;text-decoration:none}
</style></head><body>
<div class="header"><h1>🏭 微企通</h1><p>升级套餐，解锁更多功能</p></div>
<div class="container">
<div class="card">
<div class="plan-name">{{plan_name}}</div>
<div class="plan-desc">{{plan_desc}}</div>
<div class="price"><span class="yen">¥</span>{{price}}<span>/年</span></div>
<div style="font-size:12px;color:#999;margin-top:4px">14天免费试用中，到期前续费即可</div>
</div>

<div class="card">
<h3 style="margin-bottom:16px;font-size:16px">📱 扫码支付</h3>
<div class="qr-section">
<div class="qr-card"><img src="https://jiaxiao.t-hub.cc/uploads/wechat_qr.png" alt="微信收款码"><div class="qr-label">微信支付</div><div class="qr-tip">扫码支付 ¥{{price}}</div></div>
<div class="qr-card"><img src="https://jiaxiao.t-hub.cc/uploads/alipay_qr.png" alt="支付宝收款码"><div class="qr-label">支付宝</div><div class="qr-tip">扫码支付 ¥{{price}}</div></div>
</div>
<p class="note">⚠️ 付完请截图发给对接人员确认开通</p>
</div>
</div>
<div class="back"><a href="javascript:history.back()">← 返回</a></div>
</body></html>"""

@app.route("/pay/<tid>")
def customer_pay(tid):
    d = db()
    t = d.execute("SELECT * FROM tenants WHERE id=?",[tid]).fetchone()
    if not t: d.close(); return "客户不存在", 404
    price_map = {"basic":(999,"基础版","品牌展示+报名+预约"),"standard":(1999,"标准版","+教练端+数据+营销"),"pro":(2999,"专业版","+支付+合同+多场地")}
    price, name, desc = price_map.get(t["plan"],(999,"基础版","品牌展示+在线报名"))
    d.close()
    return render_template_string(PAY_PAGE, price=price, plan_name=name, plan_desc=desc)

@app.route("/admin/tenant/<tid>/mark-paid")
@require_admin
def admin_mark_paid(tid):
    """管理员确认客户已付款，激活账户"""
    d = db()
    now_str = date.today().isoformat()
    d.execute("UPDATE tenants SET status='active', trial_end=? WHERE id=?", [now_str, tid])
    # 更新配置状态
    d.execute("UPDATE configs SET status='deployed' WHERE tenant_id=? AND status='draft'", [tid])
    d.commit(); d.close()
    return redirect("/admin")

# 在管理页面客户列表加付费按钮
# ==================== 推广人管理 ====================

PARTNER_PAGE = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>推广人管理</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#f0f2f5}
.header{background:#1e293b;color:#fff;padding:12px 20px;display:flex;justify-content:space-between}
.header h2{font-size:16px}.header a{color:#94a3b8;text-decoration:none;font-size:13px}
.container{max-width:1000px;margin:0 auto;padding:20px}
.card{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
h3{font-size:16px;margin-bottom:14px;display:flex;justify-content:space-between}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #f0f0f0}
th{color:#999;font-weight:500}.empty{text-align:center;color:#bbb;padding:20px}
.money{color:#52c41a;font-weight:700}
.inp{padding:8px;border:1px solid #d9d9d9;border-radius:4px;flex:1;min-width:80px;font-size:13px}
.row{display:flex;gap:10px;align-items:end;flex-wrap:wrap}
.btn{padding:8px 16px;background:#667eea;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:13px;white-space:nowrap}
.btn-del{background:#ff4d4f}
</style></head><body>
<div class="header"><h2>推广人管理</h2><a href="/admin">返回</a></div>
<div class="container">
{% for p in partners %}
<div class="card"><h3>{{p.name}} ({{p.phone or '-'}}) · 佣金率:{{p.commission_rate}}% · 已赚:<span class="money">¥{{p.total_commission or 0}}</span>
<a class="btn btn-del" href="/admin/partner/{{p.id}}/delete" onclick="return confirm('确定删除？')" style="font-size:11px;padding:3px 8px;margin-left:8px;color:#fff;text-decoration:none">删除</a></h3>
<p style="font-size:12px;color:#666;margin-bottom:8px">🔗 推广链接: <code>https://jiaxiao.t-hub.cc/ref/{{p.code}}</code> <a href="javascript:void(0)" onclick="var t=document.createElement('textarea');t.value='https://jiaxiao.t-hub.cc/ref/{{p.code}}';document.body.appendChild(t);t.select();document.execCommand('copy');alert('已复制！');document.body.removeChild(t)" style="color:#1890ff;font-size:11px;margin-left:4px">复制</a></p>
{% if p.clients %}<table><tr><th>客户</th><th>套餐</th><th>类型</th><th>佣金</th><th>时间</th></tr>
{% for c in p.clients %}<tr><td>{{c.name}}</td><td>{{c.plan}}</td><td>{{c.year_type}}</td><td class="money">¥{{c.commission}}</td><td>{{c.created_at[:10]}}</td></tr>{% endfor %}</table>
{% else %}<p class="empty">暂无客户</p>{% endif %}</div>
{% endfor %}
<div class="card"><h3>+ 添加推广人</h3>
<form method="POST" action="/admin/partner/new" class="row">
<input name="name" placeholder="姓名" required class="inp"><input name="phone" placeholder="电话" class="inp">
<input name="password" placeholder="密码" value="123456" class="inp" style="max-width:80px">
<input name="commission_rate" placeholder="佣金%" type="number" value="20" class="inp" style="max-width:80px">
<button class="btn" type="submit">添加</button></form></div>
</div></body></html>"""

@app.route("/admin/partners")
@require_admin
def admin_partners():
    d = db()
    partners = d.execute("SELECT * FROM referrers WHERE role='agent' AND is_active=1 ORDER BY created_at DESC").fetchall()
    pd_list = []
    for p in partners:
        pd = dict(p)
        clients = d.execute("SELECT * FROM tenants WHERE referrer_id=? AND status!='inactive' ORDER BY created_at DESC", [p["id"]]).fetchall()
        cl = []; total = 0; rate = p["commission_rate"] or 20
        for c in clients:
            yt = "首年"; r = rate
            if c["created_at"]:
                try:
                    ts = _time.mktime(_time.strptime(c["created_at"][:10],"%Y-%m-%d"))
                    if (_time.time()-ts)/86400/30 > 12: yt = "续费"; r = rate//2
                except: pass
            price = {"basic":999,"standard":1999,"pro":2999,"trial":0}.get(c["plan"],999)
            comm = int(price*r/100); total += comm
            cl.append({"name":c["name"],"plan":c["plan"],"year_type":yt,"commission":comm,"created_at":c["created_at"]})
        pd["clients"] = cl; pd["total_commission"] = total; pd_list.append(pd)
    d.close()
    return render_template_string(PARTNER_PAGE, partners=pd_list)

@app.route("/admin/partner/new", methods=["POST"])
@require_admin
def admin_partner_new():
    d = db(); import random, string
    code = ''.join(random.choices(string.ascii_letters+string.digits, k=8))
    d.execute("INSERT INTO referrers (name,phone,password,code,commission_rate,role,is_active) VALUES (?,?,?,?,?,?,1)",
              [request.form["name"],request.form.get("phone",""),request.form.get("password","123456"),code,int(request.form.get("commission_rate",20)),"agent"])
    d.commit(); d.close()
    return redirect("/admin/partners")

@app.route("/admin/partner/<int:pid>/delete")
@require_admin
def admin_partner_delete(pid):
    d = db(); d.execute("UPDATE referrers SET is_active=0 WHERE id=?",[pid]); d.commit(); d.close()
    return redirect("/admin/partners")

PARTNER_LOGIN = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>推广人登录</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border-radius:16px;padding:40px;width:90%;max-width:360px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.2)}
h2{font-size:20px;margin-bottom:8px}.sub{color:#999;font-size:13px;margin-bottom:20px}
input{width:100%;padding:12px;border:1px solid #d9d9d9;border-radius:8px;font-size:15px;margin-bottom:12px;text-align:center}
.btn{width:100%;padding:12px;background:#667eea;color:#fff;border:none;border-radius:8px;font-size:15px;cursor:pointer;font-weight:600}
.err{color:#ff4d4f;font-size:12px;margin-bottom:8px}</style></head><body>
<div class="card"><h2>佣金查询</h2><p class="sub">推广人登录</p>
<form method="POST"><input name="phone" placeholder="手机号" required><input name="password" placeholder="密码"><button class="btn" type="submit">登录</button></form>
<p class="err">{{error or ''}}</p></div></body></html>"""

PARTNER_DASHBOARD = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>我的佣金</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#f0f2f5}
.header{background:#1e293b;color:#fff;padding:12px 20px}.header h2{font-size:16px}
.container{max-width:600px;margin:0 auto;padding:20px}
.card{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px;text-align:center}
.big-num{font-size:48px;font-weight:800;color:#52c41a}.big-label{color:#999;font-size:14px;margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:13px;margin-top:16px}th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #f0f0f0}
th{color:#999;font-weight:500}.money{color:#52c41a;font-weight:700}.empty{text-align:center;color:#bbb;padding:20px}
</style></head><body><div class="header"><h2>我的佣金</h2></div><div class="container">
<div class="card"><div class="big-num">¥{{total}}</div><div class="big-label">累计佣金</div></div>
<div class="card" style="text-align:left"><p style="font-size:14px;color:#666">你的专属推广链接：</p>
<p style="font-size:16px;word-break:break-all;margin:8px 0;background:#f0f5ff;padding:10px;border-radius:6px">{{link}}</p>
<p style="font-size:12px;color:#999">发给客户打开，系统自动记录你推荐的客户</p></div>
<div class="card"><h3 style="text-align:left;margin-bottom:12px">客户明细</h3>
{% if clients %}<table><tr><th>客户</th><th>套餐</th><th>年费</th><th>佣金率</th><th>佣金</th><th>付费</th></tr>
{% for c in clients %}<tr><td>{{c.name}}</td><td>{{c.plan}}</td><td>¥{{c.price}}</td><td>{{c.rate}}%</td><td class="money">¥{{c.commission}}</td>
<td><a href="/pay/{{c.tid}}" target="_blank" style="color:#ff9800;text-decoration:none;font-weight:600;font-size:12px">付</a></td>
</tr>{% endfor %}</table>
{% else %}<p class="empty">还没有推荐客户</p>{% endif %}</div>
</div></body></html>"""

@app.route("/partner/login", methods=["GET","POST"])
def partner_login():
    error = None
    if request.method == "POST":
        d = db(); p = d.execute("SELECT * FROM referrers WHERE phone=? AND role='agent' AND is_active=1",[request.form["phone"]]).fetchone(); d.close()
        if p and p["password"]==request.form.get("password",""):
            resp = redirect("/partner/dashboard"); resp.set_cookie("partner_id",str(p["id"]),max_age=86400*7); return resp
        error = "手机号或密码错误"
    return render_template_string(PARTNER_LOGIN, error=error)

@app.route("/ref/<code>", methods=["GET","POST"])
def partner_ref(code):
    """推广链接落地页"""
    d = db(); p = d.execute("SELECT * FROM referrers WHERE code=? AND role='agent' AND is_active=1",[code]).fetchone()
    if not p: d.close(); return "推广链接无效", 404
    msg = ""
    if request.method == "POST":
        tid = f"t{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        d.execute("INSERT INTO tenants (id,name,contact_phone,industry_id,status,plan,referrer_id,trial_end) VALUES (?,?,?,?,?,?,?,?)",
                  [tid, request.form["name"], request.form["phone"], "drv001", "trial", "trial", p["id"], (date.today()+timedelta(days=14)).isoformat()])
        d.commit(); d.close()
        msg = "提交成功！14天免费试用已开通，我们将在24小时内联系您确认信息。"
    d.close()
    FORM = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>微企通</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#1e3a5f,#2563eb);min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border-radius:16px;padding:30px;width:90%;max-width:380px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.2)}
h2{font-size:20px;margin-bottom:4px}.sub{color:#999;font-size:13px;margin-bottom:20px}
input{width:100%;padding:10px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;margin-bottom:12px}
.btn{width:100%;padding:10px;background:#2563eb;color:#fff;border:none;border-radius:6px;font-size:15px;cursor:pointer;font-weight:600}
.msg{color:#52c41a;font-size:13px;margin-top:10px}</style></head><body>
<div class="card"><h2>🏭 免费试用微信小程序</h2><p class="sub">14天免费试用，满意再付费 · 留下联系方式立即开通</p>
<form method="POST"><input name="name" placeholder="商家名称" required><input name="phone" placeholder="联系电话" required><button class="btn" type="submit">提交申请</button></form>
<p class="msg">MSG</p></div></body></html>"""
    return FORM.replace("MSG", msg)
    return resp

@app.route("/partner/dashboard")
def partner_dashboard():
    pid = request.cookies.get("partner_id","");
    if not pid: return redirect("/partner/login")
    d = db(); p = d.execute("SELECT * FROM referrers WHERE id=?",[int(pid)]).fetchone()
    if not p: d.close(); return redirect("/partner/login")
    clients = d.execute("SELECT * FROM tenants WHERE referrer_id=? AND status!='inactive'",[int(pid)]).fetchall()
    cl = []; total = 0; rate = p["commission_rate"] or 20
    for c in clients:
        price = {"basic":999,"standard":1999,"pro":2999,"trial":0}.get(c["plan"],999); r = rate
        if c["created_at"]:
            try:
                if (_time.time()-_time.mktime(_time.strptime(c["created_at"][:10],"%Y-%m-%d")))/86400/30>12: r=rate//2
            except: pass
        comm = int(price*r/100); total += comm
        cl.append({"name":c["name"],"plan":c["plan"],"price":price,"rate":r,"commission":comm,"tid":c["id"]})
    d.close()
    ref_code = p["code"]
    ref_link = f"https://jiaxiao.t-hub.cc/ref/{ref_code}"
    return render_template_string(PARTNER_DASHBOARD, total=total, clients=cl, code=ref_code, link=ref_link)

@app.route("/debug/wx")
def debug_wx():
    """调试：查看微信票据状态"""
    ticket = wx_get_stored(WX_TICKET_FILE) or "空"
    token = wx_get_stored(WX_ACCESS_TOKEN_FILE) or "空"
    return jsonify({"ticket":ticket[:50]+"..." if len(ticket)>50 else ticket, "token":token[:50]+"..." if len(token)>50 else token})

@app.route("/api/health")
def health():
    d = db()
    tc = d.execute("SELECT COUNT(*) as c FROM tenants").fetchone()["c"]
    d.close()
    return jsonify({"status":"ok","server":"Miami","tenants":tc,"timestamp":now()})

# ==================== 启动 ====================

# ==================== 客户自助管理后台 ====================

CUSTOMER_LOGIN = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{tenant.name}}管理后台</title>
<style>*{margin:0;padding:0;box-sizing:border-box} body{font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border-radius:16px;padding:40px 30px;width:90%;max-width:400px;box-shadow:0 20px 60px rgba(0,0,0,.2);text-align:center}
h2{font-size:22px;margin-bottom:8px} .sub{color:#999;font-size:14px;margin-bottom:24px}
input{width:100%;padding:12px;border:1px solid #d9d9d9;border-radius:8px;font-size:16px;margin-bottom:16px;text-align:center}
.btn{width:100%;padding:12px;background:#667eea;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;font-weight:600}
.err{color:#ff4d4f;font-size:13px;margin-bottom:12px}</style></head><body>
<div class="card"><h2>🏫 {{tenant.name}}</h2><p class="sub">小程序管理后台</p>
<form method="POST"><input type="password" name="password" placeholder="请输入管理密码" required><br>
{% if error %}<p class="err">{{error}}</p>{% endif %}
<button class="btn" type="submit">登录</button></form></div></body></html>"""

CUSTOMER_DASHBOARD = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{tenant.name}} · 管理</title>
<style>:root{--primary:#667eea} *{margin:0;padding:0;box-sizing:border-box} body{font-family:-apple-system,sans-serif;background:#f0f2f5}
.header{background:#1e293b;color:#fff;padding:12px 20px;display:flex;justify-content:space-between;align-items:center}
.header h2{font-size:16px} .header a{color:#94a3b8;text-decoration:none;font-size:13px}
.container{max-width:800px;margin:0 auto;padding:20px}
.card{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.card h3{font-size:16px;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between}
.card h3 a{font-size:12px;color:var(--primary);text-decoration:none;font-weight:400}
table{width:100%;border-collapse:collapse;font-size:13px} th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #f0f0f0}
th{color:#999;font-weight:500}.empty{text-align:center;color:#bbb;padding:20px}
.btn-sm{font-size:11px;padding:3px 8px;border-radius:3px;border:none;cursor:pointer;text-decoration:none;color:#fff;display:inline-block}
.btn-del{background:#ff4d4f}</style></head><body>
<div class="header"><h2>🏫 {{tenant.name}}</h2><div><a href="/school/{{tenant.id}}/password" style="color:#94a3b8;text-decoration:none;font-size:13px;margin-right:16px">修改密码</a><a href="/school/{{tenant.id}}/login">退出</a></div></div>
<div class="container">

<div class="card"><h3>💳 升级套餐 <a href="/pay/{{tenant.id}}" target="_blank">立即付费</a></h3>
<p style="font-size:13px;color:#666">当前: {{tenant.plan}} · 状态: {{tenant.status}}</p></div>

<div class="card"><h3>🖼️ 小程序背景</h3>
<form method="POST" action="/school/{{tenant.id}}/upload-bg" enctype="multipart/form-data" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
<input type="file" name="bg_image" accept="image/*" required style="padding:6px;border:1px solid #d9d9d9;border-radius:4px;flex:1;min-width:200px">
<button type="submit" class="btn-sm" style="background:#667eea;color:#fff;padding:8px 16px;font-size:13px">上传并设为背景</button>
</form></div>

<div class="card"><h3>📢 公告 <a href="/school/{{tenant.id}}/announcement/new">+ 发布</a></h3>
{% if announcements %}<table><tr><th>标题</th><th>时间</th><th>操作</th></tr>
{% for a in announcements %}<tr><td>{{a.title}}</td><td>{{a.created_at[:10]}}</td><td><a class="btn-sm btn-del" href="/school/{{tenant.id}}/announcement/{{a.id}}/delete" onclick="return confirm('确定删除？')">删除</a></td></tr>{% endfor %}</table>
{% else %}<p class="empty">暂无公告</p>{% endif %}</div>

<div class="card"><h3>💰 课程 <a href="/school/{{tenant.id}}/course/new">+ 添加</a></h3>
{% if courses %}<table><tr><th>名称</th><th>价格</th><th>状态</th><th>操作</th></tr>
{% for c in courses %}<tr><td>{{c.name}}</td><td>¥{{c.price}}</td><td>{{'显示' if c.is_visible else '隐藏'}}</td><td><a class="btn-sm btn-del" href="/school/{{tenant.id}}/course/{{c.id}}/delete" onclick="return confirm('确定删除？')">删除</a></td></tr>{% endfor %}</table>
{% else %}<p class="empty">暂无动态课程（配置页的课程优先）</p>{% endif %}</div>

<div class="card"><h3>👨‍🏫 教练 <a href="/school/{{tenant.id}}/coach/new">+ 添加</a></h3>
{% if coaches %}<table><tr><th>姓名</th><th>教龄</th><th>评分</th><th>操作</th></tr>
{% for c in coaches %}<tr><td>{{c.name}}</td><td>{{c.experience}}年</td><td>{{c.rating or '-'}}</td><td><a class="btn-sm btn-del" href="/school/{{tenant.id}}/coach/{{c.id}}/delete" onclick="return confirm('确定删除？')">删除</a></td></tr>{% endfor %}</table>
{% else %}<p class="empty">暂无教练</p>{% endif %}</div>

<div class="card"><h3>📂 商品类目 <a href="/school/{{tenant.id}}/categories">管理</a></h3>
<p style="font-size:13px;color:#666">自定义商品分类</p></div>

<div class="card"><h3>⚙️ 预约设置 <a href="/school/{{tenant.id}}/appointment-settings">管理</a></h3>
<p style="font-size:13px;color:#666">设可约时段、人数上限、开关预约</p></div>

<div class="card"><h3>👥 招生老师 <a href="/school/{{tenant.id}}/referrers">管理</a></h3>
<p style="font-size:13px;color:#666">管理招生老师账号，查看各渠道推荐数据</p></div>

{% if industry_slug in ('retail','restaurant','beauty') %}
<div class="card"><h3>📂 商品类目 <a href="/school/{{tenant.id}}/categories">管理</a></h3><p style="font-size:13px;color:#666">自定义商品分类</p></div>
{% endif %}
<div class="card"><h3>📋 最近预约</h3>
{% if appointments %}<table><tr><th>学员</th><th>电话</th><th>课程</th><th>时间</th><th>状态</th><th>操作</th></tr>
{% for a in appointments %}<tr><td>{{a.student_name}}</td><td>{{a.student_phone}}</td><td>{{a.course_type}}</td><td>{{a.appointment_time}}</td><td><span class="tag tag-{{a.status}}">{{a.status}}</span></td>
<td>{% if a.status=='pending' %}<a class="btn-sm" style="background:#52c41a;color:#fff" href="/school/{{tenant.id}}/appointment/{{a.id}}/confirm">确认</a>{% elif a.status=='confirmed' %}<a class="btn-sm" style="background:#1890ff;color:#fff" href="/school/{{tenant.id}}/appointment/{{a.id}}/complete">完成</a>{% endif %}</td></tr>{% endfor %}</table>
{% else %}<p class="empty">暂无预约</p>{% endif %}</div>

</div></body></html>"""

@app.route("/school/<tid>/login", methods=["GET","POST"])
def customer_login(tid):
    d = db()
    t = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    if not t: d.close(); return "驾校不存在", 404
    error = None
    if request.method == "POST":
        pw = request.form.get("password","")
        admin = d.execute("SELECT * FROM customer_admins WHERE tenant_id=?", [tid]).fetchone()
        # 首次登录自动创建管理员
        if not admin:
            d.execute("INSERT INTO customer_admins (tenant_id,password) VALUES (?,?)", [tid, pw])
            d.commit()
            admin = {"password": pw}
        if pw == admin["password"]:
            resp = redirect(f"/school/{tid}/dashboard")
            resp.set_cookie("school_admin", tid, max_age=86400*7)
            d.close()
            return resp
        error = "密码错误"
    d.close()
    return render_template_string(CUSTOMER_LOGIN, tenant=dict(t), error=error)

@app.route("/school/<tid>/dashboard")
def customer_dashboard(tid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()):
        return redirect(f"/school/{tid}/login")
    d = db()
    t = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    industry = d.execute("SELECT slug FROM industries WHERE id=?",[t["industry_id"]]).fetchone()
    industry_slug = industry["slug"] if industry else "driving"
    announcements = d.execute("SELECT * FROM announcements WHERE tenant_id=? ORDER BY is_pinned DESC, created_at DESC", [tid]).fetchall()
    courses = d.execute("SELECT * FROM dynamic_courses WHERE tenant_id=? ORDER BY sort_order", [tid]).fetchall()
    coaches = d.execute("SELECT * FROM dynamic_coaches WHERE tenant_id=? ORDER BY sort_order", [tid]).fetchall()
    categories = d.execute("SELECT * FROM dynamic_categories WHERE tenant_id=? AND is_active=1 ORDER BY sort_order",[tid]).fetchall()
    appointments = d.execute("SELECT * FROM appointments WHERE tenant_id=? ORDER BY created_at DESC LIMIT 20", [tid]).fetchall()
    d.close()
    return render_template_string(CUSTOMER_DASHBOARD, tenant=dict(t), announcements=announcements, courses=courses, coaches=coaches, categories=categories, appointments=appointments, industry_slug=industry_slug)

@app.route("/school/<tid>/announcement/new", methods=["GET","POST"])
def customer_announcement_new(tid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    if request.method == "POST":
        d = db()
        d.execute("INSERT INTO announcements (tenant_id,title,content) VALUES (?,?,?)", [tid, request.form["title"], request.form.get("content","")])
        d.commit(); d.close()
        return redirect(f"/school/{tid}/dashboard")
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>发布公告</title>
<style>*{{margin:0;padding:0}}body{{font-family:-apple-system,sans-serif;background:#f0f2f5;padding:20px}}
.card{{background:#fff;max-width:500px;margin:40px auto;padding:24px;border-radius:8px}}
h3{{margin-bottom:16px}} input,textarea{{width:100%;padding:10px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;margin-bottom:12px}}
textarea{{resize:vertical;min-height:100px}}
.btn{{padding:10px 24px;background:#667eea;color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:600}}
</style></head><body><div class="card"><h3>📢 发布公告</h3>
<form method="POST"><input name="title" placeholder="公告标题" required><textarea name="content" placeholder="公告内容"></textarea>
<button class="btn" type="submit">发布</button><a href="/school/{tid}/dashboard" style="margin-left:12px;color:#999;font-size:13px">取消</a></form></div></body></html>"""

@app.route("/school/<tid>/announcement/<int:aid>/delete")
def customer_announcement_delete(tid, aid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    d = db(); d.execute("DELETE FROM announcements WHERE id=? AND tenant_id=?", [aid, tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/dashboard")

@app.route("/school/<tid>/course/new", methods=["GET","POST"])
def customer_course_new(tid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    if request.method == "POST":
        d = db()
        d.execute("INSERT INTO dynamic_courses (tenant_id,name,price,original_price,features,tag) VALUES (?,?,?,?,?,?)",
                  [tid, request.form["name"], float(request.form["price"]), float(request.form.get("original_price",0) or 0), request.form.get("features",""), request.form.get("tag","")])
        d.commit(); d.close()
        return redirect(f"/school/{tid}/dashboard")
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>添加课程</title>
<style>*{{margin:0;padding:0}}body{{font-family:-apple-system,sans-serif;background:#f0f2f5;padding:20px}}
.card{{background:#fff;max-width:500px;margin:40px auto;padding:24px;border-radius:8px}}
h3{{margin-bottom:16px}} input{{width:100%;padding:10px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;margin-bottom:12px}}
.row{{display:flex;gap:12px}} .row input{{flex:1}}
.btn{{padding:10px 24px;background:#667eea;color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:600}}
</style></head><body><div class="card"><h3>💰 添加课程</h3>
<form method="POST"><input name="name" placeholder="课程名称" required><div class="row"><input name="price" placeholder="价格" type="number" required><input name="original_price" placeholder="原价（可选）" type="number"></div>
<input name="features" placeholder="特色（逗号分隔，如：免费接送,不限课时）"><input name="tag" placeholder="标签（如：热销）">
<button class="btn" type="submit">添加</button><a href="/school/{tid}/dashboard" style="margin-left:12px;color:#999;font-size:13px">取消</a></form></div></body></html>"""

@app.route("/school/<tid>/course/<int:cid>/delete")
def customer_course_delete(tid, cid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    d = db(); d.execute("DELETE FROM dynamic_courses WHERE id=? AND tenant_id=?", [cid, tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/dashboard")

@app.route("/school/<tid>/coach/new", methods=["GET","POST"])
def customer_coach_new(tid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    if request.method == "POST":
        d = db()
        d.execute("INSERT INTO dynamic_coaches (tenant_id,name,experience,pass_rate,rating,tags,phone) VALUES (?,?,?,?,?,?,?)",
                  [tid, request.form["name"], int(request.form.get("experience",0) or 0), int(request.form.get("pass_rate",0) or 0), float(request.form.get("rating",0) or 0), request.form.get("tags",""), request.form.get("phone","")])
        d.commit(); d.close()
        return redirect(f"/school/{tid}/dashboard")
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>添加教练</title>
<style>*{{margin:0;padding:0}}body{{font-family:-apple-system,sans-serif;background:#f0f2f5;padding:20px}}
.card{{background:#fff;max-width:500px;margin:40px auto;padding:24px;border-radius:8px}}
h3{{margin-bottom:16px}} input{{width:100%;padding:10px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;margin-bottom:12px}}
.row{{display:flex;gap:12px}} .row input{{flex:1}}
.btn{{padding:10px 24px;background:#667eea;color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:600}}
</style></head><body><div class="card"><h3>👨‍🏫 添加教练</h3>
<form method="POST"><input name="name" placeholder="教练姓名" required><div class="row"><input name="experience" placeholder="教龄(年)" type="number"><input name="pass_rate" placeholder="通过率(%)" type="number"></div>
<div class="row"><input name="rating" placeholder="评分(1-5)" type="number" step="0.1"><input name="phone" placeholder="电话"></div>
<input name="tags" placeholder="特点（逗号分隔，如：耐心,技术好）">
<button class="btn" type="submit">添加</button><a href="/school/{tid}/dashboard" style="margin-left:12px;color:#999;font-size:13px">取消</a></form></div></body></html>"""

@app.route("/school/<tid>/coach/<int:cid>/delete")
def customer_coach_delete(tid, cid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    d = db(); d.execute("DELETE FROM dynamic_coaches WHERE id=? AND tenant_id=?", [cid, tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/dashboard")

@app.route("/school/<tid>/password", methods=["GET","POST"])
def customer_password(tid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    d = db(); msg = ""
    if request.method == "POST":
        old = request.form.get("old",""); new = request.form.get("new","")
        admin = d.execute("SELECT * FROM customer_admins WHERE tenant_id=?", [tid]).fetchone()
        if not admin or old != admin["password"]: msg = "原密码错误"
        elif len(new) < 4: msg = "新密码至少4位"
        else:
            d.execute("UPDATE customer_admins SET password=? WHERE tenant_id=?", [new, tid]); d.commit()
            msg = "密码修改成功"
    d.close()
    color = '#ff4d4f' if '错误' in msg else '#52c41a'
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>修改密码</title>
<style>*{{margin:0;padding:0}}body{{font-family:-apple-system,sans-serif;background:#f0f2f5;padding:20px}}.card{{background:#fff;max-width:400px;margin:60px auto;padding:30px;border-radius:8px;text-align:center}}
h3{{margin-bottom:20px}}input{{width:100%;padding:10px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;margin-bottom:12px;text-align:center}}
.btn{{width:100%;padding:10px;background:#667eea;color:#fff;border:none;border-radius:4px;cursor:pointer;font-weight:600;font-size:14px}}
.msg{{color:{color};font-size:13px;margin-bottom:12px}}
</style></head><body><div class="card"><h3>🔒 修改管理密码</h3>
<form method="POST"><input type="password" name="old" placeholder="原密码" required><input type="password" name="new" placeholder="新密码（至少4位）" required>
<button class="btn" type="submit">确认修改</button></form>
<p class="msg">{msg or ''}</p>
<a href="/school/{tid}/dashboard" style="font-size:13px;color:#999;text-decoration:none">← 返回</a>
</div></body></html>"""

@app.route("/school/<tid>/impersonate")
@require_admin
def customer_impersonate(tid):
    """超级管理员免密码进入客户后台"""
    resp = redirect(f"/school/{tid}/dashboard")
    resp.set_cookie("school_admin", tid, max_age=86400)
    return resp

# ==================== 微信授权 & 代码上传 ====================

@app.route("/api/wechat/auth-url/<tid>")
@require_admin
def wechat_auth_url(tid):
    """生成驾校老板扫码授权的URL"""
    code = wx_get_pre_auth_code()
    if not code: return jsonify({"error":"获取预授权码失败，请稍后重试"}), 500
    # 文件存映射（跨worker+重启不丢）
    wx_store(os.path.join(WX_MAP_DIR, code.split("@@@")[-1][:20]), tid)
    url = f"https://jiaxiao.t-hub.cc/auth/{tid}?code={code}"
    return jsonify({"url": url, "tip":"请将此链接发给驾校老板，用微信打开后扫码授权"})

@app.route("/auth/<tid>")
def wechat_auth_page(tid):
    """授权跳转页"""
    import urllib.parse
    code = request.args.get("code","")
    auth_code = request.args.get("auth_code","")
    # 如果收到auth_code（微信授权回调），直接处理
    if auth_code:
        handle_auth_callback(tid, auth_code)
        return redirect(f"/school/{tid}/dashboard?auth=ok")
    # 否则是pre_auth_code，跳转微信授权
    redirect_uri = urllib.parse.quote(f"https://jiaxiao.t-hub.cc/auth/{tid}", safe='')
    wx_url = f"https://mp.weixin.qq.com/cgi-bin/componentloginpage?component_appid={WX_COMPONENT_APPID}&pre_auth_code={code}&redirect_uri={redirect_uri}&auth_type=3"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>授权</title></head>
<body style="text-align:center;padding-top:40px;font-family:sans-serif">
<p>正在跳转到微信授权...</p>
<script>location.href="{wx_url}";</script>
</body></html>"""

def handle_auth_callback(tid, auth_code):
    """处理微信授权回调：用auth_code换取authorizer_access_token"""
    token = wx_get_component_token()
    if not token or not auth_code: return
    resp = _requests.post(f"https://api.weixin.qq.com/cgi-bin/component/api_query_auth?component_access_token={token}", json={
        "component_appid": WX_COMPONENT_APPID,
        "authorization_code": auth_code
    }).json()
    info = resp.get("authorization_info",{})
    if info:
        d = db()
        appid = info.get("authorizer_appid","")
        d.execute("INSERT OR REPLACE INTO wechat_auths (tenant_id,authorizer_appid,authorizer_access_token,authorizer_refresh_token,authorized_at) VALUES (?,?,?,?,datetime('now'))",
                  [tid, appid, info.get("authorizer_access_token",""), info.get("authorizer_refresh_token","")])
        # 同步更新配置里的AppID
        latest = d.execute("SELECT * FROM configs WHERE tenant_id=? ORDER BY version DESC LIMIT 1", [tid]).fetchone()
        if latest:
            cfg = json.loads(latest["config"])
            cfg["school"]["appId"] = appid
            d.execute("INSERT INTO configs (tenant_id,version,config,status,mini_appid) VALUES (?,?,?,?,?)",
                      [tid, latest["version"]+1, json.dumps(cfg, ensure_ascii=False), "draft", appid])
        d.commit(); d.close()

@app.route("/api/wechat/upload-code/<tid>", methods=["POST"])
@require_admin
def wechat_upload_code(tid):
    """上传代码到授权小程序"""
    d = db()
    token = wx_get_authorizer_token(tid)
    if not token: d.close(); return jsonify({"error":"该驾校尚未授权或token获取失败"}), 400
    config = d.execute("SELECT * FROM configs WHERE tenant_id=? ORDER BY version DESC LIMIT 1", [tid]).fetchone()
    d.close()
    if not config: return jsonify({"error":"请先保存小程序配置"}), 400

    cfg = json.loads(config["config"])
    # 构造ext.json注入驾校配置
    ext_json = json.dumps({
        "extEnable": True,
        "extAppid": auth["authorizer_appid"],
        "directCommit": False,
        "ext": {
            "schoolName": cfg["school"]["name"],
            "schoolPhone": cfg["school"]["phone"],
            "primaryColor": cfg["school"]["theme"]["primaryColor"]
        }
    }, ensure_ascii=False)

    # 1. 提交代码
    commit_resp = _requests.post(f"https://api.weixin.qq.com/wxa/commit?access_token={token}", json={
        "template_id": 0,  # 0=不使用模板，直接上传
        "ext_json": ext_json,
        "user_version": f"v{config['version']}",
        "user_desc": "小程序工厂自动部署"
    }).json()
    if commit_resp.get("errcode",0) != 0:
        return jsonify({"error":commit_resp.get("errmsg","上传失败"),"detail":commit_resp})

    return jsonify({"ok":True,"message":"代码已上传","version":f"v{config['version']}"})

@app.route("/api/wechat/submit-audit/<tid>", methods=["POST"])
@require_admin
def wechat_submit_audit(tid):
    """提交代码审核"""
    token = wx_get_authorizer_token(tid)
    if not token: return jsonify({"error":"该驾校尚未授权"}), 400

    data = request.get_json() or {}
    item_list = data.get("item_list", [
        {"address":"pages/index/index","tag":"驾校预约","title":"首页"},
        {"address":"pages/courses/courses","tag":"在线教育","title":"培训课程"},
        {"address":"pages/appointment/appointment","tag":"预约预订","title":"预约练车"}
    ])
    resp = _requests.post(f"https://api.weixin.qq.com/wxa/submit_audit?access_token={token}", json={"item_list": item_list}).json()
    if resp.get("errcode",0) != 0:
        return jsonify({"error":resp.get("errmsg","提审失败"),"detail":resp})
    return jsonify({"ok":True,"auditid":resp.get("auditid"),"message":"审核已提交，预计1-7个工作日"})

@app.route("/api/wechat/undocodeaudit/<tid>", methods=["POST"])
@require_admin
def wechat_undo_audit(tid):
    """撤回审核"""
    token = wx_get_authorizer_token(tid)
    if not token: return jsonify({"error":"未授权"}), 400
    resp = _requests.get(f"https://api.weixin.qq.com/wxa/undocodeaudit?access_token={token}").json()
    if resp.get("errcode",0) != 0:
        return jsonify({"error":resp.get("errmsg","撤回失败")})
    return jsonify({"ok":True,"message":"已撤回审核"})

@app.route("/api/wechat/release/<tid>", methods=["POST"])
@require_admin
def wechat_release(tid):
    """发布已审核通过的小程序"""
    token = wx_get_authorizer_token(tid)
    if not token: return jsonify({"error":"未授权"}), 400
    resp = _requests.post(f"https://api.weixin.qq.com/wxa/release?access_token={token}", json={}).json()
    if resp.get("errcode",0) != 0:
        return jsonify({"error":resp.get("errmsg","发布失败"),"detail":resp})
    return jsonify({"ok":True,"message":"已发布上线"})

@app.route("/api/wechat/auth-status/<tid>")
@require_admin
def wechat_auth_status(tid):
    """查看驾校授权状态"""
    d = db()
    auth = d.execute("SELECT authorizer_appid,authorized_at FROM wechat_auths WHERE tenant_id=?", [tid]).fetchone()
    d.close()
    if auth:
        return jsonify({"authorized":True,"appid":auth["authorizer_appid"],"time":auth["authorized_at"]})
    return jsonify({"authorized":False})

# ==================== 代注册小程序 ====================

@app.route("/api/wechat/fast-register/<tid>", methods=["POST"])
@require_admin
def wechat_fast_register(tid):
    """帮客户一键注册小程序"""
    d = db()
    t = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    if not t: d.close(); return jsonify({"error":"客户不存在"}), 404
    token = wx_get_component_token()
    if not token: d.close(); return jsonify({"error":"微信服务暂不可用"}), 500

    data = request.get_json()
    resp = _requests.post(
        f"https://api.weixin.qq.com/cgi-bin/component/fastregisterweapp?action=create&component_access_token={token}",
        json={
            "name": data.get("mp_name", t["name"]),
            "code": data.get("license_code", ""),
            "code_type": 1,
            "legal_persona_wechat": data.get("legal_wechat", ""),
            "legal_persona_name": data.get("legal_name", ""),
            "component_phone": data.get("phone", t["contact_phone"] or "")
        }
    ).json()

    if resp.get("errcode", 0) != 0:
        err = resp.get("errmsg", "注册失败")
        d.close(); return jsonify({"error": err})

    # 保存法人信息
    d.execute("UPDATE tenants SET contact_name=?, contact_phone=? WHERE id=?",
              [data.get("legal_name", t["contact_name"] or ""), data.get("phone", t["contact_phone"] or ""), tid])
    d.commit(); d.close()

    return jsonify({"ok": True, "qrcode_base64": resp.get("qrcode_url", ""),
                    "tip": "请将二维码发给法人，用微信扫码后在小程序内确认。确认后小程序自动创建并授权给平台。"})

# ==================== 图片上传 ====================
import os as _os
UPLOAD_DIR = "/opt/jiaxiao/static/uploads"
_os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/school/<tid>/upload-bg", methods=["POST"])
def customer_upload_bg(tid):
    if request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw():
        return redirect(f"/school/{tid}/login")
    file = request.files.get("bg_image")
    if not file: return "请选择图片", 400
    ext = file.filename.rsplit(".",1)[-1].lower()
    if ext not in ("jpg","jpeg","png","gif","webp"): return "仅支持 JPG/PNG/GIF/WEBP", 400
    fname = f"{tid}_bg.{ext}"
    file.save(_os.path.join(UPLOAD_DIR, fname))
    url = f"https://jiaxiao.t-hub.cc/uploads/{fname}"
    d = db()
    latest = d.execute("SELECT * FROM configs WHERE tenant_id=? ORDER BY version DESC LIMIT 1", [tid]).fetchone()
    if latest:
        cfg = json.loads(latest["config"])
        cfg["school"]["photos"] = [url]
        new_ver = latest["version"] + 1
        d.execute("INSERT INTO configs (tenant_id,version,config,status,mini_appid,mini_appname) VALUES (?,?,?,?,?,?)",
                  [tid, new_ver, json.dumps(cfg, ensure_ascii=False), "draft", latest["mini_appid"] or "", latest["mini_appname"] or ""])
        d.commit()
    d.close()
    return redirect(f"/school/{tid}/dashboard")

# 公开API：小程序端读取动态内容
@app.route("/api/public/<tid>/announcements")
def api_public_announcements(tid):
    d = db()
    rows = d.execute("SELECT id,title,content,created_at FROM announcements WHERE tenant_id=? ORDER BY is_pinned DESC, created_at DESC LIMIT 20", [tid]).fetchall()
    d.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/public/<tid>/courses")
def api_public_courses(tid):
    d = db()
    rows = d.execute("SELECT id,name,price,original_price,features,tag FROM dynamic_courses WHERE tenant_id=? AND is_visible=1 ORDER BY sort_order", [tid]).fetchall()
    d.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/public/<tid>/coaches")
def api_public_coaches(tid):
    d = db()
    rows = d.execute("SELECT id,name,experience,pass_rate,rating,tags,phone,avatar FROM dynamic_coaches WHERE tenant_id=? AND is_visible=1 ORDER BY sort_order", [tid]).fetchall()
    d.close()
    return jsonify([dict(r) for r in rows])

# ==================== 启动 ====================

# ==================== 招生老师管理 ====================

@app.route("/school/<tid>/referrers")
def customer_referrers(tid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    d = db()
    t = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    referrers = d.execute("SELECT r.*, (SELECT COUNT(*) FROM referrals rf WHERE rf.referrer_id=r.id) as ref_count FROM referrers r WHERE r.tenant_id=? AND r.is_active=1 ORDER BY r.created_at DESC", [tid]).fetchall()
    # 查询每个招生老师的最近报名
    ref_data = []
    for r in referrers:
        rd = dict(r)
        recent = d.execute("SELECT * FROM referrals WHERE referrer_id=? ORDER BY created_at DESC LIMIT 5", [r["id"]]).fetchall()
        rd["recent"] = recent
        ref_data.append(rd)
    d.close()
    return render_template_string(CUSTOMER_REFERRERS, tenant=dict(t), referrers=ref_data)

CUSTOMER_REFERRERS = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>招生老师管理</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,sans-serif;background:#f0f2f5}
.header{background:#1e293b;color:#fff;padding:12px 20px;display:flex;justify-content:space-between;align-items:center}
.header h2{font-size:16px}.header a{color:#94a3b8;text-decoration:none;font-size:13px}
.container{max-width:900px;margin:0 auto;padding:20px}
.card{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.card h3{font-size:16px;margin-bottom:14px;display:flex;justify-content:space-between}
.card h3 a{font-size:12px;color:#1890ff;text-decoration:none;font-weight:400}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #f0f0f0}
th{color:#999;font-weight:500}.empty{text-align:center;color:#bbb;padding:20px}
.tag{padding:2px 8px;border-radius:10px;font-size:11px}
.tag-lead{background:#fff7e6;color:#fa8c16}.tag-signed{background:#f6ffed;color:#52c41a}
.btn-sm{font-size:11px;padding:3px 8px;border-radius:3px;border:none;cursor:pointer;text-decoration:none;display:inline-block}
.btn-del{background:#ff4d4f;color:#fff}</style></head><body>
<div class="header"><h2>👥 {{tenant.name}} · 招生老师</h2><a href="/school/{{tenant.id}}/dashboard">← 返回</a></div>
<div class="container">
{% for r in referrers %}
<div class="card">
<h3>{{r.name}} <span style="font-size:12px;color:#999;font-weight:400">{{r.phone or ''}}</span>
<div style="font-size:12px;color:#999">
  专属码：<b style="color:#1890ff;font-size:14px">{{r.code}}</b> | 佣金：{{r.commission_rate}}%
  <a class="btn-sm btn-del" href="/school/{{tenant.id}}/referrer/{{r.id}}/delete" onclick="return confirm('确定删除？')" style="margin-left:8px">删除</a>
</div></h3>
<p style="font-size:13px;color:#666;margin-bottom:8px">累计推荐：<b>{{r.ref_count}}</b> 人</p>
{% if r.recent %}
<table><tr><th>学员</th><th>电话</th><th>状态</th><th>时间</th></tr>
{% for s in r.recent %}<tr>
<td>{{s.student_name}}</td><td>{{s.student_phone}}</td>
<td><span class="tag tag-{{s.status}}">{{s.status}}</span></td>
<td>{{s.created_at[:16]}}</td>
</tr>{% endfor %}</table>
{% else %}<p class="empty">暂无推荐记录</p>{% endif %}
</div>
{% endfor %}
{% if not referrers %}
<div class="card"><p class="empty">还没有招生老师，点击右上角添加</p></div>
{% endif %}
<div class="card"><h3>+ 添加招生老师</h3>
<form method="POST" action="/school/{{tenant.id}}/referrer/new" style="display:flex;gap:10px;flex-wrap:wrap;align-items:end">
<input name="name" placeholder="姓名" required style="padding:8px;border:1px solid #d9d9d9;border-radius:4px;flex:1;min-width:80px">
<input name="phone" placeholder="电话" style="padding:8px;border:1px solid #d9d9d9;border-radius:4px;flex:1;min-width:100px">
<input name="code" placeholder="专属码（如ZS01）" required style="padding:8px;border:1px solid #d9d9d9;border-radius:4px;flex:1;min-width:80px">
<input name="commission_rate" placeholder="佣金%" type="number" value="0" style="padding:8px;border:1px solid #d9d9d9;border-radius:4px;width:70px">
<button class="btn-sm" type="submit" style="background:#667eea;color:#fff;padding:8px 16px;font-size:14px">添加</button>
</form></div>
</div></body></html>"""

@app.route("/school/<tid>/referrer/new", methods=["POST"])
def customer_referrer_new(tid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    d = db()
    d.execute("INSERT INTO referrers (tenant_id,name,phone,code,commission_rate) VALUES (?,?,?,?,?)",
              [tid, request.form["name"], request.form.get("phone",""), request.form["code"], float(request.form.get("commission_rate",0) or 0)])
    d.commit(); d.close()
    return redirect(f"/school/{tid}/referrers")

@app.route("/school/<tid>/referrer/<int:rid>/delete")
def customer_referrer_delete(tid, rid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    d = db(); d.execute("UPDATE referrers SET is_active=0 WHERE id=? AND tenant_id=?", [rid, tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/referrers")

# 公开API：记录推荐
@app.route("/api/public/<tid>/referral", methods=["POST"])
def api_referral(tid):
    """学生通过招生老师链接访问时记录: {referrer_code, student_name, student_phone}"""
    data = request.get_json()
    code = data.get("referrer_code","")
    d = db()
    ref = d.execute("SELECT id FROM referrers WHERE tenant_id=? AND code=? AND is_active=1", [tid, code]).fetchone()
    d.execute("INSERT INTO referrals (tenant_id,referrer_id,referrer_code,student_name,student_phone,source) VALUES (?,?,?,?,?,?)",
              [tid, ref["id"] if ref else None, code, data.get("student_name",""), data.get("student_phone",""), data.get("source","mini_program")])
    d.commit(); d.close()
    return jsonify({"ok":True, "referrer": ref["id"] if ref else None})

@app.route("/school/<tid>/appointment/<int:aid>/confirm")
def customer_appointment_confirm(tid, aid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    d = db(); d.execute("UPDATE appointments SET status='confirmed' WHERE id=? AND tenant_id=?", [aid, tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/dashboard")

@app.route("/school/<tid>/appointment/<int:aid>/complete")
def customer_appointment_complete(tid, aid):
    if (request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw()): return redirect(f"/school/{tid}/login")
    d = db(); d.execute("UPDATE appointments SET status='completed' WHERE id=? AND tenant_id=?", [aid, tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/dashboard")

# ==================== 类目管理 ====================

@app.route("/school/<tid>/categories", methods=["GET","POST"])
def customer_categories(tid):
    if request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw():
        return redirect(f"/school/{tid}/login")
    d = db()
    t = d.execute("SELECT * FROM tenants WHERE id=?",[tid]).fetchone()
    if request.method == "POST":
        name = request.form.get("name","").strip()
        if name:
            d.execute("INSERT INTO dynamic_categories (tenant_id,name) VALUES (?,?)",[tid,name])
            d.commit()
        d.close(); return redirect(f"/school/{tid}/categories")
    cats = d.execute("SELECT * FROM dynamic_categories WHERE tenant_id=? AND is_active=1 ORDER BY sort_order,id",[tid]).fetchall()
    d.close()
    rows = "".join([f"<tr><td>{c['name']}</td><td><a href='/school/{tid}/category/{c['id']}/delete' onclick=\"return confirm('确定删除？')\" style='color:#ff4d4f;font-size:12px'>删除</a></td></tr>" for c in cats])
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>类目管理</title>
<style>*{{margin:0;padding:0}}body{{font-family:-apple-system,sans-serif;background:#f0f2f5;padding:20px}}
.card{{background:#fff;max-width:500px;margin:20px auto;padding:24px;border-radius:12px;box-shadow:0 2rpx 12rpx rgba(0,0,0,.06)}}
h3{{font-size:18px;margin-bottom:16px}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #f0f0f0}}th{{color:#999}}
form{{display:flex;gap:10px;margin-top:12px}}input{{flex:1;padding:8px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px}}
.btn{{padding:8px 16px;background:#667eea;color:#fff;border:none;border-radius:4px;cursor:pointer}}a{{color:#999;text-decoration:none;font-size:13px}}
</style></head><body><div class="card"><h3>📂 {t['name']} · 商品类目</h3>
<table><tr><th>类目名称</th><th>操作</th></tr>{rows or '<tr><td colspan="2" style="color:#bbb;text-align:center">暂无类目</td></tr>'}</table>
<form method="POST"><input name="name" placeholder="新类目名称" required><button class="btn" type="submit">添加</button></form>
<p style="margin-top:16px"><a href="/school/{tid}/dashboard">← 返回</a></p>
</div></body></html>"""

@app.route("/school/<tid>/category/<int:cid>/delete")
def customer_category_delete(tid, cid):
    if request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw():
        return redirect(f"/school/{tid}/login")
    d = db(); d.execute("UPDATE dynamic_categories SET is_active=0 WHERE id=? AND tenant_id=?",[cid,tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/categories")

@app.route("/api/public/<tid>/categories")
def api_public_categories(tid):
    d = db()
    rows = d.execute("SELECT name FROM dynamic_categories WHERE tenant_id=? AND is_active=1 ORDER BY sort_order,id",[tid]).fetchall()
    d.close()
    cats = ["全部"] + [r["name"] for r in rows if r["name"]!="全部"]
    return jsonify(cats)

# ==================== 预约设置 ====================

@app.route("/school/<tid>/appointment-settings", methods=["GET","POST"])
def customer_appointment_settings(tid):
    if request.cookies.get("school_admin") != tid and request.cookies.get("admin_token") != get_admin_pw():
        return redirect(f"/school/{tid}/login")
    d = db()
    t = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    if request.method == "POST":
        d.execute("INSERT OR REPLACE INTO appointment_settings (tenant_id,advance_days,time_slots,capacity,is_open) VALUES (?,?,?,?,?)",
                  [tid, int(request.form.get("advance_days",7)), request.form.get("time_slots",'["08:00-10:00","10:00-12:00","14:00-16:00","16:00-18:00"]'), int(request.form.get("capacity",3)), int(request.form.get("is_open",1))])
        d.commit(); d.close()
        return redirect(f"/school/{tid}/dashboard")
    settings = d.execute("SELECT * FROM appointment_settings WHERE tenant_id=?", [tid]).fetchone()
    d.close()
    slots = json.loads(settings["time_slots"]) if settings else ["08:00-10:00","10:00-12:00","14:00-16:00","16:00-18:00"]
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>预约设置</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,sans-serif;background:#f0f2f5;padding:20px}}
.card{{background:#fff;max-width:500px;margin:20px auto;padding:24px;border-radius:12px;box-shadow:0 2rpx 12rpx rgba(0,0,0,.06)}}
h3{{font-size:18px;margin-bottom:20px}} label{{display:block;font-size:13px;color:#666;margin-bottom:6px;font-weight:500}}
input,select{{width:100%;padding:10px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;margin-bottom:16px}}
.slot-row{{display:flex;gap:10px;margin-bottom:10px;align-items:center}}
.slot-row input{{flex:1;margin-bottom:0}}
.slot-row button{{background:#ff4d4f;color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px}}
.btn{{padding:10px 24px;background:#667eea;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;font-size:14px}}
.btn-sm{{background:#1890ff;color:#fff;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;font-size:12px;margin-top:8px}}
a{{color:#999;text-decoration:none;font-size:13px;margin-left:12px}}
</style></head><body><div class="card"><h3>⚙️ 预约设置</h3>
<form method="POST" id="f">
<label>预约开关</label><select name="is_open"><option value="1" {'selected' if settings and settings['is_open']==1 else ''}>开启</option><option value="0" {'selected' if settings and settings['is_open']==0 else ''}>关闭</option></select>
<label>提前展示天数</label><input name="advance_days" type="number" min="1" max="30" value="{settings['advance_days'] if settings else 7}">
<label>每时段可约人数</label><input name="capacity" type="number" min="1" max="20" value="{settings['capacity'] if settings else 3}">
<label>可约时段</label>
<div id="slots">{''.join(f'<div class="slot-row"><input name="slot_{i}" value="{s}"><button type="button" onclick="this.parentElement.remove()">删除</button></div>' for i,s in enumerate(slots))}</div>
<button type="button" class="btn-sm" onclick="addSlot()">+ 添加时段</button>
<input type="hidden" name="time_slots" id="time_slots_val">
<div style="margin-top:20px"><button class="btn" type="submit" onclick="collectSlots()">💾 保存设置</button><a href="/school/{tid}/dashboard">← 返回</a></div>
</form></div>
<script>
function addSlot(){{var d=document.createElement('div');d.className='slot-row';d.innerHTML='<input placeholder=\"如 08:00-10:00\" value=\"\"><button type=\"button\" onclick=\"this.parentElement.remove()\">删除</button>';document.getElementById('slots').appendChild(d)}}
function collectSlots(){{var s=[];document.querySelectorAll('#slots input').forEach(function(i){{if(i.value.trim())s.push(i.value.trim())}});document.getElementById('time_slots_val').value=JSON.stringify(s)}}
collectSlots();
</script></body></html>"""

@app.route("/api/public/<tid>/appointment-settings")
def api_appointment_settings(tid):
    d = db()
    s = d.execute("SELECT * FROM appointment_settings WHERE tenant_id=?", [tid]).fetchone()
    d.close()
    if s:
        return jsonify({"advance_days":s["advance_days"],"time_slots":json.loads(s["time_slots"]),"capacity":s["capacity"],"is_open":bool(s["is_open"])})
    return jsonify({"advance_days":7,"time_slots":["08:00-10:00","10:00-12:00","14:00-16:00","16:00-18:00"],"capacity":3,"is_open":True})

# ==================== 预约 API ====================

@app.route("/api/public/<tid>/appointments", methods=["POST"])
def api_create_appointment(tid):
    data = request.get_json()
    d = db()
    d.execute("INSERT INTO appointments (tenant_id,student_name,student_phone,coach_name,course_type,appointment_time,status) VALUES (?,?,?,?,?,?,?)",
              [tid, data["student_name"], data.get("student_phone",""), data.get("coach_name",""), data.get("course_type",""), data.get("appointment_time",""), "pending"])
    d.commit(); d.close()
    return jsonify({"ok":True, "message":"预约已提交"})

@app.route("/api/public/<tid>/coach-slots")
def api_coach_slots(tid):
    """返回可预约时段（简化版：固定时段+查询已约）"""
    import time as _time
    slots = []
    for day_offset in range(7):
        t = _time.time() + day_offset * 86400
        date_str = _time.strftime("%m月%d日", _time.localtime(t))
        weekdays = ["日","一","二","三","四","五","六"]
        for h in [8,10,14,16,18]:
            label = f"{h:02d}:00-{h+1:02d}:30"
            slots.append({"date":date_str,"weekday":weekdays[_time.localtime(t).tm_wday],"time":label,"full":False,"remain":3})
    return jsonify(slots)

# ==================== 题库 API ====================

@app.route("/api/public/<tid>/exam-questions")
def api_exam_questions(tid):
    d = db()
    rows = d.execute("SELECT id,type,title,option_a,option_b,option_c,option_d,explain,chapter FROM exam_questions WHERE is_active=1 ORDER BY random() LIMIT 100").fetchall()
    d.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/public/<tid>/exam-check", methods=["POST"])
def api_exam_check(tid):
    data = request.get_json()
    qids = list(data.get("answers",{}).keys())
    d = db()
    placeholders = ",".join(["?" for _ in qids])
    rows = d.execute(f"SELECT id,answer,explain FROM exam_questions WHERE id IN ({placeholders})", qids).fetchall()
    d.close()
    answers = {str(r["id"]): {"correct": r["answer"], "explain": r["explain"]} for r in rows}
    return jsonify({"answers": answers})

# ==================== 启动 ====================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5100, debug=False)
