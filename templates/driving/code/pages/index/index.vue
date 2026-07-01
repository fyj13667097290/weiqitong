<template>
  <view class="page">
    <view class="header" :style="{background: theme.primaryColor}">
      <image class="logo" :src="school.logo" mode="aspectFit" v-if="school.logo" />
      <text class="school-name">{{school.name}}</text>
      <text class="school-desc" v-if="school.description">{{school.description}}</text>
      <view class="header-stats">
        <view class="stat-item"><text class="stat-num">{{allCoaches.length}}</text><text class="stat-label">位教练</text></view>
        <view class="stat-item"><text class="stat-num">{{allCourses.length}}</text><text class="stat-label">种课程</text></view>
        <view class="stat-item"><text class="stat-num">4.8</text><text class="stat-label">分好评</text></view>
      </view>
    </view>

    <view class="notice-bar" v-if="announcements.length" @tap="showNotice">
      <text class="notice-icon">📢</text>
      <text class="notice-text">{{announcements[0].title}}</text>
    </view>

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
    </view>

    <view class="section" v-if="allCourses.length">
      <view class="section-title"><text>热门课程</text><text class="more" @tap="goCourses">全部 ></text></view>
      <view class="course-card" v-for="(c,i) in allCourses.slice(0,3)" :key="i">
        <view class="course-tag" v-if="c.tag">{{c.tag}}</view>
        <text class="course-name">{{c.name}}</text>
        <view class="course-price"><text class="price">¥{{c.price}}</text><text class="original" v-if="c.originalPrice||c.original_price">¥{{c.originalPrice||c.original_price}}</text></view>
      </view>
    </view>

    <view class="section" v-if="allCoaches.length">
      <view class="section-title"><text>金牌教练</text><text class="more" @tap="goCoaches">全部 ></text></view>
      <scroll-view scroll-x class="coach-scroll">
        <view class="coach-card" v-for="(c,i) in allCoaches.slice(0,6)" :key="i">
          <image class="coach-avatar" :src="c.avatar || '/static/default-avatar.png'" mode="aspectFill" />
          <text class="coach-name">{{c.name}}</text>
          <text class="coach-exp">{{c.experience}}年教龄</text>
        </view>
      </scroll-view>
    </view>

    <view class="section" v-if="school.address">
      <view class="section-title"><text>训练场地</text></view>
      <view class="location-card" @tap="goMap">
        <text class="loc-name">{{school.address}}</text>
        <text class="loc-phone">{{school.phone}}</text>
      </view>
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
