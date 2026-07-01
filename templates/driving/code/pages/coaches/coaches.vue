<template>
  <view class="page">
    <view class="coach-card" v-for="(c,i) in allCoaches" :key="i">
      <image class="avatar" :src="c.avatar || '/static/default-avatar.png'" mode="aspectFill" />
      <view class="info">
        <text class="name">{{c.name}}</text>
        <text class="exp">教龄 {{c.experience}} 年</text>
        <view class="stars" v-if="c.rating">⭐ {{c.rating}}</view>
        <text class="rate" v-if="c.passRate||c.pass_rate">通过率 {{c.passRate||c.pass_rate}}%</text>
        <view class="tags" v-if="hasTags(c)">
          <text class="tag" v-for="(t,j) in getTags(c)" :key="j">{{t}}</text>
        </view>
      </view>
      <button class="btn" :style="{background:theme.primaryColor}" size="mini" @tap="callCoach(c)">联系</button>
    </view>
    <view class="empty" v-if="!allCoaches.length">暂无教练信息</view>
  </view>
</template>
<script>
import config from '../../school.config.json';
const TID = (config._meta && config._meta.tenantId) || '';
const API = (config._meta && config._meta.apiBase) || '';
function getList(p){ return new Promise(function(resolve){ uni.request({url:API+'/api/public/'+TID+'/'+p,success:function(r){resolve(r.data)},fail:function(){resolve([])}}); }); }
export default {
  data() { return { allCoaches: config.coaches||[], theme: config.school.theme }; },
  onLoad(){ var s=this; getList('coaches').then(function(r){ if(r.length)s.allCoaches=s.allCoaches.concat(r); }); },
  methods: {
    callCoach(c){ var phone=c.phone||config.school.phone; if(phone)uni.makePhoneCall({phoneNumber:phone}); },
    hasTags(c){ var t=c.tags; return t && (typeof t==='string'?t.trim():t.length>0); },
    getTags(c){ var t=c.tags; return typeof t==='string'?t.split(',').map(function(x){return x.trim()}):(t||[]); }
  }
}
</script>
<style scoped>
.page{padding:20rpx}
.coach-card{background:#fff;border-radius:16rpx;padding:24rpx;margin-bottom:20rpx;display:flex;align-items:center}
.avatar{width:120rpx;height:120rpx;border-radius:60rpx;margin-right:20rpx}
.info{flex:1}
.name{font-size:32rpx;font-weight:600;display:block}
.exp{font-size:24rpx;color:#999;margin:4rpx 0}
.stars{font-size:26rpx}.rate{font-size:24rpx;color:#52c41a;display:block}
.tags{margin-top:8rpx}
.tag{display:inline-block;background:#f0f5ff;color:#1890ff;font-size:20rpx;padding:4rpx 12rpx;border-radius:4rpx;margin-right:8rpx}
.btn{border-radius:40rpx;color:#fff;height:60rpx;line-height:60rpx}
.empty{text-align:center;color:#999;padding:100rpx 0}
</style>
