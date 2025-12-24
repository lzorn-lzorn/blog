---
title: UE-UI框架Slate{1}-使用Slate扩展UI
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
# 使用Slate
Slate 本质上是一个UI框架, 所以你可以基于 Slate 扩展蓝图工具, 亦或者基于 Slate 创建自己的 UMG 控件.
在 Slate 中提供了了对用户界面命令元数据的抽象: UI Command, 其描述了一个可在 UI 中表现, 可被快捷键触发, 可被菜单/工具栏/快捷键系统绑定的操作, 但它本身不包含执行逻辑. 并提供 命令提供名字, 显示文本, 提示(tooltip), 类型(按钮/切换/复选等)、以及默认快捷键等信息. 实际的执行行为由命令被映射到的 action/delegate(例如通过 `FUICommandList::MapAction` 提供的 `Execute/CanExecute/IsChecked` 委托)来实现


# 使用SWidget的宏
在 `DeclarativeSyntaxSupport.h` 中定义了大量 Slate 系统中声明 `SWidget` 需要使用的宏, 在我们定义自己的 Slate Widget 的时候需要使用到这些宏才能和 Slate 中其他组件相互配合, 同时也减少重复代码的方式.
## SLATE_BEGIN_ARGS() And SLATE_END_ARGS()
`SLATE_BEGIN_ARGS()` And `SLATE_END_ARGS()` 是 SWidget 中用于声明其类内成员变量使用的宏, 其用法如下:
```Cpp
/**  
 * Widget authors can use SLATE_BEGIN_ARGS and SLATE_END_ARS to add support 
 * for widget construction via SNew and SAssignNew. 
 * e.g. 
 * SLATE_BEGIN_ARGS( SMyWidget )  
 *         , _PreferredWidth( 150.0f ) 
 *         , _ForegroundColor( FLinearColor::White ) 
 *          {} 
 *
 *     SLATE_ATTRIBUTE(float, PreferredWidth) 
 *     SLATE_ATTRIBUTE(FSlateColor, ForegroundColor) 
 * SLATE_END_ARGS() 
 */
```
其内部会给你的类定义一个 `FArguments` 作为 SWidget 的内置参数(命名参数模式), 只有定义了 `FArguments` 才可以使用 `SNew()` 和 `SAssignNew()` 来创建 `SWidget` 对象, 具体来说: 
```Cpp
class SMySlider {
    SLATE_BEGIN_ARGS( SMyWidget ) {/* 我们自己写的括号 */}
    SLATE_END_ARGS()
};
// 等价于
class SMySlider {
public:
    // SLATE_BEGIN_ARGS
    struct FArguments : public TSlateBaseNamedArgs<SMySlider> { 
        typedef FArguments WidgetArgsType;
        typedef SMySlider WidgetType;
        FORCENOINLINE FArguments()
        {/* 我们自己写的括号 */}
    }; // SLATE_END_ARGS()
};
```
在这两个 Beign 和 End 开始定义参数, 事件 等等
## `SLATE_ARGUMENT(ArgType, ArgName)`
该宏会定义一个变量和一个同名的Set方法:
```Cpp
SLATE_ARGUMENT(ArgType, ArgName)        // SLATE_ARGUMENT(int, Value)
// 等价于
ArgType _ArgName;                       // int _Value; ArgType _##ArgName
// SLATE_PRIVATE_ARGUMENT_FUNCTION
WidgetArgsType& Value(ArgType InArg)    // WidgetArgsType& Value(int InArg)
{
    _Value = InArg; // _Value 是 _##ArgName 拼接出来的
    // Me() 定义于 TSlateBaseNamedArgs 中用于 链式调用的
    return static_cast<WidgetArgsType*>(this)->Me(); 
}
```

## `SLATE_ATTRIBUTE(AttrType, AttrName)`
Attribute 的语义既可以是一个固定参数(value), 又可以是一个动态绑定(function); 其目的是使得类内成员参数既可以支持静态常量, 又支持随时绑定回调(动态更新), 并在构造接口上以链式调用的方式暴露(`SNew(MyWidget).MyAttr(...)`)
```Cpp
TAttribute<Type> _Attr;
WidgetArgsType& Attr(TAttribute<Type> InAttribute)
{
    _Attr = MoveTemp(InAttribute);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <typename... VarTypes>
WidgetArgsType& Attr_Static(
    TIdentity_T<typename TAttribute<Type>::FGetter::template TFuncPtr<VarTypes...>> InFunc,
    VarTypes... Vars)
{
    _Attr = TAttribute<Type>::Create(TAttribute<Type>::FGetter::CreateStatic(InFunc, Vars...));
    return static_cast<WidgetArgsType*>(this)->Me();
}

// 绑定 Lambda
WidgetArgsType& Attr_Lambda(TFunction<Type(void)>&& InFunctor)
{
    _Attr = TAttribute<float>::Create(Forward<TFunction<Type(void)>>(InFunctor));
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& Attr_Raw(UserClass* InUserObject,
     typename TAttribute<Type>::FGetter::template TConstMethodPtr<UserClass, VarTypes...>
     InFunc, VarTypes... Vars)
{
    _Attr = TAttribute<Type>::Create(TAttribute<Type>::FGetter::CreateRaw(InUserObject, InFunc, Vars...));
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& Attr(TSharedRef<UserClass> InUserObjectRef,
    typename TAttribute<Type>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc,
    VarTypes... Vars)
{
    _Attr = TAttribute<Type>::Create(TAttribute<Type>::FGetter::CreateSP(InUserObjectRef, InFunc, Vars...));
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& Attr(UserClass* InUserObject,
    typename TAttribute<Type>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc,
    VarTypes... Vars)
{
    _Attr = TAttribute<Type>::Create(TAttribute<Type>::FGetter::CreateSP(InUserObject, InFunc, Vars...));
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& Attr_UObject(UserClass* InUserObject,
    typename TAttribute<Type>::FGetter::template TConstMethodPtr<UserClass, VarTypes...>
    InFunc, VarTypes... Vars)
{
    _Attr = TAttribute<Type>::Create(TAttribute<Type>::FGetter::CreateUObject(InUserObject, InFunc, Vars...));
    return static_cast<WidgetArgsType*>(this)->Me();
}
```
`SLATE_ATTRIBUTE` 本质就是定义一个 TAttibute 对象, `TAttribute<T>` 是 Slate 的"属性"容器: 要么保存一个固定的值, 要么保存一个getter delegate(返回 T 的函数/方法). 使用者通过 `Get()` 取得当前最新的值. UI 的属性发生变化是 UI 不会主动更新, `TAttribute<T>` 本质上就是在解决这个问题, 通过绑定各种回调, 来保证调用 `Get()` 时其值一直是最新的, 例如
```Cpp
TAttribute<FText> Label;

SNew(SMyWidget)
.Label_Lambda([]() -> FText {
    return FText::FromString(FDateTime::Now().ToString());
})
// TSharedRef Provider = MakeShared<MyProvider>();
.Label(Provider, &MyProvider::GetLabel)
// UMyObject* MyObject = xxx;
.Label_UObject(MyObject, &MyObject::GetLabel)
// 每次 Get() 的时候, 获取当前最新的值
```
如果属性背后的数据改变时, 但是没有触发 UI 的重新绘制, UI不会自动重新获取值并更新, 此时在数据改变的调用 `Widget->Invalidate(EInvalidateWidgetReason::Paint` 就可以强制重新渲染, 但是不要在 FGetter() 中调用开销大的函数, 因为每帧都会调用, 对于开销大的计算要缓存其值.

