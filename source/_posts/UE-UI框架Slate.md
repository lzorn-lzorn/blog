---
title: UE-UI框架Slate{0}-UI设计及Slate的机制
date: 2025-12-10 21:29:58
tags: 
  - UE
  - C++
categories:
  - UE
  - UE-UI
cover: /lib/background/bg3.jpg
---

<!-- toc -->

# UE的UI框架-Slate
UE 使用 C++ 实现了自己原生的一套UI界面, 这里的 C++ 是纯C++ 并不是使用了 UObject 的C++, 原因是 UObject 系统对于要求流程丝滑的 UI 界面而已太过沉重. 但是对于游戏中用户界面又必须要被整个GC所接管, 例如玩家的血条, 这里的血条控件应该和玩家单位使用同一套回收机制. 所以 UE 使用一个继承自 UObject 的类去包裹 Slate 的对象, 即 UMG 对象. 换句话说, UMG 对象只是 Slate 对象的容器, 真正的逻辑都执行在 Slate 的基础控件中.

`FSlateApplication` 是 Slate 系统的入口. `FEngineLoop::Tick` 通过 `FSlateApplication::Tick` 渲染 Slate 已经执行其逻辑

在 UI 设计中, 有一些问题是无法绕过的:
1. 窗口之间的关系如何组织
2. 窗口内的各种控件的关系如何组织
3. 具体窗口和控件的渲染如何处理
4. 窗口如何进行事件响应

接下来会一一说明
# UI窗口的组织SWindow
窗口是一个典型的树结构, `SWindow` 中存有一个父类的弱引用(`TWeakPtr<SWindow> ParentWindowPtr;`), 同时存有所有子窗口的共享应用(`TArray<TSharedRef<SWindow>> ChildWindows;`). `FSlateApplication` 中管理了所有顶窗口, 即没有父窗口的窗口(`TArray<TSharedRef<SWindow>> SlateWindows;`)

# 窗口的渲染
# UI窗口的组织SWindow
窗口是一个典型的树结构, `SWindow` 中存有一个父类的弱引用(`TWeakPtr<SWindow> ParentWindowPtr;`), 同时存有所有子窗口的共享应用(`TArray<TSharedRef<SWindow>> ChildWindows;`). `FSlateApplication` 中管理了所有顶窗口, 即没有父窗口的窗口(`TArray<TSharedRef<SWindow>> SlateWindows;`)

# 窗口的渲染
## 渲染执行的入口-模态窗口机制
Slate 中渲染每一个 `SWindows` 大致分为两个主要阶段: 数据处理阶段, 实际渲染 Draw-Call 的调用.
Slate 中主要负责的是前者, 换句话说, Slate 只是负责处理窗口的各种数据, 实际的渲染会派发给渲染器(SlateRender), 其实际调用是:
`FEngineLoop::Tick` 
-> `FSlateApplication::Tick` 
-> `FSlateApplication::TickAndDrawWidgets`
-> `FSlateApplication::DrawWindows`
从 `FSlateApplication::DrawWindows` 这个函数开始, 正式进入渲染的流程, 如下图

![UE-UI的渲染入口](./images/UE-UI的渲染入口.png)

在这里设计到一个概念: <font color="#c0504d">模态窗口(Modal Window)</font>, 这个是一个在UI设计中常用的概念: 其是一种特殊的用户界面元素, 当它被激活时, 会阻止用户与应用程序的其他部分进行交互, 直到用户完成当前操作并关闭该窗口. 也就是强制用户进行完当前操作. 

在 WPF 中 `ShowDialog` 就是一种模态窗口; 在 Qt 中也可以调用 `QDialog` 中的 `setModal`, 来设置其模态属性; 在 Electron 中, 
```JavaScript
let modal = new BrowserWindow({
  parent: mainWindow,  // 设置父窗口
  modal: true,         // 设置为模态
  show: false
});
```
也可以设置 modal 属性. 

所以, 在渲染时, Slate 会优先渲染模态窗口. 在整个渲染的入口中, 所有的步骤都是在处理 `DrawWindowArgs.OutDrawBuffer` 并使其可以达到可以被渲染器直接使用的程度.

