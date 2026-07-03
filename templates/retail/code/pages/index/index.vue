<template>
  <view class="page">
    <view class="hero" :style="{backgroundColor: theme.primaryColor}">
      <view class="hero-content">
        <image class="hero-logo" :src="shop.logo" mode="aspectFit" v-if="shop.logo" />
        <text class="hero-name">{{shop.shortName || shop.name}}</text>
        <text class="hero-desc" v-if="shop.description">{{shop.description}}</text>
      </view>
    </view>

    <view class="notice" v-if="shop.phone" @tap="callShop">
      <text class="notice-icon">📞</text>
      <text class="notice-text">联系店家 · {{shop.phone}}</text>
    </view>

    <view class="section" v-if="allProducts.length">
      <view class="section-title"><text class="sdot"></text>热门商品<navigator url="/pages/products/products" class="smore">全部</navigator></view>
      <view class="product-grid">
        <view class="product-card" v-for="(p,i) in allProducts.slice(0,6)" :key="i" @tap="goProducts">
          <view class="p-img-wrap"><text class="p-img-placeholder">📦</text></view>
          <text class="p-name">{{p.name}}</text>
          <view class="p-price-box"><text class="p-price">¥{{p.price}}</text><text class="p-tag" v-if="p.tag">{{p.tag}}</text></view>
        </view>
      </view>
    </view>

    <view class="section" v-if="shop.address">
      <view class="section-title"><text class="sdot"></text>店铺信息</view>
      <view class="info-card" @tap="goMap">
        <text class="info-addr">{{shop.address}}</text>
        <text class="info-tel" v-if="shop.phone">{{shop.phone}}</text>
      </view>
    </view>

    <view class="footer"><text>{{shop.name}}</text></view>
  </view>
</template>
<script>
import config from '../../school.config.json';
var TID=(config._meta&&config._meta.tenantId)||'',API=(config._meta&&config._meta.apiBase)||'';
function getList(p){ return new Promise(function(resolve){ uni.request({url:API+'/api/public/'+TID+'/'+p,success:function(r){resolve(r.data)},fail:function(){resolve([])}}); }); }
export default {
  data(){ return { shop:config.shop, theme:config.shop.theme, allProducts:config.products||[] }; },
  onLoad(){ var s=this; getList('products').then(function(r){ if(r.length)s.allProducts=r; }); },
  methods: {
    goProducts(){ uni.navigateTo({url:'/pages/products/products'}); },
    goMap(){ uni.openLocation({address:this.shop.address}); },
    callShop(){ uni.makePhoneCall({phoneNumber:this.shop.phone}); }
  }
}
</script>
<style scoped>
.page{background:#f5f5f5;min-height:100vh}
.hero{padding:50rpx 30rpx 40rpx;color:#fff;text-align:center}
.hero-logo{width:100rpx;height:100rpx;border-radius:20rpx;border:3rpx solid rgba(255,255,255,.4);margin-bottom:12rpx;background:#fff}
.hero-name{font-size:42rpx;font-weight:800;display:block}.hero-desc{font-size:24rpx;opacity:.85;margin-top:8rpx;display:block}
.notice{display:flex;align-items:center;margin:20rpx 24rpx;padding:16rpx 20rpx;background:#fff;border-radius:12rpx;box-shadow:0 2rpx 8rpx rgba(0,0,0,.04)}
.notice-icon{margin-right:12rpx;font-size:28rpx}.notice-text{font-size:26rpx;color:#333}
.section{background:#fff;margin:0 24rpx 20rpx;border-radius:16rpx;padding:24rpx;box-shadow:0 2rpx 8rpx rgba(0,0,0,.04)}
.section-title{display:flex;align-items:center;font-size:32rpx;font-weight:700;margin-bottom:20rpx}
.sdot{width:10rpx;height:28rpx;border-radius:5rpx;margin-right:12rpx;display:inline-block}
.smore{margin-left:auto;font-size:26rpx;color:#999}
.product-grid{display:flex;flex-wrap:wrap;gap:16rpx}
.product-card{flex:0 0 calc(33.33% - 11rpx);text-align:center;margin-bottom:8rpx}
.p-img-wrap{width:100%;aspect-ratio:1;background:#f8f8f8;border-radius:12rpx;display:flex;align-items:center;justify-content:center;margin-bottom:10rpx}
.p-img-placeholder{font-size:60rpx}
.p-name{font-size:26rpx;font-weight:500;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.p-price-box{display:flex;justify-content:center;align-items:center;gap:6rpx;margin-top:6rpx}
.p-price{font-size:28rpx;font-weight:700;color:#ff4d4f}.p-tag{font-size:18rpx;background:#ff4d4f;color:#fff;padding:2rpx 8rpx;border-radius:6rpx}
.info-card{background:#fafafa;padding:20rpx;border-radius:8rpx}.info-addr{font-size:28rpx;display:block}.info-tel{font-size:24rpx;color:#1890ff;margin-top:8rpx;display:block}
.footer{text-align:center;padding:40rpx;color:#ccc;font-size:22rpx}
</style>
