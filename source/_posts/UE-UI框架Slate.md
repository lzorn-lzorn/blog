---
title: UE-UI 框架:Slate
date: 2025-12-10 21:29:58
tags: 
  - UE
  - C++
categories:
  - UE
cover: /lib/background/bg3.jpg
---
# UE的UI框架-Slate
UE 使用 C++ 实现了自己原生的一套UI界面, 这里的 C++ 是纯C++ 并不是使用了 UObject 的C++, 原因是 UObject 系统对于要求流程丝滑的 UI 界面而已太过沉重. 但是对于游戏中用户界面又必须要被整个GC所接管, 例如玩家的血条, 这里的血条控件应该和玩家单位使用同一套回收机制. 所以 UE 使用一个继承自 UObject 的类去包裹 Slate 的对象, 即 UMG 对象. 换句话说, UMG 对象只是 Slate 对象的容器, 真正的逻辑都执行在 Slate 中.

`FSlateApplication` 是 Slate 系统的入口. `FEngineLoop::Tick` 通过 `FSlateApplication::Tick` 渲染 Slate 已经执行其逻辑

### 控件树机制
控件树: 在UI设计中, 窗口之间的逻辑关系是一种树关系, 在不同的系统中使用到了不同的方式来组织管理控件树
`FWidgetPath` 是对于控件树的垂直切片(vertical slice), 是从某一个节点A开始到另一个可达子节点B路径的表示. `FArrangedChildren` 是内部的容器表示, 内部存有 `FArrangedWidget` (保有控件指针 `TSharedRef<SWidget>` 和 位置信息 `FGeometry`)
![FWidgetPath](/images/FWidgetPath.png)

### 屏幕网格 `FHittestGrid`
屏幕网格结构 `FHittestGrid`: 其内部有保有 `FCell` (本质上持有一个SWideget的句柄数组 `TArray<int32> WidgetIndexes`) 
![FHittestGrid示意图](/images/FHittestGrid.png)


