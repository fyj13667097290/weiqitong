<template>
  <view class="page">
    <!-- 头部 -->
    <view class="hero" :style="{backgroundImage: school.photos&&school.photos.length?'url('+school.photos[0]+')':'', backgroundColor: theme.primaryColor}">
      <view class="hero-mask"></view>
      <view class="hero-content">
        <image class="hero-logo" :src="school.logo" mode="aspectFit" v-if="school.logo" />
        <text class="hero-name">{{school.shortName || school.name}}</text>
        <text class="hero-desc" v-if="school.description">{{school.description}}</text>
      </view>
    </view>

    <!-- 公告 -->
    <view class="notice" v-if="announcements.length" @tap="showNotice">
      <text class="notice-icon">📢</text>
      <text class="notice-text">{{announcements[0].title}}</text>
      <text class="notice-arrow">></text>
    </view>

    <!-- 快捷入口 -->
    <view class="actions">
      <view class="act" @tap="goAppointment" v-if="features.appointment">
        <view class="act-icon bg1">📅</view>
        <text class="act-label">预约练车</text>
      </view>
      <view class="act" @tap="goExam" v-if="features.examPrep">
        <view class="act-icon bg2">📝</view>
        <text class="act-label">题库练习</text>
      </view>
      <view class="act" @tap="callSchool">
        <view class="act-icon bg3">📞</view>
        <text class="act-label">电话咨询</text>
      </view>
      <view class="act" @tap="goMap" v-if="school.address">
        <view class="act-icon bg4">📍</view>
        <text class="act-label">导航到校</text>
      </view>
    </view>

    <!-- 培训课程 -->
    <view class="panel" v-if="allCourses.length">
      <view class="panel-hd">
        <view class="panel-title"><text class="dot"></text>培训课程</view>
        <navigator url="/pages/courses/courses" class="panel-more">查看全部 ></navigator>
      </view>
      <scroll-view scroll-x class="course-scroll">
        <view class="course-card" v-for="(c,i) in allCourses.slice(0,5)" :key="i" @tap="goCourses">
          <view class="course-top">
            <text class="course-name">{{c.name}}</text>
            <text class="course-badge" v-if="c.tag">{{c.tag}}</text>
          </view>
          <text class="course-price"><text class="yen">¥</text>{{c.price}}</text>
          <text class="course-orig" v-if="c.originalPrice||c.original_price">原价 ¥{{c.originalPrice||c.original_price}}</text>
        </view>
      </scroll-view>
    </view>

    <!-- 金牌教练 -->
    <view class="panel" v-if="allCoaches.length">
      <view class="panel-hd">
        <view class="panel-title"><text class="dot"></text>金牌教练</view>
        <navigator url="/pages/coaches/coaches" class="panel-more">查看全部 ></navigator>
      </view>
      <scroll-view scroll-x class="coach-scroll">
        <view class="coach-card" v-for="(c,i) in allCoaches.slice(0,6)" :key="i">
          <view class="coach-avatar-wrap">
            <image class="coach-avatar" :src="c.avatar || '/static/default-avatar.png'" mode="aspectFill" />
          </view>
          <text class="coach-name">{{c.name}}</text>
          <view class="coach-stars" v-if="c.rating">
            <text v-for="s in Math.floor(c.rating||0)" :key="s">⭐</text>
            <text class="coach-rate">{{c.rating}}</text>
          </view>
          <text class="coach-exp">{{c.experience}}年教龄 · 通过率{{c.passRate||c.pass_rate}}%</text>
        </view>
      </scroll-view>
    </view>

    <!-- 训练场地 -->
    <view class="panel" v-if="school.address">
      <view class="panel-hd"><view class="panel-title"><text class="dot"></text>训练场地</view></view>
      <view class="location-card" @tap="goMap">
        <text class="loc-icon">📍</text>
        <view class="loc-info">
          <text class="loc-addr">{{school.address}}</text>
          <text class="loc-tel">{{school.phone}}</text>
        </view>
        <text class="loc-go">导航 ></text>
      </view>
    </view>

    <!-- 底部 -->
    <view class="footer">
      <text>{{school.name}}</text>
      <text class="footer-tel">{{school.phone}}</text>
    </view>
  </view>
</template>

<script>
import config from '../../school.config.json';
const TID = (config._meta && config._meta.tenantId) || '';
const API = (config._meta && config._meta.apiBase) || '';
function getList(p){ return new Promise(function(resolve){ uni.request({url:API+'/api/public/'+TID+'/'+p,success:function(r){resolve(r.data)},fail:function(){resolve([])}}); }); }
export default {
  data() { return { school:config.school, features:config.features, theme:config.school.theme, allCourses:config.courses||[], allCoaches:config.coaches||[], announcements:[] }; },
  onLoad(){ var s=this; getList('announcements').then(function(r){s.announcements=r}); getList('courses').then(function(r){if(r.length)s.allCourses=s.allCourses.concat(r)}); getList('coaches').then(function(r){if(r.length)s.allCoaches=s.allCoaches.concat(r)}); },
  methods: {
    goAppointment(){uni.navigateTo({url:'/pages/appointment/appointment'})}, goExam(){uni.navigateTo({url:'/pages/exam/exam'})},
    goCourses(){uni.navigateTo({url:'/pages/courses/courses'})}, goCoaches(){uni.navigateTo({url:'/pages/coaches/coaches'})},
    goMap(){uni.openLocation({address:this.school.address})}, callSchool(){uni.makePhoneCall({phoneNumber:this.school.phone})},
    showNotice(){var a=this.announcements[0];if(a)uni.showModal({title:a.title,content:a.content||'',showCancel:false})}
  }
}
</script>