在实际渲染数据处理的过程中, 有两个阶段:
1. 预处理: `DrawPrepass()` 其目的主要是处理窗口和控件的各种尺寸
2. 正式进行渲染数据的处理: `DrawWindowAndChildren()`

## 对于渲染的数据操作-快慢路径绘制流程
对于正在进行渲染数据的处理流程: 如下图
![渲染单个窗口进行数据操作.png](./images/渲染单个窗口进行数据操作.png)
这里出现了第二个概念: <font color="#c0504d">快路径渲染和慢路径渲染</font>, 同时需要介绍UE这里的缓存机制: UI 框架为了优化渲染性能, 尽可能减少渲染次数, 在很多时候不会对窗口进行重新绘制, 而是采用缓存中已有的数据进行渲染, 这就是快路径渲染. 而对于缓存实效的情况, 则需要按照正常流程渲染窗口, 子窗口, 以及控件, 也就是慢路径渲染, 所以只有在慢路径渲染的情况下才会去重新调用控件的 `OnPaint()` 方法.
更详细的来说: 慢路径渲染是一次完整的, 保守的从根到叶的遍历——重新评估布局/可见性/几何, 重建/绘制每个 widget, 更新 hit-test 网格, 并重建或刷新绘制元素缓存(CachedElementData). 它保证在任何结构性或状态变化后画面正确, 但开销大; 而快路径绘制是在没有结构性变化时尽量"重用上帧结果", 只做必要更新(Eg: 几何/变换、剪裁、z 层调整、对少量"最终更新" widget 的重绘、以及同步 hit-test)

## Widget的渲染流程: 失效机制(Invalidate)
在每帧渲染时会检查失效状态, 如果调用了 `SetVisibility()`, `SetRenderTransform()` 等函数则会触发失效检查, 会在控件内部调用 `Invalidate(Reason)`, 然后触发控件的重新绘制, 但是并不是所有的重绘都要重新走一边流程, 在UE中由以下失效理由:
```Cpp
enum class EInvalidateWidgetReason : uint8
{
    None = 0, // 不需要任何无效化
    Layout = 1 << 0,
    Paint = 1 << 1,
    Volatility = 1 << 2,
    ChildOrder = 1 << 3,
    RenderTransform = 1 << 4,
    Visibility = 1 << 5,
    AttributeRegistration = 1 << 6,
    Prepass = 1 << 7,
    PaintAndVolatility = Paint | Volatility,
    LayoutAndVolatility = Layout | Volatility,
};
```
其中: 
- `Layout`: 则会触发重布局-则会对控件进行重新测量, 重新准备数据, 重新绘制, 是开销最大的一种 `Reason`. 但是如果控件的位置变化, 大小变化, 排列变化(Padding, Slot 这种参数变化), 则必须重布局
- `Paint`: 表示控件需要重新绘制，但不会影响布局(例如: Icon的颜色变了吗, 文本颜色变了, 仅视觉内容不同)
- `Volatility` 表示波动性: 如果一个控件被设置为 `Volatility` 则其会每帧调用 `Paint` 重新绘制, 如果没有设置为 `Volatility` 的控件, 则会复用其缓存的信息. (动画控件，或Tick频繁变内容的控件), 由于控件由原来的静态变为动态, 会影响 `RenderBatch`
- `ChildOrder`: 子控件被增加或删除(如Panel子项变动). 属于重布局的变动，隐含触发 Prepass/Layout
- `RenderTransform`: 控件的Render变换(位置、旋转、缩放等), 发生变化. <u>只影响控件渲染, 影响布局</u>.
- `Visibility`: 可见性变化(Visible/Collapsed/Hidden)通常需要<u>重布局</u>, 因为不可见控件不再占空间
    - Collapsed: 必然重布局的, 不占据任何布局空间, 等价于在树里将节点从Panel的子集合中临时移除那样的效果
    - Hidden: 只是重绘, 不会强制触发重布局( ==todo==: 待验证, 断不到源码位置)
- `AttributeRegistration`: 属性的绑定/解绑变化(SlateAttribute绑定/解绑)时触发. 用于属性反射或Slate绑定机制内部处理
- `Prepass`: <u>递归强制</u>重走子树的Prepass(递归更新DesiredSize), 一般用于布局大幅改变或子节点数巨变，需要全部节点自下而上检查尺寸, 比 `Layout` 还消耗性能

