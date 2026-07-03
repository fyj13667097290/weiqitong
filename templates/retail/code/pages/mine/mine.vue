<template>
  <view class="page">
    <view class="header" :style="{background:theme.primaryColor}">
      <image class="avatar" src="/static/default-avatar.png" mode="aspectFill" />
      <text class="name">顾客</text>
    </view>
    <view class="menu"><navigator url="/pages/orders/orders" class="menu-item"><text>📋 我的订单</text><text class="arrow">></text></navigator></view>
    <view class="menu"><view class="menu-item" @tap="callShop"><text>📞 联系店家</text><text class="arrow">></text></view></view>
    <view class="footer"><text>{{shop.name}}</text></view>
  </view>
</template>
<script>
import config from '../../school.config.json';
export default {
  data(){ return { shop:config.shop, theme:config.shop.theme }; },
  methods: { callShop(){ uni.makePhoneCall({phoneNumber:this.shop.phone}); } }
}
</script>
<style scoped>
.page{padding-bottom:40rpx}
.header{padding:60rpx 30rpx 40rpx;text-align:center;color:#fff}
.avatar{width:120rpx;height:120rpx;border-radius:60rpx;border:3rpx solid rgba(255,255,255,.5)}
.name{font-size:36rpx;font-weight:600;display:block;margin-top:16rpx}
.menu{background:#fff;margin:20rpx 24rpx;border-radius:16rpx;overflow:hidden}
.menu-item{display:flex;justify-content:space-between;padding:28rpx 24rpx;font-size:30rpx;border-bottom:1rpx solid #f5f5f5}
.menu-item:last-child{border-bottom:none}.arrow{color:#ccc}
.footer{text-align:center;padding:40rpx;color:#ccc;font-size:24rpx}
</style>
