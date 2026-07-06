<template><view class="page">
<view class="card"><text class="title">选择日期</text>
<view style="padding:10rpx 0;font-size:22rpx;color:#ff4d4f">平日¥188 周末¥268 节假日¥388</view>
<scroll-view scroll-x class="date-list"><view class="date-item" v-for="(d,i) in dates" :key="i" :class="{active:selDate===i}" @tap="selDate=i"><text class="week">{{d.weekday}}</text><text class="day">{{d.month}}/{{d.day}}</text></view></scroll-view></view>
<view class="card" v-if="selDate!==null"><text class="title">选择时段</text>
<view class="time-grid"><view class="time-btn" v-for="(t,i) in timeSlots" :key="i" :class="{active:selTime===i}" @tap="selTime=i"><text>{{t}}</text></view></view></view>
<view class="card" v-if="selTime!==null"><text class="title">填写信息</text>