## SLATE_EVENT(DelegateName, EventName)
这个语义与 `SLATE_ATTRIBUTE(AttrType, AttrName)` 是正好相反的, `SLATE_ATTRIBUTE(AttrType, AttrName)` 是通过 Getter 来主动拉去变化, 但是 SLATE_EVENT 会定义一个事件, 这个是推送式的, 即 `SWidget` 在某个时间主动调用 delegate 来通知外部, 而 `SLATE_ATTRIBUTE` 是 `SWidget` 主动拉去某个值的变化.
该宏希望, 让 widget 的创建者把回调注入到 widget 中, 例如 `SNew(SMyWidget).OnClicked(...)`
```Cpp
SLATE_EVENT(FOnExSliderValueChangedNative, OnValueChanged) 
// 等价于
WidgetArgsType& OnValueChanged(const FOnExSliderValueChangedNative& InDelegate)
{
    _OnValueChanged = InDelegate;
    return static_cast<WidgetArgsType*>(this)->Me();
}

WidgetArgsType& OnValueChanged(FOnExSliderValueChangedNative&& InDelegate)
{
    _OnValueChanged = MoveTemp(InDelegate);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <typename StaticFuncPtr, typename... VarTypes>
WidgetArgsType& OnValueChanged_Static(StaticFuncPtr InFunc, VarTypes... Vars)
{
    _OnValueChanged = FOnExSliderValueChangedNative::CreateStatic(InFunc, Vars...);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <typename FunctorType, typename... VarTypes>
WidgetArgsType& OnValueChanged_Lambda(FunctorType&& InFunctor, VarTypes... Vars)
{
    _OnValueChanged = FOnExSliderValueChangedNative::CreateLambda(Forward<FunctorType>(InFunctor), Vars...);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& OnValueChanged_Raw(UserClass* InUserObject,
                                   typename FOnExSliderValueChangedNative::template TMethodPtr<
                                       UserClass, VarTypes...> InFunc, VarTypes... Vars)
{
    _OnValueChanged = FOnExSliderValueChangedNative::CreateRaw(InUserObject, InFunc, Vars...);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& OnValueChanged_Raw(UserClass* InUserObject,
                                   typename FOnExSliderValueChangedNative::template TConstMethodPtr<
                                       UserClass, VarTypes...> InFunc, VarTypes... Vars)
{
    _OnValueChanged = FOnExSliderValueChangedNative::CreateRaw(InUserObject, InFunc, Vars...);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& OnValueChanged(TSharedRef<UserClass> InUserObjectRef,
                               typename FOnExSliderValueChangedNative::template TMethodPtr<UserClass, VarTypes...>
                               InFunc, VarTypes... Vars)
{
    _OnValueChanged = FOnExSliderValueChangedNative::CreateSP(InUserObjectRef, InFunc, Vars...);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& OnValueChanged(TSharedRef<UserClass> InUserObjectRef,
                               typename FOnExSliderValueChangedNative::template TConstMethodPtr<
                                   UserClass, VarTypes...> InFunc, VarTypes... Vars)
{
    _OnValueChanged = FOnExSliderValueChangedNative::CreateSP(InUserObjectRef, InFunc, Vars...);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& OnValueChanged(UserClass* InUserObject,
                               typename FOnExSliderValueChangedNative::template TMethodPtr<UserClass, VarTypes...>
                               InFunc, VarTypes... Vars)
{
    _OnValueChanged = FOnExSliderValueChangedNative::CreateSP(InUserObject, InFunc, Vars...);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& OnValueChanged(UserClass* InUserObject,
                               typename FOnExSliderValueChangedNative::template TConstMethodPtr<
                                   UserClass, VarTypes...> InFunc, VarTypes... Vars)
{
    _OnValueChanged = FOnExSliderValueChangedNative::CreateSP(InUserObject, InFunc, Vars...);
    return static_cast<WidgetArgsType*>(this)->Me();
}

template <class UserClass, typename... VarTypes>
WidgetArgsType& OnValueChanged_UObject(UserClass* InUserObject,
                                       typename FOnExSliderValueChangedNative::template TMethodPtr<
                                           UserClass, VarTypes...> InFunc, VarTypes... Vars)
{
    _OnValueChanged = FOnExSliderValueChangedNative::CreateUObject(InUserObject, InFunc, Vars...); 
    return static_cast<WidgetArgsType*>(this)->Me();
}
```
对于上述例子中 `SLATE_EVENT(FOnMyWidgetValueChangedNative, OnValueChanged)` 本质上就是定义所有可以定义 `FOnMyWidgetValueChangedNative` 的方式, 其中 `DECLARE_DELEGATE_OneParam(FOnExSliderValueChangedNative, float);` 是定义的一个委托 `TDelegate<void(float)>`. 
## SLATE_NAMED_SLOT 和 SLATE_DEFAULT_SLOT
在 FArgument 中声明一个命名插槽, 该插槽只接受一个子控件, 允许 `SNew(...).SlotName()[ ... ]` 的语法中把一个子节点提供给该命名插槽

# Slate 框架中声明式语法, 设计自己的Slate-UMG控件
Slate 中每一个控件的操作在 UMG 的界面都可以找到对应, 所以对于常见的 UI 设计, 可以使用 UMG 设计, 然后再将其翻译为 Slate 的声明式语法. 对于 Slate 的声明式语法例如:
在以下自定义控件中, 有一系列子控件的 Slot: `ChildSlot` 该自定义插件继承于 `class SCompoundWidget;` 其中定义了 `FCompoundWidgetOneChildSlot ChildSlot;`
在以下程序中有两个操作符重载:
- `WidgetArgsType& operator + (typename SlotType::FSlotArguments& SlotToAdd)`
- `typename SlotType::FSlotArguments& operator[](TSharedRef<SWidget>&& InChildWidget)`

在 `[]` 中只可以是一个 `TSharedRef<SWidget>` 类型, 同时 `+` 后的运算符只能是一个 Slot. 
同时在 `DeclarativeSyntaxSupport.h` 中可以看到对于各种宏的使用:
```Cpp
/**  
 * Slate widgets are constructed through SNew and SAssignNew. 
 * e.g. 
 * TSharedRef<SButton> MyButton = SNew(SButton);
 *      or 
 * TSharedPtr<SButton> MyButton; 
 * SAssignNew( MyButton, SButton );
 * Using SNew and SAssignNew ensures that widgets are populated |
 * 补充另一个例子:
 * SHorizontalBox::FArguments BoxArgs;
 * ((FSlateBaseNamedArgs&)BoxArgs) = (FSlateBaseNamedArgs)InArgs;
 * TSharedRef<SHorizontalBox> HorizontalBox = SArgumentNew(BoxArgs, SHorizontalBox);  
 */
```
换句话说 `SNew(SWidget)` 返回的是通过一个类型 `SWidget` 创建一个局部对象; 而 `SAssignNew( SMyWidget, SWidget )` 可以将一个对象赋值给另一个对象; `SArgumentNew()` 则是用已经构造好的命名参数对象( `WidgetType::FArguments` ) 来构造 `SWidget`
- `SNew` 会构造一个空对象
- `SArgumentNew()` 用已有的参数构造一个对象
- `SAssignNew()` 构造一个对象并赋值给另一个已有的对象
```Cpp
ChildSlot  
[  
    SNew(SHorizontalBox)  // 构造一个空的 SHorizontalBox 对象
    + SHorizontalBox::Slot()  // 给 SNew(SHorizontalBox) 添加了一个 Slot 
    .AutoWidth()  // 设置 Slot 的各种属性
    .VAlign(VAlign_Center)  
    .Padding(2.0f)  
    [  // 在 Slot 中添加一个子控件
       SAssignNew(SubButton, SButton)  
       .OnClicked(this, &SExSlider::HandleSubClicked)  // 绑定 Clicked 回调, 返回 FArguments
       [  // SetText() 是 TextBlock 自带的方式, 不是 Slot 中的方法
          SNew(STextBlock).Text(FText::FromString(TEXT("-")))  
       ]  
    ]  
];
```
对应如下图
![[Slate和UMG操作的对应.png]]