<style scoped>
.page{background:#f5f5f5;min-height:100vh}
.hero{position:relative;background-size:cover;background-position:center;min-height:380rpx;display:flex;align-items:flex-end}
.hero-mask{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,.2),rgba(0,0,0,.6))}
.hero-content{position:relative;z-index:1;padding:40rpx 30rpx;color:#fff}
.hero-logo{width:100rpx;height:100rpx;border-radius:20rpx;border:3rpx solid rgba(255,255,255,.4);margin-bottom:12rpx;background:#fff}
.hero-name{display:block;font-size:44rpx;font-weight:800;text-shadow:0 2rpx 8rpx rgba(0,0,0,.3)}
.hero-desc{display:block;font-size:26rpx;opacity:.9;margin-top:8rpx;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.notice{display:flex;align-items:center;margin:20rpx 24rpx;padding:18rpx 20rpx;background:#fff;border-radius:12rpx;box-shadow:0 2rpx 8rpx rgba(0,0,0,.04)}
.notice-icon{margin-right:12rpx;font-size:28rpx}
.notice-text{flex:1;font-size:26rpx;color:#333;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.notice-arrow{color:#ccc}
.actions{display:flex;justify-content:space-around;padding:28rpx 0;margin:0 24rpx;background:#fff;border-radius:16rpx;box-shadow:0 2rpx 8rpx rgba(0,0,0,.04)}
.act{display:flex;flex-direction:column;align-items:center}
.act-icon{width:96rpx;height:96rpx;border-radius:24rpx;display:flex;align-items:center;justify-content:center;font-size:44rpx;margin-bottom:10rpx}
.bg1{background:#e6f7ff}.bg2{background:#f0f5ff}.bg3{background:#fff7e6}.bg4{background:#f6ffed}
.act-label{font-size:24rpx;color:#555;font-weight:500}
.panel{background:#fff;margin:20rpx 24rpx;border-radius:16rpx;padding:24rpx;box-shadow:0 2rpx 8rpx rgba(0,0,0,.04)}
.panel-hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:20rpx}
.panel-title{font-size:32rpx;font-weight:700;display:flex;align-items:center}
.dot{width:10rpx;height:28rpx;background:#1890ff;border-radius:5rpx;margin-right:12rpx;display:inline-block}
.panel-more{font-size:26rpx;color:#999}
.course-scroll{white-space:nowrap;margin:-12rpx}
.course-card{display:inline-block;width:260rpx;background:linear-gradient(135deg,#f8faff,#f0f5ff);border-radius:14rpx;padding:22rpx;margin:12rpx 16rpx 12rpx 0;vertical-align:top}
.course-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12rpx}
.course-name{font-size:28rpx;font-weight:700;white-space:normal;line-height:1.3}
.course-badge{background:#ff4d4f;color:#fff;font-size:18rpx;padding:2rpx 10rpx;border-radius:8rpx;flex-shrink:0;margin-left:8rpx}
.course-price{font-size:40rpx;font-weight:800;color:#ff4d4f;display:block}
.yen{font-size:24rpx}
.course-orig{font-size:22rpx;color:#bbb;text-decoration:line-through;display:block;margin-top:4rpx}
.coach-scroll{white-space:nowrap}
.coach-card{display:inline-block;width:180rpx;text-align:center;margin-right:24rpx}
.coach-avatar-wrap{width:120rpx;height:120rpx;border-radius:60rpx;margin:0 auto 12rpx;padding:4rpx;background:linear-gradient(135deg,#1890ff,#36cfc9)}
.coach-avatar{width:112rpx;height:112rpx;border-radius:56rpx;border:3rpx solid #fff}
.coach-name{font-size:28rpx;font-weight:600;display:block}
.coach-stars{margin:6rpx 0}
.coach-rate{font-size:22rpx;color:#fa8c16;margin-left:4rpx}
.coach-exp{font-size:22rpx;color:#999;display:block;white-space:normal;line-height:1.3}
.location-card{display:flex;align-items:center;padding:16rpx;background:#fafafa;border-radius:8rpx}
.loc-icon{font-size:36rpx;margin-right:16rpx}
.loc-info{flex:1}.loc-addr{font-size:28rpx;font-weight:500;display:block}.loc-tel{font-size:24rpx;color:#1890ff;margin-top:4rpx;display:block}
.loc-go{color:#999;font-size:24rpx}
.footer{text-align:center;padding:40rpx 20rpx 60rpx;color:#ccc;font-size:22rpx}
.footer-tel{display:block;color:#1890ff;margin-top:6rpx}
</style>
