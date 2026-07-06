<template>
  <view class="page">
    <!-- 日历 -->
    <view class="card">
      <view class="card-title">选择练车日期</view>
      <view class="calendar">
        <view class="cal-cell" v-for="(d,i) in dates" :key="i" :class="{active:selDate===i, today:d.isToday}" @tap="selDate=i">
          <text class="cal-week">{{d.weekday}}</text>
          <text class="cal-day">{{d.day}}</text>
          <view class="cal-dot" v-if="d.isToday"></view>
        </view>
      </view>
    </view>

    <!-- 时段 -->
    <view class="card" v-if="selDate!==null">
      <view class="card-title">{{dates[selDate].weekday}} {{dates[selDate].month}}月{{dates[selDate].day}}日 · 可选时段</view>
      <view class="time-grid">
        <view class="time-btn" v-for="(t,i) in currentSlots" :key="i" :class="{active:selTime===i, full:t.full}" @tap="!t.full&&(selTime=i)">
          <text class="time-label">{{t.time}}</text>
          <text class="time-sub" v-if="!t.full">剩余 {{t.remain}} 位</text>
          <text class="time-sub" v-else>已约满</text>
        </view>
      </view>
    </view>

    <!-- 信息 -->
    <view class="card" v-if="selTime!==null">
      <view class="card-title">填写个人信息</view>
      <input class="inp" v-model="studentName" placeholder="您的姓名" />
      <input class="inp" v-model="studentPhone" type="number" placeholder="手机号码" maxlength="11" />
      <input class="inp" v-model="remark" placeholder="备注（选填）" />
    </view>

    <!-- 确认 -->
    <view class="bottom" v-if="studentName&&studentPhone">
      <view class="summary">
        <text>{{dates[selDate].weekday}} {{dates[selDate].month}}/{{dates[selDate].day}} · {{currentSlots[selTime].time}}</text>
      </view>
      <button class="btn" :style="{background:theme.primaryColor}" @tap="submit">确认预约</button>
    </view>
  </view>
</template>

<script>
import config from '../../school.config.json';
var TID=(config._meta&&config._meta.tenantId)||'',API=(config._meta&&config._meta.apiBase)||'';
function getJSON(p){return new Promise(function(r){uni.request({url:API+'/api/public/'+TID+'/'+p,success:function(res){r(res.data)},fail:function(){r(null)}})});}
function genSlots(settings){
  var adv=settings.advance_days||7,caps=settings.capacity||3,slots=settings.time_slots||['08:00-10:00','10:00-12:00','14:00-16:00','16:00-18:00'];
  var s=[],wd=['周日','周一','周二','周三','周四','周五','周六'];
  for(var d=0;d<adv;d++){
    var t=new Date(Date.now()+d*86400000),m=t.getMonth()+1,dd=t.getDate(),isToday=d===0;
    slots.forEach(function(tm){s.push({month:m,day:dd,weekday:wd[t.getDay()],isToday:isToday,time:tm,full:false,remain:caps})});
  }
  return s;
}
export default {
  data(){return{theme:config.school.theme,dates:[],selDate:null,selTime:null,currentSlots:[],studentName:'',studentPhone:'',remark:''}},
  onLoad(){this.buildCalendar()},
  methods:{
    buildCalendar(){
      var s=this;getJSON('appointment-settings').then(function(st){
        if(!st)st={advance_days:7,time_slots:['08:00-10:00','10:00-12:00','14:00-16:00','16:00-18:00'],capacity:3};
        var slots=genSlots(st),dm={};
        slots.forEach(function(sl){var k=sl.month+'-'+sl.day;if(!dm[k])dm[k]=[];dm[k].push(sl)});
        s.dates=Object.keys(dm).map(function(k){var p=k.split('-');return{month:parseInt(p[0]),day:parseInt(p[1]),weekday:dm[k][0].weekday,isToday:dm[k][0].isToday,slots:dm[k]}});
      });
    },
    submit(){
      var s=this,d=s.dates[s.selDate],t=s.currentSlots[s.selTime];
      uni.showToast({title:'预约成功',icon:'success'});setTimeout(function(){uni.navigateBack()},1500);
    }
  },
  watch:{selDate:function(i){if(i===null)return;this.selTime=null;this.currentSlots=this.dates[i].slots}}
}
</script>

<style scoped>
.page{padding:20rpx;padding-bottom:200rpx}
.card{background:#fff;border-radius:16rpx;padding:28rpx;margin-bottom:20rpx;box-shadow:0 2rpx 12rpx rgba(0,0,0,.03)}
.card-title{font-size:30rpx;font-weight:700;margin-bottom:20rpx}
.calendar{display:flex;justify-content:space-between}
.cal-cell{display:flex;flex-direction:column;align-items:center;width:84rpx;padding:16rpx 0;border-radius:16rpx;position:relative}
.cal-cell.active{background:#f0f5ff}.cal-cell.active .cal-day{color:#1890ff;font-weight:800}
.cal-week{font-size:22rpx;color:#999;margin-bottom:10rpx}
.cal-day{font-size:34rpx;font-weight:600;color:#333}
.cal-dot{width:8rpx;height:8rpx;border-radius:4rpx;background:#1890ff;margin-top:8rpx}
.time-grid{display:flex;flex-wrap:wrap;gap:16rpx}
.time-btn{flex:0 0 calc(50% - 8rpx);text-align:center;padding:24rpx 16rpx;border-radius:14rpx;border:2rpx solid #eee;background:#fff}
.time-btn.active{border-color:#1890ff;background:#f0f5ff}.time-btn.full{background:#f8f8f8;border-color:#f0f0f0}
.time-label{display:block;font-size:30rpx;font-weight:600}.time-sub{display:block;font-size:22rpx;color:#999;margin-top:6rpx}
.inp{width:100%;padding:22rpx 0;border-bottom:1px solid #f0f0f0;font-size:28rpx;margin-bottom:4rpx}
.inp:last-child{border-bottom:none}
.bottom{position:fixed;bottom:0;left:0;right:0;background:#fff;padding:16rpx 30rpx;padding-bottom:calc(16rpx + env(safe-area-inset-bottom));box-shadow:0 -2rpx 16rpx rgba(0,0,0,.04);z-index:10}
.summary{font-size:26rpx;color:#666;margin-bottom:12rpx;text-align:center}
.btn{width:100%;color:#fff;border-radius:50rpx;height:92rpx;line-height:92rpx;font-size:32rpx;font-weight:600}
</style>
