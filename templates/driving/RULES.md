# 小程序模板开发规范

## 1. WXML 模板语法限制

微信 WXML `{{ }}` 中不能使用 `<` `>` 符号（XML 保留字符）。

### 禁止写法
```html
{{a < b ? '是' : '否'}}
{{arr.length > 0 ? arr[0] : '空'}}
{{currentQ < questions.length - 1 ? '下一题' : '完成'}}
```

### 正确写法
```html
<!-- 用 computed 属性 -->
{{nextBtnText}}
```
```javascript
computed: {
  nextBtnText() { return this.currentQ < this.questions.length - 1 ? '下一题' : '完成'; }
}
```

## 2. 字符串内不能有未转义换行

Python 代码中的 `\n` 会被解释为真正换行符，跑到 JS 代码里导致语法错误。

### 禁止写法
```python
html = "...join('\n')..."  # Python 把 \n 变成真换行
```

### 正确写法
```python
html = "...join('\\n')..."  # 双反斜杠保留给 JS 用
```

## 3. 安全过审原则
- 小程序第一版不加营销内容（优惠券、推荐有礼等）
- 纯工具属性更容易过审
- 科一科四题库必须基于交通部标准
- 不包含第三方广告
