-- ============================================================================
-- V2: 种子数据
-- 移植自 Python src/tools.py 的 mock dict，保证两端展示效果一致。
-- ============================================================================

INSERT INTO orders (order_id, product, price, status, order_date, carrier, tracking_no, shipping_address, estimated_delivery)
VALUES
    ('2024-78901', 'Keychron K8 Pro 机械键盘 (茶轴)', 598.00, 'SHIPPED',          '2025-01-15', '顺丰速运', 'SF1234567890', '北京市朝阳区望京街道 10 号院 3 号楼 1502 室', '2025-01-18'),
    ('2024-78902', 'Logitech MX Master 3S 无线鼠标',  699.00, 'PENDING_SHIPMENT', '2025-01-16', '京东物流', NULL,           '上海市浦东新区张江高科技园区 88 号',           '2025-01-20');

INSERT INTO return_policies (category, period_days, condition_text, shipping_responsibility)
VALUES
    ('键盘',   7,  '未拆封、无使用痕迹',         '商家承担'),
    ('鼠标',   7,  '未拆封、无使用痕迹',         '商家承担'),
    ('耳机',   15, '包装完好、无外观损伤',       '客户承担（质量问题除外）'),
    ('显示器', 7,  '无亮点/暗点、包装齐全',      '商家承担'),
    ('笔记本', 7,  '未激活、配件齐全',           '商家承担'),
    ('默认',   7,  '包装完好、不影响二次销售',   '客户承担');

INSERT INTO products (product_id, name, price, category, highlights, specs_json)
VALUES
    ('keychron-k8-pro',
     'Keychron K8 Pro 机械键盘',
     '¥598',
     '键盘',
     'QMK/VIA 自定义按键、PBT 双色键帽、吸音棉设计',
     '{"switch":"佳达隆 G Pro 茶轴（可热插拔）","layout":"80% (87键)","connectivity":"蓝牙 5.1 / USB-C 有线","battery":"4000mAh，约 2-4 周续航","compatibility":"Mac / Windows / Linux","backlight":"RGB 背光，18 种灯效","weight":"约 1.1kg"}'
    ),
    ('logitech-mx-master-3s',
     'Logitech MX Master 3S 无线鼠标',
     '¥699',
     '鼠标',
     '静音按键、Flow 跨设备控制、人体工学设计',
     '{"dpi":"8000 DPI（可调）","sensor":"Darkfield 激光传感器（可在玻璃上使用）","connectivity":"蓝牙 / Bolt USB 接收器","battery":"USB-C 充电，满电约 70 天","compatibility":"Windows / Mac / Linux / iPadOS","buttons":"7 个可编程按键 + MagSpeed 电磁滚轮","weight":"141g"}'
    ),
    ('sony-wh-1000xm5',
     'Sony WH-1000XM5 头戴式降噪耳机',
     '¥2,499',
     '耳机',
     '自适应降噪、佩戴感应、快充 3 分钟播放 3 小时',
     '{"driver":"30mm 驱动单元","anc":"双芯片主动降噪，8 麦克风","battery":"30 小时（开 ANC）/ 40 小时（关 ANC）","connectivity":"蓝牙 5.2 / 3.5mm 有线","codec":"LDAC / AAC / SBC","weight":"250g"}'
    );
