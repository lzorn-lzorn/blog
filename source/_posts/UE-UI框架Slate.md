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
渲染流程的调用
`FEngineLoop::Tick` -> `FSlateApplication::Tick`
-> `FSlateApplication::TickAndDrawWidgets`
-> `FSlateApplication::DrawWindows`
-> `FSlateApplication::DrawWindowAndChildren(CurrentWindow)`
-> `FSlateApplication::DrawWindowAndChildren(CurrentWindow->GetChildWindow())`
-> `SWindow::PaintWindow`
-> `FSlateInvlidationRoot::PaintInvalidationRoot`: FSlateInvalidationContext 是一次窗口/绘制遍历的"上下文对象", 携带了画布、绘制参数、剪裁/缩放信息和若干开关, 供 PaintInvalidationRoot(以及递归的子控件绘制逻辑) 使用来决定如何绘制/跳过, 如何构建 hit-test, 以及如何处理缓存的绘制元素
-> `SWindow::PaintSlowPath`: 慢路径绘制, 一次完整的, 保守的从根到叶的遍历——重新评估布局/可见性/几何, 重建/绘制每个 widget, 更新 hit-test 网格, 并重建或刷新绘制元素缓存(CachedElementData). 它保证在任何结构性或状态变化后画面正确, 但开销大; 因此只有在 fast-path 不可用或检测到需要时才使用.
对应的 `PaintFastPath`: 在没有结构性变化时尽量"重用上帧结果", 只做必要更新(Eg: 几何/变换、剪裁、z 层调整、对少量“最终更新”widget 的重绘、以及同步 hit-test)
-> `SWidget::Paint`: 准备绘制
-> `Virtual SWidget::OnPaint`: 真正的对应控件绘制
-> `FSlateDrawElement::MakeBox`: 工厂绘制方法, 向命令列表添加矩形类型的绘制.
`FSlateDrawElement` 是 Slate 渲染流水线里的最小“绘制命令”单元：框架把 UI 的视觉输出描述为按序列出的若干 `FSlateDrawElement`，这些元素最终被打包成 render batches 并提交到渲染器/GPU

实际上真正向GPU提交绘制命令并不在Slate层中, FSlateApplication 将所有数据准备好之后, 在 `FSlateApplication::PrivateDrawWindows` 中调用 `Renderer->DrawWindows`
最后进入 `SlateRHIRender::DrawWindow_RenderThread` 中调用 `FRHICommandList::BeginDrawingViewport` (RHICmdList) ->
`FRHICommandList::RHIBeginDrawingViewport` (GetContext()), 进入真实运行的在当前系统的 RenderDynamicRHI 封装中 ->
`FRHICommandList::BeginRenderPass` (RHICmdList) ->
`FSlateRHIRenderingPolicy::DrawElements` (RenderingPolicy) 内部会设置各种和渲染有关的细节(Eg: 顶点着色器, 像素着色器, 纹理, 渲染资源), 其中每一次对 `FRHICommandList::DrawIndexedPrimitive` 的调用就是一次 DrawCall
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