## 一个完整的 FArgument
```Cpp
// 完整展开示例：不使用任何 SLATE_* 宏，手工实现与宏等价的 FArguments。
// 说明：这是为一个示例 Widget 名为 SMyWidget 展开的 FArguments 实现。
//       代码尽量逐项对应宏中会生成的成员与方法，并在注释中指明“对应哪个宏”。
// 注意：此文件演示 FArguments 的结构与方法，不包含 SMyWidget 的其它实现。

#pragma once

#include "CoreMinimal.h"
#include "Misc/Attribute.h"
#include "Layout/Visibility.h"
#include "Layout/Clipping.h"
#include "Widgets/WidgetPixelSnapping.h"
#include "Layout/FlowDirection.h"
#include "Rendering/SlateRenderTransform.h"
#include "GenericPlatform/ICursor.h"
#include "Types/ISlateMetaData.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/Accessibility/SlateWidgetAccessibleTypes.h"
#include "Templates/Identity.h"
#include "Delegates/Delegate.h"
#include "Templates/SharedPointer.h"
#include "Templates/Function.h"

// 前向声明（示例用）
class IToolTip;
class SUserWidget;
class SWidget;

/**
 * 一个始终有效的 widget 引用（等价于文件中 TAlwaysValidWidget）。
 * 它用于命名槽默认值为 SNullWidget::NullWidget，避免空检查。
 */
struct TAlwaysValidWidget
{
    TAlwaysValidWidget()
        : Widget(SNullWidget::NullWidget)
    {
    }

    TSharedRef<SWidget> Widget;
};


/**
 * NamedSlotProperty 模板，用于实现 .SlotName()[ child ] 的语法。
 * 它与文件中 NamedSlotProperty 的作用一致。
 */
template<class DeclarationType>
struct NamedSlotProperty
{
    NamedSlotProperty(DeclarationType& InOwnerDeclaration, TAlwaysValidWidget& InSlotContent)
        : OwnerDeclaration(InOwnerDeclaration)
        , SlotContent(InSlotContent)
    {}

    // 当 DSL 写 .SlotName()[ child ] 时会调用此 operator[]
    DeclarationType& operator[](const TSharedRef<SWidget>& InChild)
    {
        SlotContent.Widget = InChild;
        return OwnerDeclaration;
    }

private:
    DeclarationType& OwnerDeclaration;
    TAlwaysValidWidget& SlotContent;
};


/**
 * 完整展开的 FArguments（为 SMyWidget 展开）。
 */
struct SMyWidget_FArguments
{
    // typedefs 来模仿宏产生的类型别名
    typedef SMyWidget_FArguments WidgetArgsType;
    typedef void WidgetType; // 占位（实际为 SMyWidget），仅为与宏语义对齐

    // ---- 构造（宏 SLATE_BEGIN_ARGS 可能会生成默认值初始化） ----
    SMyWidget_FArguments()
        : _IsEnabled(TAttribute<bool>(true))  // SLATE_PRIVATE_ATTRIBUTE_VARIABLE(bool, IsEnabled) = true;
        , _ForceVolatile(false)               // SLATE_PRIVATE_ARGUMENT_VARIABLE(bool, ForceVolatile) = false;
        , _EnabledAttributesUpdate(true)      // SLATE_PRIVATE_ARGUMENT_VARIABLE(bool, EnabledAttributesUpdate) = true;
        , _Clipping(EWidgetClipping::Inherit)               // default
        , _PixelSnappingMethod(EWidgetPixelSnapping::Inherit)
        , _FlowDirectionPreference(EFlowDirectionPreference::Inherit)
        , _RenderOpacity(1.f)
        , _RenderTransformPivot(FVector2D::ZeroVector)
        , _AccessibleParams(TOptional<FAccessibleWidgetData>())
    {
    }

    // ---- 私有数据成员（对应 SLATE_PRIVATE_ATTRIBUTE_VARIABLE / SLATE_PRIVATE_ARGUMENT_VARIABLE 等） ----

    // Attributes (可绑定/可为常量) - 对应 SLATE_PRIVATE_ATTRIBUTE_VARIABLE
    TAttribute<FText>                         _ToolTipText;        // SLATE_PRIVATE_ATTRIBUTE_VARIABLE(FText, ToolTipText)
    TAttribute<TSharedPtr<IToolTip>>          _ToolTip;            // SLATE_PRIVATE_ATTRIBUTE_VARIABLE(TSharedPtr<IToolTip>, ToolTip)
    TAttribute<TOptional<EMouseCursor::Type>> _Cursor;             // SLATE_PRIVATE_ATTRIBUTE_VARIABLE(TOptional<EMouseCursor::Type>, Cursor)
    TAttribute<bool>                          _IsEnabled;          // SLATE_PRIVATE_ATTRIBUTE_VARIABLE(bool, IsEnabled) = true;
    TAttribute<EVisibility>                   _Visibility;         // SLATE_PRIVATE_ATTRIBUTE_VARIABLE(EVisibility, Visibility) = Visible;
    // Arguments (值型，仅值，不是 Attribute)
    bool                                      _ForceVolatile;      // SLATE_PRIVATE_ARGUMENT_VARIABLE(bool, ForceVolatile) = false;
    bool                                      _EnabledAttributesUpdate; // SLATE_PRIVATE_ARGUMENT_VARIABLE(bool, EnabledAttributesUpdate) = true;
    EWidgetClipping                           _Clipping;           // SLATE_PRIVATE_ARGUMENT_VARIABLE(EWidgetClipping, Clipping) = Inherit;
    EWidgetPixelSnapping                      _PixelSnappingMethod;// SLATE_PRIVATE_ARGUMENT_VARIABLE(EWidgetPixelSnapping, PixelSnappingMethod) = Inherit;
    EFlowDirectionPreference                  _FlowDirectionPreference; // SLATE_PRIVATE_ARGUMENT_VARIABLE(EFlowDirectionPreference, FlowDirectionPreference) = Inherit;
    float                                     _RenderOpacity;      // SLATE_PRIVATE_ARGUMENT_VARIABLE(float, RenderOpacity) = 1.f;
    // 更多 attributes
    TAttribute<TOptional<FSlateRenderTransform>> _RenderTransform;    // SLATE_PRIVATE_ATTRIBUTE_VARIABLE(TOptional<FSlateRenderTransform>, RenderTransform)
    TAttribute<FVector2D>                        _RenderTransformPivot; // SLATE_PRIVATE_ATTRIBUTE_VARIABLE(FVector2D, RenderTransformPivot) = ZeroVector

    // arguments
    FName                                        _Tag;                // SLATE_PRIVATE_ARGUMENT_VARIABLE(FName, Tag)
    TOptional<FAccessibleWidgetData>             _AccessibleParams;   // SLATE_PRIVATE_ARGUMENT_VARIABLE(TOptional<FAccessibleWidgetData>, AccessibleParams)
    TAttribute<FText>                            _AccessibleText;     // SLATE_PRIVATE_ATTRIBUTE_VARIABLE(FText, AccessibleText)

    // MetaData array
    TArray<TSharedRef<ISlateMetaData>>           MetaData;

    // ---- Named slots / Default slot (对应 SLATE_NAMED_SLOT / SLATE_DEFAULT_SLOT) ----
    // 示例：我们提供两个命名插槽：Header（命名插槽）与 Content（默认插槽）
    TAlwaysValidWidget                           _Header;   // 对应 SLATE_NAMED_SLOT(..., Header)
    TAlwaysValidWidget                           _Content;  // 对应 SLATE_NAMED_SLOT(..., Content) / SLATE_DEFAULT_SLOT(..., Content)

    // ---- 如果需要 event/delegate 成员，此处可声明 Delegate 类型成员（对应 SLATE_EVENT） ----
    // 示例：声明一个事件成员（此处注释，具体 delegate type 依据需求声明）
    // FSimpleDelegate _OnSomething; // SLATE_EVENT(FSimpleDelegate, OnSomething)

    // ---- 以下为链式设置方法（对应 SLATE_PRIVATE_ATTRIBUTE_FUNCTION / SLATE_PRIVATE_ARGUMENT_FUNCTION / SLATE_NAMED_SLOT 实现） ----

    // Me() 方法（对应 TSlateBaseNamedArgs::Me）
    WidgetArgsType& Me()
    {
        return *this;
    }

    // ----------------------------
    // Attribute setters (示例写法：为每个 attribute 提供多种绑定 overload，与宏的生成保持一致)
    //
    // 对应宏：SLATE_PRIVATE_ATTRIBUTE_FUNCTION(AttrType, AttrName)
    // 生成的变体包括：
    //  - AttrName(TAttribute<AttrType> InAttribute)
    //  - AttrName_Static(...)
    //  - AttrName_Lambda(...)
    //  - AttrName_Raw(...)
    //  - AttrName(TSharedRef<UserClass>, MethodPtr)
    //  - AttrName(UserClass*, MethodPtr)
    // ----------------------------

    // ToolTipText（示例）
    WidgetArgsType& ToolTipText(TAttribute<FText> InAttribute)
    {
        _ToolTipText = MoveTemp(InAttribute);
        return Me();
    }

    template<typename... VarTypes>
    WidgetArgsType& ToolTipText_Static(TIdentity_T<typename TAttribute<FText>::FGetter::template TFuncPtr<VarTypes...>> InFunc, VarTypes... Vars)
    {
        _ToolTipText = TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateStatic(InFunc, Vars...));
        return Me();
    }

    WidgetArgsType& ToolTipText_Lambda(TFunction<FText(void)>&& InFunctor)
    {
        _ToolTipText = TAttribute<FText>::Create(MoveTemp(InFunctor));
        return Me();
    }

    template<class UserClass, typename... VarTypes>
    WidgetArgsType& ToolTipText_Raw(UserClass* InUserObject, typename TAttribute<FText>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _ToolTipText = TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(InUserObject, InFunc, Vars...));
        return Me();
    }

    template<class UserClass, typename... VarTypes>
    WidgetArgsType& ToolTipText(TSharedRef<UserClass> InUserObjectRef, typename TAttribute<FText>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _ToolTipText = TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateSP(InUserObjectRef, InFunc, Vars...));
        return Me();
    }

    template<class UserClass, typename... VarTypes>
    WidgetArgsType& ToolTipText(UserClass* InUserObject, typename TAttribute<FText>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _ToolTipText = TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateSP(InUserObject, InFunc, Vars...));
        return Me();
    }

    // ToolTip attribute (TSharedPtr<IToolTip>)
    WidgetArgsType& ToolTip(TAttribute<TSharedPtr<IToolTip>> InAttribute)
    {
        _ToolTip = MoveTemp(InAttribute);
        return Me();
    }
    template<typename... VarTypes>
    WidgetArgsType& ToolTip_Static(TIdentity_T<typename TAttribute<TSharedPtr<IToolTip>>::FGetter::template TFuncPtr<VarTypes...>> InFunc, VarTypes... Vars)
    {
        _ToolTip = TAttribute<TSharedPtr<IToolTip>>::Create(TAttribute<TSharedPtr<IToolTip>>::FGetter::CreateStatic(InFunc, Vars...));
        return Me();
    }
    WidgetArgsType& ToolTip_Lambda(TFunction<TSharedPtr<IToolTip>(void)>&& InFunctor)
    {
        _ToolTip = TAttribute<TSharedPtr<IToolTip>>::Create(MoveTemp(InFunctor));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& ToolTip_Raw(UserClass* InUserObject, typename TAttribute<TSharedPtr<IToolTip>>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _ToolTip = TAttribute<TSharedPtr<IToolTip>>::Create(TAttribute<TSharedPtr<IToolTip>>::FGetter::CreateRaw(InUserObject, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& ToolTip(TSharedRef<UserClass> InUserObjectRef, typename TAttribute<TSharedPtr<IToolTip>>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _ToolTip = TAttribute<TSharedPtr<IToolTip>>::Create(TAttribute<TSharedPtr<IToolTip>>::FGetter::CreateSP(InUserObjectRef, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& ToolTip(UserClass* InUserObject, typename TAttribute<TSharedPtr<IToolTip>>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _ToolTip = TAttribute<TSharedPtr<IToolTip>>::Create(TAttribute<TSharedPtr<IToolTip>>::FGetter::CreateSP(InUserObject, InFunc, Vars...));
        return Me();
    }

    // Cursor attribute (TOptional<EMouseCursor::Type>)
    WidgetArgsType& Cursor(TAttribute<TOptional<EMouseCursor::Type>> InAttribute)
    {
        _Cursor = MoveTemp(InAttribute);
        return Me();
    }
    template<typename... VarTypes>
    WidgetArgsType& Cursor_Static(TIdentity_T<typename TAttribute<TOptional<EMouseCursor::Type>>::FGetter::template TFuncPtr<VarTypes...>> InFunc, VarTypes... Vars)
    {
        _Cursor = TAttribute<TOptional<EMouseCursor::Type>>::Create(TAttribute<TOptional<EMouseCursor::Type>>::FGetter::CreateStatic(InFunc, Vars...));
        return Me();
    }
    WidgetArgsType& Cursor_Lambda(TFunction<TOptional<EMouseCursor::Type>(void)>&& InFunctor)
    {
        _Cursor = TAttribute<TOptional<EMouseCursor::Type>>::Create(MoveTemp(InFunctor));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& Cursor_Raw(UserClass* InUserObject, typename TAttribute<TOptional<EMouseCursor::Type>>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _Cursor = TAttribute<TOptional<EMouseCursor::Type>>::Create(TAttribute<TOptional<EMouseCursor::Type>>::FGetter::CreateRaw(InUserObject, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& Cursor(TSharedRef<UserClass> InUserObjectRef, typename TAttribute<TOptional<EMouseCursor::Type>>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _Cursor = TAttribute<TOptional<EMouseCursor::Type>>::Create(TAttribute<TOptional<EMouseCursor::Type>>::FGetter::CreateSP(InUserObjectRef, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& Cursor(UserClass* InUserObject, typename TAttribute<TOptional<EMouseCursor::Type>>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _Cursor = TAttribute<TOptional<EMouseCursor::Type>>::Create(TAttribute<TOptional<EMouseCursor::Type>>::FGetter::CreateSP(InUserObject, InFunc, Vars...));
        return Me();
    }

    // Visibility (Attribute<EVisibility>)
    WidgetArgsType& Visibility(TAttribute<EVisibility> InAttribute)
    {
        _Visibility = MoveTemp(InAttribute);
        return Me();
    }
    template<typename... VarTypes>
    WidgetArgsType& Visibility_Static(TIdentity_T<typename TAttribute<EVisibility>::FGetter::template TFuncPtr<VarTypes...>> InFunc, VarTypes... Vars)
    {
        _Visibility = TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateStatic(InFunc, Vars...));
        return Me();
    }
    WidgetArgsType& Visibility_Lambda(TFunction<EVisibility(void)>&& InFunctor)
    {
        _Visibility = TAttribute<EVisibility>::Create(MoveTemp(InFunctor));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& Visibility_Raw(UserClass* InUserObject, typename TAttribute<EVisibility>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _Visibility = TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateRaw(InUserObject, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& Visibility(TSharedRef<UserClass> InUserObjectRef, typename TAttribute<EVisibility>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _Visibility = TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(InUserObjectRef, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& Visibility(UserClass* InUserObject, typename TAttribute<EVisibility>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _Visibility = TAttribute<EVisibility>::Create(TAttribute<EVisibility>::FGetter::CreateSP(InUserObject, InFunc, Vars...));
        return Me();
    }

    // AccessibleText
    WidgetArgsType& AccessibleText(TAttribute<FText> InAttribute)
    {
        _AccessibleText = MoveTemp(InAttribute);
        return Me();
    }
    template<typename... VarTypes>
    WidgetArgsType& AccessibleText_Static(TIdentity_T<typename TAttribute<FText>::FGetter::template TFuncPtr<VarTypes...>> InFunc, VarTypes... Vars)
    {
        _AccessibleText = TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateStatic(InFunc, Vars...));
        return Me();
    }
    WidgetArgsType& AccessibleText_Lambda(TFunction<FText(void)>&& InFunctor)
    {
        _AccessibleText = TAttribute<FText>::Create(MoveTemp(InFunctor));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& AccessibleText_Raw(UserClass* InUserObject, typename TAttribute<FText>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _AccessibleText = TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateRaw(InUserObject, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& AccessibleText(TSharedRef<UserClass> InUserObjectRef, typename TAttribute<FText>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _AccessibleText = TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateSP(InUserObjectRef, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& AccessibleText(UserClass* InUserObject, typename TAttribute<FText>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _AccessibleText = TAttribute<FText>::Create(TAttribute<FText>::FGetter::CreateSP(InUserObject, InFunc, Vars...));
        return Me();
    }

    // RenderTransform (TOptional<FSlateRenderTransform>)
    WidgetArgsType& RenderTransform(TAttribute<TOptional<FSlateRenderTransform>> InAttribute)
    {
        _RenderTransform = MoveTemp(InAttribute);
        return Me();
    }
    template<typename... VarTypes>
    WidgetArgsType& RenderTransform_Static(TIdentity_T<typename TAttribute<TOptional<FSlateRenderTransform>>::FGetter::template TFuncPtr<VarTypes...>> InFunc, VarTypes... Vars)
    {
        _RenderTransform = TAttribute<TOptional<FSlateRenderTransform>>::Create(TAttribute<TOptional<FSlateRenderTransform>>::FGetter::CreateStatic(InFunc, Vars...));
        return Me();
    }
    WidgetArgsType& RenderTransform_Lambda(TFunction<TOptional<FSlateRenderTransform>(void)>&& InFunctor)
    {
        _RenderTransform = TAttribute<TOptional<FSlateRenderTransform>>::Create(MoveTemp(InFunctor));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& RenderTransform_Raw(UserClass* InUserObject, typename TAttribute<TOptional<FSlateRenderTransform>>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _RenderTransform = TAttribute<TOptional<FSlateRenderTransform>>::Create(TAttribute<TOptional<FSlateRenderTransform>>::FGetter::CreateRaw(InUserObject, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& RenderTransform(TSharedRef<UserClass> InUserObjectRef, typename TAttribute<TOptional<FSlateRenderTransform>>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _RenderTransform = TAttribute<TOptional<FSlateRenderTransform>>::Create(TAttribute<TOptional<FSlateRenderTransform>>::FGetter::CreateSP(InUserObjectRef, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& RenderTransform(UserClass* InUserObject, typename TAttribute<TOptional<FSlateRenderTransform>>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _RenderTransform = TAttribute<TOptional<FSlateRenderTransform>>::Create(TAttribute<TOptional<FSlateRenderTransform>>::FGetter::CreateSP(InUserObject, InFunc, Vars...));
        return Me();
    }

    // RenderTransformPivot (FVector2D)
    WidgetArgsType& RenderTransformPivot(TAttribute<FVector2D> InAttribute)
    {
        _RenderTransformPivot = MoveTemp(InAttribute);
        return Me();
    }
    template<typename... VarTypes>
    WidgetArgsType& RenderTransformPivot_Static(TIdentity_T<typename TAttribute<FVector2D>::FGetter::template TFuncPtr<VarTypes...>> InFunc, VarTypes... Vars)
    {
        _RenderTransformPivot = TAttribute<FVector2D>::Create(TAttribute<FVector2D>::FGetter::CreateStatic(InFunc, Vars...));
        return Me();
    }
    WidgetArgsType& RenderTransformPivot_Lambda(TFunction<FVector2D(void)>&& InFunctor)
    {
        _RenderTransformPivot = TAttribute<FVector2D>::Create(MoveTemp(InFunctor));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& RenderTransformPivot_Raw(UserClass* InUserObject, typename TAttribute<FVector2D>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _RenderTransformPivot = TAttribute<FVector2D>::Create(TAttribute<FVector2D>::FGetter::CreateRaw(InUserObject, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& RenderTransformPivot(TSharedRef<UserClass> InUserObjectRef, typename TAttribute<FVector2D>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _RenderTransformPivot = TAttribute<FVector2D>::Create(TAttribute<FVector2D>::FGetter::CreateSP(InUserObjectRef, InFunc, Vars...));
        return Me();
    }
    template<class UserClass, typename... VarTypes>
    WidgetArgsType& RenderTransformPivot(UserClass* InUserObject, typename TAttribute<FVector2D>::FGetter::template TConstMethodPtr<UserClass, VarTypes...> InFunc, VarTypes... Vars)
    {
        _RenderTransformPivot = TAttribute<FVector2D>::Create(TAttribute<FVector2D>::FGetter::CreateSP(InUserObject, InFunc, Vars...));
        return Me();
    }

    // ----------------------------
    // Argument setters (值型)
    // 对应宏 SLATE_PRIVATE_ARGUMENT_FUNCTION(ArgType, ArgName)
    // ----------------------------

    WidgetArgsType& ForceVolatile(bool In)
    {
        _ForceVolatile = In;
        return Me();
    }

    WidgetArgsType& EnabledAttributesUpdate(bool In)
    {
        _EnabledAttributesUpdate = In;
        return Me();
    }

    WidgetArgsType& Clipping(EWidgetClipping In)
    {
        _Clipping = In;
        return Me();
    }

    WidgetArgsType& PixelSnappingMethod(EWidgetPixelSnapping In)
    {
        _PixelSnappingMethod = In;
        return Me();
    }

    WidgetArgsType& FlowDirectionPreference(EFlowDirectionPreference In)
    {
        _FlowDirectionPreference = In;
        return Me();
    }

    WidgetArgsType& RenderOpacity(float In)
    {
        _RenderOpacity = In;
        return Me();
    }

    WidgetArgsType& Tag(FName In)
    {
        _Tag = In;
        return Me();
    }

    WidgetArgsType& AccessibleParams(TOptional<FAccessibleWidgetData> In)
    {
        _AccessibleParams = In;
        return Me();
    }

    // ----------------------------
    // MetaData helpers（对应 TSlateBaseNamedArgs::AddMetaData 重载）
    // ----------------------------
    template<typename MetaDataType, typename Arg0Type>
    WidgetArgsType& AddMetaData(Arg0Type InArg0)
    {
        MetaData.Add(MakeShared<MetaDataType>(InArg0));
        return Me();
    }
    template<typename MetaDataType, typename Arg0Type, typename Arg1Type>
    WidgetArgsType& AddMetaData(Arg0Type InArg0, Arg1Type InArg1)
    {
        MetaData.Add(MakeShared<MetaDataType>(InArg0, InArg1));
        return Me();
    }
    WidgetArgsType& AddMetaData(TSharedRef<ISlateMetaData> InMetaData)
    {
        MetaData.Add(InMetaData);
        return Me();
    }

    // ----------------------------
    // Named slot support（对应 SLATE_NAMED_SLOT / SLATE_DEFAULT_SLOT）
    // 通过提供 SlotName() 返回 NamedSlotProperty，和重载 operator[] 来支持默认 slot
    // ----------------------------

    // Header() named slot accessor (对应 SLATE_NAMED_SLOT)
    NamedSlotProperty<WidgetArgsType> Header()
    {
        return NamedSlotProperty<WidgetArgsType>(*this, _Header);
    }

    // Content() named slot accessor (对应 SLATE_NAMED_SLOT)
    NamedSlotProperty<WidgetArgsType> Content()
    {
        return NamedSlotProperty<WidgetArgsType>(*this, _Content);
    }

    // Default slot operator[] (对应 SLATE_DEFAULT_SLOT)
    // 使得 SNew(SMyWidget)[ child ] 将 child 存入默认槽 _Content
    WidgetArgsType& operator[](const TSharedRef<SWidget>& InChild)
    {
        _Content.Widget = InChild;
        return Me();
    }

    // 也提供 Content as default explicit operator to follow macro semantics:
    WidgetArgsType& ContentDefault(const TSharedRef<SWidget>& InChild)
    {
        _Content.Widget = InChild;
        return Me();
    }

    // ----------------------------
    // 供外部读取内部成员（通常 InArgs._Something 在 Construct 中使用）
    // 这里直接暴露成员是为了演示：Construct(const FArguments& InArgs) 可读取 InArgs._ToolTipText 等
    // ----------------------------
    // （成员已在顶部定义）

}; // end struct SMyWidget_FArgumentsaz
```


