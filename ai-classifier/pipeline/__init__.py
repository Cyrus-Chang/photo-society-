"""图片类型/风格分类器：特征 → 训练 → 推理服务。

模块：
    colorfeat  24 维色彩影调特征（不依赖模型权重）
    train      抽 CLIP 特征、训练线性头、评测、导出 onnx
    serve      FastAPI + ONNX Runtime 推理服务
"""
