import type { BookingOrder, DiscoverQuery, MarketPost, Photographer, WorkCard } from '../types'
import { isRemoteImage, makeAvatar } from '../utils/avatar'
import { localWorkUrl, spiralUrl } from '../utils/media'

export const works: WorkCard[] = [
  {
    id: 'w-001', imageUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=900&q=86',
    title: '灯笼落在肩上', photographerId: 'p-001', photographerName: '林初禾', photographerAvatar: 'https://i.pravatar.cc/96?img=47',
    location: '西安 · 小寨', city: '西安', styles: ['古风', '夜景', '人像'], shootDate: '周六 18:00 后', canBook: true,
    matchReason: '命中：夜景、灯笼、古风；周六在小寨附近有档期', accent: '#db6c4d'
  },
  {
    id: 'w-002', imageUrl: 'https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=900&q=86',
    title: '风从城墙边经过', photographerId: 'p-002', photographerName: '赵野', photographerAvatar: 'https://i.pravatar.cc/96?img=12',
    location: '西安 · 城墙南门', city: '西安', styles: ['纪实', '胶片', '城市'], shootDate: '周六全天', canBook: true,
    matchReason: '命中：城墙、自然光；周六全天可到场', accent: '#738b8c'
  },
  {
    id: 'w-003', imageUrl: 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=900&q=86',
    title: '红墙边的半分钟', photographerId: 'p-003', photographerName: '周末', photographerAvatar: 'https://i.pravatar.cc/96?img=32',
    location: '西安 · 大雁塔', city: '西安', styles: ['汉服', '暖调', '人像'], shootDate: '周日 09:00—13:00', canBook: true,
    matchReason: '命中：汉服、暖调；周日在大雁塔有空档', accent: '#b38865'
  },
  {
    id: 'w-004', imageUrl: 'https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?auto=format&fit=crop&w=900&q=86',
    title: '把风留在海边', photographerId: 'p-001', photographerName: '林初禾', photographerAvatar: 'https://i.pravatar.cc/96?img=47',
    location: '青岛 · 小麦岛', city: '青岛', styles: ['日系', '海边', '轻旅拍'], shootDate: '下周五可约', canBook: true,
    matchReason: '命中：海边、轻旅拍；已打开跨城档期', accent: '#7b9ca0'
  },
  {
    id: 'w-005', imageUrl: 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=900&q=86',
    title: '一束光的肖像', photographerId: 'p-002', photographerName: '赵野', photographerAvatar: 'https://i.pravatar.cc/96?img=12',
    location: '西安 · 曲江', city: '西安', styles: ['肖像', '自然光', '低饱和'], shootDate: '周六 15:00 后', canBook: true,
    matchReason: '命中：自然光、肖像；周六下午可约', accent: '#9c7963'
  },
  {
    id: 'w-006', imageUrl: 'https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?auto=format&fit=crop&w=900&q=86',
    title: '回到街角', photographerId: 'p-003', photographerName: '周末', photographerAvatar: 'https://i.pravatar.cc/96?img=32',
    location: '成都 · 玉林', city: '成都', styles: ['街拍', '复古', '生活感'], shootDate: '本周日可约', canBook: false,
    matchReason: '命中：街拍、复古；当前档期已接近满档', accent: '#9a6f6d'
  }
]

