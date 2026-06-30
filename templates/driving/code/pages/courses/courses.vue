<template>
  <view class="page">
    <view class="course-card" v-for="(c,i) in courses" :key="i">
      <view class="tag" v-if="c.tag" :style="{background:theme.primaryColor}">{{c.tag}}</view>
      <view class="head">
        <text class="name">{{c.name}}</text>
        <view class="price-box">
          <text class="price">¥{{c.price}}</text>
          <text class="original" v-if="c.originalPrice">¥{{c.originalPrice}}</text>
        </view>
      </view>
      <view class="features" v-if="c.features && c.features.length">
        <text class="ftag" v-for="(f,j) in c.features" :key="j">✓ {{f}}</text>
      </view>
      <button class="btn" :style="{background:theme.primaryColor}" @tap="signUp(c)">立即报名</button>
    </view>
    <view class="empty" v-if="!courses.length">暂无课程信息，请联系驾校</view>
  </view>
</template>
<script>
import config from '../../school.config.json'
export default {
  data() { return { courses: config.courses, theme: config.school.theme } },
  methods: { signUp(c) { uni.makePhoneCall({phoneNumber: config.school.phone}) } }
}
</script>
<style scoped>
.page { padding: 20rpx; }
.course-card { background: #fff; border-radius: 16rpx; padding: 30rpx; margin-bottom: 20rpx; position: relative; overflow: hidden; }
.tag { position: absolute; top: 0; right: 0; color: #fff; font-size: 22rpx; padding: 6rpx 20rpx; border-radius: 0 16rpx 0 16rpx; }
.name { font-size: 34rpx; font-weight: 700; }
.price-box { margin: 16rpx 0; }
.price { font-size: 44rpx; font-weight: 700; color: #ff4d4f; }
.original { font-size: 26rpx; color: #999; text-decoration: line-through; margin-left: 16rpx; }
.ftag { display: block; font-size: 26rpx; color: #666; line-height: 1.8; }
.btn { margin-top: 20rpx; color: #fff; border-radius: 40rpx; height: 80rpx; line-height: 80rpx; font-size: 30rpx; }
.empty { text-align: center; color: #999; padding: 100rpx 0; }
</style>
