---
title: 原子操作(Atomic)和内存一致性模型(Memory Order)
date: 2026-03-09 06:04:02
tags:
  - C++
categories:
  - C++
cover: /lib/background/bg14.jpg
---

<!-- toc -->

# Atomic
[Double-Checked Locking 的正确性](https://preshing.com/20130929/double-checked-locking-is-fixed-in-cpp11/)
原子操作是指在多线程环境中, 某个操作要么全部完成, 要么完全不执行. 
`int b = a + 3; ` 这个操作实际上不是原子的. 编译器会将其翻译成3 个操作:
```asm
 mov     eax, DWORD PTR [rbp-4]
 add     eax, 3
 mov     DWORD PTR [rbp-8], eax
```
而在多线程环境中这个操作会被穿插, 导致程序出现与预期不一致的情况. 
## std::atomic
在 C++中, [`std atomic`](https://en.cppreference.com/w/cpp/atomic/atomic.html) 变量整合了原子性和保证内存序的功能. 
在语义上, `std::atomic` 有三个操作方式:
- load 操作: <u>读取</u>一个原子变量中的值
- store 操作: 往一个原子变量中<u>写入</u>值
- read modify write: RMW 操作, 即先读取, 再修改, 最后写入的一套操作
```cpp
std::atomic<int> atomic_int(0);
int value = atomic_int. load(); // 读取原子变量的值
atomic_int. store(10);          // 存储值到原子变量
```
注意: `std::atomic<T>` 中的类型 `T` 必须是可平凡拷贝的类型([TrivaiallyCopyable](https://en.cppreference.com/w/cpp/named_req/TriviallyCopyable. html), 即可以使用 `memcopy` 的类型).
但是对于常见的类型, 例如 int, char, bool, long 等这类常见类型, 其对应的例如 `std::atomic<int>` 只是对应 `std::atomic_int` 的别名, 但是总得来说, 只有整数类型才提供了别名的实现 `std::atomic<Integral>`. 同时, 虽然 C++ 重载了 `atomic::operator=` 来使得 `int value = atomic_int; ` 这样的隐式类型转换可以成立. 但是依旧不推荐使用这个隐式转换, 因为这将无法指定我们需要的内存序.

### std::atomic_flag
C++ 标准并不保证 `std::atomic<T>` 这个"任意"原子操作必须使用 CPU 底层的原子操作指令还是使用锁机制来实现(可以通过 `is_lock_free()` 来查看, 如果是无锁返回 `true`,  详情见 [Atomic 的无锁实现](#^atomic-and-lockfree). 但是标准保证必然使用 CPU 原子指令实现的类型只有 [`atomic_flag`](https://en.cppreference.com/w/cpp/atomic/atomic_flag. html)
该类型的语义虽然是一个 bool 类型的原子变量, 但是不等价于 `atomic<bool>`, 因为其不提供 load 和 store 操作. 例如:
```cpp
// 初始化: 
std::atomic_flag flag = ATOMIC_FLAG_INIT;
std::atomic_flag flag = 0;
std::atomic_flag flag {}; // 在 C++20 以前, 行为未定义; C++20 以后默认为 false
// 修改:
flag.clear(/* memory_order m = memory_order_seq_cst */); // 将其设置为 false;
flag.test_and_set(); // 原子地将其设置为 true;
```
例如: 一个自定义自旋锁(spin lock)的实现
```cpp
class spin_lock{
public:
    void lock() {
        while(flag. test_and_set(std::memory_order_acquire)){}
    }
    void unlock() {
        flag.clear(std::memory_order_release);
    }
private:
    std::atomic_flag flag = ATOMIC_FLAG_INIT;
};
/*
 * C++中关于 BasicLockable, 实现了 lock 和 unlock 函数的类型. 
 * 对于 std::lock_guard 等, 可以调用 BasicLockable 的对象
 */
```
以上只是一个例子, 实际上不要自定义实现自旋锁, 因为这会导致等待该锁的线程一直处于 while 的轮询状态. 本质原因是对于系统的调度器而言, 用户态实现的 `spin_lock` 是不可见的, 系统调度器无法优化这个等待行为.
在 C++20 中 `std::atomic_flag` 的使用得到了进一步改善
- `test()`: 读取
- `wait(old_val)`: 等待条件的达成
- `notify_one()` / `notify_all()`: 通知 {任意一个}/ {所有} 等待线程结束等待


> Atomic 的无锁实现
> C++ 标准规定: 除了 std::atomic_flag 以外, 所有的原子类型都不保证一定是互斥体实现还是使用 CPU 原子指令, 所以可以使用 [`atomic<T>::is_lock_free`](https://en.cppreference.com/w/cpp/atomic/atomic/is_lock_free.html) 来查看, 如果返回 `true` 则是使用了原子指令.
> 实际上, 对于基本类型的原子类型而言, 其都是使用 CPU 的原子指令而不是互斥体实现.
> 对于自定义类型, 这主要取决于自定义类型首先要满足内存对齐为默认的对齐方式, 以及内存占用要是有2 的幂次, 同时查看当前 CPU 支持多少位原子操作, 才能确定其是否能调用 CPU 的原子指令

### Compare & Swap, CAS 操作
CAS 操作常常用于原子地更新一个原子变量的值
```cpp
std::atomic<int> atomic_int(0);
atomic_int. fetch_add(1); // 原子的加1 操作
atomic_int. fetch_sub(1); // 原子的减1 操作
```
只能使用其给定的接口来加或者减, 因为对于 `atomic_int = atomic_int + 1; ` 等价于 `atomic_int. store(atomicInt. load() + 1); ` 这个操作依旧不是原子的. 在 `fetch_add` 的内部实际上会使用硬件指令锁住地址总线来保证其操作的原子性.

如果我们希望比较并交换(从 C++角度来看比较突然, 但这是硬件的一个常用指令 CAS), `compare_exchange_strong()` 和 `compare_exchange_weak()` 用于比较并交换操作(详情见 [C++中的 CAS 指令](#^cas)), 即在变量等于某个期望值时, 将其替换为新值. 这两者的区别在于, strong 版本的接口成功交换一定返回 `ture`, 但是 weak 版本的接口即便是成功之后也有可能返回 `false`. 这是因为有很多硬件平台本身不能保证内存顺序一致性, 所以在这些如内存序的平台上 weak 生成比 strong 更加高效的硬件指令.
```cpp
std::atomic<int> atomic_int(0);
int expected = 0;
bool exchanged = atomic_int.compare_exchange_strong(expected, 10);
// 如果 atomicInt 的值是 expected( 即0 ), 则将其改为10, 返回 true; 否则返回 false
```

如果只是单纯的交换, 则可以
```cpp
std::atomic<int> atomic_int(0);
int expected = 0;
bool exchanged = atomic_int.compare_exchange_strong(expected, 10);
// 如果 atomicInt 的值是 expected( 即0 ), 则将其改为10, 返回 true; 否则返回 false
```

有了 `compare_exchange_strong` 就可以自己写复合需求的 `fetch`,
```cpp
template<typename T>
double fetch_square(std::atomic<T> num){
	auto old_num = num. load();
	do{
		auto new_num = old_num * old_num;
	}while(!num.compare_exchange_strong(old_num, new_num))
// 如果 num 的值是 old_num, 将其改为 new_num. 返回 true;
// 由于这里使用的 while 的循环, 所以如果要照顾弱内存序平台的话, 可以使用
// compare_exchange_weak 这个接口, 反正错了就多循环几次.
    return static_cast<double>(old_num);
}
template<typename T>
int fetch_multiply(std::atomic<T>& value, int multiplier){
    int old_val = value. load();
    int desired;
    do {
        desired = old_val * multiplier;
    } while(!value.compare_exchange_strong(old_value, desired));
}
```

`compare_exchange_strong` 的行为相当于:
```Cpp
template <typename Ty>
class atomic{
public:
    bool compare_exchange_strong(Ty &expected, const Ty& new_value){
        std::lock_guard<std::mutex> lock(m);
        if (val == expected) {
            val = new_value;
            return true;
        }
        expected = val;
        return false;
    }
private:
    Ty val;
    std::mutex m;
};
```
只是使用对应 CPU 提供的原子指令完成

> CAS 操作
> [知乎: 理解 C++无锁编程 compare_exchange_weak](https://zhuanlan.zhihu.com/p/1980446889984946486)
> 
> [Cppref: compare_exchange](https://en.cppreference.com/w/cpp/atomic/atomic/compare_exchange)
> 
> `bool compare_exchange_weak(T& expected, T desired, memory_order success, memory_order failure); `
> `bool compare_exchange_weak(T& expected, T desired, memory_order order = memory_order_seq_cst); `
> 其参数含义如下:
> - `expected`: 一个引用, 指向存储期望值的变量. 如果比较成功, 原子变量会被更新为 `desired`; 如果失败, `expected` 会被更新为原子变量的当前值
> - `desired`: 要设置的新值
> - `success`: 指定在比较成功时使用的内存顺序(memory order)
> - `failure`: 指定在比较失败时使用的内存顺序
> 
> strong‌‌ 和 weak 的不同在于, weak 可能出现伪失败(spurious failure), 即原子变量的当前值与期望值相等, 操作也会失败, 通常是为了在某些硬件平台上实现更高的性能. 由于 `compare_exchange_weak` 的伪失败特性, 它通常需要在循环中使用, 直到操作成功为止
> 
> ```cpp
> T old_val = expected;
> while (!atomic_var.compare_exchange_weak(old_val, desired, std::memory_order_release, std::memory_order_relaxed)) {
>    // 重试逻辑
> }
> ```

# Memory Order
C++ 编译器默认程序单线程的, 所以多线程的没有任何保护措施的写入是未定义行为. 具体来说, 由于单线程假设, 编译器在优化时可以在保证正确性的前提下随意交换指令顺序以优化性能. 

现实的 CPU 会将所有数据写入缓存, 再通过缓存将数据写入内存, 这对于所有 CPU 来说都是一样的. 所以在多核CPU语境下, 缓存数据和内存数据同步时会因为编译器默认的指令优化而出现各种数据错误的情况. 所以在涉及到多核 CPU 缓存向内存同步数据时, 应该保证有某种确定顺序进行同步, 即内存序问题. 

对于多线程的情况下, 不同线程执行的顺序有快有慢, 所有线程内的各种语句顺序会互相穿插, 但是无论如何穿插我们都希望最后实际的执行的顺序中, 同一个线程内的指令相对顺序的稳定, 而不会被编译器优化, 即内存一致性问题.

内存顺序一致性模型是由计算机科学家 Leslie Lamport 在1979 年提出的一种内存一致性模型. 根据顺序一致性模型, 所有线程中的操作都按照某个全局的、单一的顺序执行, 这个顺序对所有线程来说是一致的. 换句话说, 程序中的所有操作看起来就像是按照某个特定的顺序依次执行的, 而不涉及实际的并行执行. 

例如,

```cpp
std::thread th1([&](){
    // 指令 1
    // 指令 2
});
std::thread th2([&](){
    // 指令 3
    // 指令 4
});
```

上述四条指令在实际运行时会相互穿插. 所以实际的执行顺序可能有以下:

- 1, 2, 3, 4
- 1, 3, 4, 2
- 1, 3, 2, 4
- 3, 1, 2, 4
- 3, 1, 4, 2
- 3, 4, 1, 2

这其中必须保证 1, 2 和 3, 4 的相对位置. 这也各种操作系统上所讲的多线程模型. 这种关系叫做<font color="#c0504d">全序一致性</font>. 即我们不允许编译器因为代码优化导致代码的相对位置被改变, 但同时编译器也不能完全放弃优化.

<font color="#c0504d">多线程的不一致问题出现的根本原因就是对共享数据的读写操作</font>. 所以以共享数据的读写操作为锚点, 阻止编译器改变代码执行顺序, 成为了一个解决方案, 也是目前支持最广泛的方式.

C++标准中提供以下[内存序](https://cppreference.com/cpp/atomic/memory_order):

- `memory_order_relaxed`: 只保证变量是一个原子变量, 不关心代码顺序的问题
- `memory_order_acquire`: 把内存中的值读到缓存里去, 所以编译器要保证不能把后面的代码优化到前面, 防止提前读入错误数据
- `memory_order_release`: 把缓存中的值同步到内存里去, 所以编译器要保证不能把前面的语句优化到该语句的后面, 防止往内存中写入错误数据
- `memory_order_acq_rel`: `memory_order_release` + `memory_order_acquire`
- `memory_order_seq_cst`: 全序一致性, 不要更换任何代码顺序

如图:
![Cache-Memory模型](/images/Cache-Memory模型.png)
