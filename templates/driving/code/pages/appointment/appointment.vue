<template>
  <view class="page">
    <view class="section"><text class="title">选择日期</text>
      <scroll-view scroll-x class="date-list">
        <view class="date-item" v-for="(d,i) in dates" :key="i" :class="{active:selDate===i}" @tap="selDate=i">
          <text class="week">{{d.weekday}}</text><text class="day">{{d.date}}</text>
        </view></scroll-view></view>
    <view class="section" v-if="selDate!==null"><text class="title">选择时段</text>
      <view class="time-grid">
        <view class="time-item" v-for="(t,i) in currentSlots" :key="i" :class="{active:selTime===i, full:t.full}" @tap="!t.full&&(selTime=i)">
          <text>{{t.time}}</text><text class="remain" v-if="!t.full">余{{t.remain}}位</text><text class="full-text" v-else>已满</text>
        </view></view></view>
    <view class="section" v-if="selTime!==null"><text class="title">填写信息</text>
      <input class="inp" v-model="studentName" placeholder="姓名" /><input class="inp" v-model="studentPhone" placeholder="手机号" type="number" /></view>
    <view class="submit" v-if="studentName&&studentPhone"><button class="btn" :style="{background:theme.primaryColor}" @tap="submit">确认预约</button></view>
  </view></template>
<script>
import config from '../../school.config.json';
const TID = (config._meta && config._meta.tenantId) || '';
const API = (config._meta && config._meta.apiBase) || '';
function genStaticSlots(){var s=[];var weekdays=['日','一','二','三','四','五','六'];for(var d=0;d<7;d++){var now=new Date();var t=new Date(now.getTime()+d*86400000);var ds=(t.getMonth()+1)+'月'+t.getDate()+'日';var wd=weekdays[t.getDay()];['08:00-09:30','10:00-11:30','14:00-15:30','16:00-17:30','18:00-19:30'].forEach(function(tm){s.push({date:ds,weekday:wd,time:tm,full:Math.random()<0.2,remain:Math.floor(Math.random()*4)+1})})}return s;}
export default {
  data(){return{theme:config.school.theme,dates:[],selDate:null,selTime:null,currentSlots:[],studentName:'',studentPhone:''}},
  onLoad(){this.loadSlots()},
  methods:{
    loadSlots(){var s=this;var slots=genStaticSlots();var dm={};slots.forEach(function(sl){if(!dm[sl.date])dm[sl.date]=[];dm[sl.date].push(sl)});s.dates=Object.keys(dm).map(function(d){return{date:d,weekday:slots.find(function(x){return x.date===d}).weekday,slots:dm[d]}});},
    submit(){var s=this;var slot=s.currentSlots[s.selTime];var date=s.dates[s.selDate];uni.showToast({title:'预约成功！('+(date.date+' '+slot.time)+')',icon:'success'});setTimeout(function(){uni.navigateBack()},1500)}
  },
  watch:{selDate:function(i){if(i===null)return;this.selTime=null;this.currentSlots=this.dates[i].slots}}
}
</script>
