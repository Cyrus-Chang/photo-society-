-- ============================================================================
-- AI-3 图片分类打标签：新增表（MySQL 8.0）
-- 与现有 后端架构设计.md 的约定保持一致：
--   BIGINT 雪花主键 / 枚举存字符串 / created_at+updated_at+deleted_at / utf8mb4
-- 执行顺序：先建表，再跑文末的 work_tag 增量迁移（可选但建议）
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. label_dictionary 标签字典（唯一真源）
--    分类器能训出来的类别上限由这张表决定。产品/摄影师改口径只能改这里，
--    不允许模型自由生成新标签，避免 work_tag 里长出几万个同义词。
-- ---------------------------------------------------------------------------
CREATE TABLE `label_dictionary` (
  `id`          BIGINT       NOT NULL COMMENT '雪花 ID',
  `tag_type`    VARCHAR(16)  NOT NULL COMMENT 'SUBJECT / STYLE / LIGHT / OUTFIT',
  `tag_code`    VARCHAR(48)  NOT NULL COMMENT '稳定编码，如 STYLE_BLUE_TONE',
  `name_cn`     VARCHAR(32)  NOT NULL COMMENT '展示名，如 蓝调',
  `prompt_en`   VARCHAR(160) NOT NULL DEFAULT '' COMMENT '零样本用的英文提示词，如 a blue-toned photo',
  `definition`  VARCHAR(500) NOT NULL DEFAULT '' COMMENT '判定标准（给标注员看，必须写得能被第三方复用）',
  `negative_hint` VARCHAR(300) NOT NULL DEFAULT '' COMMENT '易混淆的相邻类，以及怎么区分',
  `sort_no`     INT          NOT NULL DEFAULT 0,
  `enabled`     TINYINT      NOT NULL DEFAULT 1 COMMENT '0=停用；停用后历史标签保留，但不再参与训练与召回',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at`  DATETIME     NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_dict_type_code` (`tag_type`, `tag_code`),
  KEY `idx_dict_type_enabled` (`tag_type`, `enabled`, `sort_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='标签字典：分类器的类别空间';

-- ---------------------------------------------------------------------------
-- 2. ai_model_registry 模型注册表
--    每次训练产出一个不可变版本；线上只认 status=ONLINE 的那一版，
--    灰度靠 traffic_ratio，回滚就是把旧版本 ratio 改回 0。
-- ---------------------------------------------------------------------------
CREATE TABLE `ai_model_registry` (
  `id`             BIGINT       NOT NULL,
  `model_key`      VARCHAR(64)  NOT NULL COMMENT '如 photo-cls-subject / photo-cls-style',
  `version`        VARCHAR(32)  NOT NULL COMMENT '如 v3-20261115',
  `task`           VARCHAR(16)  NOT NULL COMMENT 'SUBJECT / STYLE',
  `backbone`       VARCHAR(64)  NOT NULL DEFAULT 'clip-vit-b32' COMMENT '特征主干',
  `artifact_key`   VARCHAR(255) NOT NULL COMMENT '对象存储里的 onnx 模型 key',
  `labels_key`     VARCHAR(255) NOT NULL DEFAULT '' COMMENT 'labels.json key（类别顺序必须与 onnx 输出一致）',
  `metrics_json`   JSON         NULL COMMENT 'macroF1 / 各类 P-R / 混淆矩阵路径 / 样本数',
  `threshold_json` JSON         NULL COMMENT '按类别的置信度阈值，如 {"STYLE_BLUE_TONE":0.62}',
  `sample_count`   INT          NOT NULL DEFAULT 0,
  `traffic_ratio`  DECIMAL(4,3) NOT NULL DEFAULT 0.000 COMMENT '灰度比例 0.000~1.000',
  `status`         VARCHAR(16)  NOT NULL DEFAULT 'TRAINED' COMMENT 'TRAINED / VALIDATING / ONLINE / RETIRED',
  `trained_by`     BIGINT       NULL,
  `trained_at`     DATETIME     NULL,
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at`     DATETIME     NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_model_ver` (`model_key`, `version`),
  KEY `idx_model_online` (`model_key`, `status`, `traffic_ratio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='模型版本注册表';

-- ---------------------------------------------------------------------------
-- 3. classify_sample 训练样本池（数据飞轮的落点）
--    ★ 必须带 photographer_id：同一摄影师的片子高度同质，
--      随机划分会把同一组照片同时放进训练和验证集，指标虚高 20 个点以上。
--      训练脚本按 photographer_id 分组划分，这条约束就靠这个字段。
-- ---------------------------------------------------------------------------
CREATE TABLE `classify_sample` (
  `id`             BIGINT       NOT NULL,
  `work_id`        BIGINT       NULL COMMENT '来自作品入库时自动回流',
  `photographer_id` BIGINT      NULL,
  `object_key`     VARCHAR(255) NOT NULL COMMENT '训练图对象存储 key（不要直接把用户原图拿去训，先转 512 长边 webp）',
  `subject_codes`  VARCHAR(255) NOT NULL DEFAULT '' COMMENT '多标签，逗号分隔，如 PORTRAIT,STREET',
  `style_codes`    VARCHAR(255) NOT NULL DEFAULT '' COMMENT '风格主标签，通常单选',
  `labeler_id`     BIGINT       NULL COMMENT '标注人；NULL 表示用户自己确认的',
  `label_source`   VARCHAR(16)  NOT NULL DEFAULT 'USER' COMMENT 'USER=摄影师确认 / EDITOR=标注员 / IMPORT=外部数据集',
  `split`          VARCHAR(8)   NOT NULL DEFAULT 'UNASSIGNED' COMMENT 'TRAIN / VAL / TEST / UNASSIGNED（由训练脚本写入，划分一次后冻结）',
  `quality`        VARCHAR(16)  NOT NULL DEFAULT 'OK' COMMENT 'OK / BLURRY / TINY / WATERMARK / DUP —— 非 OK 不参与训练',
  `content_hash`   CHAR(64)     NOT NULL DEFAULT '' COMMENT 'sha256，跨 photographer 去重，防止同图多份',
  `license_note`   VARCHAR(120) NOT NULL DEFAULT '' COMMENT 'IMPORT 时必填来源与授权，比赛材料要用',
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at`     DATETIME     NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sample_hash` (`content_hash`, `object_key`),
  KEY `idx_sample_split` (`split`, `quality`),
  KEY `idx_sample_ph` (`photographer_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='训练样本池';

-- ---------------------------------------------------------------------------
-- 4. classify_prediction_log 推理日志（只记预测，不重复存标签）
--    work_tag 仍是标签的唯一真源；这张表只回答三件事：
--    预测得准不准、阈值该往上调还是往下调、哪些图值得送去人工标。
-- ---------------------------------------------------------------------------
CREATE TABLE `classify_prediction_log` (
  `id`            BIGINT       NOT NULL,
  `work_id`       BIGINT       NOT NULL,
  `model_version` VARCHAR(32)  NOT NULL,
  `subject_json`  JSON         NULL COMMENT '[{"code":"PORTRAIT","conf":0.91},...]',
  `style_json`    JSON         NULL,
  `color_json`    JSON         NULL COMMENT '24 维色彩特征，风格判错时靠它复盘',
  `top1_conf`     DECIMAL(5,4) NOT NULL DEFAULT 0 COMMENT '用于挑低置信样本',
  `final_tag_json` JSON        NULL COMMENT '用户确认后的最终标签，用来算修正率',
  `is_corrected`  TINYINT      NOT NULL DEFAULT 0 COMMENT '1=用户改过 AI 结果',
  `latency_ms`    INT          NOT NULL DEFAULT 0,
  `fallback`      VARCHAR(24)  NOT NULL DEFAULT '' COMMENT '降级原因：TIMEOUT / MODEL_MISSING / ZERO_SHOT',
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_plog_work` (`work_id`),
  KEY `idx_plog_review` (`model_version`, `top1_conf`, `created_at`),
  KEY `idx_plog_corrected` (`is_corrected`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='分类推理日志，用于阈值调优与主动学习采样';

-- ---------------------------------------------------------------------------
-- 5.（可选）work_tag 增量迁移
--    现有 work_tag 的 (work_id, tag_type, tag_code, confidence, source) 已够用，
--    补两列能让"这条标签是哪版模型给的"可追溯，答辩时能画出准确率曲线。
-- ---------------------------------------------------------------------------
ALTER TABLE `work_tag`
  ADD COLUMN `model_version` VARCHAR(32) NOT NULL DEFAULT '' COMMENT '产生该标签的模型版本，USER 来源为空' AFTER `source`,
  ADD COLUMN `is_confirmed`  TINYINT     NOT NULL DEFAULT 0  COMMENT '用户是否确认' AFTER `model_version`;

-- ---------------------------------------------------------------------------
-- 6. 字典种子数据（先只放演示必需的核心类，其余按 AI-3 文档第 3 节补全）
-- ---------------------------------------------------------------------------
INSERT INTO `label_dictionary` (`id`, `tag_type`, `tag_code`, `name_cn`, `prompt_en`, `definition`, `negative_hint`, `sort_no`) VALUES
(1001, 'SUBJECT', 'PORTRAIT',   '人像',   'a portrait photo of a person',           '主体为人物，面部或半身以上占比明显，背景次要',       '与街拍区分：街拍的人物更小、环境占比更大', 10),
(1002, 'SUBJECT', 'ARCHITECTURE','建筑',  'an architectural photo of a building',    '主体为建筑立面、结构、线条或室内空间',               '与城市街景区分：建筑为主体且强调几何', 20),
(1003, 'SUBJECT', 'LANDSCAPE',  '风光',   'a landscape photo of nature',             '自然景观为主体：山川湖海、天空、植被',               '与人像区分：画面中无明确主体人物', 30),
(1004, 'SUBJECT', 'STREET',     '街拍',   'a candid street photography shot',        '街头环境中的抓拍，人物与城市环境并重',               '与建筑区分：有人物活动与生活感', 40),
(1005, 'SUBJECT', 'CONVENTION', '漫展',   'a photo taken at an anime convention',    '漫展/展会现场：展馆、同人摊位、Cosplay 场照',         '与影棚人像区分：有场馆环境与人群', 50),
(1006, 'SUBJECT', 'STILL',      '静物',   'a still life product photo',              '静物、产品、桌面小物，主体单一且可控',               '与美食区分：非食物', 60),
(2001, 'STYLE',   'BLUE_TONE',  '蓝调',   'a photo with a blue color tone',          '整体偏蓝/青蓝：b* 均值为负，暗部明显偏冷，白平衡偏冷',   '与黑白区分：仍有色彩；与冷灰区分：蓝相明确', 10),
(2002, 'STYLE',   'INS',        'ins风',  'a clean bright minimal instagram style photo', '高亮低对比、黑位抬升（暗部不死黑）、干净留白、轻暖白平衡', '与日系区分：ins 更强调留白与几何，日系更强调空气感与柔光', 20),
(2003, 'STYLE',   'JAPANESE',   '日系',   'a soft airy japanese style photo',        '低饱和、高明度、柔光、轻微高光溢出、青绿倾向',         '与 ins 区分：日系不追求锐利与留白', 30),
(2004, 'STYLE',   'FILM',       '胶片',   'a film emulation photo with grain',       '颗粒感、黑位抬升、色彩偏移（青影暖高光）、对比柔和',   '与复古区分：复古强调色调年代感与褪色', 40),
(2005, 'STYLE',   'CYBER',      '赛博',   'a cyberpunk neon photo',                  '霓虹高饱和、青品对冲、硬光、暗部保留高饱和光斑',       '与夜景区分：夜景只是时间，赛博强调霓虹配色', 50),
(2006, 'STYLE',   'DARK_MOOD',  '暗调',   'a moody low key dark photo',              '低调摄影：大面积暗部、单一光源、情绪压抑',             '与黑白区分：可能仍是彩色', 60),
(2007, 'STYLE',   'MONO',       '黑白',   'a black and white photo',                 '完全去色，仅灰阶',                                   '', 70),
(2008, 'STYLE',   'HK_RETRO',   '港风',   'a hong kong retro style portrait',        '偏绿青中间调、暖肤色、硬光、年代感颗粒',               '与胶片区分：港风强调绿青中间调与港片构图', 80);

-- ---------------------------------------------------------------------------
-- 7. 本期训练范围锁定
--    平台 85% 以上是有人像的作品，题材维度区分度不足，所以只保留 3 类题材；
--    训练重心放在 STYLE。其余类别的定义保留（enabled=0），等样本够了再开。
-- ---------------------------------------------------------------------------
INSERT INTO `label_dictionary` (`id`, `tag_type`, `tag_code`, `name_cn`, `prompt_en`, `definition`, `negative_hint`, `sort_no`) VALUES
(1007, 'SUBJECT', 'OTHER', '其他题材', 'a photograph of architecture, landscape, food or still life without a person as the main subject', '非人像、非场照的其余作品：风光、建筑、静物、美食、街拍空镜、宠物。本类作用是把非人像作品分流出去', '与人像区分：画面中没有明确的人物主体', 70);

UPDATE `label_dictionary` SET `enabled` = 0
 WHERE `tag_type` = 'SUBJECT' AND `tag_code` NOT IN ('PORTRAIT', 'CONVENTION', 'OTHER');

UPDATE `label_dictionary` SET `enabled` = 0
 WHERE `tag_type` = 'STYLE' AND `tag_code` NOT IN ('BLUE_TONE', 'INS', 'JAPANESE', 'FILM', 'DARK_MOOD', 'MONO');

-- ---------------------------------------------------------------------------
-- 8. v2.1 迁移：题材改为人像细分 5 子类 + 非人像 3 大类；风格扩到 8 类；新增 TONE 维度
--    ★ 放在 §7 之后执行。旧编码不删除、只停用（历史 work_tag 还要能解析出展示名）。
--    ★ 全部用 ON DUPLICATE KEY UPDATE，重复执行不会报主键/唯一键冲突。
-- ---------------------------------------------------------------------------
INSERT INTO `label_dictionary` (`id`, `tag_type`, `tag_code`, `name_cn`, `definition`, `negative_hint`, `sort_no`) VALUES
(1101, 'SUBJECT', 'STUDIO',            '棚拍人像',     '影棚/纯色背景/布景纸，人工布光（柔光箱、轮廓光、发丝光），背景干净可控', '与 INTERIOR_PORTRAIT 区分：棚拍背景是纯色或布景纸，室内环境人像的背景是真实空间', 10),
(1102, 'SUBJECT', 'OUTDOOR',           '外景人像',     '自然环境为背景的人像：公园、海边、山野、草地、花田，自然光为主',       '与 STREET_PORTRAIT 区分：外景强调自然元素，街拍强调城市人文环境', 20),
(1103, 'SUBJECT', 'STREET_PORTRAIT',   '街拍人像',     '城市街头环境的人像：店面、招牌、涂鸦、街道设施、通勤人群为背景，环境参与叙事', '与 OUTDOOR 区分：城市元素而非自然元素；与 CONVENTION 区分：无展会语境', 30),
(1104, 'SUBJECT', 'INTERIOR_PORTRAIT', '室内环境人像', '真实室内空间为背景的人像：咖啡馆、家居、民宿、书店、暗房，环境是叙事的一部分', '与 STUDIO 区分：背景是真实可生活空间，不是纯色布', 40),
(1105, 'SUBJECT', 'ARCHITECTURE',      '建筑',         '非人像，主体为建筑立面、结构、几何线条、室内空间结构；可有极小人物作尺度参照', '与 INTERIOR_PORTRAIT 区分：画面中没有人像主体', 50),
(1106, 'SUBJECT', 'LANDSCAPE',         '风光',         '非人像，自然景观为主体：山川、湖海、天空、云、植被、雪景、星空',       '与 OUTDOOR 区分：画面中没有人像主体', 60),
(1107, 'SUBJECT', 'STILL_FOOD',        '静物美食',     '非人像，单个/少量主体可控布景：产品、桌面小物、花艺、食物与饮品',     '与 ARCHITECTURE 区分：主体是独立物件而非空间结构', 70),
(1108, 'SUBJECT', 'CONVENTION',        '漫展场照',     '漫展/展会现场：展板、摊位、横幅、排队人群、场馆顶棚泛光，主体通常是 Coser', '与 STUDIO／OUTDOOR 区分：场照的本质是"在现场"，有展会环境线索', 80)
ON DUPLICATE KEY UPDATE
  `name_cn` = VALUES(`name_cn`), `definition` = VALUES(`definition`),
  `negative_hint` = VALUES(`negative_hint`), `sort_no` = VALUES(`sort_no`), `enabled` = 1;

-- TONE：规则算，不训练。rule 写进 definition，服务端实现见 pipeline/serve.py:derive_tone()
INSERT INTO `label_dictionary` (`id`, `tag_type`, `tag_code`, `name_cn`, `definition`, `sort_no`) VALUES
(3001, 'TONE', 'TONE_WARM',          '暖调',     'rule: warmth > 0.035',  10),
(3002, 'TONE', 'TONE_COOL',          '冷调',     'rule: warmth < -0.020', 20),
(3003, 'TONE', 'TONE_HIGH_SAT',      '高饱和',   'rule: S_mean > 0.45',   30),
(3004, 'TONE', 'TONE_LOW_SAT',       '低饱和',   'rule: S_mean < 0.22',   40),
(3005, 'TONE', 'TONE_HIGH_CONTRAST', '高对比',   'rule: L_range > 0.72',  50),
(3006, 'TONE', 'TONE_LOW_CONTRAST',  '柔和',     'rule: L_range < 0.45',  60),
(3007, 'TONE', 'TONE_HIGH_KEY',      '高调',     'rule: L_mean > 0.62',   70),
(3008, 'TONE', 'TONE_LOW_KEY',       '低调',     'rule: L_mean < 0.28',   80),
(3009, 'TONE', 'TONE_LIFTED_BLACK',  '黑位抬升', 'rule: L_p05 > 0.16',    90)
ON DUPLICATE KEY UPDATE
  `name_cn` = VALUES(`name_cn`), `definition` = VALUES(`definition`), `sort_no` = VALUES(`sort_no`);

-- 重新锁定启用范围（v2.1：题材 8 类、风格 8 类、TONE 全部规则产出不需要 enabled 控制）
UPDATE `label_dictionary` SET `enabled` = 1
 WHERE `tag_type` = 'SUBJECT'
   AND `tag_code` IN ('STUDIO','OUTDOOR','CONVENTION','STREET_PORTRAIT',
                      'INTERIOR_PORTRAIT','ARCHITECTURE','LANDSCAPE','STILL_FOOD');

UPDATE `label_dictionary` SET `enabled` = 0
 WHERE `tag_type` = 'SUBJECT'
   AND `tag_code` IN ('PORTRAIT','STREET','STILL','OTHER','PET','EVENT');

UPDATE `label_dictionary` SET `enabled` = 1
 WHERE `tag_type` = 'STYLE'
   AND `tag_code` IN ('BLUE_TONE','INS','JAPANESE','FILM','DARK_MOOD','MONO','HK_RETRO','CYBER');

UPDATE `label_dictionary` SET `enabled` = 0
 WHERE `tag_type` = 'STYLE' AND `tag_code` IN ('VINTAGE','LOW_SAT');

-- ---------------------------------------------------------------------------
-- 9. v3.0 迁移：风格扩到 13 类，并改为多标签（sigmoid）
--    为什么改多标签：13 个风格里日系↔清新、胶片↔复古、港风↔胶片 天然共存，
--    单标签 softmax 会逼模型在本可共存的类之间做选择，越加越乱。
--    ★ 模型侧以 models/style.labels.json 的 "multi": true 为准，数据库这里只存标签字典。
-- ---------------------------------------------------------------------------
INSERT INTO `label_dictionary` (`id`,`tag_type`,`tag_code`,`name_cn`,`definition`,`negative_hint`,`sort_no`) VALUES
(2010,'STYLE','KOREAN',   '韩系',  '奶油感：皮肤通透白皙偏粉、浅色调、低对比、黑位轻微抬升、画面干净锐度中高', '与日系区分：偏粉白且更锐；与 ins 区分：更强调人物皮肤质感', 100),
(2011,'STYLE','WESTERN',  '欧美',  '欧美杂志/时尚 editorial：高反差、硬光、强轮廓阴影、暖中性色或冷蓝背景、妆造强烈', '与暗调区分：高反差不是大面积暗部；★定义最宽，混淆严重时优先拆掉', 110),
(2012,'STYLE','CINEMATIC','电影感','青橙调色：暗部偏青、高光偏橙、S 形对比曲线、两端不裁切、常配宽画幅', '与赛博区分：青+橙 vs 青+品红；与欧美区分：有明确双色对冲', 120),
(2013,'STYLE','FRESH',    '清新',  '高明度、低饱和、通透、浅色、阳光感、干净，比日系更亮更白', '与日系区分：更亮更白、无灰雾；★可共存，多标签允许同时为真', 130)
ON DUPLICATE KEY UPDATE
  `name_cn` = VALUES(`name_cn`), `definition` = VALUES(`definition`),
  `negative_hint` = VALUES(`negative_hint`), `sort_no` = VALUES(`sort_no`), `enabled` = 1;

UPDATE `label_dictionary` SET `enabled` = 1
 WHERE `tag_type` = 'STYLE'
   AND `tag_code` IN ('BLUE_TONE','INS','JAPANESE','KOREAN','WESTERN','FILM','VINTAGE',
                      'CINEMATIC','FRESH','DARK_MOOD','MONO','HK_RETRO','CYBER');

UPDATE `label_dictionary` SET `enabled` = 0
 WHERE `tag_type` = 'STYLE' AND `tag_code` = 'LOW_SAT';
