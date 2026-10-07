---
title: UI系统设计-布局引擎
date: 2026-10-07 14:00:13
tags:
  - C++
  - UI 系统
categories:
  - 引擎开发
cover: /lib/background/p5/7.jpg
mathjax: true
---

# 锚点-转轴系统 Anchor-Pivot

布局引擎(Layout Engine)是 UI 系统的核心子系统, 负责回答一个基本问题: **给定控件树和父容器的尺寸, 每个控件应该放在哪里, 占多大空间**.一次完整的布局通常分为三个阶段:

1. 测量(Measure): 自底向上, 子控件根据内容计算出期望尺寸(desired size)
2. 布局(Layout): 自顶向下, 父容器根据子控件的布局规则, 确定每个子控件的最终位置与尺寸
3. 渲染(Render): 把布局结果(矩形 + 变换)交给渲染层绘制

本笔记聚焦布局阶段最核心, 也最容易出错的一部分: 当父容器尺寸动态变化(窗口缩放, 设备旋转, 分辨率适配)时, 子控件如何跟随变化——这正是锚点(Anchor)与转轴(Pivot)系统要解决的问题.

## 布局引擎的结构

布局引擎围绕一棵**控件树(Widget Tree)**工作: 每个控件是一个节点, 父控件负责确定子控件的位置与尺寸.核心数据结构与接口如下(只摘与布局相关的部分):

```cpp
// 坐标基础类型
struct Vector2 { float x, y; };
struct Size2D  { float w, h; };
struct Rect    { Vector2 position; Size2D size; };

// 锚点-转轴-偏移 布局参数
struct LayoutParams {
    Vector2 anchorMin, anchorMax;  // 双锚点(归一化)
    Vector2 offsetMin, offsetMax;  // 四边偏移(像素)
    Vector2 pivot;                 // 转轴(归一化)
};

// 控件基类(只保留布局接口)
class Widget {
    Widget* parent;
    std::vector<Widget*> children;

    virtual Size2D Measure(const Size2D& available);  // 自底向上: 计算期望尺寸
    virtual void    Arrange(const Rect& finalRect);   // 自顶向下: 确定最终矩形

    Rect         m_rect;     // 布局结果
    LayoutParams m_layout;   // 布局参数(锚点/转轴/偏移)
};
```

布局流程由这两个虚函数串起来: 父容器先 `Measure` 询问子控件期望尺寸, 再根据子控件的 `LayoutParams` 用 `Arrange` 算出最终矩形——锚点-转轴公式(见下文)正是 `Arrange` 内部的核心计算.

## 布局系统: Flex 与 Grid 布局模型

锚点-转轴解决的是"单个控件如何定位/跟随父容器"; 但"多个子控件如何排列"这个更高层的问题, 由**布局模型(Layout Model)**决定——类似 CSS 的 flexbox 与 grid.它位于锚点-转轴之上: 布局模型先为每个子控件算出目标矩形, 锚点-转轴再据此定位.

```cpp
// 布局模型接口: 输入父内容区域 + 子控件集合, 输出每个子控件的目标矩形
class LayoutModel {
public:
    virtual void ComputeLayout(
        const Rect& contentRect,
        const std::vector<Widget*>& children
    ) = 0;
};

// Flex 布局: 一维排列(主轴 + 交叉轴)
class FlexLayout : public LayoutModel {
public:
    enum Direction { Row, Column };
    enum Justify   { Start, Center, End, SpaceBetween, SpaceAround };
    enum Align     { Start, Center, End, Stretch };

    Direction direction = Row;
    Justify   justify   = Start;
    Align     align     = Stretch;
    float     gap       = 0;   // 子项间距
};

// Grid 布局: 二维排列(行轨道 + 列轨道)
class GridLayout : public LayoutModel {
public:
    struct Track { float size; };
    std::vector<Track> columns;
    std::vector<Track> rows;
    float gap = 0;
};
```

1. **布局模型(Flex/Grid)** 在 `Arrange` 阶段被调用, 根据布局规则算出每个子控件的目标矩形
2. **锚点-转轴** 再根据目标矩形 + 锚点参数, 决定子控件在父容器变化时如何跟随/定位
3. 即: 布局系统是"排布策略", 锚点-转轴是"定位/适配基础", 前者构建在后者之上

锚点系统需要解决的问题是, 假设一个父控件面板尺寸从 $800\times 600$ 变化为 $1200\times 800$ 时, 其子控件应该如何变化.

2D UI 锚点(Anchor)标准模型: 锚框 (归一化矩形) + 四边偏移 + 轴心 Pivot. 其解决:
1. 父容器尺寸变化时, 子控件如何跟随拉伸 / 固定位置
2. 旋转, 缩放的参考基准

Anchor: 决定父容器变化时, 控件矩形四个角怎么动
Pivot: 决定控件矩形内部, 坐标原点在哪; 旋转缩放以哪个点为中心