如果父控件失效了, 则其失效标记会扩散到子控件. 对于一些经常变化颜色和UI动画应该设置 `Volatility` 往往是比较保险的

在UE的UI中还有常见的两种优化策略:
- 合批优化: 其本质是, 对于满足一些条件UI元素进行合并 Draw-Call, 可以只使用一次 Draw-Call 来批量绘制UI元素. 具体见后 {UE-UI框架Slate-2-Slate的监控和优化}
- 重绘盒优化: 具体见后 {UE-UI框架Slate-2-Slate的监控和优化}

## 实际的绘制调用(Draw-Call)
最后, 实际上真正向GPU提交绘制命令并不在Slate层中, FSlateApplication 将所有数据准备好之后, 在 `FSlateApplication::PrivateDrawWindows` 中调用 `Renderer->DrawWindows`
最后进入 `SlateRHIRender::DrawWindow_RenderThread` 中调用 `FRHICommandList::BeginDrawingViewport` (RHICmdList) ->
`FRHICommandList::RHIBeginDrawingViewport` (GetContext()), 进入真实运行的在当前系统的 RenderDynamicRHI 封装中 ->
`FRHICommandList::BeginRenderPass` (RHICmdList) ->
`FSlateRHIRenderingPolicy::DrawElements` (RenderingPolicy) 内部会设置各种和渲染有关的细节(Eg: 顶点着色器, 像素着色器, 纹理, 渲染资源), 其中每一次对 `FRHICommandList::DrawIndexedPrimitive` 的调用就是一次 DrawCall, 具体流程如下:
![实际的渲染Draw-Call](./images/实际的渲染Draw-Call.png)
更详细的来说, GPU(同时包括渲染API)只是渲染最基础的各种图元和定点信息和片段信息, 而这些信息会在之前的 SlateApplication 阶段就基本已经处理好, 在 Render 中只是将这些基本的 WindowElement 转化为顶点数据和片段数据(像素数据), 由于UE对各种渲染API的封装, 所以不必关心具体的渲染细节, 例如: 在 Vulkan 中实际上已经没有 VBO, EBO这种结构, 已经被 Vulkan 抽象为一个缓冲区等.

# 窗口的事件响应

## 屏幕网格
屏幕网格结构 `FHittestGrid`: 其内部有保有 `FCell` (本质上持有一个SWideget的句柄数组 `TArray<int32> WidgetIndexes`) 
![FHittestGrid示意图](./images/FHittestGrid.png)

