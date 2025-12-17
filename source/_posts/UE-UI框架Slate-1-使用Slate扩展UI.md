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

# Slate 框架中声明式语法
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

# 扩展编辑器模块

# 自定义UMG类