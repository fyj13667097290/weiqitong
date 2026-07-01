<template>
  <view class="page">
    <view class="mode-bar">
      <view class="mode" :class="{active:mode==='practice'}" @tap="startPractice">顺序练习</view>
      <view class="mode" :class="{active:mode==='exam'}" @tap="startExam">模拟考试</view>
      <view class="mode" :class="{active:mode==='wrong'}" @tap="mode='wrong'">错题本</view>
    </view>

    <!-- 顺序练习 -->
    <view v-if="mode==='practice' && questions.length">
      <view class="question-card" v-for="(q,i) in questions" :key="i" v-if="i===currentQ">
        <view class="q-num">第 {{i+1}}/{{questions.length}} 题</view>
        <view class="q-type" :class="q.type==='judge'?'judge':'single'">{{q.type==='judge'?'判断题':'单选题'}}</view>
        <view class="q-title">{{q.title}}</view>
        <view class="options">
          <view class="option" v-for="(o,k) in ['A','B','C','D']" :key="k" v-if="q['option_'+k.toLowerCase()]"
            :class="{correct:answered&&k===correctAnswer, wrong:answered&&k===userAnswer&&k!==correctAnswer}"
            @tap="!answered&&selectOption(k)">
            <text class="opt-label">{{k}}</text><text>{{q['option_'+k.toLowerCase()]}}</text>
          </view>
        </view>
        <view class="explain" v-if="answered">
          <text class="result" :style="{color:userAnswer===correctAnswer?'#52c41a':'#ff4d4f'}">{{userAnswer===correctAnswer?'✓ 正确':'✗ 错误'}}</text>
          <text class="explain-text" v-if="correctExplain">{{correctExplain}}</text>
        </view>
      </view>
      <view class="nav-btns" v-if="answered">
        <button class="btn" @tap="prevQ" :disabled="currentQ===0">上一题</button>
        <button class="btn primary" :style="{background:theme.primaryColor}" @tap="nextQ">{{nextBtnText}}</button>
      </view>
    </view>

    <!-- 模拟考试 -->
    <view v-if="mode==='exam' && examList.length">
      <view class="exam-header">
        <text class="timer">⏱ {{examTime}}</text>
        <text class="progress">{{answeredCount}}/{{examList.length}}</text>
        <button class="submit-btn" size="mini" @tap="submitExam">交卷</button>
      </view>
      <view class="question-card" v-for="(q,i) in examList" :key="i" v-if="i===examCurrent">
        <view class="q-num">第 {{i+1}}/{{examList.length}} 题</view>
        <view class="q-title">{{q.title}}</view>
        <view class="options">
          <view class="option" v-for="(o,k) in ['A','B','C','D']" :key="k" v-if="q['option_'+k.toLowerCase()]"
            :class="{selected:examAnswers[i]===k}" @tap="examAnswers[i]=k;$set(examAnswers,i,k)">
            <text class="opt-label">{{k}}</text><text>{{q['option_'+k.toLowerCase()]}}</text>
          </view>
        </view>
        <view class="nav-btns">
          <button class="btn" @tap="examCurrent=Math.max(0,examCurrent-1)" :disabled="examCurrent===0">上一题</button>
          <button class="btn primary" :style="{background:theme.primaryColor}" @tap="examCurrent=Math.min(examList.length-1,examCurrent+1)">{{examCurrent<examList.length-1?'下一题':'返回首题'}}</button>
        </view>
      </view>
    </view>

    <!-- 错题本 -->
    <view v-if="mode==='wrong'">
      <view v-if="wrongList.length===0" class="empty">暂无错题，继续保持！</view>
      <view class="question-card" v-for="(q,i) in wrongList" :key="i">
        <view class="q-title">{{q.title}}</view>
        <view class="explain"><text class="explain-text">{{q.explain}}</text></view>
      </view>
    </view>

    <view class="loading" v-if="loading">加载题库中...</view>
  </view>