## Slate的渲染流程
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
最后进入 `SlateRHIRender::DrawWindow_RenderThread` 中调用 `FRHICommandList::BeginDrawingViewport`(RHICmdList) ->
`FRHICommandList::RHIBeginDrawingViewport` (GetContext()), 进入真实运行的在当前系统的 RenderDynamicRHI 封装中 ->
`FRHICommandList::BeginRenderPass` (RHICmdList) ->
`FSlateRHIRenderingPolicy::DrawElements` (RenderingPolicy) 内部会设置各种和渲染有关的细节(Eg: 顶点着色器, 像素着色器, 纹理, 渲染资源), 其中每一次对 `FRHICommandList::DrawIndexedPrimitive` 的调用就是一次 DrawCall
## Slate的事件响应
Slate 系统的用于处理用户输入的类为 FSlateUser(不仅能处理输入)
`FSlateUser` 表示一个逻辑上的用户/输入上下文(包含指针位置、捕获、焦点路径、tooltip 状态、drag-drop 状态等), 一个 `FSlateUser` 会管理一个或多个指针索引（鼠标、触摸点等）以及与该用户相关的状态, 手柄会控制光标和指针, 所以插入手柄会增加一个 `FSlateUser`, 但是并不是随便插入一个交互设备就能添加一个 `FSlateUser`. 其主要负责 Cursor (光标):
- Focus: 聚焦
- Capture: 捕获
- DragDrop: 拖动
- Draw: 绘制
[Slate 的事件响应](https://blog.csdn.net/j756915370/article/details/121964442)

![点击事件响应流程](/images/点击事件响应流程.png)


Slate 中基类是 `SWidget`, 继承 `SWidget` 的有另外三个基础类:
- `SPanel` : 有多个子节点
- `SLeafWidget` : 没有子节点
- `SCompoundWidget` : 可以有一个子节点
# UE的游戏UI-UMG

## UI 滚动和点击
[知乎 - UMG拖拽、滚动、单击、双击兼容解决方案](https://zhuanlan.zhihu.com/p/1965075031336916853)

# 使用Slate
Slate 本质上是一个UI框架, 所以你可以基于 Slate 扩展蓝图工具, 亦或者基于 Slate 创建自己的 UMG 控件.
在 Slate 中提供了了对用户界面命令元数据的抽象: UI Command, 其描述了一个可在 UI 中表现, 可被快捷键触发, 可被菜单/工具栏/快捷键系统绑定的操作, 但它本身不包含执行逻辑. 并提供 命令提供名字, 显示文本, 提示(tooltip), 类型(按钮/切换/复选等)、以及默认快捷键等信息. 实际的执行行为由命令被映射到的 action/delegate(例如通过 `FUICommandList::MapAction` 提供的 `Execute/CanExecute/IsChecked` 委托)来实现

> [UI扩展点]
> 编辑器偏好设置 > 其他 > 开发者工具 > 显示UI扩展点 > true
> Editor Preference > General > Miscellaneous > Developer Tools > Display UI Extension Pointers > true.
> 开启之后, 通过这些绿色的字就说明UI可以扩展的位置.

> UI扩展点
> 编辑器偏好设置 > 其他 > 开发者工具 > 显示UI扩展点 > true
> Editor Preference > General > Miscellaneous > Developer Tools > Display UI Extension Pointers > true.
> 开启之后, 通过这些绿色的字就说明UI可以扩展的位置.

创建菜单项: 这里会涉及以下三个内容:
`MyEditorTools`: 用户自定义的插件
`FMyUICommands`: 用户自定义的UI Commands
`MyEditorToolsStyle`: 用户自定义插件的风格化文件
```Cpp
// 为了省地方就干脆写一起了
class MyEditorToolsStyle {
public:
    static void Initialize(){
        if(!Instance){
            Instance = Create();
            FSlateStyleRegistry::RegisterSlateStyle(*Instance);
        }
    }
    static void Shutdown(){
        FSlateStyleRegistry::UnRegisterSlateStyle(*Instance);
        ensure(Instance.IsUnique());
        Instance.Reset();
    }
    static void ReloadTextures();
    static const ISlateStyles& Get();
    static FName GetStyleSetName(){
        static FName StyleName(TEXT("MyEditorToolsStyle"));
        return StyleName;
    }
private:
    static TSharedRef<class FSlateStyleSet> Create();
    static TSharePtr<class FSlateStyleSet> Instance;
};
TSharedPtr< FSlateStyleSet > MyEditorToolsStyle::Instance = NULL;
#define IMAGE_BRUSH( RelativePath, ... ) \
    FSlateImageBrush( \
        Style->RootToContentDir( RelativePath, TEXT(".png") ), \
        __VA_ARGS__\
    )

#define BOX_BRUSH( RelativePath, ... ) FSlateBoxBrush( Style->RootToContentDir( RelativePath, TEXT(".png") ), __VA_ARGS__ )

#define BORDER_BRUSH( RelativePath, ... ) FSlateBorderBrush( Style->RootToContentDir( RelativePath, TEXT(".png") ), __VA_ARGS__ )

#define TTF_FONT( RelativePath, ... ) FSlateFontInfo( Style->RootToContentDir( RelativePath, TEXT(".ttf") ), __VA_ARGS__ )

#define OTF_FONT( RelativePath, ... ) FSlateFontInfo( Style->RootToContentDir( RelativePath, TEXT(".otf") ), __VA_ARGS__ )

const FVector2D Icon16x16(16.0f, 16.0f);
const FVector2D Icon20x20(20.0f, 20.0f);
const FVector2D Icon40x40(40.0f, 40.0f);

TSharedRef<FSlateStyleSet> MyEditorToolsStyle::Create(){
	TSharedRef FSlateStyleSet> Style = MakeShareable(
	    new FSlateStyleSet("MyEditorToolsStyle"));
	Style->SetContentRoot(
	    IPluginManager::Get()
	        .FindPlugin("MyEditorToolsStyle")
	        ->GetBaseDir() / TEXT("Resources")
	);
	Style->Set(
	    "MyEditorToolsStyle.PluginAction", 
	    new IMAGE_BRUSH(TEXT("ButtonIcon_40x"), 
	    Icon40x40)
	);
	return Style;
}

#undef IMAGE_BRUSH
#undef BOX_BRUSH
#undef BORDER_BRUSH
#undef TTF_FONT
#undef OTF_FONT
void MyEditorToolsStyle::ReloadTextures(){
	if (FSlateApplication::IsInitialized()){
		FSlateApplication::Get().GetRenderer()->ReloadTextureResources();
	}
}
const ISlateStyle& MyEditorToolsStyle::Get(){
	return *Instance;
}

class FMyUICommands : public TCommands<FMyUICommands>{
public:
    FMyUICommands()
        : TCommands<FMyUICommands>(
        /* 
            InContextName: 上下文的唯一名称 (FName), 
            在 FInputBindingManager 中索引/查找此命令集合 
        */
            TEXT("FMyUICommands"),
        /*
            InContextDesc: 上下文的本地化描述 (FText)
        */
            NSLOCTEXT(
                "Contexts",  // 是本地化命名空间
                "MyEditorTools",  // 键
                "MyEditorTools Plugin" // 默认文本
            ),
        /*
            InContextParent:上级上下文 (FName), 用于建立命令上下文层级/继承关系
            如果不需要父上下文, 用 NAME_None
        */
            NAME_None,
        /*
            InStyleSetName: 指定样式集
            用于在生成工具栏按钮/菜单项时查找图标(Slate 样式表)
            通常通过自定义模块 style 的 GetStyleSetName() 提供
        */
            MyEditorToolsStyle::GetStyleSetName()
        )
    {
    }
    
    /*
        Register() 会把命令上下文注册到全局的 FInputBindingManager
        以便于快捷键管理/重绑定/菜单自动显示快捷键等
    */
    virtual void RegisterCommands() override {
        UI_COMMAND(
        /*
            MemberVariableName: 要赋值的成员变量名(这里是 PluginAction)
            type: TSharedPtr<FUICommandInfo>
        */
            PluginAction, 
        /*
            FriendlyName: 命令在 UI 中显示的短名称
            type: FText 或 const char*，宏会包成 TEXT(...) / LOCTEXT
        */
            "MyEditorTools", 
        /*
            InDescription: 更详细的描述或 tooltip(显示在鼠标悬停等场景)
        */
            "Execute MyEditorTools Action",
        /*
            CommandType: EUserInterfaceActionType，指示命令类型:
                Button, ToggleButton, RadioButton, Check
            这影响菜单项/工具栏如何呈现以及是否支持切换/选中状态
        */
            EUserInterfaceActionType::Button,
        /*
            InDefaultChord (或 FInputGesture/FInputChord): 命令的默认快捷键
            如果为空或FInputGesture()则无默认快捷键
            FInputChord 表示按键组合
        */
            FInputGesture()
        )
    }
public:
    TSharedPtr<FUICommandInfo> PluginAction;
}

// 实际应该写 .cpp 中
static const FName MyEditorToolbarButtonTabName("MyEditorToolbarButton");
#define LOCTEXT_NAMESPACE "FMyEditorToolbarButtonModule"
class FMyEditorToolsModule : public IModuleInterface {
public:
    virtual void StartupModule() override{
        MyEditorToolsStyle::Initialize();
        MyEditorToolsStyle::ReloadTextures();
        
        FMyUICommands::Register();
    
        PluginCommands = MakeShareble(new FMyUICommands);
        PluginCommands->MapAction(
            FMyUICommands::Get().PluginAction,
            // 绑定回调
            FExcuteAction::CreateRaw(this, &FMyEditorToolsModule::PluginButtonClicked); 
            // 是否可以执行回调
            FCanExecuteAction()
            // 可选 FIsActionChecked 等回调用于 Toggle/Check 类型
        );
        
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
        FMyUICommands::Unregister();
    }
    void PluginButtonClicked(){
        // 点击按钮之后执行的逻辑
    }
private:
    void Register(){
        FToolMenuOwnerScoped OwnerScoped(this);
        {
            UToolMenu* menu = UToolMenus::Get()->ExtendMenu("MainFrame.MainMenu.Window");
            FToolMenuSection& section = Menu->FindOrAddSection("WindowLayout");
            section.AddMenuEntryWithCommandList(
                FMyUICommands:Get().PluginAction,
                PluginCommands
            );
        }
        {
            UToolMenu* menu = UToolMenus::Get()->ExtendMenu("AssetEditor.BlueprintEditor.MainMenu.Window");
            FToolMenuSection& section = Menu->FindOrAddSection("WindowLayout");
            section.AddMenuEntryWithCommandList(
                FMyUICommands:Get().PluginAction,
                PluginCommands
            );
        }
        {
            FBlueprintEditorModule& BOEditorModule = FModuleManager::LoadModuleChecked<FBlueprintEditorModule>("Kismet");
            BlueprintEditorModule
                .OnRegisterTabsForEditor()
                .AddRaw(this, &FMyEditorToolsModule::OnBPToolBarRegister);
        }
        {
            UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar");
            FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("Settings");
            FToolMenuEntry& Entry = Section.AddEntry(FToolMenuEntry::InitToolBarButton(FMyUICommands::Get().PluginAction));
            Entry.SetCommandList(PluginCommands);
            FToolMenuEntry& Entry1 = Section.AddEntry(
                FToolMenuEntry::InitToolBarButton(FMyUICommands::Get().PluginAction),
                TAttribute<FText>(),
                TAttribute<FText>(),
                TAttribute<FSlateIcon>(),
                NAME_None,
                "LastBuuuuutton"
            );
            Entry1.SetCommandList(PluginCommands);
            Entry1.InsertPosition.Position = EToolMenuInsertType::First;
        }
        {
            UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar");
            FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("File");
            FToolMenuEntry& Entry = Section.AddEntry(FToolMenuEntry::InitToolsBarButton(FMyUICommands::Get().PluginAction));
            Entry.SetCommandList(PluginCommands);
            Entry.InsertPosition.Position = EToolMenuInsertType::First;
        }
        {
            UToolMenu* ToolbarMenu = UToolMenus::Get();
            UToolMenu* MyMenu = ToolbarMenu->RegisterMenu("LevelEditor.MainMenu.MySubMenu");
            FToolMenuSection& Section = MyMenu->FindOrAddSection("MySection");
            Section.AddMenuEntryWitheCommandList(FMyUICommands::Get().PluginAction, PluginCommands);
            UToolMenu* MenuBar = UToolMenus::Get()->ExtendMenu("LevelEditor.MainMenu");
            MenuBar->AddSubMenu(
                "MainMenu",
                "MySection",
                "MySubMenu",
                LOCTEXT("MyMenu", "My")
            );
        }
        IAnimationBlueprintEditorModule& AnimationBlueprintEditorModule 
            = FModuleManager::LoadModuleChecked<IAnimationBlueprintEditorModule>("AnimationBlueprintEditor");
    	{
    		TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender);
    		MenuExtender->AddMenuExtension(
    		    "HelpApplication", 
    		    EExtensionHook::After, 
    		    PluginCommands, 
    		    FMenuExtensionDelegate::CreateRaw(this, &FMyEditorToolsModule::AddMenuExtension)
    		);
    		AnimationBlueprintEditorModule.GetMenuExtensibilityManager()->AddExtender(MenuExtender);
    	}
    	{
    		TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender);
    		MenuExtender->AddMenuBarExtension(
    		    "Help", 
    		    EExtensionHook::After, 
    		    PluginCommands, 
    		    FMenuBarExtensionDelegate::CreateRaw(this, &FMyEditorToolsModule::AddMenuBarExtension)
    		);
    		AnimationBlueprintEditorModule.GetMenuExtensibilityManager()->AddExtender(MenuExtender);
    	}

    	{
    		TSharedPtr<FExtender> MenuExtender = MakeShareable(new FExtender);
    		MenuExtender->AddToolBarExtension(
    		    "Settings", 
    		    EExtensionHook::After, 
    		    PluginCommands, 
    		    FToolBarExtensionDelegate::CreateRaw(this, &FMyEditorToolsModule::AddToolBarExtension)
    		);
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

    	{
    		FBlueprintEditorModule& BlueprintEditorModule = FModuleManager::LoadModuleChecked<FBlueprintEditorModule>(TEXT("Kismet"));
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
    void AddMenuExtension(FMenuBuilder& builder){
        Builder.BeginSection(TEXT("MyButton"));
	    Builder.AddMenuEntry(FMyUICommands::Get().PluginAction);
	    Builder.EndSection();
    }
    void AddMenuBarExtension(FMenuBuilder& builder){
        Builder.AddMenuEntry(FMyUICommands::Get().PluginAction);
    }
    void AddToolBarExtension(FMenuBuilder& builder){
        Builder.BeginSection(TEXT("MyButton"));
    	Builder.AddToolBarButton(FMyUICommands::Get().PluginAction);
    	Builder.EndSection();
    }
    void OnBPToolBarRegister(
        class FWorkflowAllowedTabSet& tabset, 
        FName name, 
        TSharedPtr<class FBlueprintEditor> BP
    ){
        TSharedPtr<FExtender> ToolBarExtender = MakeShareable(new FExtender);
    	ToolBarExtender->AddToolBarExtension(
    	    "Settings", 
    	    EExtensionHook::After, 
    	    PluginCommands, 
    	    FToolBarExtensionDelegate::CreateRaw(this, &FMyEditorToolsModule::AddToolBarExtension)
    	);
    	BP->AddToolbarExtender(ToolBarExtender);
    }
private:
    TSharedPtr<class FUICommandList> PluginCommands;
}
// 在 .cpp 最后注销
#undef LOCTEXT_NAMESPACE
IMPLEMENT_MODULE(FMyEditorToolsModule, MyEditorTool) // 模块名
```

