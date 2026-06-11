---
title: C++类型擦除
date: 2026-06-12 01:30:31
tags:
  - C++
categories:
  - C++
cover: /lib/background/bg14.jpg
---
# C 语言时代的类型擦除
在C语言时代, 类型擦除主要是使用 `void *`. 因为在C语言时代, `void *` 是一个万能口袋, 所有的指针都可以转换为 `void *`, 但是一旦转换为  `void *` 原本的类型是找不回来的. 
```C
int int_compare(const void* a, const void* b) {
    return *(const int*)a - *(const int*)b;
}

int str_compare(const void* a, const void* b) {
    return strcmp((const char*)a, (const char*)b);
}
```

# 使用继承的类型擦除
在支持面向对象的编程语言中，继承本身就是一种类型擦除。因为接口输入的参数是基类的指针，没有人知道具体传入的是哪一个对应的实现。相当于把子类的类型擦除为父类的类型。但是不同于 `void*` 这种方式，继承只是擦除了传入对象的类型，而其本身的类型并没有丢掉，也算是类型安全。但是继承的类型擦除是侵入性的，也就是要求派生类必须重写接口或者继承父类，这本身就是一个桎梏，每需要一个对象你都需要设定一个基类。同时对于很多第三方库和内置，你是没有办法通过继承实现类型擦除的。
```Cpp
template <typename R, typename... Params>
struct Invokable{
	virtual ~Invokable() = default;
	virtual R call(Params...) = 0; 
	virtual bool active() const = 0;
};

template <typename I, typename R, typename... Params>
struct CapturedInvokable final : Invokable<R, Params...> {
	explicit CapturedInvokable(I&& holder_) : holder(std::move(holder_)){}
	explicit CaptureInvokable(const I& holder_) : holder(holder_) {}
	R call(Params... params) override {
		return holder(std::forward<Params>(params)...)
	}
	bool active() const override { return true; }
	I holder;
};
template <typename I, typename R, typename... Params>
struct NullInvoker final : Invokable<R, Params...>{
    R call(Params...) override { return R(); }
    bool active() const override { return false; }
};
template <typename I, typename R, typename... Params>
struct CapturedPlain final : Invokable<R, Params...>{
    explicit CapturedPlain(R (*func_)(Params...)) : func(func_) {}
    R call(Params... params) override { return func(std::forward<Params>(params)...); }
    bool active() const override { return func != nullptr; }
    R (*func)(Params...);
};

template <typename T, typename R, typename... Params>
struct CapturedMemberFunc final : Invokable<R, Params...>{
    explicit CapturedMemberFunc(T *ptr_, R (T::*func_)(Params...)) : ptr(ptr_), func(func_) {}
    R call(Params... params) override { return (ptr->*func)(std::forward<Params>(params)...); }
    bool active() const override {
	     return ptr != nullptr && func != nullptr; 
    }
    T *ptr;
    R (T::*func)(Params...);
};
```

在这里基类为Invokable，子类分别为CapturedInvokable、NullInvoker 、CapturedPlain 、CapturedMemberFunc分别实现覆盖基类中的call函数，后续只要通过Invokable的指针或引用来调用到派生类的call函数却不需要关心这些派生类的具体类型和实现是怎么样的。

# Duck Type

如果一个东西，走路像鸭子，叫声也像鸭子，那么它就是鸭子。换句话说，如果一个东西，满足我们对鸭子的所有要求，那么它就是鸭子。如果一个 `T`，满足我们对 `X` 的所有要求，那么它就是 `X`。这就是duck typing，即鸭子类型。

C++的模板就是一种鸭子类型

```Cpp
template <typename Container>
int CountByColor(const Container& container, Color color) {
    int count = 0;
    for (const auto& item: container) {
        if (item.Color() == color) {
            ++count;
        }
    }
    return count;
}
```

只要 `Container` 可遍历(支持迭代器)，内部的对象都有 `Color() const` 这个方法. 且 `T` 与 `Color` 类型有合适的 `operator==` 函数存在。