</template>
<script>
import config from '../../school.config.json';
const TID = (config._meta && config._meta.tenantId) || '';
const API = (config._meta && config._meta.apiBase) || '';
function getList(p){ return new Promise(function(resolve){ uni.request({url:API+'/api/public/'+TID+'/'+p,success:function(r){resolve(r.data)},fail:function(){resolve([])}}); }); }
export default {
  data() { return { theme:config.school.theme, mode:'practice', questions:[], currentQ:0, answered:false, userAnswer:null, correctAnswer:null, correctExplain:'', wrongList:[], examList:[], examCurrent:0, examAnswers:[], examTime:'45:00', examTimer:null, loading:true }; },
  computed: {
    nextBtnText(){ return this.currentQ<this.questions.length-1?'下一题':'完成'; },
    answeredCount(){ return this.examAnswers.filter(Boolean).length; }
  },
  onLoad(){ this.fetchQuestions(); },
  methods: {
    fetchQuestions(){
      var s=this; s.loading=true;
      getList('exam-questions').then(function(r){
        s.questions=r.length?r:[];
        s.loading=false;
        if(!r.length)uni.showToast({title:'暂无题库数据',icon:'none'});
      });
    },
    startPractice(){ this.mode='practice'; this.currentQ=0; this.answered=false; this.userAnswer=null; if(!this.questions.length)this.fetchQuestions(); },
    selectOption(k){ this.userAnswer=k; this.answered=true; this.correctAnswer=this.questions[this.currentQ].answer; this.correctExplain=this.questions[this.currentQ].explain||''; if(k!==this.correctAnswer){ var q=this.questions[this.currentQ]; var exists=this.wrongList.some(function(w){return w.title===q.title}); if(!exists)this.wrongList.push(q); } },
    nextQ(){ if(this.currentQ<this.questions.length-1){ this.currentQ++; this.answered=false; this.userAnswer=null; this.correctAnswer=null; this.correctExplain=''; }else{ uni.showToast({title:'已完成所有题目！'}); this.currentQ=0; this.answered=false; } },
    prevQ(){ if(this.currentQ>0){ this.currentQ--; var q=this.questions[this.currentQ]; this.answered=true; this.userAnswer=null; } },
    startExam(){ this.mode='exam'; if(!this.questions.length)this.fetchQuestions(); var s=this; setTimeout(function(){ s.examList=s.questions.slice(0,Math.min(100,s.questions.length)); s.examCurrent=0; s.examAnswers=Array(s.examList.length).fill(null); s.examTime='45:00'; var secs=2700; s.examTimer=setInterval(function(){ secs--; var m=Math.floor(secs/60),sec=secs%60; s.examTime=m+':'+(sec<10?'0':'')+sec; if(secs<=0){clearInterval(s.examTimer);s.submitExam();} },1000); },500); },
    submitExam(){ clearInterval(this.examTimer); var s=this, score=0; this.examList.forEach(function(q,i){ if(s.examAnswers[i]===q.answer)score++; }); var total=this.examList.length; uni.showModal({title:'考试成绩',content:'正确 '+score+'/'+total+' 题\\n得分 '+Math.round(score/total*100)+' 分',success:function(){s.mode='practice';} }); }
  }
}
</script>
<style scoped>
.page{padding-bottom:200rpx}
.mode-bar{display:flex;background:#fff;padding:16rpx;border-radius:12rpx;margin:20rpx}
.mode{flex:1;text-align:center;padding:16rpx;font-size:28rpx;border-radius:8rpx;color:#666}
.mode.active{background:#1890ff;color:#fff}
.question-card{background:#fff;margin:20rpx;padding:30rpx;border-radius:16rpx}
.q-num{font-size:24rpx;color:#999;margin-bottom:8rpx}
.q-type{display:inline-block;padding:4rpx 16rpx;border-radius:8rpx;font-size:22rpx;margin-bottom:12rpx}
.judge{background:#fff7e6;color:#fa8c16}.single{background:#e6f7ff;color:#1890ff}
.q-title{font-size:30rpx;font-weight:500;line-height:1.6;margin-bottom:20rpx}
.option{padding:20rpx;margin-bottom:12rpx;border:2rpx solid #eee;border-radius:8rpx;font-size:28rpx;display:flex;align-items:center}
.option.selected{border-color:#1890ff;background:#f0f5ff}
.option.correct{border-color:#52c41a;background:#f6ffed}
.option.wrong{border-color:#ff4d4f;background:#fff2f0}
.opt-label{width:48rpx;height:48rpx;border-radius:24rpx;background:#f0f0f0;text-align:center;line-height:48rpx;margin-right:16rpx;font-size:26rpx;flex-shrink:0}
.explain{margin-top:16rpx;padding:16rpx;background:#fafafa;border-radius:8rpx}
.result{font-size:28rpx;font-weight:600;display:block}
.explain-text{font-size:26rpx;color:#666;margin-top:8rpx;display:block}
.nav-btns{display:flex;gap:20rpx;padding:20rpx}
.nav-btns button{flex:1}
.btn{border-radius:40rpx}.btn.primary{color:#fff}
.exam-header{display:flex;align-items:center;background:#fff;padding:20rpx 30rpx;margin:20rpx;border-radius:12rpx}
.timer{flex:1;font-size:32rpx;font-weight:600;color:#ff4d4f}
.progress{font-size:28rpx;color:#666;margin-right:20rpx}
.empty{text-align:center;color:#999;padding:100rpx 0}
.loading{text-align:center;color:#999;padding:100rpx 0}
</style>
