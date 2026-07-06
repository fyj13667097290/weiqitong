<template><view class="page">
<view class="cat-bar"><view class="cat-item" v-for="(c,i) in categories" :key="i" :class="{active:selCat===c}" @tap="selCat=c">{{c}}</view></view>
<view class="svc-card" v-for="(s,i) in filteredServices" :key="i">
<view class="svc-info"><text class="svc-name">{{s.name}}</text><text class="svc-price">¥{{s.price}}</text></view>
<button class="svc-btn" :style="{background:theme.primaryColor}" size="mini" @tap="bookService(s)">立即预约</button>
</view>
<view class="empty" v-if="!filteredServices.length">暂无服务</view>
</view></template>
<script>import config from '../../school.config.json';export default{data(){return{services:config.products||[],categories:['全部','热门','优惠'],selCat:'全部',theme:config.shop.theme}},computed:{filteredServices(){var s=this;if(s.selCat==='全部')return s.services;return s.services.filter(function(x){return x.category===s.selCat})}},methods:{bookService(s){uni.navigateTo({url:'/pages/booking/booking?svc='+(s.name||'')+'&price='+(s.price||'')})}}}</script>
<style scoped>.page{padding:20rpx}.cat-bar{display:flex;gap:12rpx;margin-bottom:20rpx;flex-wrap:wrap}.cat-item{padding:10rpx 24rpx;border-radius:20rpx;font-size:26rpx;background:#fff;color:#666}.cat-item.active{background:#1890ff;color:#fff}.svc-card{background:#fff;border-radius:14rpx;padding:20rpx;margin-bottom:14rpx;display:flex;align-items:center;justify-content:space-between}.svc-name{font-size:30rpx;font-weight:500}.svc-price{font-size:28rpx;color:#ff4d4f;font-weight:700;display:block;margin-top:4rpx}.svc-btn{border-radius:20rpx;color:#fff;font-size:24rpx}.empty{text-align:center;color:#999;padding:100rpx 0}</style>
