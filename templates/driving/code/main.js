import Vue from 'vue'
import App from './App'
import config from './school.config.json'

Vue.config.productionTip = false
Vue.prototype.$school = config.school
Vue.prototype.$courses = config.courses
Vue.prototype.$coaches = config.coaches
Vue.prototype.$features = config.features
Vue.prototype.$theme = config.school.theme

App.mpType = 'app'
const app = new Vue({ ...App })
app.$mount()