# 第三方编辑器插件的创建
在UE中插件的定位相当于C++中第三方库, 虽然官方给开发者预先定义了一些模板, 但是本质上还是第三方库. 本节讨论的是关于模块这一模板的创建方式. 通过引擎内部的方式创建模块, 其最终的目录如下:
```
MyModule:
-> Public:
--> MyModule.h
-> Private:
--> MyModule.cpp
-> MyModule.Build.cs
```
.Build.cs 是模块的 Build 文件, 类似C语言的Makefile, C++ CMakeLists.txt, 它是用来指导 UBT 来进行模块的编译链接
```C#
using UnrealBuildTool;
public class MyCustomModule : ModuleRules
{
    public MyCustomModule(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", });
        PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore", });
        PublicIncludePaths.AddRange(new string[] {});
        PrivateIncludePaths.AddRange(new string[] {});

        if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.AddRange(new string[] { "UnrealEd", });
        }
    }
}
```
这里的public和private控制的是: 当你的模块被其他模块被引用时, public 的东西, 其他模块也能看到. private 则不能. 这个对于第三方库的实现来说很重要.
在具体的实现中: (以下.h和.cpp写一起)
```Cpp
class FMyCustomModule : public IModuleInterface {
public:
    /**
     * 模块启动时调用
     * 用于初始化模块资源、注册委托等
     */
    virtual void StartupModule() override;
    /**
     * 模块关闭时调用
     * 用于清理资源、注销委托等
     */
    virtual void ShutdownModule() override;
    /**
     * 检查模块是否支持动态重新加载
     */
    virtual bool SupportsDynamicReloading() override { return true; }
private:
    // 私有成员变量和函数
};
// Cpp 中
IMPLEMENT_MODULE(FMyCustomModule, MyCustomModuleInBuildCS)
//               ^^^^模块类名^^^^ ^^^^^模块名称(字符串)^^^^^
```
其中 宏 `IMPLEMENT_MODULE` 作为模块导出导致做了以下几件事:
- 注册模块：将模块类与模块名称关联
- 创建工厂函数：提供模块实例化的方法 `extern "C" DLLEXPORT IModuleInterface* InitializeModule(){ return new FMyCustomModule(); }`
- 导出符号：使模块管理器能够动态加载模块
```Cpp
namespace {
    static class FModuleRegistration {
    public:
        FModuleRegistration(){
            // 向模块管理器注册模块
            FModuleManager::Get().AddModule(
                TEXT("MyCustomModule"),  // 模块名称
                []() -> IModuleInterface* { 
                    return new FMyCustomModule(); 
                }
            );
        }
    } GModuleRegistration;
}
```

