<template>
  <view class="page">
    <view v-if="orders.length">
      <view class="order-card" v-for="(o,i) in orders" :key="i">
        <view class="o-header"><text class="o-date">{{o.time}}</text><text class="o-status" :style="{color:o.status==='已完成'?'#52c41a':'#fa8c16'}">{{o.status}}</text></view>
        <view class="o-item" v-for="(item,j) in o.items" :key="j"><text class="oi-name">{{item.name}} x{{item.qty}}</text><text class="oi-price">¥{{item.price*item.qty}}</text></view>
        <view class="o-total">合计 <text class="ot-price">¥{{o.total}}</text></view>
      </view>
    </view>
    <view class="empty" v-else>暂无订单</view>
  </view>
</template>
<script>
export default {
  data(){ return { orders:[] }; },
  onShow(){ this.orders=uni.getStorageSync('orders')||[]; }
}
</script>
<style scoped>
.page{padding:20rpx}
.order-card{background:#fff;border-radius:14rpx;padding:20rpx;margin-bottom:16rpx}
.o-header{display:flex;justify-content:space-between;margin-bottom:12rpx;font-size:24rpx}
.o-date{color:#999}.o-status{font-weight:600}
.o-item{display:flex;justify-content:space-between;padding:8rpx 0;font-size:26rpx}
.oi-name{flex:1}.oi-price{color:#ff4d4f}
.o-total{text-align:right;font-size:28rpx;font-weight:600;margin-top:12rpx;padding-top:12rpx;border-top:1rpx solid #f0f0f0}
.ot-price{color:#ff4d4f}
.empty{text-align:center;color:#999;padding:100rpx 0;font-size:28rpx}
</style>
