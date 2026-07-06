<template><view class="page">
<view class="hero" :style="{backgroundColor:theme.primaryColor}">
<view class="hero-content"><text class="hero-name">{{shop.shortName||shop.name}}</text><text class="hero-desc">{{shop.description}}</text></view>
</view>
<view class="banner"><text class="banner-icon">🎁</text><text class="banner-text">新客首晚8折 · 连住三天免一天</text></view>
<view class="actions"><view class="act" @tap="goServices"><view class="act-icon bg1">🏠</view><text>房型查看</text></view>
<view class="act" @tap="goBooking"><view class="act-icon bg2">📅</view><text>在线预订</text></view>
<view class="act" @tap="goOrders"><view class="act-icon bg3">📋</view><text>订单管理</text></view>
<view class="act" @tap="callShop"><view class="act-icon bg4">📞</view><text>联系前台</text></view></view>
<view class="section"><text class="stitle">🛏️ 推荐房型</text>
<scroll-view scroll-x class="room-scroll">
<view class="room-card" v-for="i in 3" :key="i" @tap="goServices"><view class="room-img">🏨</view><text class="room-name">{{['大床房','双床房','套房'][i-1]}}</text><text class="room-price">¥{{[188,268,388][i-1]}}/晚</text></view></scroll-view></view>
<view class="section" v-if="shop.address"><text class="stitle">📍 {{shop.address}}</text></view>
</view></template>
<script>import config from '../../school.config.json';export default{data(){return{shop:config.shop,theme:config.shop.theme}},methods:{goServices(){uni.navigateTo({url:'/pages/services/services'})},goBooking(){uni.navigateTo({url:'/pages/booking/booking'})},goOrders(){uni.switchTab({url:'/pages/orders/orders'})},callShop(){uni.makePhoneCall({phoneNumber:this.shop.phone})}}}</script>
<style scoped>.page{background:#f5f5f5;min-height:100vh}.hero{padding:50rpx 30rpx 40rpx;color:#fff;text-align:center}.hero-name{font-size:44rpx;font-weight:800}.hero-desc{font-size:24rpx;opacity:.85;margin-top:8rpx}.banner{display:flex;align-items:center;margin:20rpx 24rpx;padding:20rpx;background:linear-gradient(135deg,#795548,#a1887f);border-radius:14rpx;color:#fff}.banner-icon{margin-right:12rpx;font-size:32rpx}.banner-text{flex:1;font-size:26rpx;font-weight:500}.actions{display:flex;margin:20rpx 24rpx;background:#fff;border-radius:16rpx;padding:28rpx 0}.act{flex:1;text-align:center;font-size:24rpx}.act-icon{width:96rpx;height:96rpx;border-radius:24rpx;margin:0 auto 10rpx;display:flex;align-items:center;justify-content:center;font-size:44rpx}.bg1{background:#efebe9}.bg2{background:#e8f5e9}.bg3{background:#e3f2fd}.bg4{background:#fce4ec}.section{margin:20rpx 24rpx;padding:20rpx;background:#fff;border-radius:12rpx}.stitle{font-size:30rpx;font-weight:700;display:block;margin-bottom:16rpx}.room-scroll{white-space:nowrap}.room-card{display:inline-block;width:220rpx;margin-right:16rpx;text-align:center;background:#fafafa;padding:16rpx;border-radius:12rpx}.room-img{font-size:72rpx;padding:20rpx}.room-name{font-size:28rpx;font-weight:600;display:block}.room-price{font-size:26rpx;color:#ff4d4f;font-weight:700;margin-top:6rpx;display:block}</style>