基本上, 你需要继承 `IModuleInterface` 这个UE提供的模块接口, 并重写 `StartupModule` 和 `ShutdownModule` 两个虚函数来控制模块的装载和卸载, 最后打开 .uproject 文件中加入你的模块
```C#
"Modules": [
    // ... 
    {
        "Name":  "MyCustomModule",
        "Type": "Editor", // Runtime
        "LoadingPhase": "Default"
    }
]
```
其中
- `Type` 说明了该模块在什么模式下有效 Editor 和 Runtime
- `LoadingPhase`: 改模块何时加载, 因为模块之间有依赖, A 依赖 B 那么A必须要等B初始化结束之后才能初始化, 这和C++通过系统API动态加载动态链接库是一样的, UE提供了以下几个阶段
    - Default: 默认加载
    - PostConfigInit: 配置系统初始化后
    - PreDefault: 默认阶段之前
    - PreLoadingScreen: 加载屏幕显示前
    - PostEngineInit: 引擎初始化后

以上是一个基本的模块实现, 在模块中我们会遇到一些常见的需求

## 单例模式
```Cpp
// MyCustomModule.h
class FMyCustomModule : public IModuleInterface {
public:
    // 获取模块单例
    static FMyCustomModule& Get() {
        return FModuleManager::LoadModuleChecked<FMyCustomModule>("MyCustomModule");
    }
    
    // 检查模块是否可用
    static bool IsValid() {
        return FModuleManager::Get().IsModuleLoaded("MyCustomModule");
    }
};
```
## 热重载
```Cpp
class FMyCustomModule : public IModuleInterface {
public: 
    // 是否支持动态重载
    virtual bool SupportsDynamicReloading() override { return true; }
    // 是否支持自动卸载
    virtual bool SupportsAutomaticShutdown() override { return true; }
    // 模块重载前调用
    virtual void PreUnloadCallback() override
    {
        // 清理必须在卸载前完成的资源
        ShutdownModule();
    }
};
```
## 日志分类
```Cpp
DECLARE_LOG_CATEGORY_EXTERN(LogMyCustomModule, Log, All); // <------
class FMyCustomModule : public IModuleInterface
{
    // ... 
};

// MyCustomModule.cpp
// 定义日志类别
DEFINE_LOG_CATEGORY(LogMyCustomModule);
void FMyCustomModule::StartupModule()
{
    // 使用自定义日志类别
    UE_LOG(LogMyCustomModule, Log, TEXT("Module started"));
    UE_LOG(LogMyCustomModule, Warning, TEXT("This is a warning"));
    UE_LOG(LogMyCustomModule, Error, TEXT("This is an error"));
    UE_LOG(LogMyCustomModule, Verbose, TEXT("Verbose information"));
}
```
## 读取配置文件
```Cpp
// MyCustomModule.h
class FMyCustomModule : public IModuleInterface
{
private:
    FString ConfigValue;
    int32 ConfigNumber;
    bool bConfigFlag;
    
public:
    void LoadConfig();
    void SaveConfig();
};

// MyCustomModule.cpp
void FMyCustomModule::LoadConfig()
{
    // 从配置文件读取
    GConfig->GetString(
        TEXT("MyCustomModule"),
        TEXT("ConfigValue"),
        ConfigValue,
        GGameIni  // 或 GEngineIni
    );
    
    GConfig->GetInt(
        TEXT("MyCustomModule"),
        TEXT("ConfigNumber"),
        ConfigNumber,
        GGameIni
    );
    
    GConfig->GetBool(
        TEXT("MyCustomModule"),
        TEXT("ConfigFlag"),
        bConfigFlag,
        GGameIni
    );
    
    UE_LOG(LogMyCustomModule, Log, TEXT("Loaded config: %s, %d, %d"), 
        *ConfigValue, ConfigNumber, bConfigFlag);
}

void FMyCustomModule::SaveConfig()
{
    GConfig->SetString(
        TEXT("MyCustomModule"),
        TEXT("ConfigValue"),
        *ConfigValue,
        GGameIni
    );
    
    GConfig->Flush(false, GGameIni);
}
```
## 委托支持
```Cpp
// MyCustomModule.h
DECLARE_MULTICAST_DELEGATE(FOnModuleInitialized);
DECLARE_MULTICAST_DELEGATE_OneParam(FOnModuleEvent, FString);

class FMyCustomModule : public IModuleInterface{
public:
    // 公共委托
    FOnModuleInitialized OnModuleInitialized;
    FOnModuleEvent OnModuleEvent;
    
    virtual void StartupModule() override;
    virtual void ShutdownModule() override;
    
private:
    // 引擎委托句柄
    FDelegateHandle PostEngineInitHandle;
    FDelegateHandle PreExitHandle;
    
    void OnPostEngineInit();
    void OnPreExit();
};

// MyCustomModule.cpp
void FMyCustomModule::StartupModule(){
    // 绑定引擎生命周期事件
    PostEngineInitHandle = FCoreDelegates::OnPostEngineInit.AddRaw(
        this, 
        &FMyCustomModule:: OnPostEngineInit
    );
    
    PreExitHandle = FCoreDelegates::OnPreExit.AddRaw(
        this, 
        &FMyCustomModule::OnPreExit
    );
    
    // 广播自定义事件
    OnModuleInitialized.Broadcast();
}

void FMyCustomModule::ShutdownModule(){
    // 解绑委托
    FCoreDelegates::OnPostEngineInit.Remove(PostEngineInitHandle);
    FCoreDelegates::OnPreExit.Remove(PreExitHandle);
    // 清空委托
    OnModuleInitialized.Clear();
    OnModuleEvent.Clear();
}

void FMyCustomModule::OnPostEngineInit(){
    UE_LOG(LogMyCustomModule, Log, TEXT("Engine initialized! "));
}

void FMyCustomModule::OnPreExit(){
    UE_LOG(LogMyCustomModule, Log, TEXT("Application is exiting"));
}

// 使用示例
void SomeClass::ListenToModule() {
    if (FMyCustomModule::IsAvailable()) {
        FMyCustomModule::Get().OnModuleEvent.AddLambda([](FString Message) {
            UE_LOG(LogTemp, Log, TEXT("Received:  %s"), *Message);
        });
    }
}
```
## 在模块中使用Tick
```Cpp
// MyCustomModule.h
class FMyCustomModule : public IModuleInterface{
private:
    FTimerHandle UpdateTimerHandle;
    FTSTicker::FDelegateHandle TickerHandle;
    
    void OnTimer();
    bool Tick(float DeltaTime);
};

// MyCustomModule.cpp
void FMyCustomModule::StartupModule(){
    // 方法1：使用定时器管理器（需要 World）
    if (GEngine && GEngine->GameViewport){
        if (UWorld* World = GEngine->GameViewport->GetWorld()){
            World->GetTimerManager().SetTimer(
                UpdateTimerHandle,
                FTimerDelegate::CreateRaw(this, &FMyCustomModule::OnTimer),
                5.0f,  // 间隔（秒）
                true   // 循环
            );
        }
    }
    
    // 方法2：使用 Ticker（不需要 World，更适合模块）
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateRaw(this, &FMyCustomModule:: Tick),
        1.0f  // 间隔（秒）
    );
}

void FMyCustomModule::ShutdownModule(){
    // 清理定时器
    if (UpdateTimerHandle.IsValid())
        if (GEngine && GEngine->GameViewport)
            if (UWorld* World = GEngine->GameViewport->GetWorld())
                World->GetTimerManager().ClearTimer(UpdateTimerHandle);
    // 移除 Ticker
    FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
}

void FMyCustomModule::OnTimer(){
    UE_LOG(LogMyCustomModule, Log, TEXT("Timer tick"));
}

bool FMyCustomModule::Tick(float DeltaTime){
    // 执行定期任务
    UE_LOG(LogMyCustomModule, Verbose, TEXT("Tick:  %f"), DeltaTime);
    return true;  // 返回 false 会自动移除 Ticker
}
```
## 控制台命令注册
```Cpp
// MyCustomModule.h
class FMyCustomModule : public IModuleInterface{
private:
    TArray<IConsoleObject*> ConsoleCommands;
    
    void RegisterConsoleCommands();
    void UnregisterConsoleCommands();
};

// MyCustomModule.cpp
void FMyCustomModule::StartupModule(){
    RegisterConsoleCommands();
}

void FMyCustomModule::ShutdownModule(){
    UnregisterConsoleCommands();
}

void FMyCustomModule::RegisterConsoleCommands(){
    // 简单命令
    ConsoleCommands. Add(IConsoleManager::Get().RegisterConsoleCommand(
        TEXT("MyModule.Hello"),
        TEXT("Prints a hello message"),
        FConsoleCommandDelegate::CreateLambda([](){
            UE_LOG(LogMyCustomModule, Log, TEXT("Hello from console!"));
        }),
        ECVF_Default
    ));
    
    // 带参数的命令
    ConsoleCommands.Add(IConsoleManager::Get().RegisterConsoleCommand(
        TEXT("MyModule.SetValue"),
        TEXT("Sets a value.  Usage: MyModule.SetValue <number>"),
        FConsoleCommandWithArgsDelegate::CreateLambda([](const TArray<FString>& Args){
            if (Args.Num() > 0){
                int32 Value = FCString:: Atoi(*Args[0]);
                UE_LOG(LogMyCustomModule, Log, TEXT("Value set to:  %d"), Value);
            }
        }),
        ECVF_Default
    ));
    
    // 控制台变量
    static int32 MyModuleDebugLevel = 0;
    ConsoleCommands.Add(IConsoleManager::Get().RegisterConsoleVariable(
        TEXT("MyModule. DebugLevel"),
        MyModuleDebugLevel,
        TEXT("Sets the debug level (0-3)"),
        ECVF_Default
    ));
}

void FMyCustomModule::UnregisterConsoleCommands(){
    for (IConsoleObject* Cmd : ConsoleCommands){
        IConsoleManager:: Get().UnregisterConsoleObject(Cmd);
    }
    ConsoleCommands.Empty();
}
```
## 资产管理器集成
```Cpp
// MyCustomModule.cpp
void FMyCustomModule::StartupModule(){
    // 注册资产搜索路径
    FPackageName::RegisterMountPoint(
        TEXT("/MyModule/"),
        FPaths:: Combine(*FPaths::ProjectPluginsDir(), TEXT("MyModule/Content"))
    );
    
    // 异步加载资产
    FStreamableManager& Streamable = UAssetManager::GetStreamableManager();
    
    FSoftObjectPath AssetPath(TEXT("/MyModule/Data/MyAsset.MyAsset"));
    Streamable.RequestAsyncLoad(
        AssetPath,
        FStreamableDelegate::CreateLambda([AssetPath](){
            if (UObject* LoadedAsset = AssetPath.ResolveObject()){
                UE_LOG(LogMyCustomModule, Log, TEXT("Asset loaded: %s"), 
                    *LoadedAsset->GetName());
            }
        })
    );
}
```
## 多线程支持
```Cpp
// MyCustomModule.h
class FMyCustomModule : public IModuleInterface{
private:
    void StartBackgroundTask();
    void OnTaskComplete(int32 Result);
};

// MyCustomModule.cpp
void FMyCustomModule::StartBackgroundTask(){
    // 异步任务
    Async(EAsyncExecution::Thread, [](){
        // 在后台线程执行
        FPlatformProcess::Sleep(2.0f);
        return 42;
        
    }, [this](int32 Result){
        // 在游戏线程执行回调
        OnTaskComplete(Result);
    });
    
    // 或使用任务图系统
    FFunctionGraphTask::CreateAndDispatchWhenReady([this](){
            UE_LOG(LogMyCustomModule, Log, TEXT("Task executing on game thread"));
        },
        TStatId(),
        nullptr,
        ENamedThreads::GameThread
    );
}

void FMyCustomModule::OnTaskComplete(int32 Result){
    UE_LOG(LogMyCustomModule, Log, TEXT("Task completed with result: %d"), Result);
}
```
## 性能测试
```Cpp
void FMyCustomModule::SomeExpensiveFunction(){
    // 性能统计
    SCOPE_CYCLE_COUNTER(STAT_MyCustomModule_ExpensiveFunction);
    // 或使用命名作用域
    TRACE_CPUPROFILER_EVENT_SCOPE(FMyCustomModule:: SomeExpensiveFunction);
    // 执行耗时操作
    // ...
}
```
# 扩展编辑器模块
## 编辑器菜单 ToolbarMenu
编辑器菜单系统分为<font color="#c0504d">描述层</font>(UObject 数据), <font color="#c0504d">命令层</font>(命令定义 + 绑定), <font color="#c0504d">构建层</font>（MultiBox/blocks）和 <font color="#c0504d">渲染层</font>(Slate widgets)。`UToolMenus` 管理 `UToolMenu` (每个菜单的描述)，`TCommands` / `FUICommandInfo` + `FUICommandList` 提供命令定义与行为绑定，`UToolMenus` 将 `UToolMenu` 的 entries 转换为 `FMultiBox` / `FMultiBoxBlock`，再由 Slate 生成 `SWidget`（按钮、菜单等）。样式（FSlateStyleSet / FEditorStyle / 模块自己的 Style）提供图标与外观

