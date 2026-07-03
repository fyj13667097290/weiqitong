#!/usr/bin/env node
/**
 * 小程序工厂 - 配置注入引擎
 * 用法: node generate.js <config.json> <output_dir> [industry]
 * 读取 school.config.json → 注入到模板代码 → 输出完整小程序
 */
const fs = require('fs');
const path = require('path');

const [configPath, outputDir, industrySlug = 'driving'] = process.argv.slice(2);

if (!configPath || !outputDir) {
  console.error('用法: node generate.js <config.json> <output_dir> [industry]');
  process.exit(1);
}

// 1. 读取配置
const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'));
const templateDir = path.join(__dirname, '..', 'templates', industrySlug, 'code');

if (!fs.existsSync(templateDir)) {
  console.error(`❌ 行业模板不存在: ${templateDir}`);
  process.exit(1);
}

const displayName = config.school?.name || config.shop?.name || '未知商家';
console.log(`🔧 开始生成 ${displayName} 的小程序...`);
console.log(`   行业: ${industrySlug}`);
console.log(`   模板: ${templateDir}`);
console.log(`   输出: ${outputDir}`);

// 2. 复制模板
fs.cpSync(templateDir, outputDir, { recursive: true });

// 3. 占位符映射
const entity = config.school || config.shop || {};
const placeholders = {
  '{{school_name}}': entity.name || '',
  '{{shop_name}}': entity.name || '',
  '{{school_short_name}}': entity.shortName || entity.name || '',
  '{{shop_short_name}}': entity.shortName || entity.name || '',
  '{{school_logo}}': entity.logo || '',
  '{{shop_logo}}': entity.logo || '',
  '{{school_phone}}': entity.phone || '',
  '{{shop_phone}}': entity.phone || '',
  '{{school_address}}': entity.address || '',
  '{{shop_address}}': entity.address || '',
  '{{school_description}}': entity.description || '',
  '{{shop_description}}': entity.description || '',
  '{{primary_color}}': entity.theme?.primaryColor || '#1890ff',
};

// 4. 写入配置文件和替换占位符
const replaceInFile = (filePath) => {
  try {
    let content = fs.readFileSync(filePath, 'utf-8');

    // 替换占位符
    Object.entries(placeholders).forEach(([key, value]) => {
      content = content.split(key).join(value);
    });

    // 替换 AppID
    const appId = entity.appId || '';
    content = content.split('__WEAPP_APPID__').join(appId);

    fs.writeFileSync(filePath, content);
    return true;
  } catch (e) {
    return false; // 二进制文件跳过
  }
};

const walkDir = (dir) => {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkDir(fullPath);
    } else if (entry.isFile()) {
      const ext = path.extname(entry.name);
      // 处理文本文件
      if (['.json', '.js', '.vue', '.css', '.scss', '.html', '.xml', '.wxml', '.wxss'].includes(ext)) {
        replaceInFile(fullPath);
      }
    }
  }
};

walkDir(outputDir);

// 5. 注入_meta信息（租户ID、API地址）
config._meta = config._meta || {};
config._meta.tenantId = config._meta.tenantId || path.basename(outputDir);
config._meta.apiBase = config._meta.apiBase || 'https://jiaxiao.t-hub.cc';

// 6. 写入完整 school.config.json
const configDest = path.join(outputDir, 'school.config.json');
fs.writeFileSync(configDest, JSON.stringify(config, null, 2), 'utf-8');

// 6. 生成 project.config.json
const projectConfig = {
  appid: entity.appId || '',
  projectname: entity.name || '小程序',
  miniprogramRoot: '',
  setting: { urlCheck: false, es6: true, postcss: true, minified: true },
};
fs.writeFileSync(
  path.join(outputDir, 'project.config.json'),
  JSON.stringify(projectConfig, null, 2)
);

console.log(`✅ 生成完成！`);
console.log(`   文件数: ${countFiles(outputDir)}`);
// 安全检查：扫描 {{}} 中的 < 符号
function scanForBadExpr(dir) {
  const issues = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const fp = path.join(dir, e.name);
    if (e.isDirectory()) { issues.push(...scanForBadExpr(fp)); }
    else if (['.vue'].includes(path.extname(e.name))) {
      const content = fs.readFileSync(fp, 'utf-8');
      const ms = content.match(/\{\{[^}]*[<>][^}]*\}\}/g);
      if (ms) issues.push(...ms.map(m => ({file: path.relative(outputDir, fp), expr: m.trim()})));
    }
  }
  return issues;
}
const badExprs = scanForBadExpr(outputDir);
if (badExprs.length) {
  console.warn('\n⚠️  WXML 兼容警告：发现 {{}} 中使用了 < 或 > 符号，会导致编译失败：');
  badExprs.forEach(b => console.warn(`   ${b.file}: ${b.expr}`));
  console.warn('   修复方法：改用 computed 属性。详见 templates/driving/RULES.md\n');
}
console.log(`   请用微信开发者工具打开: ${outputDir}`);
console.log(`   或者运行: npx yx-wechat-mini-cli --action upload`);

function countFiles(dir) {
  let count = 0;
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const e of entries) {
      if (e.isDirectory()) count += countFiles(path.join(dir, e.name));
      else count++;
    }
  } catch (_) {}
  return count;
}

// 导出供其他脚本使用
module.exports = { generate };
function generate(cfg, out, industry) {
  const tmpPath = path.join('/tmp', `gen_${Date.now()}.json`);
  fs.writeFileSync(tmpPath, JSON.stringify(cfg));
  // re-exec自身
  require('child_process').execSync(`node "${__filename}" "${tmpPath}" "${out}" "${industry}"`, { stdio: 'inherit' });
  fs.unlinkSync(tmpPath);
}