## UI 滚动和点击
[知乎 - UMG拖拽、滚动、单击、双击兼容解决方案](https://zhuanlan.zhihu.com/p/1965075031336916853)

# 使用Slate
Slate 本质上是一个UI框架, 所以你可以基于 Slate 扩展蓝图工具, 亦或者基于 Slate 创建自己的 UMG 控件.
在 Slate 中提供了了对用户界面命令元数据的抽象: UI Command, 其描述了一个可在 UI 中表现, 可被快捷键触发, 可被菜单/工具栏/快捷键系统绑定的操作, 但它本身不包含执行逻辑. 并提供 命令提供名字, 显示文本, 提示(tooltip), 类型(按钮/切换/复选等)、以及默认快捷键等信息. 实际的执行行为由命令被映射到的 action/delegate(例如通过 `FUICommandList::MapAction` 提供的 `Execute/CanExecute/IsChecked` 委托)来实现


编辑器菜单系统分为<font color="#c0504d">描述层</font>(UObject 数据), <font color="#c0504d">命令层</font>(命令定义 + 绑定), <font color="#c0504d">构建层</font>（MultiBox/blocks）和 <font color="#c0504d">渲染层</font>(Slate widgets)。`UToolMenus` 管理 `UToolMenu` (每个菜单的描述)，`TCommands` / `FUICommandInfo` + `FUICommandList` 提供命令定义与行为绑定，`UToolMenus` 将 `UToolMenu` 的 entries 转换为 `FMultiBox` / `FMultiBoxBlock`，再由 Slate 生成 `SWidget`（按钮、菜单等）。样式（FSlateStyleSet / FEditorStyle / 模块自己的 Style）提供图标与外观

>  `UToolMenu` 是对编辑器/工具内菜单的封装, 用于声明式地构建菜单, 工具栏及其子菜单. 
>  其记录了入口名 `SubMenuSourceEntryName`, 菜单名, 父菜单 `SubMenuParent`, 菜单类型 `EMultiBoxType`, 风格类型: `ISlateStyle`, 上下文 `FToolMenuContext`, 并包含若干多个 `FToolMenuSection` (每个 section 下有多个 entry). 
>  注意: 其本身是一中数据类. 真正的页签单例的管理器是 `UToolMenus` 通过 `UToolMenu::Get()` 获取其单例对象.

在实际的UE界面上, LevelEditorToolBar 是以下区域 (可以通过 Widget Reflector 来获取到具体是哪个类)
![LevelEditorToolBar.png](./images/LevelEditorToolBar.png)
如果要在这个区域注册自定义的按钮:
1. `UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar");` 从全局的菜单管理器中获取一份你需要插入位置(UI扩展点)的数据(`UToolMenu` 类型)
2. `FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("Settings");` 从这个数据中通过名字找到你要插入的对应Section(UI扩展点的一部分)
3. `FToolMenuEntry& Entry = Section.AddEntry(FToolMenuEntry::InitToolBarButton(FMyUICommands::Get().PluginAction));` 在这个 Section 中添加一个 Entry, 这里的 `FMyUICommands::Get().PluginAction` 就是你命令 Entry 入口的回调函数
4. `Entry.SetCommandList(PluginCommands);` 在这个 Entry 中设置命令, 其中 `TShardPtr<FMyUICommands> PluginCommands;` 是 `FUICommandList` 的子类

一个完整的流程如下: [例子](https://gitee.com/gunsun/PluginAndSlate)
1. 继承 TCommands, 定义自己的命令管理类 `class FMyToolBarCommands : public TCommonds<FMyToolBarCommands> {};` 这个类中定义 Label, ToolTip, `FInputChord` (快捷键), `FEditorStyle` (样式) 使用 `UI_COMMON` 宏来声明
```Cpp
class FMyUICommands : public TCommands<FMyUICommands>{
public:
    FMyUICommands()
        : TCommands<FMyUICommands>(
            // InContextName: 上下文的唯一名称 (FName), 
            // 在 FInputBindingManager 中索引/查找此命令集合 
            TEXT("FMyUICommands"),
            // InContextDesc: 上下文的本地化描述 (FText)
            NSLOCTEXT(
                "Contexts",  // 是本地化命名空间
                "MyEditorTools",  // 键
                "MyEditorTools Plugin" // 默认文本
            ),
        
            // InContextParent:上级上下文 (FName), 用于建立命令上下文层级/继承关系
            // 如果不需要父上下文, 用 NAME_None
            NAME_None,
            
            // InStyleSetName: 指定样式集
            // 用于在生成工具栏按钮/菜单项时查找图标(Slate 样式表)
            // 通常通过自定义模块 style 的 GetStyleSetName() 提供
            MyEditorToolsStyle::GetStyleSetName()
        ){}
    /*
        Register() 会把命令上下文注册到全局的 FInputBindingManager
        以便于快捷键管理/重绑定/菜单自动显示快捷键等
    */
    virtual void RegisterCommands() override {
        UI_COMMAND(
            // MemberVariableName: 要赋值的成员变量名(这里是 PluginAction)
            //type: TSharedPtr<FUICommandInfo>
            PluginAction, 
        
            // FriendlyName: 命令在 UI 中显示的短名称
            // type: FText 或 const char*，宏会包成 TEXT(...) / LOCTEXT
            "MyEditorTools", 
            
            // InDescription: 更详细的描述或 tooltip(显示在鼠标悬停等场景)
            "Execute MyEditorTools Action",
        
            // CommandType: EUserInterfaceActionType，指示命令类型:
            //   Button, ToggleButton, RadioButton, Check
            // 这影响菜单项/工具栏如何呈现以及是否支持切换/选中状态
            EUserInterfaceActionType::Button,

            // InDefaultChord (或 FInputGesture/FInputChord): 命令的默认快捷键
            // 如果为空或FInputGesture()则无默认快捷键
            // FInputChord 表示按键组合
            FInputGesture()
        )
    }
public:
    TSharedPtr<FUICommandInfo> PluginAction;
    TSharedPtr<class FUICommandList> PluginCommands;
}
```
2. 在自定义的模块继承 `IModuleInterface` 重写 `StartupModule`, 在其内部初始化并创建 `CommandList`. 并在 StartupModule 中调用我们自己的注册, 创建并绑定命令集. 在 `ShutdownModule` 中注销
```Cpp
// .cpp 开头注册
#define LOCTEXT_NAMESPACE "FMyEditorToolbarButtonModule"
class FMyEditorToolsModule : public IModuleInterface {
public:
    virtual void StartupModule() override {
        FMyToolbarCommands::Register(); // 
        PluginCommands = MakeShareable(new FUICommandList());
        PluginCommands->MapAction(
            FMyUICommands::Get().PluginAction,
            // 绑定回调
            FExecuteAction::CreateRaw(this, &FMyEditorToolsModule::PluginButtonClicked),
            // 是否可以执行回调
            FCanExecuteAction()
            // 可选 FIsActionChecked 等回调用于 Toggle/Check 类型
        );
        // 把 RegisterMenus 这个函数作为回调注册给 ToolMenus 的“启动回调”机制
        // 目的是在 ToolMenus 系统完成自身初始化后再去注册/扩展菜单
        // 菜单系统(UToolMenus)或目标菜单可能在编辑器启动时尚未初始化或尚未注册(加载顺序问题)
        // 通过注册 startup callback，确保在正确时机(ToolMenus 已就绪)调用 RegisterMenus 来实际将条目插进目标 UToolMenu，
        // 从而避免顺序 race 或找不到 MenuName 的问题
        UToolsMenus::RegisterStartupCallback(
            FSimpleMulticastDelegate::FDelegate::CreateRaw(
                this, 
                &FMyEditorToolsModule::RegisterMenus
            )
        );
    }
    virtual void ShutdownModule() override{
        UToolMenus::UnRegisterStartupCallback(this);
        UToolMenus::UnregisterOwner(this);
        FMyEditorToolsModule::Shutdown();
        PluginCommands.Reset();
        FMyToolbarCommands::Unregister();
    }
};
// 在 .cpp 最后注销
#undef LOCTEXT_NAMESPACE
IMPLEMENT_MODULE(FMyEditorToolsModule, MyEditorTool) // 模块名
```

具体的例子: 在引擎中已有的模块中添加菜单和工具: `FModuleManager::LoadModuleChecked` 获取模块. 需要注意的是: 不同的扩展会使用不同的回调函数和不同的Builder. 同时如果该模块支持扩展菜单栏则会继承 `IHasMenuExtensibility` , 如果该支持扩展工具栏则会继承 `IHasToolBarExtensibility`
```Cpp
void FMyToolbarCommands::Register(){
    {
        // 直接在主菜单中添加
        UToolMenu* ToolbarMenu = UToolMenus::Get();
        // 这里的 MySubMenu 是自定义的名字; 相当于在 LevelEditor 的 MainMenu(主菜单) 下开一个新的子菜单叫做 "MySubMenu"
        UToolMenu* MyMenu = ToolbarMenu->RegisterMenu("LevelEditor.MainMenu.MySubMenu");
        // 在自己的 "MySubMenu" 下加一个段 "MySection"
        FToolMenuSection& Section = MyMenu->FindOrAddSection("MySection");
        Section.AddMenuEntryWitheCommandList(FMyUICommands::Get().PluginAction, PluginCommands);
        
        // 在自定义的段下, 加入一个新的子菜单
        UToolMenu* MenuBar = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu");
        MenuBar->AddSubMenu(
            "MainMenu",
            "MySection",
            "MySubMenu",
            LOCTEXT("MyMenu", "My")
        );
    }
    {// Eg: 动画蓝图编辑器: 加载对应引擎的模块
        IAnimationBlueprintEditorModule& AnimationBlueprintEditorModule 
                = FModuleManager::LoadModuleChecked<IAnimationBlueprintEditorModule>("AnimationBlueprintEditor");
        // 构建扩展器
        TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender);
        // 添加一个扩展行为
        MenuExtender->AddMenuExtension(
            "HelpApplication",  // 扩展点
            EExtensionHook::After, // 扩展的位置, 在 "HelpApplication" 之后
            PluginCommands, // 命令集 FUICommandList
            // 创建委托, 绑定函数 FMyEditorToolsModule::AddMenuExtension 创建按钮
            FMenuExtensionDelegate::CreateRaw(this, &FMyEditorToolsModule::AddMenuExtension)
        );
        // 拿到该模块, 同时拿到扩展管理器, 添加扩展(只要能拿到这个管理器, 几乎所有的UI都可以添加)
        // 如果该模块可以扩展, 则会继承 IHasMenuExtensibility(可以改菜单条), IHasToolBarExtensibility(可以该工具条)
        AnimationBlueprintEditorModule.GetMenuExtensibilityManager()->AddExtender(MenuExtender);
    }
    /*
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
    */
    
    
    {
        IAnimationBlueprintEditorModule& AnimationBlueprintEditorModule 
                = FModuleManager::LoadModuleChecked<IAnimationBlueprintEditorModule>("AnimationBlueprintEditor");
        TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender);
        // 扩展菜单条 (文件, 编辑, 资产, 查看, 调试, ...) 工具栏上面的部分
        MenuExtender->AddMenuBarExtension(
            "Help", 
            EExtensionHook::After, 
            PluginCommands, 
            FMenuBarExtensionDelegate::CreateRaw(this, &FMyEditorToolsModule::AddMenuBarExtension)
            /*
                void FMyEditorToolsModule::AddMenuBarExtension(class FMenuBarBuilder& builder){
                    Builder.AddMenuEntry(FMyEditorToolbarButtonCommands::Get().PluginAction);
                }
            */
        );
        AnimationBlueprintEditorModule.GetMenuExtensibilityManager()->AddExtender(MenuExtender);
    }
    
    {
        IAnimationBlueprintEditorModule& AnimationBlueprintEditorModule 
                = FModuleManager::LoadModuleChecked<IAnimationBlueprintEditorModule>("AnimationBlueprintEditor");
        TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender);
        MenuExtender->AddToolBarExtension(
            "Settings", 
            EExtensionHook::After, 
            PluginCommands, 
            // 工具条, 就是菜单条下面那一栏
            FToolBarExtensionDelegate::CreateRaw(this, &FMyEditorToolsModule::AddToolBarExtension)
            // 对应的 builder 也是不同的
            // void FMyEditorToolsModule::AddToolBarExtension(class FToolBarBuilder& builder)
        );
        // 工具条的管理器
        AnimationBlueprintEditorModule.GetToolBarExtensibilityManager()->AddExtender(MenuExtender);
    }
    //http://wlosok.cz/editor-plugins-in-ue4-3-toolbar-button/
    /*
           If you try to do
           FBlueprintEditorModule& BlueprintEditorModule 
               = FModuleManager::LoadModuleChecked<FBlueprintEditorModule>(“Kismet”),
           the code will compile, but the engine will crash when starting up.
           One solution I found was to change LoadingPhase in .uplugin file to PostEngineInit.
    */
    
    { // 蓝图窗口: "Kismet", 模块的名字和UE的构建系统的名字是一样的, 在对应的 build.cs 中有这个名字则用这个模块
        FBlueprintEditorModule& BlueprintEditorModule 
            = FModuleManager::LoadModuleChecked<FBlueprintEditorModule>(TEXT("Kismet"));
        TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender);
        MenuExtender->AddMenuExtension(
            "HelpApplication", 
            EExtensionHook::After, 
            PluginCommands, 
            FMenuExtensionDelegate::CreateRaw(this, &FMyEditorToolsModule::AddMenuExtension)
        );
        BlueprintEditorModule.GetMenuExtensibilityManager()->AddExtender(MenuExtender);
    }
}
```

[UE4官方插件案例](https://github.com/ue4plugins/TextAsset)