>  `UToolMenu` 是对编辑器/工具内菜单的封装, 用于声明式地构建菜单, 工具栏及其子菜单. 
>  其记录了入口名 `SubMenuSourceEntryName`, 菜单名, 父菜单 `SubMenuParent`, 菜单类型 `EMultiBoxType`, 风格类型: `ISlateStyle`, 上下文 `FToolMenuContext`, 并包含若干多个 `FToolMenuSection` (每个 section 下有多个 entry). 
>  注意: 其本身是一中数据类. 真正的页签单例的管理器是 `UToolMenus` 通过 `UToolMenu::Get()` 获取其单例对象.


在实际的UE界面上, LevelEditorToolBar 是以下区域 (可以通过 Widget Reflector 来获取到具体是哪个类)
![[LevelEditorToolBar.png]]
如果要在这个区域注册自定义的按钮:
1. `UToolMenu* ToolbarMenu = UToolMenus::Get()->ExtendMenu("LevelEditor.LevelEditorToolBar");` 从全局的菜单管理器中获取一份你需要插入位置(UI扩展点)的数据(`UToolMenu` 类型)
2. `FToolMenuSection& Section = ToolbarMenu->FindOrAddSection("Settings");` 从这个数据中通过名字找到你要插入的对应Section(UI扩展点的一部分)
3. `FToolMenuEntry& Entry = Section.AddEntry(FToolMenuEntry::InitToolBarButton(FMyUICommands::Get().PluginAction));` 在这个 Section 中添加一个 Entry, 这里的 `FMyUICommands::Get().PluginAction` 就是你命令 Entry 入口的回调函数
4. `Entry.SetCommandList(PluginCommands);` 在这个 Entry 中设置命令, 其中 `TShardPtr<FMyUICommands> PluginCommands;` 是 `FUICommandList` 的子类

## 扩展模块的方式
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
    virtual void ShutdownModule() override {
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


# 自定义UMG类