父控件的内容区域(content area, 即扣除 border 和 padding 之后的区域)是一个矩形.之所以用内容区域而不是整个控件矩形, 是因为 border 和 padding 属于父控件自身的"装饰", 子控件应当相对内容区域定位:
$$
\mathrm{Parent} = [P_{x}, P_{x}+S_{x}]\times [P_{y}, P_{y}+S_{y}]
$$

其中,
- $P=(P_{x}, P_{y})$ 是父区域左上角在父坐标系下的位置
- $S=(S_{x}, S_{y})$ 是父区域的尺寸

在这个矩形内定义归一化坐标系 $u\in [0, 1], v\in[0,1]$ 映射到像素坐标
$$
\mathrm{pixel}(u, v) = P + \left(u\cdot S_{x}, v\cdot S_y\right) = P + (u, v)\odot S
$$
这个映射是仿射的, 且 $\odot$ 表示逐分量相乘, 约定 $u = 0$ 是左边缘, $u = 1$ 是右边缘, $v = 0$ 是上边缘, $v=1$ 是下边缘.

所以锚点定义为一个归一化坐标 $A = \left( A_{u}, A_{v} \right)\in \left[ 0,1 \right]^2$ 其指定了一个父坐标的参考点. 所以
$$
\mathrm{AnchorPoint}(A) = P + A \odot S
$$
而现代引擎中, 采用的双锚点系统 
$$
\begin{align}
A_\text{min} &= (A_{\text{min}, u}, A_{\text{min}, v})\\ 
A_\text{max} &= (A_{\text{max}, u}, A_{\text{max}, v})
\end{align}
$$
其各自映射到父区域的两个参考点
$$
\begin{align}
Q_\text{min} = P + A_\text{min}\odot S \\
Q_\text{max} = P + A_\text{max}\odot S
\end{align}
$$
在加上各自的偏移量 $O_\text{min}$ 和 $O_\text{max}$, 得到矩形的边界
$$
\begin{align}
R_\text{min} &= P + A_\text{min}\odot S + O_\text{min} \\
R_\text{max} &= P + A_\text{max}\odot S  + O_\text{max} 
\end{align}
$$
所以控件矩形就是 $[R_\text{min}, R_\text{max}]$

所以当 $A_\text{min} = A_\text{max}$ 则为**单点锚定**, 当 $A_\text{min} \ne A_\text{max}$ 则为**拉伸锚定**
对于单点锚定的情况: 
$$
\begin{align}
R_\text{min} &= P + A_\text{min}\odot S + O_\text{min} \\
R_\text{max} &= P + A_\text{max}\odot S  + O_\text{max} 
\end{align}
$$
两式相减 $D=R_\text{max}-R_\text{min}=O_\text{max}-O_\text{min}$. 即控件尺寸完全由这两个偏移量之差决定, 和父控件尺寸无关. 父区域变化时, $P+A\odot S$ 整体平移, 控件也跟着平移, 但尺寸不变.

对于拉伸锚定的情况:
此时 $Q_\text{min}$ 和 $Q_\text{max}$ 是父区域的两个不同点, 当父尺寸变化时
$$
\begin{align}
Q_\text{max} - Q_\text{min} = (A_\text{max} - A_\text{min})\odot S
\end{align}
$$
该差值就会随着父控件尺寸缩放, 所以此时控件尺寸为
$$
D = (A_\text{max}-A_\text{min})\odot S + (O_\text{max} - O_\text{min})
$$
其中
- $(A_\text{max}-A_\text{min})\odot S$ 随父控件拉伸(锚点差值部分)
- $(O_\text{max} - O_\text{min})$ 部分固定(偏移量之差, 不随父尺寸变化)


引擎内置16种锚点预设:
固定点位: 左上, 中上, 右上, 左中, 居中, 右中, 左下, 中下, 右下
拉伸模式: 顶横条, 底横条, 左竖条, 右竖条, 水平铺满, 垂直铺满, 完全铺满

其中 9 个固定点位预设都是**单点锚定**($A_\text{min} = A_\text{max}$, 对应 3×3 网格的九个位置); 7 个拉伸模式预设都是**拉伸锚定**($A_\text{min} \ne A_\text{max}$), 例如:
- 顶横条: $A_\text{min}=(0,0),\; A_\text{max}=(1,0)$, 贴着顶部水平拉伸
- 完全铺满: $A_\text{min}=(0,0),\; A_\text{max}=(1,1)$, 四边同时拉伸

**Pivot 是控件自身坐标系中的一个归一化点**，$p=(p_{u},p_{v})\in [0, 1]^{2}$ 表示控件矩形内的参考点
$$
\mathrm {PivotPoint} = R_\text{min} + p\odot D
$$
其中 $\odot$ 表示逐分量相乘.
- $p = (0,0)$ : 控件左上角
- $p = (1,1)$ : 控件右下角


