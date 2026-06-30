"""
小程序工厂 - 管理后台 API v2
多租户 + JSON配置驱动 + 行业模板可插拔
"""
import sqlite3, json, uuid, os
from datetime import date, datetime, timedelta
from flask import Flask, request, jsonify, render_template_string

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
<div class="container"><a href="/" class="back">← 返回</a><div class="card"><h2>+ 添加驾校客户</h2>
<form method="POST" action="/api/tenants"><div class="form-group"><label>驾校全称 *</label><input name="name" required placeholder="如：鑫达机动车驾驶培训学校"></div>
<div class="form-group"><label>简称</label><input name="short_name" placeholder="如：鑫达驾校" maxlength="10"></div>
<div class="form-group"><label>联系人</label><input name="contact_name" placeholder="驾校老板姓名"></div>
<div class="form-group"><label>联系电话</label><input name="contact_phone" placeholder="手机号"></div>
<div class="form-group"><label>行业</label><select name="industry_id"><option value="drv001">🚗 驾校</option></select></div>
<div class="form-group"><label>套餐</label><select name="plan"><option value="trial">试用版（免费14天）</option><option value="basic">基础版 999元/年</option><option value="standard">标准版 1999元/年</option><option value="pro">专业版 2999元/年</option></select></div>
<button type="submit" class="btn btn-primary">创建客户</button></form></div></div></body></html>"""

HTML_CONFIG = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>驾校配置</title>
<style>:root{--primary:#1890ff;--bg:#f0f2f5} *{margin:0;padding:0;box-sizing:border-box} body{font-family:-apple-system,sans-serif;background:var(--bg)}
.container{max-width:800px;margin:20px auto;padding:20px} .card{background:#fff;border-radius:8px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:20px}
h2{font-size:18px;margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid #f0f0f0} h3{font-size:15px;margin:16px 0 10px;color:#555}
.form-group{margin-bottom:14px} label{display:block;margin-bottom:5px;font-weight:500;font-size:13px;color:#555}
input,select,textarea{width:100%;padding:9px 12px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px} input:focus,select:focus,textarea:focus{border-color:var(--primary);outline:none;box-shadow:0 0 0 2px rgba(24,144,255,.2)}
textarea{resize:vertical;min-height:80px}
.btn{padding:10px 24px;border-radius:4px;border:none;font-size:14px;cursor:pointer;font-weight:500} .btn-primary{background:var(--primary);color:#fff} .btn-success{background:#52c41a;color:#fff}
.btn-group{display:flex;gap:10px;margin-top:16px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.back{color:#999;text-decoration:none;font-size:13px;margin-bottom:16px;display:inline-block}
.tab{border-bottom:2px solid #f0f0f0;margin-bottom:20px} .tab a{display:inline-block;padding:10px 20px;color:#999;text-decoration:none;font-size:14px;border-bottom:2px solid transparent;margin-bottom:-2px}
.tab a.active{color:var(--primary);border-bottom-color:var(--primary);font-weight:500}</style></head><body>
<div class="container"><a href="/" class="back">← 返回</a>
<div class="tab"><a href="#" class="active">基本信息</a><a href="#">课程套餐</a><a href="#">教练团队</a><a href="#">功能开关</a></div>
<div class="card"><h2>🏫 {{tenant.name}} - 小程序配置</h2>
<form id="configForm"><div id="formContent"></div>
<div class="btn-group"><button type="button" class="btn btn-primary" onclick="saveConfig()">保存配置</button>
<button type="button" class="btn btn-success" onclick="deploy()">生成并部署</button></div></form></div>
<div class="card" id="deployLog" style="display:none"><h2>部署日志</h2><pre id="logContent" style="background:#1a1a2e;color:#52c41a;padding:16px;border-radius:4px;font-size:13px;overflow-x:auto"></pre></div>
</div>
<script>
const tid = window.location.pathname.split('/')[2];
let cfg = null;

async function loadConfig(){
  const r = await fetch('/api/tenants/'+tid+'/config');
  const d = await r.json();
  cfg = d.config || {};
  renderForm(cfg);
}
function renderForm(c){
  document.getElementById('formContent').innerHTML = `
    <h3>基本信息</h3>
    <div class="row"><div class="form-group"><label>驾校全称</label><input name="school.name" value="${c.school?.name||''}"></div>
    <div class="form-group"><label>简称</label><input name="school.shortName" value="${c.school?.shortName||''}"></div></div>
    <div class="row"><div class="form-group"><label>联系电话</label><input name="school.phone" value="${c.school?.phone||''}"></div>
    <div class="form-group"><label>Logo URL</label><input name="school.logo" value="${c.school?.logo||''}"></div></div>
    <div class="form-group"><label>地址</label><input name="school.address" value="${c.school?.address||''}"></div>
    <div class="form-group"><label>驾校简介</label><textarea name="school.description">${c.school?.description||''}</textarea></div>
    <div class="row"><div class="form-group"><label>主题色</label><input type="color" name="school.theme.primaryColor" value="${c.school?.theme?.primaryColor||'#1890ff'}" style="width:60px;height:40px"></div>
    <div class="form-group"><label>小程序AppID</label><input name="mini_appid" placeholder="wx开头的小程序ID"></div></div>
    <h3>课程套餐</h3>
    <div id="coursesContainer">${(c.courses||[]).map((co,i)=>`<div class="row" style="margin-bottom:8px"><input name="courses.${i}.name" value="${co.name||''}" placeholder="套餐名"><input name="courses.${i}.price" value="${co.price||''}" placeholder="价格" type="number"></div>`).join('')}</div>
    <button type="button" class="btn btn-primary btn-sm" onclick="addCourse()">+ 添加课程</button>
    <h3>教练团队</h3>
    <div id="coachesContainer">${(c.coaches||[]).map((ch,i)=>`<div class="row" style="margin-bottom:8px"><input name="coaches.${i}.name" value="${ch.name||''}" placeholder="教练姓名"><input name="coaches.${i}.experience" value="${ch.experience||''}" placeholder="教龄(年)" type="number"></div>`).join('')}</div>
    <button type="button" class="btn btn-primary btn-sm" onclick="addCoach()">+ 添加教练</button>
  `;
}
function addCourse(){ const c = (cfg.courses||[]); c.push({name:'',price:0}); cfg.courses=c; renderForm(cfg); }
function addCoach(){ const c = (cfg.coaches||[]); c.push({name:'',experience:0}); cfg.coaches=c; renderForm(cfg); }
function collectForm(){
  const inputs = document.querySelectorAll('#configForm input, #configForm textarea');
  const out = {school:{name:'',shortName:'',logo:'',phone:'',address:'',description:'',photos:[],theme:{primaryColor:'#1890ff'}},courses:[],coaches:[],locations:[],features:{appointment:true,examPrep:true,onlinePayment:false}};
  const matrix = {};
  inputs.forEach(i=>{ if(i.name){ const keys=i.name.split('.'); let obj=matrix; for(let k=0;k<keys.length-1;k++){ if(!isNaN(keys[k])){ const arrKey=keys.slice(0,k).join('.'); if(!obj[arrKey]){ obj[arrKey]=[]; const path=arrKey.split('.'); let t=matrix; for(let p=0;p<path.length-1;p++)t=t[path[p]]; t[path[path.length-1]]=obj[arrKey]; } if(!obj[arrKey][parseInt(keys[k])])obj[arrKey][parseInt(keys[k])]={}; obj=obj[arrKey][parseInt(keys[k])]; continue; } if(!obj[keys[k]])obj[keys[k]]={}; obj=obj[keys[k]]; } obj[keys[keys.length-1]]=i.value; }});
  return collectNested(matrix);
}
function collectNested(obj){
  if(typeof obj!=='object'||obj===null)return obj;
  const keys=Object.keys(obj); const allNum=keys.every(k=>!isNaN(k));
  if(allNum){ const arr=[]; keys.sort((a,b)=>parseInt(a)-parseInt(b)).forEach(k=>arr.push(collectNested(obj[k]))); return arr; }
  const out={}; keys.forEach(k=>out[k]=collectNested(obj[k])); return out;
}
async function saveConfig(){
  const config = collectForm();
  const r = await fetch('/api/tenants/'+tid+'/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({config})});
  const d = await r.json();
  alert(d.message||'保存成功');
}
async function deploy(){
  await saveConfig();
  const r = await fetch('/api/tenants/'+tid+'/deploy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'upload'})});
  const d = await r.json();
  document.getElementById('deployLog').style.display='block';
  document.getElementById('logContent').textContent = JSON.stringify(d,null,2);
}
loadConfig();
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
.empty{text-align:center;color:#bbb;padding:40px}</style></head><body>
<div class="header"><h1>🏭 微企通 · 管理后台</h1><span style="color:#94a3b8;font-size:13px">驾校行业 v1.0</span></div>
<div class="container">
<div class="stats">
<div class="stat"><div class="num">{{stats.tenants}}</div><div class="label">总客户</div></div>
<div class="stat"><div class="num">{{stats.active}}</div><div class="label">活跃客户</div></div>
<div class="stat"><div class="num">{{stats.deployed}}</div><div class="label">已部署</div></div>
<div class="stat"><div class="num">{{stats.industries}}</div><div class="label">行业模板</div></div>
</div>
<div class="card">
<h2>客户列表 <a href="/new" class="btn btn-primary" style="float:right">+ 添加客户</a></h2>
<table><thead><tr><th>名称</th><th>行业</th><th>套餐</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead>
<tbody>{% if tenants %}{% for t in tenants %}<tr>
<td><strong>{{t.name}}</strong></td><td>{{t.industry_name or '-'}}</td>
<td><span class="badge badge-trial">{{t.plan}}</span></td>
<td><span class="badge {% if t.status=='active' %}badge-active{% else %}badge-trial{% endif %}">{{t.status}}</span></td>
<td>{{t.created_at[:10] if t.created_at else '-'}}</td>
<td><a href="/tenants/{{t.id}}/config" class="btn btn-primary btn-sm">配置</a></td>
</tr>{% endfor %}{% else %}<tr><td colspan="6" class="empty">还没有客户，点击右上角添加</td></tr>{% endif %}</tbody></table>
</div></div></body></html>"""

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
    tenants = d.execute("SELECT t.*, i.name as industry_name FROM tenants t LEFT JOIN industries i ON t.industry_id=i.id ORDER BY t.created_at DESC").fetchall()
    d.close()
    return render_template_string(ADMIN_PAGE, stats=stats, tenants=tenants)

@app.route("/new")
def new_tenant():
    return render_template_string(HTML_NEW)

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
    return render_template_string("""<html><body><script>alert('客户创建成功！');location.href='/'</script></body></html>"""), 201

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

# ==================== API: 健康检查 ====================

@app.route("/api/health")
def health():
    d = db()
    tc = d.execute("SELECT COUNT(*) as c FROM tenants").fetchone()["c"]
    d.close()
    return jsonify({"status":"ok","server":"Miami","tenants":tc,"timestamp":now()})

# ==================== 启动 ====================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5100, debug=False)
