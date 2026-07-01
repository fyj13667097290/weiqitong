<template>
  <view class="page">
    <view class="section">
      <text class="title">选择日期</text>
      <scroll-view scroll-x class="date-list">
        <view class="date-item" v-for="(d,i) in dates" :key="i" :class="{active:selDate===i}" @tap="selDate=i">
          <text class="week">{{d.weekday}}</text>
          <text class="day">{{d.date}}</text>
        </view>
      </scroll-view>
    </view>

    <view class="section" v-if="selDate!==null">
      <text class="title">选择时段</text>
      <view class="time-grid">
        <view class="time-item" v-for="(t,i) in currentSlots" :key="i" :class="{active:selTime===i, full:t.full}" @tap="!t.full&&(selTime=i)">
          <text>{{t.time}}</text>
          <text class="remain" v-if="!t.full">余{{t.remain}}位</text>
          <text class="full-text" v-else>已满</text>
        </view>
      </view>
    </view>

    <view class="section" v-if="selTime!==null">
      <text class="title">填写信息</text>
      <input class="inp" v-model="studentName" placeholder="姓名" />
      <input class="inp" v-model="studentPhone" placeholder="手机号" type="number" />
    </view>

    <view class="submit" v-if="studentName&&studentPhone">
      <button class="btn" :style="{background:theme.primaryColor}" @tap="submit">确认预约</button>
    </view>
  </view>
</template>
<script>
import config from '../../school.config.json';
const TID = (config._meta && config._meta.tenantId) || '';
const API = (config._meta && config._meta.apiBase) || '';
function getList(p){ return new Promise(function(resolve){ uni.request({url:API+'/api/public/'+TID+'/'+p,success:function(r){resolve(r.data)},fail:function(){resolve([])}}); }); }
export default {
  data() { return { theme:config.school.theme, dates:[], selDate:null, selTime:null, currentSlots:[], studentName:'', studentPhone:'' }; },
  onLoad(){ this.loadSlots(); },
  methods: {
    loadSlots(){
      var s=this;
      getList('coach-slots').then(function(r){
        if(!r.length) return;
        var dateMap={}; r.forEach(function(sl){
          if(!dateMap[sl.date]) dateMap[sl.date]=[];
          dateMap[sl.date].push(sl);
        });
        s.dates=Object.keys(dateMap).map(function(d){ return {date:d,weekday:r.find(function(x){return x.date===d}).weekday,slots:dateMap[d]}; });
      });
    },
    submit(){
      var s=this; var slot=s.currentSlots[s.selTime]; var date=s.dates[s.selDate];
      uni.request({url:API+'/api/public/'+TID+'/appointments',method:'POST',data:{
        student_name:s.studentName,student_phone:s.studentPhone,
        appointment_time:date.date+' '+slot.time, course_type:'练车'
      },success:function(r){
        if(r.data.ok){ uni.showToast({title:'预约成功！',icon:'success'}); setTimeout(function(){uni.navigateBack()},1500); }
        else uni.showToast({title:r.data.message||'预约失败',icon:'none'});
      },fail:function(){ uni.showToast({title:'网络错误',icon:'none'}); }});
    }
  },
  watch: {
    selDate: function(i){
      if(i===null) return; this.selTime=null; this.currentSlots=this.dates[i].slots;
    }
  }
}
</script>
<style scoped>
.page{padding:20rpx;padding-bottom:200rpx}
.section{background:#fff;border-radius:16rpx;padding:24rpx;margin-bottom:20rpx}
.title{font-size:30rpx;font-weight:600;margin-bottom:16rpx;display:block}
.date-list{white-space:nowrap}
.date-item{display:inline-block;text-align:center;width:100rpx;padding:16rpx 0;border-radius:12rpx;margin-right:12rpx;border:2rpx solid #eee}
.date-item.active{border-color:#1890ff;background:#f0f5ff}
.week{font-size:24rpx;color:#999;display:block}.day{font-size:28rpx;font-weight:600;margin-top:4rpx;display:block}
.time-grid{display:flex;flex-wrap:wrap;gap:16rpx}
.time-item{flex:0 0 calc(50% - 8rpx);text-align:center;padding:20rpx;border-radius:12rpx;border:2rpx solid #eee}
.time-item.active{border-color:#1890ff;background:#f0f5ff}.time-item.full{background:#f5f5f5;opacity:.6}
.time-item text:first-child{font-size:28rpx;font-weight:500;display:block}
.remain{font-size:22rpx;color:#52c41a}.full-text{font-size:22rpx;color:#999}
.inp{width:100%;padding:20rpx;border:1px solid #eee;border-radius:8rpx;font-size:28rpx;margin-bottom:16rpx}
.submit{padding:20rpx}
.btn{color:#fff;border-radius:40rpx;height:88rpx;line-height:88rpx;font-size:32rpx}
</style>