| 角色        | 作用域  | 影响              |
| :-------- | :--- | :-------------- |
| **定位参考点** | 布局阶段 | 决定控件矩形相对锚点的摆放位置 |
| **变换原点**  | 渲染阶段 | 决定旋转, 缩放围绕哪个点进行  |
两者**互不干扰**: 布局只关心 Pivot 参与定位的公式, 渲染只关心 Pivot 作为变换原点的矩阵

单点锚定时, 用户通常这样描述需求：把控件的 **Pivot 点** 放在锚点位置上，再偏移 position, 即
$$
\text{PivotPoint} = P + A \odot S + \text{position}
$$

代入 $\text{PivotPoint} = R_{\min} + p \odot D$：

$$
R_{\min} = P + A \odot S + \text{position} - p \odot D
$$
例如: 弹窗尺寸 $800 \times 600$, 真正居中.

$$
A = (0.5, 0.5), \quad p = (0.5, 0.5), \quad \text{position} = (0, 0)
$$
代入:

$$
\begin{align}
O_{\min} &= \text{position} - p \odot D = (0,0) - (0.5,0.5) \odot (800,600) = (-400, -300) \\
O_{\max} &= O_{\min} + D = (-400, -300) + (800, 600) = (400, 300)
\end{align}
$$


中心锚点必须配中心 Pivot, 才能实现真正的几何居中


当控件旋转角度 $\theta$ 或缩放 $s$ 时，如果直接对局部坐标做变换, 会绕控件局部原点(通常是左上角)进行, 导致

- **旋转**：控件左上角不动，其余部分绕左上角画弧，视觉上控件"甩"了出去.
- **缩放**：左上角固定，右下角伸缩，控件"从一个角长出来".

大多数场景下，用户希望旋转/缩放围绕某个更有意义的点进行，例如：

- 居中旋转：围绕控件中心.
- 手柄缩放：围绕对角手柄.
- 菜单展开：围绕触发按钮的某个角.

这个"围绕点"就是 Pivot.


设变换前某点在父坐标系下的坐标为 $x$, Pivot 在父坐标系下的位置为 $p_w = \text{PivotPoint}(R)$.
围绕 $p_w$ 旋转 $\theta$, 缩放 $s = (s_x, s_y)$ 的变换是:
$$
M_{\text{transform}} = T(p_w) \cdot R(\theta) \cdot S(s) \cdot T(-p_w)
$$
其中：
$$
T(t) = \begin{pmatrix} 1 & 0 & t_x \\ 0 & 1 & t_y \\ 0 & 0 & 1 \end{pmatrix}, \quad
R(\theta) = \begin{pmatrix} \cos\theta & -\sin\theta & 0 \\ \sin\theta & \cos\theta & 0 \\ 0 & 0 & 1 \end{pmatrix}, \quad
S(s) = \begin{pmatrix} s_x & 0 & 0 \\ 0 & s_y & 0 \\ 0 & 0 & 1 \end{pmatrix}
$$
对于任意点 $x$：

$$
x' = p_w + R(\theta) \cdot S(s) \cdot (x - p_w)
$$
- 当 $x = p_w$ 时，$x' = p_w$：**Pivot 点不动**，这正是"围绕 Pivot 变换"的含义.
- 当 $x \neq p_w$ 时，点相对于 $p_w$ 做旋转和缩放，再平移回原位.

## 命中测试与逆变换

点击检测时，屏幕坐标 $q$ 需要逆变换到控件局部空间：

$$
x = M_{\text{transform}}^{-1} \cdot q
$$

然后判断 $x \in R$.

由于 $M_{\text{transform}} = T(p_w) \cdot R(\theta) \cdot S(s) \cdot T(-p_w)$，其逆为：

$$
M_{\text{transform}}^{-1} = T(p_w) \cdot S^{-1}(s) \cdot R(-\theta) \cdot T(-p_w)
$$

注意 $S^{-1}(s) = S(1/s_x, 1/s_y)$，需要处理 $s_x = 0$ 或 $s_y = 0$ 的退化情况.

把所有公式汇总，Pivot 的完整参与路径是：

$$
\boxed{
\begin{aligned}
&\text{布局阶段:}\quad R_{\min} = P + A \odot S + \text{position} - p \odot D \\
&\text{变换阶段:}\quad M = T(p_w) \cdot R(\theta) \cdot S(s) \cdot T(-p_w),\quad p_w = R_{\min} + p \odot D \\
&\text{渲染阶段:}\quad x' = M \cdot x \\
&\text{命中阶段:}\quad x = M^{-1} \cdot q
\end{aligned}
}
$$

- **布局公式**里 $p$ 参与决定控件摆放
- **变换公式**里 $p$ 决定旋转/缩放中心
- **渲染与命中**共享同一个 $M$，保证视觉与交互一致

Pivot 它不过是**控件内部的一个参考点**, 在定位时决定对齐语义, 在变换时决定不动点. 两者形式不同, 但都源于同一个 $p \in [0,1]^2$