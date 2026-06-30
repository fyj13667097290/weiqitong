<template>
  <view class="page">
    <view class="header" :style="{background: theme.primaryColor}">
      <image class="avatar" src="/static/default-avatar.png" mode="aspectFill" />
      <text class="name">学员</text>
      <text class="phone">未登录</text>
    </view>

    <view class="menu-section">
      <view class="menu-item" @tap="goPage('appointment')">
        <text>📅 我的预约</text><text class="arrow">></text>
      </view>
      <view class="menu-item" @tap="goPage('exam')">
        <text>📝 我的成绩</text><text class="arrow">></text>
      </view>
      <view class="menu-item" @tap="goPage('courses')">
        <text>🎓 我的课程</text><text class="arrow">></text>
      </view>
    </view>

    <view class="menu-section">
      <view class="menu-item" @tap="contactSchool">
        <text>📞 联系驾校</text><text class="arrow">></text>
      </view>
      <view class="menu-item" @tap="shareApp">
        <text>💬 推荐给朋友</text><text class="arrow">></text>
      </view>
    </view>

    <view class="footer">
      <text>{{school.name}}</text>
      <text class="phone">{{school.phone}}</text>
    </view>
  </view>
</template>
<script>
import config from '../../school.config.json'
export default {
  data() { return { school: config.school, theme: config.school.theme } },
  methods: {
    goPage(p) { const map={appointment:'/pages/appointment/appointment',exam:'/pages/exam/exam',courses:'/pages/courses/courses'}; uni.navigateTo({url:map[p]}) },
    contactSchool() { uni.makePhoneCall({phoneNumber: this.school.phone}) },
    shareApp() { uni.showToast({title:'点击右上角分享'}) }
  }
}
</script>
<style scoped>
.page { padding-bottom: 40rpx; }
.header { padding: 60rpx 30rpx 40rpx; text-align: center; color: #fff; }
.avatar { width: 120rpx; height: 120rpx; border-radius: 60rpx; border: 3px solid rgba(255,255,255,.5); }
.name { font-size: 36rpx; font-weight: 600; display: block; margin-top: 16rpx; }
.phone { font-size: 26rpx; opacity: .8; }
.menu-section { background: #fff; margin: 20rpx 24rpx; border-radius: 16rpx; overflow: hidden; }
.menu-item { display: flex; justify-content: space-between; padding: 28rpx 24rpx; font-size: 30rpx; border-bottom: 1rpx solid #f5f5f5; }
.menu-item:last-child { border-bottom: none; }
.arrow { color: #ccc; }
.footer { text-align: center; padding: 40rpx; color: #999; font-size: 24rpx; }
.footer text { display: block; }
.phone { color: #1890ff; margin-top: 8rpx; }
</style>
