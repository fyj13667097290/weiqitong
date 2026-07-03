import Vue from 'vue';import App from './App';import config from './school.config.json';
Vue.config.productionTip=false;Vue.prototype.$shop=config.shop;Vue.prototype.$theme=config.shop.theme;
App.mpType='app';const app=new Vue({...App});app.$mount();
