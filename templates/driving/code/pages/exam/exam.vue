<template>
  <view class="page">
    <view class="mode-bar">
      <view class="mode" :class="{active:mode==='practice'}" @tap="mode='practice'">顺序练习</view>
      <view class="mode" :class="{active:mode==='exam'}" @tap="startExam">模拟考试</view>
      <view class="mode" :class="{active:mode==='wrong'}" @tap="mode='wrong'">错题本</view>
    </view>

    <!-- 顺序练习 -->
    <view v-if="mode==='practice' && questions.length">
      <view class="question-card" v-for="(q,i) in questions" :key="i" v-if="i===currentQ">
        <view class="q-num">第 {{i+1}}/{{questions.length}} 题</view>
        <view class="q-type" :class="q.type==='judge'?'judge':'single'">{{q.type==='judge'?'判断题':'单选题'}}</view>
        <view class="q-title">{{q.title}}</view>
        <image v-if="q.image" :src="q.image" mode="widthFix" class="q-image" />
        <view class="options">
          <view class="option" v-for="(o,k) in q.options" :key="k"
            :class="{correct:answered&&k===q.answer, wrong:answered&&k===userAnswer&&k!==q.answer}"
            @tap="!answered&&selectOption(k)">
            <text class="opt-label">{{k}}</text><text>{{o}}</text>
          </view>
        </view>
        <view class="explain" v-if="answered">
          <text class="result" :style="{color:userAnswer===q.answer?'#52c41a':'#ff4d4f'}">{{userAnswer===q.answer?'✓ 回答正确':'✗ 回答错误'}}</text>
          <text class="explain-text" v-if="q.explain">{{q.explain}}</text>
        </view>
      </view>
      <view class="nav-btns" v-if="answered">
        <button class="btn" @tap="prevQ" :disabled="currentQ===0">上一题</button>
        <button class="btn primary" :style="{background:theme.primaryColor}" @tap="nextQ">{{nextBtnText}}</button>
      </view>
    </view>

    <!-- 模拟考试 -->
    <view v-if="mode==='exam'">
      <view class="exam-header">
        <text class="timer">⏱ {{examTime}}</text>
        <text class="progress">{{answeredCount}}/{{examQuestions.length}}</text>
        <button class="submit-btn" size="mini" @tap="submitExam">交卷</button>
      </view>
      <view class="question-card" v-for="(q,i) in examQuestions" :key="i" v-if="i===examCurrent">
        <view class="q-num">第 {{i+1}}/{{examQuestions.length}} 题</view>
        <view class="q-title">{{q.title}}</view>
        <view class="options">
          <view class="option" v-for="(o,k) in q.options" :key="k" :class="{selected:examAnswers[i]===k}" @tap="examAnswers[i]=k;$set(examAnswers,i,k)">
            <text class="opt-label">{{k}}</text><text>{{o}}</text>
          </view>
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
  </view>
