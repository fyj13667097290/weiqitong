<template>
  <view class="page">
    <view class="course-card" v-for="(c,i) in allCourses" :key="i">
      <view class="tag" v-if="c.tag" :style="{background:theme.primaryColor}">{{c.tag}}</view>
      <text class="name">{{c.name}}</text>
      <view class="price-box">
        <text class="price">¥{{c.price}}</text>
        <text class="original" v-if="c.originalPrice||c.original_price">¥{{c.originalPrice||c.original_price}}</text>
      </view>
      <view class="features" v-if="hasFeatures(c)">
        <text class="ftag" v-for="(f,j) in getFeatures(c)" :key="j">✓ {{f}}</text>
      </view>
      <button class="btn" :style="{background:theme.primaryColor}" @tap="signUp">立即报名</button>
    </view>
    <view class="empty" v-if="!allCourses.length">暂无课程信息</view>
  </view>
</template>
<script>
import config from '../../school.config.json';
const TID = (config._meta && config._meta.tenantId) || '';
const API = (config._meta && config._meta.apiBase) || '';
function getList(p){ return new Promise(function(resolve){ uni.request({url:API+'/api/public/'+TID+'/'+p,success:function(r){resolve(r.data)},fail:function(){resolve([])}}); }); }
export default {
  data() { return { allCourses: config.courses||[], theme: config.school.theme }; },
  onLoad(){ var s=this; getList('courses').then(function(r){ if(r.length)s.allCourses=s.allCourses.concat(r); }); },
  methods: {
    signUp(){ uni.makePhoneCall({phoneNumber: config.school.phone}); },
    hasFeatures(c){ var f=c.features; return f && (typeof f==='string'?f.trim():f.length>0); },
    getFeatures(c){ var f=c.features; return typeof f==='string'?f.split(',').map(function(t){return t.trim()}):(f||[]); }
  }
}
</script>
<style scoped>
.page{padding:20rpx}
.course-card{background:#fff;border-radius:16rpx;padding:30rpx;margin-bottom:20rpx;position:relative;overflow:hidden}
.tag{position:absolute;top:0;right:0;color:#fff;font-size:22rpx;padding:6rpx 20rpx;border-radius:0 16rpx 0 16rpx}
.name{font-size:34rpx;font-weight:700;display:block}
.price-box{margin:16rpx 0}
.price{font-size:44rpx;font-weight:700;color:#ff4d4f}
.original{font-size:26rpx;color:#999;text-decoration:line-through;margin-left:16rpx}
.ftag{display:block;font-size:26rpx;color:#666;line-height:1.8}
.btn{margin-top:20rpx;color:#fff;border-radius:40rpx;height:80rpx;line-height:80rpx;font-size:30rpx}
.empty{text-align:center;color:#999;padding:100rpx 0}
</style>