const cyrusWorks: WorkCard[] = [
  { id: 'cyrus-001', imageUrl: localWorkUrl('baea7746e45f670df9e27e388077b86d.jpg'), title: '围栏边的短暂停留', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 校园球场', city: '北京', styles: ['蓝调', '纪实', '低饱和'], types: ['人像', '街头'], device: '小米 15', shootDate: '作品集 · 现场记录', canBook: false, matchReason: '蓝调纪实的人像记录', accent: '#7281a0' },
  { id: 'cyrus-002', imageUrl: localWorkUrl('09ff6d2517085a76ef74c580d8cca1b5.jpg'), title: '秋色从树梢落下来', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 秋日公园', city: '北京', styles: ['秋色', '暖调', '自然'], types: ['风景', '植物'], device: '小米 15', shootDate: '作品集 · 秋日散步', canBook: false, matchReason: '暖色秋叶与自然光', accent: '#b4753e' },
  { id: 'cyrus-003', imageUrl: localWorkUrl('4c70462bcc53c43cd1775790a5007ff4.jpg'), title: '夜场散场前', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 夜间活动', city: '北京', styles: ['蓝调', '夜景', '纪实'], types: ['人像', '活动'], device: '小米 15', shootDate: '作品集 · 夜间现场', canBook: false, matchReason: '蓝调夜景中的群像叙事', accent: '#667caa' },
  { id: 'cyrus-004', imageUrl: localWorkUrl('f1c5fff349cb2c7cd9457320c67191f5.jpg'), title: '在人群里看向镜头', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 活动现场', city: '北京', styles: ['蓝调', '纪实', '群像'], types: ['人像', '团体'], device: '小米 15', shootDate: '作品集 · 活动记录', canBook: false, matchReason: '自然抓拍与多人关系', accent: '#687ba7' },
  { id: 'cyrus-005', imageUrl: localWorkUrl('ce7a48ecb84d87ef131cf5f4502a2825.jpg'), title: '树影框住古建', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 颐和园', city: '北京', styles: ['古典', '旅行', '框景'], types: ['建筑', '风景'], device: '小米 15', shootDate: '作品集 · 古建漫游', canBook: false, matchReason: '树影与古建的层次构图', accent: '#788f8a' },
  { id: 'cyrus-006', imageUrl: localWorkUrl('9e891167f97b19510a05cccde75dab8d.jpg'), title: '湖面尽头的长廊', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 颐和园', city: '北京', styles: ['旅行', '古典', '留白'], types: ['建筑', '风景'], device: '小米 15', shootDate: '作品集 · 湖畔建筑', canBook: false, matchReason: '留白构图与皇家园林', accent: '#87969a' },
  { id: 'cyrus-007', imageUrl: localWorkUrl('f2a67ba078c0756eb13714a8fb1f1a10.jpg'), title: '佛香阁与树梢', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 颐和园', city: '北京', styles: ['暗调', '古典', '建筑线条'], types: ['建筑'], device: '小米 15', shootDate: '作品集 · 建筑观察', canBook: false, matchReason: '暗部层次与建筑轮廓', accent: '#5e6e66' },
  { id: 'cyrus-008', imageUrl: localWorkUrl('d72eaf69ab2b3a9ccdc3289d2e3976c1.jpg'), title: '城墙与侧脸', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 景山', city: '北京', styles: ['环境人像', '旅行', '留白'], types: ['人像', '建筑'], device: '小米 15', shootDate: '作品集 · 旅行肖像', canBook: false, matchReason: '人物与城市风景的同框', accent: '#8798a4' },
  { id: 'cyrus-009', imageUrl: localWorkUrl('5461bea0fe26dad034e9fc7e11de7552.jpg'), title: '荷叶边的夏日肖像', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 北海公园', city: '北京', styles: ['日系', '自然光', '清新'], types: ['人像', '风景'], device: '小米 15', shootDate: '作品集 · 夏日公园', canBook: false, matchReason: '自然光下的松弛人像', accent: '#6f8f86' },
  { id: 'cyrus-010', imageUrl: localWorkUrl('6383584ebff23e0a46860c6483194e6a.jpg'), title: '门与远山', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 故宫角楼', city: '北京', styles: ['对称', '旅行', '纪实'], types: ['建筑'], device: '小米 15', shootDate: '作品集 · 城市旅行', canBook: false, matchReason: '对称门洞与远景层次', accent: '#7f846e' },
  { id: 'cyrus-011', imageUrl: localWorkUrl('3afd6b04671d1fb4319886fbb35bc183.jpg'), title: '藻井的旋转秩序', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 古建筑内部', city: '北京', styles: ['对称', '色彩', '细节'], types: ['建筑', '细节'], device: '小米 15', shootDate: '作品集 · 建筑细节', canBook: false, matchReason: '向心构图与传统彩绘', accent: '#8f7c63' },
  { id: 'cyrus-012', imageUrl: localWorkUrl('3c6015483e7d968f48e7d13588dc6487.jpg'), title: '红墙前的旅人', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 故宫', city: '北京', styles: ['旅行', '人文', '暖调'], types: ['人像', '建筑'], device: '小米 15', shootDate: '作品集 · 旅行人像', canBook: false, matchReason: '人物与红墙的色彩呼应', accent: '#b98163' },
  { id: 'cyrus-013', imageUrl: localWorkUrl('ccb5977eb0044804f78505c99bccb2c9.jpg'), title: '旗帜与城门', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 天安门', city: '北京', styles: ['纪实', '城市', '建筑'], types: ['建筑', '城市'], device: '小米 15', shootDate: '作品集 · 城市地标', canBook: false, matchReason: '建筑细节与现场人群', accent: '#9a725f' },
  { id: 'cyrus-014', imageUrl: localWorkUrl('fac3cabe740ed07cdac991bfc0f357fc.jpg'), title: '祈年殿的深色屋檐', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 天坛', city: '北京', styles: ['暗调', '几何', '建筑'], types: ['建筑'], device: '小米 15', shootDate: '作品集 · 建筑线条', canBook: false, matchReason: '屋檐线条与深色质感', accent: '#626b70' },
  { id: 'cyrus-015', imageUrl: localWorkUrl('8c22ffe9a7036963e215c6f01f0c4c37.jpg'), title: '檐角向上生长', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '北京 · 古建园林', city: '北京', styles: ['明亮', '古风', '仰拍'], types: ['建筑'], device: '小米 15', shootDate: '作品集 · 古风建筑', canBook: false, matchReason: '仰拍视角与高亮天空', accent: '#d8aa71' },
  { id: 'cyrus-016', imageUrl: localWorkUrl('732bef5b6f98c69dec02d7fadebcd2a4.jpg'), title: '窗外山色入夜', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 室内窗边', city: '西安', styles: ['蓝调', '氛围', '室内'], types: ['静物', '风景'], device: '小米 15', shootDate: '作品集 · 窗边日记', canBook: false, matchReason: '窗框分割出的蓝调风景', accent: '#5b8eaf' },
  { id: 'cyrus-017', imageUrl: localWorkUrl('7d3a27628dff43d7b262a6e87cd75d9e.jpg'), title: '一桌热气与晚餐', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 餐厅', city: '西安', styles: ['暖调', '生活感', '低光'], types: ['美食', '静物'], device: '小米 15', shootDate: '作品集 · 生活碎片', canBook: false, matchReason: '低光环境中的食物与陪伴', accent: '#b66a32' },
  { id: 'cyrus-018', imageUrl: localWorkUrl('564bb89b9fa369f229fc2bfb634c5bc6.jpg'), title: '檐下看见一座塔', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 古寺', city: '西安', styles: ['古风', '旅行', '框景'], types: ['建筑'], device: '小米 15', shootDate: '作品集 · 古寺漫游', canBook: false, matchReason: '叶片框景与传统建筑', accent: '#718b78' },
  { id: 'cyrus-019', imageUrl: localWorkUrl('8a02ee6142c6a75362ca71196decbc0f.jpg'), title: '彩色烟雾升起时', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 校园活动', city: '西安', styles: ['高饱和', '庆典', '现场'], types: ['活动', '风景'], device: '小米 15', shootDate: '作品集 · 活动现场', canBook: false, matchReason: '彩色烟雾与大场面活动', accent: '#be3e6c' },
  { id: 'cyrus-020', imageUrl: localWorkUrl('e0a0a9175f309bb4bf30424d965744f9.jpg'), title: '窗边的山与咖啡', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 咖啡馆', city: '西安', styles: ['暖调', '生活感', '静物'], types: ['静物', '风景'], device: '小米 15', shootDate: '作品集 · 咖啡馆日常', canBook: false, matchReason: '室内桌面与远山景色', accent: '#aa754b' },
  { id: 'cyrus-021', imageUrl: localWorkUrl('73def5f9b02dfb6bd6365c5f4bfed42b.jpg'), title: '夜车上的同行者', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 夜间车站', city: '西安', styles: ['低光', '纪实', '夜景'], types: ['人像', '纪实'], device: '小米 15', shootDate: '作品集 · 夜行记录', canBook: false, matchReason: '低光里保留现场情绪', accent: '#5a6b67' },
  { id: 'cyrus-022', imageUrl: localWorkUrl('20cd7d65c810bd3c1049832daf043ef6.jpg'), title: '华山石壁上的红线', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '陕西 · 华山', city: '西安', styles: ['旅行', '山岳', '自然'], types: ['风景', '户外'], device: '大疆 Osmo Pocket 3', shootDate: '作品集 · 山岳旅行', canBook: false, matchReason: '山岳尺度与行进中的人', accent: '#7c8e96' },
  { id: 'cyrus-023', imageUrl: localWorkUrl('7477a4d06549c6111e68b189b755bf6d.jpg'), title: '夜市里的红伞', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 夜市', city: '西安', styles: ['夜景', '蓝调', '街拍'], types: ['人像', '街头'], device: '大疆 Osmo Pocket 3', shootDate: '作品集 · 夜市街拍', canBook: false, matchReason: '蓝调夜景与摊位灯光', accent: '#4d6b96' },
  { id: 'cyrus-024', imageUrl: localWorkUrl('69ad5fc404908ee05df3d8da54713b72.jpg'), title: '雪落古寺，蓝调人像', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 古寺', city: '西安', styles: ['蓝调', '氛围', '纪实'], types: ['人像', '活动'], device: '大疆 Osmo Pocket 3', shootDate: '作品集 · 雪天现场', canBook: false, matchReason: '雪景、建筑与人物关系', accent: '#5f8fc4' },
  { id: 'cyrus-025', imageUrl: localWorkUrl('2d877e352b8d4982db812575933c8f59.jpg'), title: '经幡的饱和色阶', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 文化景区', city: '西安', styles: ['高饱和', '旅行', '文化'], types: ['风景', '文化'], device: '大疆 Osmo Pocket 3', shootDate: '作品集 · 色彩旅行', canBook: false, matchReason: '经幡色彩与斜线构图', accent: '#d55762' },
  { id: 'cyrus-026', imageUrl: localWorkUrl('6741fc86c8912535c59258de05236f46.jpg'), title: '雪中的古寺旅人', photographerId: 'p-cyrus', photographerName: 'Cyrus_chang', photographerAvatar: 'https://i.pravatar.cc/160?img=68', location: '西安 · 古寺景区', city: '西安', styles: ['蓝调', '环境人像', '纪实'], types: ['人像', '旅行'], device: '大疆 Osmo Pocket 3', shootDate: '作品集 · 旅行人像', canBook: false, matchReason: '雪景环境中的人物肖像', accent: '#7a82b5' }
]

// 用户提供的两张实拍：只做描述性标题，作者沿用 mock 里的 Cyrus_chang，缺的字段留「待补充」。
const extraWorks: WorkCard[] = [
  {
    id: 'cyrus-027', imageUrl: localWorkUrl('city-night.jpg'), title: '外滩夜色',
    photographerId: 'p-qinihaoheguozhi', photographerName: '祺你喝好果汁', photographerAvatar: 'https://i.pravatar.cc/160?img=68',
    location: '上海 · 外滩', city: '上海', styles: ['夜景', '城市', '蓝调'], types: ['城市', '风景'],
    device: '待补充', shootDate: '作品集 · 城市夜景', canBook: false, matchReason: '夜色与城市轮廓', accent: '#3f5f86'
  },
  {
    id: 'cyrus-028', imageUrl: localWorkUrl('star-trail.jpg'), title: '雪原上的星轨',
    photographerId: 'p-schedinger', photographerName: '薛定谔', photographerAvatar: 'https://i.pravatar.cc/160?img=68',
    location: '待补充', city: '待补充', styles: ['星轨', '雪景', '长曝光'], types: ['风景', '户外'],
    device: '待补充', shootDate: '作品集 · 长曝光', canBook: false, matchReason: '长曝光下的星轨与雪地', accent: '#6c7f9a'
  }
]

/* 2026-11-16 用户补的三张实拍（也是薛定谔的作品）。
   EXIF 已丢：机型没有的就留「待补充」，不编。
   地点/城市：用户 22:40 答复「西藏」（经幡、银河两张），没细化到具体机位，就写西藏。
   这三张用户还要同时进首页螺旋墙（Q5「进」），所以提成常量给两处共用，
   避免同一个 id 在 works 里出现两次（列表 key 会重复）。 */
const xdgWorks: WorkCard[] = [
  {
    id: 'xdg-01', imageUrl: localWorkUrl('tiananmen.webp'), title: '晴空下的城楼',
    photographerId: 'p-schedinger', photographerName: '薛定谔', photographerAvatar: makeAvatar('薛定谔'),
    location: '北京 · 天安门', city: '北京', styles: ['建筑', '纪实', '晴天'], types: ['建筑', '城市'],
    device: '待补充', shootDate: '作品集 · 城市记录', canBook: false, matchReason: '晴空与城楼的色彩关系', accent: '#c8564b'
  },
  {
    id: 'xdg-02', imageUrl: localWorkUrl('prayer-flags.webp'), title: '经幡在风里',
    photographerId: 'p-schedinger', photographerName: '薛定谔', photographerAvatar: makeAvatar('薛定谔'),
    location: '西藏', city: '西藏', styles: ['高饱和', '色彩', '仰拍'], types: ['风景', '文化'],
    device: 'DJI Osmo Pocket 4', shootDate: '作品集 · 色彩记录', canBook: false, matchReason: '仰拍视角里的经幡与天色', accent: '#d55762'
  },
  {
    id: 'xdg-03', imageUrl: localWorkUrl('milky-way.webp'), title: '银河落在这条路上',
    photographerId: 'p-schedinger', photographerName: '薛定谔', photographerAvatar: makeAvatar('薛定谔'),
    location: '西藏', city: '西藏', styles: ['星空', '蓝调', '夜色'], types: ['风景', '夜景'],
    device: '待补充', shootDate: '作品集 · 星空记录', canBook: false, matchReason: '银河与地面人间的同框', accent: '#6b7fb3'
  }
]

works.push(...extraWorks, ...xdgWorks, ...cyrusWorks)

/* =========================================================================
   螺旋照片墙专用作品（2026-11-15）
   16 张图来自用户上传，已转 WebP 落到 src/assets/spirals/s01..s16.webp。
   作者/机型/地点由用户指定：
     · 祺你喝好果汁 —— 上海，索尼 A7M5，5 张（s01 s03 s06 s09 s13）
     · 青耘 —— 南京，尼康 D7100，11 张
   标题由 AI 草拟（用户授权「你可以拟草大字介绍」），只做客观描述，不编故事；
   详细介绍一律用用户指定的占位文案，等作者自己写。
   ========================================================================= */
const LAZY_STORY = '老师有点懒，这张照片少了点故事.......'

const QIN = { id: 'p-qinihaoheguozhi', name: '祺你喝好果汁', avatar: makeAvatar('祺你喝好果汁'), city: '上海', device: '索尼 A7M5' }
const QING = { id: 'p-qingyun', name: '青耘', avatar: makeAvatar('青耘'), city: '南京', device: '尼康 D7100' }

function spiralWork(index: number, owner: typeof QIN | typeof QING, title: string, styles: string[], types: string[]): WorkCard {
  return {
    id: `sp-${String(index).padStart(2, '0')}`,
    imageUrl: spiralUrl(`s${String(index).padStart(2, '0')}.webp`),
    title,
    photographerId: owner.id,
    photographerName: owner.name,
    photographerAvatar: owner.avatar,
    location: owner.city,
    city: owner.city,
    styles,
    types,
    device: owner.device,
    shootDate: '作品集 · 2026',
    canBook: false,
    story: LAZY_STORY
  }
}

/** 螺旋墙用「已有的作品图」造一条，避免为墙面再存一份文件（用户：螺旋墙只增加照片） */
function wallWork(ownerId: string, ownerName: string, device: string, file: string, title: string, styles: string[], types: string[]): WorkCard {
  return {
    id: `wall-${file.replace('.webp', '')}`,
    imageUrl: localWorkUrl(file),
    title,
    photographerId: ownerId,
    photographerName: ownerName,
    photographerAvatar: makeAvatar(ownerName),
    location: '西安 · 作品集',
    city: '西安',
    styles,
    types,
    device,
    shootDate: '作品集 · 2026',
    canBook: false
  }
}

/** 打散混排：祺与青耘交替出现，避免同类扎堆 */
export const spiralWorks: WorkCard[] = [
  spiralWork(1, QIN, '钢架塔尖', ['城市', '建筑', '蓝天'], ['建筑', '城市']),
  spiralWork(2, QING, '城墙、塔影与一湖春水', ['古建', '旅行', '绿调'], ['古建', '风景']),
  spiralWork(3, QIN, '幕墙与飞过的航班', ['城市', '建筑', '蓝天'], ['建筑', '城市']),
  spiralWork(4, QING, '台阶上的人群', ['纪实', '人文', '旅行'], ['纪实', '人文']),
  spiralWork(5, QING, '古树与临水的亭', ['园林', '古建', '绿调'], ['古建', '风景']),
  spiralWork(6, QIN, '街道尽头的超高层', ['夜景', '城市', '低光'], ['城市', '建筑']),
  spiralWork(7, QING, '黑白水面的鸭子', ['黑白', '生态', '静物'], ['生态', '纪实']),
  spiralWork(8, QING, '柳枝与两只水鸟', ['黑白', '生态', '留白'], ['生态', '风景']),
  spiralWork(9, QIN, '球体与塔身的夜光', ['夜景', '建筑', '高饱和'], ['建筑', '城市']),
  spiralWork(10, QING, '荷塘里的两朵', ['花卉', '自然', '微距'], ['花卉', '自然']),
  spiralWork(11, QING, '白花与枝影', ['花卉', '自然', '浅景深'], ['花卉', '自然']),
  spiralWork(12, QING, '柱子框住的塔', ['古建', '框景', '旅行'], ['古建', '建筑']),
  spiralWork(13, QIN, '江对岸的天际线', ['夜景', '城市', '蓝调'], ['城市', '风景']),
  spiralWork(14, QING, '抬头看见的树冠', ['自然', '仰拍', '绿调'], ['风景', '自然']),
  spiralWork(15, QING, '木台阶上的白鸽', ['生态', '人文', '浅景深'], ['生态', '纪实']),
  spiralWork(16, QING, '塔内的穹顶', ['古建', '室内', '高饱和'], ['古建', '建筑']),
  // 2026-11-15 用户：螺旋墙只增加照片。以下 12 张直接复用已入库的作品图。
  wallWork('p-ume', 'U咩人', '尼康 D7100', 'ume-04.webp', '面纱星云的丝状轮廓', ['星空', '长曝光', '暗调'], ['天文', '风景']),
  wallWork('p-ume', 'U咩人', '尼康 D7100', 'ume-12.webp', '绕北天极转一圈的星轨', ['星轨', '长曝光', '夜空'], ['天文', '风景']),
  wallWork('p-ume', 'U咩人', '尼康 D7100', 'ume-11.webp', '银河的核心', ['银河', '长曝光', '暗调'], ['天文', '风景']),
  wallWork('p-ume', 'U咩人', '尼康 D7100', 'ume-05.webp', '一团蓝色的星', ['星空', '星团', '暗调'], ['天文', '风景']),
  wallWork('p-ume', 'U咩人', '尼康 D7100', 'ume-07.webp', '树下的一对父女', ['人像', '自然光', '生活感'], ['人像', '纪实']),
  wallWork('p-yiwukaluo', '伊芜卡洛', '尼康 ZR', 'yiwu-02.webp', '夜里跨过桥面的车流', ['车流', '夜景', '长曝光'], ['城市', '夜景']),
  wallWork('p-yiwukaluo', '伊芜卡洛', '尼康 ZR', 'yiwu-08.webp', '从窗洞里框住的高架', ['框景', '城市', '日间'], ['城市', '建筑']),
  wallWork('p-yiwukaluo', '伊芜卡洛', '尼康 ZR', 'yiwu-10.webp', '倾斜的湖面与红桥', ['水景', '倒影', '秋色'], ['风景', '自然']),
  wallWork('p-tianshicong', '天使葱', '尼康 D5100', 'ts-11.webp', '逆光的枫叶', ['植物', '逆光', '秋色'], ['植物', '自然']),
  wallWork('p-tianshicong', '天使葱', '尼康 D5100', 'ts-03.webp', '落羽杉的红枝', ['植物', '秋色', '逆光'], ['植物', '自然']),
  wallWork('p-tianshicong', '天使葱', '尼康 D5100', 'ts-08.webp', '路边的一只狸花与一只橘猫', ['动物', '自然光', '生活感'], ['动物', '纪实']),
  wallWork('p-tianshicong', '天使葱', '尼康 D5100', 'ts-12.webp', '林间的石头与彩叶', ['秋色', '林间', '柔和'], ['风景', '自然'])
]

/* 首页螺旋墙实际用的数据：原有 28 张（16 张用户实拍 + 12 张复用作品图），
   加上 2026-11-16 用户 Q5 拍板「进」的薛定谔三张。
   注意：墙读这个数组，不要把这 3 条再 push 进 spiralWorks，否则 works 里会出现重复 id。 */
export const spiralWallWorks: WorkCard[] = [...spiralWorks, ...xdgWorks]

works.push(...spiralWorks)

/* =========================================================================
   用户 2026-11-15 21:1x 新给的两组作品（20 张，已转 WebP 落到 src/assets/works/）
     · U咩人   —— 15 张，尼康 D7100
     · 伊芜卡洛 —— 5 张，尼康 ZR
   城市、简介、报价一律「待补充」：用户只给了作者名与机型，不代为编造（C2）。
   标题按画面客观描述，不写故事。
   每人数组的第一张是「代表作」：选作品页按摄影师去重后，留下的就是它。
   ========================================================================= */
const UME = { id: 'p-ume', name: 'U咩人', city: '待补充', device: '尼康 D7100' }
const YIWU = { id: 'p-yiwukaluo', name: '伊芜卡洛', city: '待补充', device: '尼康 ZR' }

function setWork(owner: typeof UME | typeof YIWU, file: string, title: string, styles: string[], types: string[]): WorkCard {
  return {
    id: file.replace('.webp', ''),
    imageUrl: localWorkUrl(file),
    title,
    photographerId: owner.id,
    photographerName: owner.name,
    photographerAvatar: makeAvatar(owner.name),
    location: `${owner.city} · 作品集`,
    city: owner.city,
    styles,
    types,
    device: owner.device,
    shootDate: '作品集 · 2026',
    canBook: false
  }
}

const umeWorks: WorkCard[] = [
  setWork(UME, 'ume-04.webp', '面纱星云的丝状轮廓', ['星空', '长曝光', '暗调'], ['天文', '风景']),
  setWork(UME, 'ume-01.webp', '深空里的一片红', ['星空', '长曝光', '暗调'], ['天文', '风景']),
  setWork(UME, 'ume-02.webp', '高架桥上方向相反的两种车灯', ['车流', '夜景', '长曝光'], ['城市', '夜景']),
  setWork(UME, 'ume-03.webp', '仙女座星系与它的伴星系', ['星空', '长曝光', '暗调'], ['天文', '风景']),
  setWork(UME, 'ume-05.webp', '一团蓝色的星', ['星空', '星团', '暗调'], ['天文', '风景']),
  setWork(UME, 'ume-06.webp', '半个月面和它的环形山', ['月亮', '长焦', '暗调'], ['天文', '静物']),
  setWork(UME, 'ume-07.webp', '树下的一对父女', ['人像', '自然光', '生活感'], ['人像', '纪实']),
  setWork(UME, 'ume-08.webp', '操场边低头看手机的人', ['纪实', '逆光', '校园'], ['纪实', '人像']),
  setWork(UME, 'ume-09.webp', '星海里的一条红色暗带', ['星空', '长曝光', '暗调'], ['天文', '风景']),
  setWork(UME, 'ume-10.webp', '荷塘里的一朵荷花', ['花卉', '长焦', '浅景深'], ['花卉', '自然']),
  setWork(UME, 'ume-11.webp', '银河的核心', ['银河', '长曝光', '暗调'], ['天文', '风景']),
  setWork(UME, 'ume-12.webp', '绕北天极转一圈的星轨', ['星轨', '长曝光', '夜空'], ['天文', '风景']),
  setWork(UME, 'ume-13.webp', '黑金配色的假面骑士手办', ['静物', '灯位', '手办'], ['静物', '手办']),
  setWork(UME, 'ume-14.webp', '猎户座大星云', ['星空', '长曝光', '暗调'], ['天文', '风景']),
  setWork(UME, 'ume-15.webp', '树枝上方扫过的星轨', ['星轨', '长曝光', '夜空'], ['天文', '风景'])
]

const yiwuWorks: WorkCard[] = [
  setWork(YIWU, 'yiwu-02.webp', '夜里跨过桥面的车流', ['车流', '夜景', '长曝光'], ['城市', '夜景']),
  setWork(YIWU, 'yiwu-01.webp', '一朵向日葵', ['花卉', '浅景深', '自然光'], ['花卉', '自然']),
  setWork(YIWU, 'yiwu-03.webp', '广场上坐着的两个人', ['纪实', '生活感', '城市'], ['纪实', '人文']),
  setWork(YIWU, 'yiwu-04.webp', '停在路边的三轮车', ['纪实', '街头', '生活感'], ['纪实', '街头']),
  setWork(YIWU, 'yiwu-05.webp', '草地上的青铜群像', ['雕塑', '纪实', '绿调'], ['雕塑', '纪实'])
]

works.push(...umeWorks, ...yiwuWorks)

/* =========================================================================
   第二批（2026-11-15 21:3x，用户同一次发的）
     · 伊芜卡洛 —— 再 5 张（yiwu-06..10）
     · 天使葱   —— 12 张，尼康 D5100（机型见水印），
       用户原话「必须在约拍页放这些作品」；螺旋照片墙属于首页，本轮不动。
   ========================================================================= */
const TIANSHI = { id: 'p-tianshicong', name: '天使葱', city: '待补充', device: '尼康 D5100' }

const yiwuMore: WorkCard[] = [
  setWork(YIWU, 'yiwu-08.webp', '从窗洞里框住的高架', ['框景', '城市', '日间'], ['城市', '建筑']),
  setWork(YIWU, 'yiwu-06.webp', '草地上的一只喜鹊', ['动物', '自然光', '绿色'], ['动物', '纪实']),
  setWork(YIWU, 'yiwu-09.webp', '一朵黄色的菊花', ['花卉', '微距', '暖调'], ['花卉', '自然']),
  setWork(YIWU, 'yiwu-10.webp', '倾斜的湖面与红桥', ['水景', '倒影', '秋色'], ['风景', '自然']),
  setWork(YIWU, 'yiwu-07.webp', '虚焦的几颗暖灯', ['虚焦', '暖调', '抽象'], ['抽象', '静物'])
]

// 代表作放第一条：逆光的枫叶
const tianWork: WorkCard[] = [
  setWork(TIANSHI, 'ts-11.webp', '逆光的枫叶', ['植物', '逆光', '秋色'], ['植物', '自然']),
  setWork(TIANSHI, 'ts-01.webp', '爬满墙面的地锦', ['植物', '绿色', '建筑'], ['植物', '纪实']),
  setWork(TIANSHI, 'ts-02.webp', '楼顶的尖塔与路灯', ['建筑', '阴天', '城市'], ['建筑', '城市']),
  setWork(TIANSHI, 'ts-03.webp', '落羽杉的红枝', ['植物', '秋色', '逆光'], ['植物', '自然']),
  setWork(TIANSHI, 'ts-04.webp', '稻穗与远山', ['田野', '逆光', '金色'], ['自然', '风景']),
  setWork(TIANSHI, 'ts-05.webp', '路灯下湿地面上的落叶', ['夜景', '低光', '细节'], ['静物', '纪实']),
  setWork(TIANSHI, 'ts-06.webp', '夜里被灯打亮的枝叶', ['夜景', '逆光', '植物'], ['植物', '静物']),
  setWork(TIANSHI, 'ts-07.webp', '夜里的一片虚光', ['夜景', '虚焦', '抽象'], ['抽象', '静物']),
  setWork(TIANSHI, 'ts-08.webp', '路边的一只狸花与一只橘猫', ['动物', '自然光', '生活感'], ['动物', '纪实']),
  setWork(TIANSHI, 'ts-09.webp', '从竹叶缝里漏下来的光', ['植物', '逆光', '绿色'], ['植物', '自然']),
  setWork(TIANSHI, 'ts-10.webp', '地上散落的黄叶', ['低角度', '秋色', '细节'], ['静物', '自然']),
  setWork(TIANSHI, 'ts-12.webp', '林间的石头与彩叶', ['秋色', '林间', '柔和'], ['风景', '自然'])
]

works.push(...yiwuMore, ...tianWork)

export const photographers: Photographer[] = [
  { id: 'p-001', name: '林初禾', avatar: 'https://i.pravatar.cc/160?img=47', city: '西安', bio: '喜欢把现场的风、灯和人的小动作都留在照片里。常在古城和海边拍摄。', tags: ['古风人像', '夜景', '轻旅拍'], devices: ['Sony α7C II', 'DJI Osmo Pocket 3'], responseTime: '通常 20 分钟内回复', nextSlot: '周六 18:00 后', works: ['w-001', 'w-004'], verified: true },
  { id: 'p-002', name: '赵野', avatar: 'https://i.pravatar.cc/160?img=12', city: '西安', bio: '纪实派，擅长在自然光和城市边缘找到不刻意的状态。', tags: ['纪实', '胶片', '城市肖像'], devices: ['Fujifilm X-T5'], responseTime: '通常 1 小时内回复', nextSlot: '周六全天', works: ['w-002', 'w-005'], verified: true },
  { id: 'p-003', name: '周末', avatar: 'https://i.pravatar.cc/160?img=32', city: '西安', bio: '从街角开始认识一座城，也记录每个人最松弛的那一面。', tags: ['街拍', '汉服', '生活感'], devices: ['Canon EOS R8'], responseTime: '通常当天回复', nextSlot: '周日 09:00—13:00', works: ['w-003', 'w-006'], verified: true },
  { id: 'p-cyrus', name: 'Cyrus_chang', avatar: 'https://i.pravatar.cc/160?img=68', city: '西安', bio: '摄影爱好者，喜欢用手机和口袋云台记录旅行、建筑和身边的人。', tags: ['旅行纪实', '建筑', '蓝调人像', '活动记录'], devices: ['小米 15', '大疆 Osmo Pocket 3'], role: 'enthusiast', responseTime: '通常当天回复', nextSlot: '欢迎先看作品再交流', works: cyrusWorks.map((work) => work.id), verified: false },
  // 用户提供的两张实拍，作者由用户订正（2026-11-14）。除名字外一律「待补充」，不编造。
  // 2026-11-16 用户补的三张实拍（天安门 / 经幡 / 银河）挂到薛定谔名下
{ id: 'p-schedinger', name: '薛定谔', avatar: makeAvatar('薛定谔'), city: '待补充', bio: '待补充', tags: [], devices: [], role: 'enthusiast', responseTime: '待补充', nextSlot: '待补充', works: ['cyrus-028', 'xdg-01', 'xdg-02', 'xdg-03'], verified: false },
  { id: 'p-qinihaoheguozhi', name: '祺你喝好果汁', avatar: makeAvatar('祺你喝好果汁'), city: '上海', bio: '待补充', tags: [], devices: ['索尼 A7M5'], role: 'enthusiast', responseTime: '待补充', nextSlot: '待补充', works: ['cyrus-027', 'sp-01', 'sp-03', 'sp-06', 'sp-09', 'sp-13'], verified: false },
  { id: 'p-qingyun', name: '青耘', avatar: makeAvatar('青耘'), city: '南京', bio: '待补充', tags: [], devices: ['尼康 D7100'], role: 'enthusiast', responseTime: '待补充', nextSlot: '待补充', works: ['sp-02', 'sp-04', 'sp-05', 'sp-07', 'sp-08', 'sp-10', 'sp-11', 'sp-12', 'sp-14', 'sp-15', 'sp-16'], verified: false },
  // 2026-11-15 用户新给：只给作者名与机型，城市/简介/报价/档期一律「待补充」。
  { id: 'p-ume', name: 'U咩人', avatar: makeAvatar('U咩人'), city: '待补充', bio: '待补充', tags: ['星空', '长曝光', '天文', '城市夜景', '纪实'], devices: ['尼康 D7100'], role: 'enthusiast', responseTime: '待补充', nextSlot: '待补充', works: umeWorks.map((work) => work.id), verified: false },
  { id: 'p-yiwukaluo', name: '伊芜卡洛', avatar: makeAvatar('伊芜卡洛'), city: '待补充', bio: '待补充', tags: ['城市纪实', '生活感', '夜景', '花卉'], devices: ['尼康 ZR'], role: 'enthusiast', responseTime: '待补充', nextSlot: '待补充', works: yiwuWorks.map((work) => work.id).concat(yiwuMore.map((work) => work.id)), verified: false },
  { id: 'p-tianshicong', name: '天使葱', avatar: makeAvatar('天使葱'), city: '待补充', bio: '待补充', tags: ['植物', '逆光', '秋色', '街头细节'], devices: ['尼康 D5100'], role: 'enthusiast', responseTime: '待补充', nextSlot: '待补充', works: tianWork.map((work) => work.id), verified: false }
]

export const posts: MarketPost[] = [
  { id: 'post-001', kind: 'requirement', title: '周六小寨古风夜景，想找一位有经验的摄影师', city: '西安', location: '小寨 / 大雁塔附近', date: '11 月 14 日', time: '18:00—21:00', author: '阿遥', avatar: 'https://i.pravatar.cc/96?img=49', description: '有服化，想拍 2 小时左右，参考图是灯笼和街巷的氛围。希望能先看 3—5 张相近作品。', budget: '预算 ¥ 600—900', status: '招募中' },
  { id: 'post-002', kind: 'availability', title: '周日曲江有空档，接一组自然光人像', city: '西安', location: '曲江池 / 寒窑', date: '11 月 15 日', time: '15:00—18:00', author: '赵野', avatar: 'https://i.pravatar.cc/96?img=12', description: '不赶场，适合想拍一组自然、松弛的肖像。可提供简单动作引导。', budget: '¥ 480 起', status: '可预约' },
  { id: 'post-003', kind: 'companion', mode: 'pure-companion', title: '周六一起去城墙边拍秋天，互相掌机', city: '西安', location: '城墙南门', date: '11 月 14 日', time: '15:30—18:00', author: '木子', avatar: 'https://i.pravatar.cc/96?img=25', description: '两个人已经成行，想再找 1—2 位同好。带自己的相机，AA 交通，不接商业单。', spots: '还差 2 位', status: '找搭子' },
  { id: 'post-004', kind: 'companion', mode: 'paid-companion', title: '顺路带拍：周日大雁塔汉服小像', city: '西安', location: '大雁塔北广场', date: '11 月 15 日', time: '09:00—12:00', author: '周末', avatar: 'https://i.pravatar.cc/96?img=32', description: '我本来要去拍一组汉服，顺路带 1 位，互相尊重现场节奏，成片 8—10 张。', budget: '象征性分摊 ¥ 120', spots: '还差 1 位', status: '可报名' },
  { id: 'post-005', kind: 'requirement', title: '想拍一组有电影感的毕业照', city: '成都', location: '玉林 / 东郊记忆', date: '11 月 21 日', time: '全天', author: '小满', avatar: 'https://i.pravatar.cc/96?img=5', description: '3 位女生，偏生活化，不要标准毕业照。可接受不同风格摄影师提案。', budget: '预算 ¥ 800—1200', status: '招募中' },
  { id: 'post-006', kind: 'availability', title: '青岛小麦岛日落旅拍，开放一个轻量档期', city: '青岛', location: '小麦岛公园', date: '11 月 20 日', time: '16:00—18:30', author: '林初禾', avatar: 'https://i.pravatar.cc/96?img=47', description: '已经在青岛，不赶时间，适合情侣、朋友或一个人的轻旅拍。', budget: '¥ 680 起', status: '可预约' },
  /* 2026-11-16 用户：「接拍是想被拍的人发的」。
     上面 post-002 / 003 / 004 / 006 是摄影师视角（开放档期、顺路带拍）或搭子视角，不再进接拍列表；
     这里补 4 条「想被拍的人」发的需求帖，避免接拍页只剩两条。 */
  { id: 'post-007', kind: 'requirement', title: '大唐不夜城想拍一组暖光夜景人像', city: '西安', location: '大唐不夜城 / 大雁塔南广场', date: '11 月 22 日', time: '19:00—21:00', author: '鹿鸣', avatar: makeAvatar('鹿鸣'), description: '一个人，想拍夜景里偏暖的光。没有服化，衣服自带，能接受走街串巷找光。', budget: '预算 ¥ 500—800', status: '招募中' },
  { id: 'post-008', kind: 'requirement', title: '太古里周边想要一组城市街拍', city: '成都', location: '太古里 / 大慈寺附近', date: '11 月 23 日', time: '14:00—16:00', author: '阿棠', avatar: makeAvatar('阿棠'), description: '第一次约拍，想要松弛一点的街拍，不需要摆太多姿势。可以先看你的作品再决定。', budget: '¥ 400 起', status: '招募中' },
  { id: 'post-009', kind: 'requirement', title: '八大关的秋天，想拍一组胶片感', city: '青岛', location: '八大关 / 太平角', date: '11 月 24 日', time: '09:00—11:00', author: '沈迟', avatar: makeAvatar('沈迟'), description: '喜欢偏灰的胶片色，上午光线好。两个人一起拍，偏生活化的记录就行。', budget: '预算 ¥ 600—900', status: '招募中' },
  { id: 'post-010', kind: 'requirement', title: '室内自然光，想拍一组安静的肖像', city: '西安', location: '曲江书城 / 附近咖啡馆', date: '11 月 21 日', time: '15:00—17:00', author: '小舟', avatar: makeAvatar('小舟'), description: '不喜欢强烈的打光，想拍窗边自然光下的状态。时长一小时左右就够。', budget: '¥ 450 起', status: '招募中' },
  /* 2026-11-16 用户：接拍里也要有搭子帖。下面两条是「纯搭子」（大家一起拍），
     不含摄影师「顺路带拍」那种视角（mode: 'paid-companion'），那条按用户口径不进接拍。 */
  { id: 'post-011', kind: 'companion', mode: 'pure-companion', title: '周末去拍银杏，想找个人一起走', city: '西安', location: '兴庆宫公园', date: '11 月 23 日', time: '10:00—12:00', author: '苏木', avatar: makeAvatar('苏木'), description: '带一台老胶片机，主要想拍树和光。不用配合我，各拍各的也行，中午可以一起吃个饭。', spots: '还差 1 位', status: '找搭子' },
  { id: 'post-012', kind: 'companion', mode: 'pure-companion', title: '想找人一起去海边拍日出', city: '青岛', location: '石老人海水浴场', date: '11 月 25 日', time: '05:30—07:30', author: '阿鲸', avatar: makeAvatar('阿鲸'), description: '起得来就一起，拍完各回各家。有车可以顺路带，没有就地铁站碰头。', spots: '还差 2 位', status: '找搭子' }
]

export const orders: BookingOrder[] = [
  { id: 'order-2408', workId: 'w-001', photographerId: 'p-001', photographerName: '林初禾', photographerAvatar: 'https://i.pravatar.cc/96?img=47', title: '小寨古风夜景约拍', location: '西安 · 小寨', date: '11 月 14 日', time: '18:30—20:30', price: '¥ 780', status: 'confirmed', statusLabel: '已确认', updatedAt: '刚刚更新' },
  { id: 'order-2397', workId: 'w-005', photographerId: 'p-002', photographerName: '赵野', photographerAvatar: 'https://i.pravatar.cc/96?img=12', title: '曲江自然光肖像', location: '西安 · 曲江', date: '11 月 09 日', time: '15:00—17:00', price: '¥ 520', status: 'shooting-done', statusLabel: '待结清', updatedAt: '2 天前' }
]

// 2026-11-15 用户拍板：所有摄影师目前所在地先统一记「西安」，地区分配之后再逐个改。
// 只改摄影师所在地；作品的 location 仍是真实拍摄地（外滩那张照样写上海）。
photographers.forEach((item) => { item.city = '西安' })

/**
 * 约拍页的作品检索。
 * 2026-11-15 用户拍板：城市是硬过滤，口径是「他人在哪」而不是「这张照片在哪拍的」；
 * 场景只影响排序、不剔除——按命中关键词打分，分高的排前面，0 命中的照样留在列表里。
 * 去重（一个摄影师只留一张）在页面层做，因为「留哪张」要按当场排序决定。
 */
export function searchWorks(query: DiscoverQuery) {
  const city = query.location.includes('西安') ? '西安' : query.location.includes('青岛') ? '青岛' : query.location.includes('成都') ? '成都' : ''
  const baseCity = new Map(photographers.map((item) => [item.id, item.city]))
  const inCity = works.filter((work) => {
    if (!city) return true
    return (baseCity.get(work.photographerId) ?? work.city) === city || work.city === city
  })
  const scene = query.scene.trim().toLowerCase()
  if (!scene) return inCity
  const scoreOf = (work: WorkCard) => {
    let hits = 0
    for (const tag of work.styles.concat(work.types || [])) {
      if (scene.includes(tag.toLowerCase())) hits += 2
    }
    if (work.title && scene.includes(work.title.toLowerCase())) hits += 3
    if (work.location && scene.includes(work.location.toLowerCase())) hits += 1
    const haystack = `${work.title}${work.styles.join('')}${(work.types || []).join('')}`
    for (const token of ['夜景', '古风', '人像', '灯笼', '蓝调', '星轨', '逆光', '街拍', '旅拍', '胶片', '纪实', '建筑']) {
      if (scene.includes(token) && haystack.includes(token)) hits += 1
    }
    return hits
  }
  return inCity
    .map((work) => ({ work, score: scoreOf(work) }))
    .sort((a, b) => b.score - a.score)
    .map((item) => item.work)
}

/* =========================================================================
   外链头像本地化（2026-11-14，用户确认方案 A）
   原来 46 个头像是 https://i.pravatar.cc 外链，国内直连不可达 → 加载失败就是白方块。
   这里在模块加载时把「http(s) 开头的头像」统一换成姓名首字母色块（data URI），
   模板一行没改。换回真实头像时：把下面的 localizeAvatars 调用删掉，或把 mock 里的地址
   换成你要用的真实地址即可。
   注意：只动头像字段，作品图片（imageUrl）不动 —— 那 6 张 unsplash 作品图仍待处理。
   ========================================================================= */
function localizeAvatars<T>(list: T[], nameKey: keyof T, avatarKey: keyof T) {
  list.forEach((item) => {
    const current = item[avatarKey]
    if (!isRemoteImage(typeof current === 'string' ? current : '')) return
    const name = item[nameKey]
    ;(item as Record<keyof T, unknown>)[avatarKey] = makeAvatar(typeof name === 'string' ? name : '')
  })
}

localizeAvatars(works, 'photographerName', 'photographerAvatar')
localizeAvatars(photographers, 'name', 'avatar')
localizeAvatars(posts, 'author', 'avatar')
localizeAvatars(orders, 'photographerName', 'photographerAvatar')