如果一个东西，走路像鸭子，叫声也像鸭子，那么它就是鸭子。换句话说，如果一个东西，满足我们对鸭子的所有要求，那么它就是鸭子。如果一个`T`，满足我们对`X`的所有要求，那么它就是`X`。这就是duck typing，即鸭子类型。

C++的模板就是一种鸭子类型
```Cpp
template <typename Container>
int CountByColor(const Container& container, Color color) {
    int count = 0;
    for (const auto& item: container) {
        if (item.Color() == color) {
            ++count;
        }
    }
    return count;
}
```

只要 `Container` 可遍历(支持迭代器)，内部的对象都有 `Color() const` 这个方法. 且`T`与`Color`类型有合适的`operator==`函数存在。

# 基于 std::variant 的实现
`std::variant` 提供一种编译期的类型安全的类型擦除。`std::variant`可以存储多种类型的对象(类似于union)，并且在运行时选择需要使用的类型。这种能力可以是该变量根据所处环境选择使用不同的类型(某种意义上这就是多态)。

```Cpp
struct Circle { void draw() const { std::cout << "Circle\n"; } };
struct Square { void draw() const { std::cout << "Square\n"; } };
struct Triangle { void draw() const { std::cout << "Triangle\n"; } };

using Shape = std::variant<Circle, Square, Triangle>;

// 这是一个泛型的可调用对象
struct GenericInvoker{
    template<typename T>
    void operator()(T& shape) const{
        shape.draw();
    }
};

// 一个可以绘制多种形状的函数
void drawShapes(const std::vector<Shape>& shapes){
    for (const auto& shape : shapes){
        std::visit(GenericInvoker(), shape);
    }
}

int main() {
    std::vector<Shape> shapes{Circle{}, Square{}, Triangle{}};
    drawShapes(shapes);
    return 0;
}
```

# 基于CRTP的类型擦除
CRTP (Curiously Recurring Template Pattern) 奇异递归模板模式, 其运用到了编译期多态, 是派生类将自身类型作为基类的模板参数，这样基类就可以了解派生类的信息。而且这个全部是都在编译期完成的，无需再运行时通过虚表的方式进行调用，而是会直接调用派生类的函数。通过CRTP可以在基类中指定一个未被实现的接口，在派生类中再提供具体的实现，这也就是编译期的多态
```Cpp
template <typename Derived>
class Base{
public:
	void interface(){
		static_cast<Derived*>(this)->implementation();
	}
	void implementation(){
	// ...
	}
};
class Derived : public Base<Derived> {
public:
	void implementation() {
	// ...
	}
}
```
这里Base类对象调用interface函数时，将this指针强转为指向Derived的指针，后面就可以通过这个指针来调用派生类的implementation函数。因为是 Derived 继承自Base，所以此时 this 其实就是一个 Derived* 类型的指针，所以强制类型转换是安全的。这样成功实现了编译时的多态。这就利用了模板在编译时期参数就已经确定的特性，在编译时完成多态的调用，避免了虚函数运行时的开销，并且在某些情况下，更能提供灵活性。

首先使用CRTP来实现是编译期多态, 无需虚表可以省去一部分的开销. 并且CRTP在编译期就确定了会调用到哪个函数, 这也更加利于编译器的优化. 但是使用了模板就难免有模板的缺点, 那就是模板会让编译时间拉长并且增大最后的代码体积, 并且模板一旦报错的话, 报错信息基本没法看.

# 使用Concepts的类型擦除
在C++20中, 提供了新的特性 `<concepts>` 用于编译期约束, 基于Concepts 实现类型擦除实际上用到了一个概念 DuckType, 只要这个类有这个方法即可. 并不关心它具体是什么, 这也是一种变相的类型擦除.

```cpp
template<typename T>
concept Printable = requires(T a) {
    { a.print(std::cout) } -> std::same_as<void>;
};

template<Printable T>
void print(const T& t) {
    t.print(std::cout);
}
```
只要 T 满足 Printable 即可, T 具体是什么类型实际上无关紧要

