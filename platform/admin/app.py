"""
小程序工厂 - 管理后台 API v2
多租户 + JSON配置驱动 + 行业模板可插拔
"""
import sqlite3, json, uuid, os
from datetime import date, datetime, timedelta
from flask import Flask, request, jsonify, redirect, render_template_string

app = Flask(__name__)
DB = "/opt/jiaxiao/platform/admin/data.db"

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
.ind-item.active{background:var(--primary);color:#fff}</style></head><body>
<div class="header"><h1>🏭 微企通 · 管理后台</h1></div>
<div class="container">
<div class="industry-bar">
  <a href="/admin" class="ind-item {% if not current_industry %}active{% endif %}">📊 全部</a>
  {% for ind in industries %}
  <a href="/admin?industry={{ind.id}}" class="ind-item {% if current_industry==ind.id %}active{% endif %}">{{ind.icon}} {{ind.name}}</a>
  {% endfor %}
</div>
<div class="stats">
<div class="stat"><div class="num">{{stats.tenants}}</div><div class="label">总客户</div></div>
<div class="stat"><div class="num">{{stats.active}}</div><div class="label">活跃客户</div></div>
<div class="stat"><div class="num">{{stats.deployed}}</div><div class="label">已部署</div></div>
<div class="stat"><div class="num">{{stats.industries}}</div><div class="label">行业模板</div></div>
</div>
<div class="card">
<h2>客户列表 <a href="/new" class="btn btn-primary" style="float:right">+ 添加客户</a></h2>
<table><thead><tr><th>名称</th><th>行业</th><th>套餐</th><th>状态</th><th>部署</th><th>创建</th><th>操作</th></tr></thead>
<tbody>{% if tenants %}{% for t in tenants %}<tr>
<td><strong>{{t.name}}</strong></td><td>{{t.industry_name or '-'}}</td>
<td><span class="badge badge-trial">{{t.plan}}</span></td>
<td><span class="badge {% if t.status=='active' %}badge-active{% else %}badge-trial{% endif %}">{{t.status}}</span></td>
<td><span class="badge {% if t.deploy_status=='success' %}badge-active{% elif t.deploy_status=='failed' %}badge-trial{% else %}badge-draft{% endif %}">{{t.deploy_status or '未部署'}}</span></td>
<td>{{t.created_at[:10] if t.created_at else '-'}}</td>
<td><a href="/tenants/{{t.id}}/config" class="btn btn-primary btn-sm">配置</a> <a href="/school/{{t.id}}/login" target="_blank" class="btn btn-sm" style="background:#52c41a;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">自助后台</a> <a href="#" onclick="copyLink('{{t.id}}')" class="btn btn-sm" style="background:#1890ff;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">复制链接</a> <a href="#" onclick="delTenant('{{t.id}}','{{t.name}}')" class="btn btn-sm" style="background:#ff4d4f;color:#fff;font-size:11px;padding:3px 8px;text-decoration:none;border-radius:3px">删除</a></td>
</tr>{% endfor %}{% else %}<tr><td colspan="7" class="empty">还没有客户，点击右上角添加</td></tr>{% endif %}</tbody></table>
</div></div>
<script>
function delTenant(id,name){
  if(!confirm('确定要删除客户「'+name+'」吗？\\n此操作不可恢复。')) return;
  fetch('/api/tenants/'+id,{method:'DELETE'}).then(function(r){ return r.json(); }).then(function(d){
    if(d.ok){ alert('已删除'); location.reload(); } else { alert('删除失败'); }
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
</script></body></html>"""

@app.route("/")
def landing():
    return LANDING_PAGE

@app.route("/admin")
def index():
    d = db()
    stats = {
        "tenants": d.execute("SELECT COUNT(*) as c FROM tenants").fetchone()["c"],
        "active": d.execute("SELECT COUNT(*) as c FROM tenants WHERE status='active'").fetchone()["c"],
        "deployed": d.execute("SELECT COUNT(*) as c FROM configs WHERE status IN ('deployed','published')").fetchone()["c"],
        "industries": d.execute("SELECT COUNT(*) as c FROM industries WHERE is_active=1").fetchone()["c"],
    }
    industry = request.args.get("industry", "")
    if industry:
        tenants = d.execute("SELECT t.*, i.name as industry_name, (SELECT d2.result FROM deployments d2 WHERE d2.tenant_id=t.id ORDER BY d2.created_at DESC LIMIT 1) as deploy_status FROM tenants t LEFT JOIN industries i ON t.industry_id=i.id WHERE t.industry_id=? ORDER BY t.created_at DESC", [industry]).fetchall()
    else:
        tenants = d.execute("SELECT t.*, i.name as industry_name, (SELECT d2.result FROM deployments d2 WHERE d2.tenant_id=t.id ORDER BY d2.created_at DESC LIMIT 1) as deploy_status FROM tenants t LEFT JOIN industries i ON t.industry_id=i.id ORDER BY t.created_at DESC").fetchall()
    industries = d.execute("SELECT * FROM industries WHERE is_active=1 ORDER BY sort_order,id").fetchall()
    d.close()
    return render_template_string(ADMIN_PAGE, stats=stats, tenants=tenants, industries=industries, current_industry=industry)

@app.route("/new")
def new_tenant():
    d = db()
    industries = d.execute("SELECT * FROM industries WHERE is_active=1 ORDER BY sort_order,id").fetchall()
    d.close()
    return render_template_string(HTML_NEW, industries=industries)

@app.route("/tenants/<tid>/config")
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
def api_create_tenant():
    data = request.form
    tid = f"t{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
    d = db()
    d.execute("INSERT INTO tenants (id,name,short_name,industry_id,contact_name,contact_phone,status,plan,trial_end) VALUES (?,?,?,?,?,?,?,?,?)",
              [tid, data["name"], data.get("short_name",""), data.get("industry_id","drv001"),
               data.get("contact_name",""), data.get("contact_phone",""),
               "trial", data.get("plan","trial"),
               (date.today() + timedelta(days=14)).isoformat()])
    d.commit(); d.close()
    return render_template_string("""<html><body><script>alert('客户创建成功！');location.href='/admin'</script></body></html>"""), 201

@app.route("/api/tenants/<tid>", methods=["GET"])
def api_get_tenant(tid):
    d = db()
    r = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    d.close()
    return jsonify(row2dict(r)) if r else (jsonify({"error":"not found"}), 404)

@app.route("/api/tenants/<tid>", methods=["DELETE"])
def api_delete_tenant(tid):
    d = db()
    d.execute("UPDATE tenants SET status='inactive' WHERE id=?", [tid])
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
def api_deploy(tid):
    action = request.json.get("action", "upload")
    d = db()
    config = d.execute("SELECT * FROM configs WHERE tenant_id=? ORDER BY version DESC LIMIT 1", [tid]).fetchone()
    if not config:
        d.close(); return jsonify({"error":"请先保存配置"}), 400
    d.execute("INSERT INTO deployments (tenant_id,config_version,action,result,message) VALUES (?,?,?,?,?)",
              [tid, config["version"], action, "pending", "部署任务已创建，等待GitHub Actions执行"])
    d.execute("UPDATE configs SET status=? WHERE id=?", ["deployed" if action=="upload" else "auditing", config["id"]])
    d.commit()

    # 写入待处理标记文件，供外部脚本读取
    tenant = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    cfg = row2dict(config)
    cfg["config"] = json.loads(cfg["config"])
    deploy_task = {
        "tenant_id": tid,
        "tenant_name": tenant["name"] if tenant else "",
        "industry": "driving",
        "action": action,
        "config": cfg["config"],
        "mini_appid": cfg["mini_appid"],
        "version": config["version"],
        "timestamp": now()
    }
    os.makedirs("/opt/jiaxiao/deploy_queue", exist_ok=True)
    with open(f"/opt/jiaxiao/deploy_queue/{tid}.json", "w") as f:
        json.dump(deploy_task, f, ensure_ascii=False, indent=2)
    d.close()
    return jsonify({"ok":True, "message":f"部署任务已创建"})

@app.route("/api/tenants/<tid>/deployments", methods=["GET"])
def api_deployments(tid):
    d = db()
    rows = d.execute("SELECT * FROM deployments WHERE tenant_id=? ORDER BY created_at DESC LIMIT 20", [tid]).fetchall()
    d.close()
    return jsonify([row2dict(r) for r in rows])

@app.route("/api/tenants/<tid>/trigger-deploy", methods=["POST"])
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

<div class="card"><h3>📋 最近预约</h3>
{% if appointments %}<table><tr><th>学员</th><th>电话</th><th>课程</th><th>时间</th><th>状态</th></tr>
{% for a in appointments %}<tr><td>{{a.student_name}}</td><td>{{a.student_phone}}</td><td>{{a.course_type}}</td><td>{{a.appointment_time}}</td><td>{{a.status}}</td></tr>{% endfor %}</table>
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
    if request.cookies.get("school_admin") != tid:
        return redirect(f"/school/{tid}/login")
    d = db()
    t = d.execute("SELECT * FROM tenants WHERE id=?", [tid]).fetchone()
    announcements = d.execute("SELECT * FROM announcements WHERE tenant_id=? ORDER BY is_pinned DESC, created_at DESC", [tid]).fetchall()
    courses = d.execute("SELECT * FROM dynamic_courses WHERE tenant_id=? ORDER BY sort_order", [tid]).fetchall()
    coaches = d.execute("SELECT * FROM dynamic_coaches WHERE tenant_id=? ORDER BY sort_order", [tid]).fetchall()
    appointments = d.execute("SELECT * FROM appointments WHERE tenant_id=? ORDER BY created_at DESC LIMIT 20", [tid]).fetchall()
    d.close()
    return render_template_string(CUSTOMER_DASHBOARD, tenant=dict(t), announcements=announcements, courses=courses, coaches=coaches, appointments=appointments)

@app.route("/school/<tid>/announcement/new", methods=["GET","POST"])
def customer_announcement_new(tid):
    if request.cookies.get("school_admin") != tid: return redirect(f"/school/{tid}/login")
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
    if request.cookies.get("school_admin") != tid: return redirect(f"/school/{tid}/login")
    d = db(); d.execute("DELETE FROM announcements WHERE id=? AND tenant_id=?", [aid, tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/dashboard")

@app.route("/school/<tid>/course/new", methods=["GET","POST"])
def customer_course_new(tid):
    if request.cookies.get("school_admin") != tid: return redirect(f"/school/{tid}/login")
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
    if request.cookies.get("school_admin") != tid: return redirect(f"/school/{tid}/login")
    d = db(); d.execute("DELETE FROM dynamic_courses WHERE id=? AND tenant_id=?", [cid, tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/dashboard")

@app.route("/school/<tid>/coach/new", methods=["GET","POST"])
def customer_coach_new(tid):
    if request.cookies.get("school_admin") != tid: return redirect(f"/school/{tid}/login")
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
    if request.cookies.get("school_admin") != tid: return redirect(f"/school/{tid}/login")
    d = db(); d.execute("DELETE FROM dynamic_coaches WHERE id=? AND tenant_id=?", [cid, tid]); d.commit(); d.close()
    return redirect(f"/school/{tid}/dashboard")

@app.route("/school/<tid>/password", methods=["GET","POST"])
def customer_password(tid):
    if request.cookies.get("school_admin") != tid: return redirect(f"/school/{tid}/login")
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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5100, debug=False)
