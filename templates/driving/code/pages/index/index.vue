<template>
  <view class="page">
    <!-- 头部品牌区 -->
    <view class="header" :style="{background: theme.primaryColor}">
      <image class="logo" :src="school.logo" mode="aspectFit" v-if="school.logo" />
      <text class="school-name">{{school.name}}</text>
      <text class="school-desc" v-if="school.description">{{school.description}}</text>
      <view class="header-stats">
        <view class="stat-item"><text class="stat-num">{{coaches.length}}</text><text class="stat-label">位教练</text></view>
        <view class="stat-item"><text class="stat-num">{{courses.length}}</text><text class="stat-label">种课程</text></view>
        <view class="stat-item"><text class="stat-num">4.8</text><text class="stat-label">分好评</text></view>
      </view>
    </view>

    <!-- 快捷入口 -->
    <view class="quick-actions">
      <view class="action" @tap="goAppointment" v-if="features.appointment">
        <view class="action-icon" :style="{background: theme.primaryColor}">📅</view>
        <text>预约练车</text>
      </view>
      <view class="action" @tap="goExam" v-if="features.examPrep">
        <view class="action-icon" :style="{background: theme.primaryColor}">📝</view>
        <text>题库练习</text>
      </view>
      <view class="action" @tap="callSchool">
        <view class="action-icon" :style="{background: theme.primaryColor}">📞</view>
        <text>电话咨询</text>
      </view>
      <view class="action" @tap="goMap" v-if="school.address">
        <view class="action-icon" :style="{background: theme.primaryColor}">📍</view>
        <text>导航到校</text>
      </view>
    </view>

    <!-- 课程推荐 -->
    <view class="section" v-if="courses.length">
      <view class="section-title">
        <text>🏎️ 热门课程</text>
        <text class="more" @tap="goCourses">全部 ></text>
      </view>
      <view class="course-list">
        <view class="course-card" v-for="(c,i) in courses.slice(0,3)" :key="i">
          <view class="course-tag" v-if="c.tag">{{c.tag}}</view>
          <text class="course-name">{{c.name}}</text>
          <view class="course-price">
            <text class="price">¥{{c.price}}</text>
            <text class="original" v-if="c.originalPrice">¥{{c.originalPrice}}</text>
          </view>
          <view class="course-features" v-if="c.features">
            <text class="feature-tag" v-for="(f,j) in c.features" :key="j">{{f}}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 教练推荐 -->
    <view class="section" v-if="coaches.length">
      <view class="section-title">
        <text>👨‍🏫 金牌教练</text>
        <text class="more" @tap="goCoaches">全部 ></text>
      </view>
      <scroll-view scroll-x class="coach-scroll">
        <view class="coach-card" v-for="(c,i) in coaches.slice(0,6)" :key="i">
          <image class="coach-avatar" :src="c.avatar || '/static/default-avatar.png'" mode="aspectFill" />
          <text class="coach-name">{{c.name}}</text>
          <text class="coach-exp">{{c.experience}}年教龄</text>
          <text class="coach-rate" v-if="c.passRate">通过率{{c.passRate}}%</text>
        </view>
      </scroll-view>
    </view>

    <!-- 驾校地址 -->
    <view class="section" v-if="school.address">
      <view class="section-title"><text>📍 训练场地</text></view>
      <view class="location-card" @tap="goMap">
        <text class="loc-name">{{school.address}}</text>
        <text class="loc-phone">{{school.phone}}</text>
      </view>
    </view>
  </view>
</template>

<script>
import config from '../../school.config.json'
export default {
  data() { return { school: config.school, courses: config.courses, coaches: config.coaches, features: config.features, theme: config.school.theme } },
  methods: {
    goAppointment() { uni.navigateTo({url:'/pages/appointment/appointment'}) },
    goExam() { uni.navigateTo({url:'/pages/exam/exam'}) },
    goCourses() { uni.navigateTo({url:'/pages/courses/courses'}) },
    goCoaches() { uni.navigateTo({url:'/pages/coaches/coaches'}) },
    goMap() { uni.openLocation({address: this.school.address}) },
    callSchool() { uni.makePhoneCall({phoneNumber: this.school.phone}) }
  }
}
</script>

<style scoped>
.page { padding-bottom: 30rpx; }
.header { padding: 40rpx 30rpx; color: #fff; text-align: center; }
.logo { width: 120rpx; height: 120rpx; border-radius: 60rpx; border: 3px solid rgba(255,255,255,.5); margin-bottom: 16rpx; }
.school-name { font-size: 40rpx; font-weight: 700; display: block; }
.school-desc { font-size: 26rpx; opacity: .85; display: block; margin-top: 8rpx; }
.header-stats { display: flex; justify-content: center; gap: 40rpx; margin-top: 24rpx; }
.stat-item { text-align: center; }
.stat-num { font-size: 36rpx; font-weight: 700; display: block; }
.stat-label { font-size: 22rpx; opacity: .75; }
.quick-actions { display: flex; background: #fff; margin: -20rpx 24rpx 20rpx; border-radius: 16rpx; padding: 24rpx 0; box-shadow: 0 4rpx 20rpx rgba(0,0,0,.08); }
.action { flex: 1; text-align: center; font-size: 24rpx; color: #333; }
.action-icon { width: 80rpx; height: 80rpx; border-radius: 40rpx; margin: 0 auto 8rpx; display: flex; align-items: center; justify-content: center; font-size: 36rpx; }
.section { background: #fff; margin: 0 24rpx 20rpx; border-radius: 16rpx; padding: 24rpx; }
.section-title { display: flex; justify-content: space-between; font-size: 32rpx; font-weight: 600; margin-bottom: 20rpx; }
.more { font-size: 26rpx; color: #999; font-weight: 400; }
.course-list { display: flex; flex-direction: column; gap: 16rpx; }
.course-card { border: 1px solid #eee; border-radius: 12rpx; padding: 20rpx; position: relative; }
.course-tag { position: absolute; top: 0; right: 0; background: #ff4d4f; color: #fff; font-size: 20rpx; padding: 4rpx 16rpx; border-radius: 0 12rpx 0 12rpx; }
.course-name { font-size: 30rpx; font-weight: 600; }
.course-price { margin: 10rpx 0; }
.price { font-size: 36rpx; font-weight: 700; color: #ff4d4f; }
.original { font-size: 24rpx; color: #999; text-decoration: line-through; margin-left: 12rpx; }
.feature-tag { display: inline-block; background: #f0f5ff; color: #1890ff; font-size: 20rpx; padding: 4rpx 12rpx; border-radius: 4rpx; margin-right: 8rpx; }
.coach-scroll { white-space: nowrap; }
.coach-card { display: inline-block; text-align: center; width: 160rpx; margin-right: 20rpx; }
.coach-avatar { width: 100rpx; height: 100rpx; border-radius: 50rpx; }
.coach-name { font-size: 28rpx; font-weight: 500; display: block; margin-top: 8rpx; }
.coach-exp { font-size: 22rpx; color: #999; }
.coach-rate { font-size: 22rpx; color: #52c41a; display: block; }
.location-card { background: #fafafa; padding: 20rpx; border-radius: 8rpx; }
.loc-name { font-size: 28rpx; display: block; }
.loc-phone { font-size: 26rpx; color: #1890ff; margin-top: 8rpx; }
</style>
