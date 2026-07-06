<template><view class="page">
<view class="hero" :style="{backgroundColor:theme.primaryColor}">
<view class="hero-content"><text class="hero-name">{{shop.shortName||shop.name}}</text><text class="hero-desc">{{shop.description}}</text></view>
</view>
<view class="banner" @tap="goMenu"><text class="banner-icon">🎉</text><text class="banner-text">新人首单立减 ¥5 · 满 ¥30 减 ¥8</text><text class="banner-arrow">></text></view>
<view class="actions"><view class="act" @tap="goMenu"><view class="act-icon bg1">📋</view><text>全部菜品</text></view>
<view class="act" @tap="goCart"><view class="act-icon bg2">🛒</view><text>点餐车</text></view>
<view class="act" @tap="goOrders"><view class="act-icon bg3">📦</view><text>订单</text></view>
<view class="act" @tap="callShop"><view class="act-icon bg4">📞</view><text>联系店家</text></view></view>
<view class="section" v-if="shop.phone||shop.address">
<view class="sinfo"><text class="saddr">{{shop.address||''}}</text><text class="stel">{{shop.phone||''}}</text></view></view>
</view></template>
<script>import config from '../../school.config.json';export default{data(){return{shop:config.shop,theme:config.shop.theme}},methods:{goMenu(){uni.navigateTo({url:'/pages/menu/menu'})},goCart(){uni.switchTab({url:'/pages/cart/cart'})},goOrders(){uni.navigateTo({url:'/pages/orders/orders'})},callShop(){uni.makePhoneCall({phoneNumber:this.shop.phone})}}}</script>
<style scoped>.page{background:#f5f5f5;min-height:100vh}.hero{padding:50rpx 30rpx 40rpx;color:#fff;text-align:center}.hero-name{font-size:44rpx;font-weight:800}.hero-desc{font-size:24rpx;opacity:.85;margin-top:8rpx}.banner{display:flex;align-items:center;margin:20rpx 24rpx;padding:20rpx;background:linear-gradient(135deg,#ff6b35,#ff8c5a);border-radius:14rpx;color:#fff}.banner-icon{margin-right:12rpx;font-size:32rpx}.banner-text{flex:1;font-size:26rpx;font-weight:500}.banner-arrow{font-size:28rpx}.actions{display:flex;margin:20rpx 24rpx;background:#fff;border-radius:16rpx;padding:28rpx 0}.act{flex:1;text-align:center;font-size:24rpx}.act-icon{width:96rpx;height:96rpx;border-radius:24rpx;margin:0 auto 10rpx;display:flex;align-items:center;justify-content:center;font-size:44rpx}.bg1{background:#fff3e0}.bg2{background:#e8f5e9}.bg3{background:#e3f2fd}.bg4{background:#fce4ec}.section{margin:20rpx 24rpx;padding:20rpx;background:#fff;border-radius:12rpx}.sinfo{font-size:26rpx}.saddr{display:block}.stel{display:block;color:#1890ff;margin-top:6rpx}</style>
