<template>
  <view class="page">
    <!-- 选择教练 -->
    <view class="section">
      <text class="title">选择教练</text>
      <scroll-view scroll-x class="coach-list">
        <view class="coach-item" v-for="(c,i) in coaches" :key="i" :class="{active:selCoach===i}" @tap="selCoach=i">
          <image :src="c.avatar||'/static/default-avatar.png'" mode="aspectFill" class="coach-img" />
          <text>{{c.name}}</text>
        </view>
      </scroll-view>
    </view>

    <!-- 选择日期 -->
    <view class="section">
      <text class="title">选择日期</text>
      <scroll-view scroll-x class="date-list">
        <view class="date-item" v-for="(d,i) in dates" :key="i" :class="{active:selDate===i}" @tap="selDate=i">
          <text class="week">{{d.week}}</text>
          <text class="day">{{d.day}}</text>
        </view>
      </scroll-view>
    </view>

    <!-- 选择时段 -->
    <view class="section" v-if="selCoach!==null && selDate!==null">
      <text class="title">选择时段</text>
      <view class="time-grid">
        <view class="time-item" v-for="(t,i) in timeSlots" :key="i" :class="{active:selTime===i, full:t.full}" @tap="!t.full && (selTime=i)">
          <text>{{t.label}}</text>
          <text class="remain" v-if="!t.full">余{{t.remain}}位</text>
          <text class="full-text" v-else>已满</text>
        </view>
      </view>
    </view>

    <!-- 预约按钮 -->
    <view class="submit" v-if="selTime!==null">
      <view class="summary">
        <text>教练：{{coaches[selCoach].name}}</text>
        <text>时间：{{dates[selDate].full}} {{timeSlots[selTime].label}}</text>
      </view>
      <button class="btn" :style="{background:theme.primaryColor}" @tap="submit">确认预约</button>
    </view>
  </view>
</template>
<script>
import config from '../../school.config.json'
export default {
  data() {
    const dates = []; const now = new Date();
    for(let i=0;i<7;i++){ const d=new Date(now.getTime()+i*86400000); dates.push({week:['日','一','二','三','四','五','六'][d.getDay()],day:d.getDate(),full:d.getMonth()+1+'月'+d.getDate()+'日'}) }
    return { coaches: config.coaches, theme: config.school.theme, dates, selCoach: null, selDate: null, selTime: null,
      timeSlots: [{label:'08:00-09:30',remain:3,full:false},{label:'10:00-11:30',remain:2,full:false},{label:'14:00-15:30',remain:0,full:true},{label:'16:00-17:30',remain:4,full:false},{label:'18:00-19:30',remain:1,full:false}] }
  },
  methods: {
    submit() {
      const t = this; uni.showModal({title:'确认预约',content:`${t.coaches[t.selCoach].name}\n${t.dates[t.selDate].full} ${t.timeSlots[t.selTime].label}`,success(r){
        if(r.confirm){ uni.showToast({title:'预约成功！',icon:'success'}); setTimeout(()=>uni.navigateBack(),1500) }
      }})
    }
  }
}
</script>
<style scoped>
.page { padding: 20rpx; padding-bottom: 200rpx; }
.section { background: #fff; border-radius: 16rpx; padding: 24rpx; margin-bottom: 20rpx; }
.title { font-size: 30rpx; font-weight: 600; margin-bottom: 16rpx; display: block; }
.coach-list { white-space: nowrap; }
.coach-item { display: inline-block; text-align: center; width: 140rpx; padding: 12rpx; border-radius: 12rpx; margin-right: 16rpx; border: 2rpx solid transparent; }
.coach-item.active { border-color: #1890ff; background: #f0f5ff; }
.coach-img { width: 80rpx; height: 80rpx; border-radius: 40rpx; display: block; margin: 0 auto 8rpx; }
.coach-item text { font-size: 26rpx; }
.date-list { white-space: nowrap; }
.date-item { display: inline-block; text-align: center; width: 100rpx; padding: 16rpx 0; border-radius: 12rpx; margin-right: 12rpx; border: 2rpx solid #eee; }
.date-item.active { border-color: #1890ff; background: #f0f5ff; }
.week { font-size: 24rpx; color: #999; display: block; }
.day { font-size: 32rpx; font-weight: 600; margin-top: 4rpx; }
.time-grid { display: flex; flex-wrap: wrap; gap: 16rpx; }
.time-item { flex: 0 0 calc(50% - 8rpx); text-align: center; padding: 20rpx; border-radius: 12rpx; border: 2rpx solid #eee; }
.time-item.active { border-color: #1890ff; background: #f0f5ff; }
.time-item.full { background: #f5f5f5; opacity: .6; }
.time-item text:first-child { font-size: 28rpx; font-weight: 500; display: block; }
.remain { font-size: 22rpx; color: #52c41a; }
.full-text { font-size: 22rpx; color: #999; }
.submit { position: fixed; bottom: 0; left: 0; right: 0; background: #fff; padding: 20rpx 30rpx; box-shadow: 0 -2rpx 20rpx rgba(0,0,0,.06); }
.summary { margin-bottom: 16rpx; display: flex; justify-content: space-between; font-size: 26rpx; color: #666; }
.btn { color: #fff; border-radius: 40rpx; height: 88rpx; line-height: 88rpx; font-size: 32rpx; }
</style>