## Slate的事件响应
Slate 系统的用于处理用户输入的类为 FSlateUser(不仅能处理输入)
`FSlateUser` 表示一个逻辑上的用户/输入上下文(包含指针位置、捕获、焦点路径、tooltip 状态、drag-drop 状态等), 一个 `FSlateUser` 会管理一个或多个指针索引（鼠标、触摸点等）以及与该用户相关的状态, 手柄会控制光标和指针, 所以插入手柄会增加一个 `FSlateUser`, 但是并不是随便插入一个交互设备就能添加一个 `FSlateUser`. 其主要负责 Cursor (光标):
- Focus: 聚焦
- Capture: 捕获
- DragDrop: 拖动
- Draw: 绘制
[Slate 的事件响应](https://blog.csdn.net/j756915370/article/details/121964442)

![点击事件响应流程.png](./images/点击事件响应流程.png)

# 控件之间的逻辑的关系
Slate 中基类是 `SWidget`, 继承 `SWidget` 的有另外三个基础类:
- `SPanel` : 有多个子节点
- `SLeafWidget` : 没有子节点
- `SCompoundWidget` : 可以有一个子节点
### 控件树机制
控件树: 在UI设计中, 窗口之间的逻辑关系是一种树关系, 在不同的系统中使用到了不同的方式来组织管理控件树
`FWidgetPath` 是对于控件树的垂直切片(vertical slice), 是从某一个节点A开始到另一个可达子节点B路径的表示. `FArrangedChildren` 是内部的容器表示, 内部存有 `FArrangedWidget` (保有控件指针 `TSharedRef<SWidget>` 和 位置信息 `FGeometry`)
![FWidgetPath](./images/FWidgetPath.png)

# 控件之间的位置关系
## UI 扩展点
UI 扩展点: 是引擎预先定义好的一些控件插入的位置 (编辑器偏好设置 > 其他 > 开发者工具 > 显示UI扩展点 > true/Editor Preference > General > Miscellaneous > Developer Tools > Display UI Extension Pointers > true. 开启之后就可以看到对应的扩展点的名字) 
UE Editor 中常用的两种 UI 位置: ToolBar 和 Menu, 往往我们的新加入的编辑器功能总是会加入这两类位置
一个UI控件扩展对应了源码中的 `FExtender`, 以下代码对应了申请的扩展点
```Cpp
TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender);
// 添加一个扩展行为
MenuExtender->AddMenuExtension(
    "HelpApplication",  // 扩展点
    EExtensionHook::After, // 扩展的位置, 在 "HelpApplication" 之后
    PluginCommands, // 命令集 FUICommandList
    // 创建委托, 绑定函数 FMyEditorToolsModule::AddMenuExtension 创建按钮
    FMenuExtensionDelegate::CreateRaw(this, &FMyEditorToolsModule::AddMenuExtension)
);
```
其中 `FMyEditorToolsModule::AddMenuExtension` 是一个约定好的回调函数, 其接收一个 Builder, 由 Builder 来负责添加对应的 Entry.
这里实际上是一个职责分离的设计: 添加扩展是使用 Builder 来添加, 更加添加的位置不同, 使用 Builder 也不同, 但是大体来说常用只有 `FMenuBuilder` 和 `FToolBarBuilder`, 同时具体点击触发的逻辑是由之前绑定好的 `FCommandList` 的来决定的 (`MapAction` 接口), Builder 中的 Begin/End Section 中的 Section 就是一个扩展点. 
```Cpp
void FMyEditorToolsModule::AddMenuExtension(class FMenuBuilder& builder){
    builder.BeginSection(TEXT("MyButton"));
    // 绑定回调 PluginAction-> FExcuteAction::CreateRaw(this, &FMyEditorToolsModule::PluginButtonClicked); 
    // -> FMyEditorToolsModule::PluginButtonClicked
    builder.AddMenuEntry(FMyEditorToolbarButtonCommands::Get().PluginAction);
    // 在一开始的时候绑定了命令集
    /*
           PluginCommands->MapAction(
                FMyUICommands::Get().PluginAction,
                // 绑定回调
                FExcuteAction::CreateRaw(this, &FMyEditorToolsModule::PluginButtonClicked); 
                // 是否可以执行回调
                FCanExecuteAction()
                // 可选 FIsActionChecked 等回调用于 Toggle/Check 类型
            );
    */
    builder.EndSection();
}
```
在UE Editor 中有很多模块: 动画蓝图模块 `IAnimationBlueprintEditorModule`, 蓝图编辑器模块 `FBlueprintEditorModule`, 但是并不是所有模块都是可以扩展的, 同时如果该模块支持扩展菜单栏则会继承 `IHasMenuExtensibility` , 如果该支持扩展工具栏则会继承 `IHasToolBarExtensibility`
## Slot
在 UE 的UI中, 有的控件是可以添加子控件的, 如何描述子控件在本控件的各种位置, 就是通过 Slot (槽) 来进行指定的. 对于不同的控件, 一般都有自己的专属的 Slot, 所以这些 Slot 往往都会以内部类声明的方式出现, 同时继承个各种接口
## Geometry
Slot 提供了子控件位置信息说明, Geometry 则是通过 Slot 提供的信息最终计算出来的实际坐标. 每一帧会触发布局计算, 然后从根控件开始, 每次调用 `OnArrangeChildren` 进行空间的递归分配位置和空间, 然后对于每一个 Slot 解析其参数, 最后确定每一个Widget的大小和坐标, 为其他系统提供准备 (渲染, 碰撞, 输入)


# UE的游戏UI-UMG
Slate 是纯使用C++实现的轻量级框架, 但是在游戏中显示UI是实实在在的游戏内对象. 所以 UMG 本质上是使用 UObject 对Slate 控件的一种封装.
所以 UMG 控件和 Slate 的控件是对应的, 当我们想设计自己的 Slate 控件时, 可以在 UMG 界面设计完成之后, 统一翻译成 Slate 的声明式语法