---
title: UE-UI 框架:Slate
date: 2025-12-10 21:29:58
tags: 
  - UE
  - C++
categories:
  - 游戏开发 Unreal Engine
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

创建菜单项: 将表项注册至 `UToolMenus` 中
```Cpp
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
		*/
			FInputGesture()
		)
	}
public:
	TSharedPtr<FUICommandInfo> PluginAction;
}
```

这里涉及到三个内容:
MyEditorTools: 用户自定义的插件
FMyUICommands: 用户自定义的UI Commands
MyEditorToolsStyle: 用户自定义插件的风格化文件
他们之间的关系是:
1) 在模块的 StartupModule() 中注册命令集合（只需注册一次）：
   void FMyModule::StartupModule()
   {
	   FMyUICommands::Register(); // 创建并注册上下文到 FInputBindingManager
	   // 可选：在此处注册样式（图标等）
   }

2) 在模块或 UI 类中创建命令列表并把命令映射到具体执行回调：
   // 通常在 Widget/Tool 的构造或初始化中：
   TSharedRef<FUICommandList> CommandList = MakeShared<FUICommandList>();

   // MapAction 将 FUICommandInfo（元数据）与执行逻辑、是否可执行、是否选中等委托绑定
   CommandList->MapAction(
	   FMyUICommands::Get().PluginAction,
	   FExecuteAction::CreateSP(this, &FMyTool::ExecutePluginAction),      // 执行回调
	   FCanExecuteAction::CreateSP(this, &FMyTool::CanExecutePluginAction) // 可选：是否允许执行
	   // 可选 FIsActionChecked 等回调用于 Toggle/Check 类型
   );

3) 在菜单/工具栏生成时使用命令信息（它会自动显示文本和快捷键）：
   FMenuBuilder MenuBuilder(true, CommandList);
   MenuBuilder.AddMenuEntry( FMyUICommands::Get().PluginAction );

   或者在工具栏里：
   FToolBarBuilder ToolBarBuilder(CommandList, FMultiBoxCustomization());
   ToolBarBuilder.AddToolBarButton(FMyUICommands::Get().PluginAction);

   注意：MenuBuilder/ToolBarBuilder 会使用当前绑定（CommandList）来决定是否绘制启用/禁用/选中状态，
		 并显示当前的快捷键绑定（不是仅显示默认快捷键，而是显示用户可能重绑定后的实际快捷键）。

4) 访问命令集合：
   // 确保已注册后可安全调用：
   const FMyUICommands& Commands = FMyUICommands::Get();

   // 获取命令的友好名（FText）：
   FText Friendly = Commands.PluginAction->GetLabel();

5) 注销（通常在模块的 ShutdownModule() 里）：
   void FMyModule::ShutdownModule()
   {
	   FMyUICommands::Unregister();
	   // 注：Unregister 会从 FInputBindingManager 移除上下文并广播 CommandsChanged。
   }

6) 关于本地化（LOCTEXT/NSLOCTEXT）：
   - UI_COMMAND 宏期望 LOCTEXT_NAMESPACE 在当前翻译单元已定义（宏内部使用 LOCTEXT 来创建本地化文本）。
   - 上文示例把上下文描述用 NSLOCTEXT 明确写在构造器中，但 UI_COMMAND 仍将使用 LOCTEXT_NAMESPACE。
   - 典型做法是在实现 RegisterCommands 的 .cpp 文件顶部写：
	   #define LOCTEXT_NAMESPACE "FMyUICommands"
	 并在文件末尾写：
	   #undef LOCTEXT_NAMESPACE

7) 关于快捷键（FInputGesture / FInputChord）：
   - FInputChord 表示按键组合（例如 Ctrl+Shift+S）。FInputGesture 是较高层的通用类型（在不同引擎版本中细节可能不同）。
   - 在 UI_COMMAND 中传入空构造表示没有默认绑定；用户或系统可以在运行时通过 FInputBindingManager 修改绑定。

总结：
- UI Command (FUICommandInfo) = 命令的元数据（显示名/描述/默认快捷键/类型/样式信息）。
- TCommands<T> 用于在模块中集中声明和注册这些命令集合（并以上下文名称在全局绑定管理器中注册以便复用）。
- 命令本身不包含执行逻辑；要把命令变为可执行，需要用 FUICommandList::MapAction 将执行委托绑定到命令上，然后将 CommandList 提供给菜单/工具栏构建器或输入处理逻辑。
