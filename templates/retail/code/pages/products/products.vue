<template>
  <view class="page">
    <view class="cat-bar">
      <view class="cat-item" v-for="(c,i) in categories" :key="i" :class="{active:selCat===c}" @tap="selCat=c">{{c}}</view>
    </view>
    <view class="product-grid">
      <view class="p-card" v-for="(p,i) in filteredProducts" :key="i">
        <view class="p-img">📦</view>
        <text class="p-name">{{p.name}}</text>
        <text class="p-price">¥{{p.price}}</text>
        <view class="p-badge" v-if="p.tag">{{p.tag}}</view>
        <button class="p-btn" :style="{background:theme.primaryColor}" size="mini" @tap="addToCart(p)">+ 加入</button>
      </view>
    </view>
    <view class="empty" v-if="!filteredProducts.length">暂无商品</view>
  </view>
</template>
<script>
import config from '../../school.config.json';
export default {
  data(){ return { products:config.products||[], categories:config.categories||['全部'], selCat:'全部', theme:config.shop.theme, cart:[] }; },
  computed: { filteredProducts(){ var s=this; if(s.selCat==='全部')return s.products; return s.products.filter(function(p){return p.category===s.selCat}); } },
  methods: {
    addToCart(p){
      var app=getApp(); if(!app.globalData.cart)app.globalData.cart=[];
      var exist=app.globalData.cart.find(function(c){return c.name===p.name});
      if(exist){ exist.qty=(exist.qty||1)+1; } else { p.qty=1; app.globalData.cart.push(p); }
      uni.showToast({title:'已加入购物车',icon:'success'});
    }
  }
}
</script>
<style scoped>
.page{padding:20rpx;padding-bottom:40rpx}
.cat-bar{display:flex;gap:12rpx;margin-bottom:20rpx;flex-wrap:wrap}
.cat-item{padding:10rpx 24rpx;border-radius:20rpx;font-size:26rpx;background:#fff;color:#666}
.cat-item.active{background:#1890ff;color:#fff}
.product-grid{display:flex;flex-wrap:wrap;gap:16rpx}
.p-card{flex:0 0 calc(50% - 8rpx);background:#fff;border-radius:14rpx;padding:16rpx;position:relative;overflow:hidden}
.p-img{width:100%;aspect-ratio:1;background:#f8f8f8;border-radius:8rpx;display:flex;align-items:center;justify-content:center;font-size:72rpx}
.p-name{font-size:28rpx;font-weight:500;display:block;margin-top:8rpx}
.p-price{font-size:30rpx;font-weight:700;color:#ff4d4f;display:block;margin-top:4rpx}
.p-badge{position:absolute;top:0;right:0;background:#ff4d4f;color:#fff;font-size:20rpx;padding:4rpx 12rpx;border-radius:0 14rpx 0 14rpx}
.p-btn{margin-top:10rpx;border-radius:20rpx;color:#fff;font-size:24rpx}
.empty{text-align:center;color:#999;padding:100rpx 0}
</style>
