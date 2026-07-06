<template><view class="page">
<view class="hero" :style="{backgroundColor:theme.primaryColor}">
<text class="hero-name">{{shop.shortName||shop.name}}</text>
<text class="hero-desc" v-if="shop.description">{{shop.description}}</text>
</view>
<view class="actions">
<view class="act" @tap="goServices"><view class="act-icon bg1">📋</view><text>服务项目</text></view>
<view class="act" @tap="goBooking"><view class="act-icon bg2">📅</view><text>在线预约</text></view>
<view class="act" @tap="goOrders"><view class="act-icon bg3">📦</view><text>我的订单</text></view>
<view class="act" @tap="callShop"><view class="act-icon bg4">📞</view><text>联系我们</text></view>
</view>
<view class="section" v-if="shop.address"><view class="stitle">📍 {{shop.address}}</view></view>
</view></template>
<script>import config from '../../school.config.json';export default{data(){return{shop:config.shop,theme:config.shop.theme}},methods:{goServices(){uni.navigateTo({url:'/pages/services/services'})},goBooking(){uni.navigateTo({url:'/pages/booking/booking'})},goOrders(){uni.switchTab({url:'/pages/orders/orders'})},callShop(){uni.makePhoneCall({phoneNumber:this.shop.phone})}}}</script>
<style scoped>.page{background:#f5f5f5;min-height:100vh}.hero{padding:60rpx 30rpx;color:#fff;text-align:center}.hero-name{font-size:44rpx;font-weight:800}.hero-desc{font-size:26rpx;opacity:.85;margin-top:8rpx}.actions{display:flex;margin:20rpx 24rpx;background:#fff;border-radius:16rpx;padding:28rpx 0}.act{flex:1;text-align:center}.act-icon{width:96rpx;height:96rpx;border-radius:24rpx;margin:0 auto 10rpx;display:flex;align-items:center;justify-content:center;font-size:44rpx}.bg1{background:#e6f7ff}.bg2{background:#f0f5ff}.bg3{background:#fff7e6}.bg4{background:#f6ffed}.section{margin:20rpx 24rpx;padding:20rpx;background:#fff;border-radius:12rpx}.stitle{font-size:28rpx}</style>