</template>
<script>
import config from '../../school.config.json'
const SAMPLE_QUESTIONS = [
  {type:'judge',title:'驾驶机动车在道路上违反交通安全法规的行为属于违法行为。',options:{A:'正确',B:'错误'},answer:'A',explain:'违反交通法规即构成违法行为。'},
  {type:'single',title:'机动车驾驶人造成事故后逃逸构成犯罪的，吊销驾驶证且多长时间不得重新取得驾驶证？',options:{A:'5年内',B:'10年内',C:'终生',D:'20年内'},answer:'C',explain:'造成事故后逃逸构成犯罪的，终生不得重新取得驾驶证。'},
  {type:'single',title:'在这段城市道路上行驶的最高速度不能超过多少？',image:'',options:{A:'30公里/小时',B:'40公里/小时',C:'50公里/小时',D:'70公里/小时'},answer:'A',explain:'城市道路无中心线限速30公里/小时。'},
  {type:'judge',title:'车辆在交叉路口绿灯亮后，遇非机动车抢道行驶时，可以不让行。',options:{A:'正确',B:'错误'},answer:'B',explain:'应礼让非机动车。'},
  {type:'single',title:'驾驶人连续驾驶不得超过多长时间？',options:{A:'4小时',B:'6小时',C:'8小时',D:'10小时'},answer:'A',explain:'连续驾驶不得超过4小时。'}
]
export default {
  data() { return { theme:config.school.theme, mode:'practice', questions:SAMPLE_QUESTIONS, currentQ:0, answered:false, userAnswer:null, wrongList:[], examQuestions:[], examCurrent:0, examAnswers:[], examTime:'45:00', examTimer:null } },
  computed: {
    nextBtnText() { return this.currentQ < this.questions.length - 1 ? '下一题' : '完成' },
    answeredCount() { return this.examAnswers.filter(Boolean).length }
  },
  methods: {
    selectOption(k){ this.userAnswer=k; this.answered=true; if(k!==this.questions[this.currentQ].answer&&!this.wrongList.find(w=>w.title===this.questions[this.currentQ].title)) this.wrongList.push(this.questions[this.currentQ]) },
    nextQ(){ if(this.currentQ<this.questions.length-1){ this.currentQ++; this.answered=false; this.userAnswer=null }else{ uni.showToast({title:'已完成所有题目！'}); this.currentQ=0; this.answered=false; this.userAnswer=null } },
    prevQ(){ if(this.currentQ>0){ this.currentQ--; const q=this.questions[this.currentQ]; this.answered=true; this.userAnswer=null } },
    startExam(){ this.mode='exam'; this.examQuestions=this.questions; this.examCurrent=0; this.examAnswers=Array(this.questions.length).fill(null); this.examTime='45:00'; let secs=2700; this.examTimer=setInterval(()=>{ secs--; const m=Math.floor(secs/60),s=secs%60; this.examTime=m+':'+(s<10?'0':'')+s; if(secs<=0){clearInterval(this.examTimer);this.submitExam()} },1000) },
    submitExam(){ clearInterval(this.examTimer); let score=0; this.examQuestions.forEach((q,i)=>{if(this.examAnswers[i]===q.answer)score++}); uni.showModal({title:'考试成绩',content:`正确 ${score}/${this.examQuestions.length} 题\n得分 ${Math.round(score/this.examQuestions.length*100)} 分`,success:()=>{this.mode='practice'} }) }
  }
}
</script>
<style scoped>
.page { padding-bottom: 200rpx; }
.mode-bar { display: flex; background: #fff; padding: 16rpx; border-radius: 12rpx; margin: 20rpx; }
.mode { flex: 1; text-align: center; padding: 16rpx; font-size: 28rpx; border-radius: 8rpx; color: #666; }
.mode.active { background: #1890ff; color: #fff; }
.question-card { background: #fff; margin: 20rpx; padding: 30rpx; border-radius: 16rpx; }
.q-num { font-size: 24rpx; color: #999; margin-bottom: 8rpx; }
.q-type { display: inline-block; padding: 4rpx 16rpx; border-radius: 8rpx; font-size: 22rpx; margin-bottom: 12rpx; }
.q-type.judge { background: #fff7e6; color: #fa8c16; }
.q-type.single { background: #e6f7ff; color: #1890ff; }
.q-title { font-size: 30rpx; font-weight: 500; line-height: 1.6; margin-bottom: 20rpx; }
.q-image { width: 100%; border-radius: 8rpx; margin-bottom: 20rpx; }
.option { padding: 20rpx; margin-bottom: 12rpx; border: 2rpx solid #eee; border-radius: 8rpx; font-size: 28rpx; display: flex; align-items: center; }
.option.selected { border-color: #1890ff; background: #f0f5ff; }
.option.correct { border-color: #52c41a; background: #f6ffed; }
.option.wrong { border-color: #ff4d4f; background: #fff2f0; }
.opt-label { width: 48rpx; height: 48rpx; border-radius: 24rpx; background: #f0f0f0; text-align: center; line-height: 48rpx; margin-right: 16rpx; font-size: 26rpx; flex-shrink: 0; }
.explain { margin-top: 16rpx; padding: 16rpx; background: #fafafa; border-radius: 8rpx; }
.result { font-size: 28rpx; font-weight: 600; display: block; }
.explain-text { font-size: 26rpx; color: #666; margin-top: 8rpx; display: block; }
.nav-btns { display: flex; gap: 20rpx; padding: 20rpx; }
.nav-btns button { flex: 1; }
.btn { border-radius: 40rpx; }
.btn.primary { color: #fff; }
.exam-header { display: flex; align-items: center; background: #fff; padding: 20rpx 30rpx; margin: 20rpx; border-radius: 12rpx; }
.timer { flex: 1; font-size: 32rpx; font-weight: 600; color: #ff4d4f; }
.progress { font-size: 28rpx; color: #666; margin-right: 20rpx; }
.empty { text-align: center; color: #999; padding: 100rpx 0; }
</style>
