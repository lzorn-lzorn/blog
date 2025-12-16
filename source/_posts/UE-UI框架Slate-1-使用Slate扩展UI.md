---
title: UE-UI框架Slate{1}-使用Slate扩展UI
date: 2025-12-10 21:29:58
tags: 
  - UE
  - C++
categories:
  - UE
cover: /lib/background/bg3.jpg
---
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
![Slate和UMG操作的对应.png](./images/Slate和UMG操作的对应.png)
# 第三方编辑器插件的创建

# 扩展编辑器模块

# 自定义UMG类