<template>
  <view class="page">
    <view v-if="cartItems.length">
      <view class="cart-item" v-for="(c,i) in cartItems" :key="i">
        <text class="ci-name">{{c.name}}</text>
        <view class="ci-ctrl">
          <view class="qty-btn" @tap="changeQty(i,-1)">-</view>
          <text class="ci-qty">{{c.qty||1}}</text>
          <view class="qty-btn" @tap="changeQty(i,1)">+</view>
        </view>
        <text class="ci-price">¥{{c.price*(c.qty||1)}}</text>
      </view>
      <view class="total-bar"><text>合计</text><text class="total-price">¥{{totalPrice}}</text></view>
      <button class="btn" :style="{background:theme.primaryColor}" @tap="submitOrder">提交订单</button>
    </view>
    <view class="empty" v-else>购物车是空的</view>
  </view>
</template>
<script>
import config from '../../school.config.json';
export default {
  data(){ return { theme:config.shop.theme, cartItems:[] }; },
  computed: { totalPrice(){ return this.cartItems.reduce(function(s,c){return s+c.price*(c.qty||1)},0); } },
  onShow(){ var app=getApp(); this.cartItems=app.globalData.cart||[]; },
  methods: {
    changeQty(i,d){ var c=this.cartItems[i]; c.qty=(c.qty||1)+d; if(c.qty<1){ this.cartItems.splice(i,1); } getApp().globalData.cart=this.cartItems; },
    submitOrder(){ uni.showToast({title:'订单已提交！',icon:'success'}); getApp().globalData.cart=[]; this.cartItems=[]; setTimeout(function(){uni.switchTab({url:'/pages/orders/orders'})},1500); }
  }
}
</script>
<style scoped>
.page{padding:20rpx;padding-bottom:200rpx}
.cart-item{background:#fff;border-radius:12rpx;padding:20rpx;margin-bottom:12rpx;display:flex;align-items:center;gap:14rpx}
.ci-name{flex:1;font-size:28rpx;font-weight:500}
.ci-ctrl{display:flex;align-items:center;gap:12rpx}
.qty-btn{width:48rpx;height:48rpx;border-radius:24rpx;background:#f0f0f0;text-align:center;line-height:48rpx;font-size:28rpx;font-weight:600}
.ci-qty{font-size:28rpx;font-weight:600;min-width:40rpx;text-align:center}
.ci-price{font-size:26rpx;color:#ff4d4f;font-weight:600;min-width:100rpx;text-align:right}
.total-bar{display:flex;justify-content:space-between;padding:20rpx;font-size:30rpx;font-weight:600}
.total-price{color:#ff4d4f}
.btn{width:100%;color:#fff;border-radius:50rpx;height:88rpx;line-height:88rpx;font-size:30rpx;font-weight:600}
.empty{text-align:center;color:#999;padding:100rpx 0;font-size:28rpx}
</style>