# 基于类封装的类型擦除
所谓类封装, 即封装不同类型, 使其有一致的行为. 例如
```Cpp
class Sword{};
class Staff{};
class Gun{};
```
实际上, 作为武器而言, 他们都有一些公共的属性: 使用, 维修, 强化等. 
我们可以使用Weapon类将其封装, 统一将其类型擦除为Weapon
```Cpp
struct Weapon {
public:
	template <typename WeaponType>
	Weapon(WeaponType weapon)
		: pimpl{ std::make_unique<detail::WeaponComponent<WeaponType>>(std::move(weapon)) }
	{

	}
public:
	bool Use() {
		return pimpl->Use();
	}
	bool Repair(int16_t degree) {
		return pimpl->Repair(degree);
	}
	bool Strengthen() {
		return pimpl->Strengthen();
	}
private:
	std::unique_ptr<detail::WeaponConcept> pimpl;
};

// ===========
struct WeaponConcept {
	virtual ~WeaponConcept() = default;
	virtual bool Use() = 0;
	virtual bool Repair(int16_t) = 0;
	virtual bool Strengthen() = 0;
	virtual bool IsEquiped() const noexcept = 0;
	virtual int16_t GetDurability() const noexcept = 0;
	virtual int16_t SetDurability(int16_t) = 0;
	virtual std::unique_ptr<WeaponConcept> Clone() const = 0;
};

template <typename WeaponType>
struct WeaponComponent : public WeaponConcept {
	using value_type = WeaponType;
	explicit WeaponComponent(WeaponType&& weapon)
		: weapon(std::forward<WeaponType>(weapon))
	{
	}
	bool Use() override {
		std::cout << "使用武器, 降低耐久度" << std::endl;
		return true;
	}
	bool Repair(int16_t degree) override {
		weapon.SetDurability(degree);
		std::cout << "修理武器, 恢复耐久度" << std::endl;
		return true;
	}
	bool Strengthen() override {
		std::cout << "强化武器, 提升攻击力" << std::endl;
		return true;
	}
	
	bool IsEquiped() const noexcept override { return true; }
	int16_t GetDurability() const noexcept override { return -1; }
	int16_t SetDurability(int16_t) override { return -1; }
	std::unique_ptr<WeaponConcept> Clone() const override { return nullptr; }

private:
	WeaponType weapon;
};
```
借由 `WeaponComponent<WeaponType>` 对 `WeaponConcept` 将其类型直接擦除, 这样无论是什么武器都只能拥有 Weapon 提供的方法, 而在所有的具体武器类都写完之后, 只需要维护 `WeaponComponment` 既可. 
进一步的, 可以给 `plmpl` 中增加一个虚函数 `TypeId()` 来返回 `typeid(WeaponType)`. 这样就算类型被擦除了, 也可以使用 rtti 获取源类型的 typeid 从而使用 `operator==` 来判断运行时类型 
`typeid(Ty)` 不是 rtti, 所以也不需要开启rtti. 只有 `typeid(*p)` 才需要开启 rtti.
这种方式也是 `std::function` 实现类型擦除的方式:
`std::function` 存有一个继承于 `FuncBase` 的 `FuncImpl`, 执行时通过 `FuncBase` 执行 invoke. 因为 `std::function` 的核心要求是把不同类型、不同形态的可调用对象(普通函数, 函数指针, Lambda, 成员函数等)收纳到同一个模板实例类型中. 同时可以赋值, 拷贝, 移动, 内部更换的函数容器. 基于这样的需求, 内部通过虚函数好像是唯一的做法:
- C 风格 `void*` 不能携带状态
- CRTP 是静态绑定
- Variant 要穷举所有的类型, 但是每个 Lambda 都是不同的.

https://zhuanlan.zhihu.com/p/433019649
https://dev.epicgames.com/documentation/zh-cn/unreal-engine/delegates-and-lamba-functions-in-unreal-engine

