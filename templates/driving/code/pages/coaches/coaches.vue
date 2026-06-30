<template>
  <view class="page">
    <view class="coach-card" v-for="(c,i) in coaches" :key="i">
      <image class="avatar" :src="c.avatar || '/static/default-avatar.png'" mode="aspectFill" />
      <view class="info">
        <text class="name">{{c.name}}</text>
        <text class="exp">教龄 {{c.experience}} 年</text>
        <view class="stars" v-if="c.rating">⭐ {{c.rating}}</view>
        <text class="rate" v-if="c.passRate">通过率 {{c.passRate}}%</text>
        <view class="tags" v-if="c.tags && c.tags.length">
          <text class="tag" v-for="(t,j) in c.tags" :key="j">{{t}}</text>
        </view>
      </view>
      <button class="btn" :style="{background:theme.primaryColor}" size="mini" @tap="callCoach(c)">联系</button>
    </view>
    <view class="empty" v-if="!coaches.length">暂无教练信息</view>
  </view>
</template>
<script>
import config from '../../school.config.json'
export default {
  data() { return { coaches: config.coaches, theme: config.school.theme } },
  methods: { callCoach(c) { c.phone ? uni.makePhoneCall({phoneNumber:c.phone}) : uni.makePhoneCall({phoneNumber:config.school.phone}) } }
}
</script>
<style scoped>
.page { padding: 20rpx; }
.coach-card { background: #fff; border-radius: 16rpx; padding: 24rpx; margin-bottom: 20rpx; display: flex; align-items: center; }
.avatar { width: 120rpx; height: 120rpx; border-radius: 60rpx; margin-right: 20rpx; }
.info { flex: 1; }
.name { font-size: 32rpx; font-weight: 600; display: block; }
.exp { font-size: 24rpx; color: #999; margin: 4rpx 0; }
.stars { font-size: 26rpx; }
.rate { font-size: 24rpx; color: #52c41a; display: block; }
.tags { margin-top: 8rpx; }
.tag { display: inline-block; background: #f0f5ff; color: #1890ff; font-size: 20rpx; padding: 4rpx 12rpx; border-radius: 4rpx; margin-right: 8rpx; }
.btn { border-radius: 40rpx; color: #fff; height: 60rpx; line-height: 60rpx; }
.empty { text-align: center; color: #999; padding: 100rpx 0; }
</style>
