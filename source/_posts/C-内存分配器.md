---
title: C++内存分配器
date: 2026-06-26 22:58:12
tags:
  - C++
categories:
  - C++
cover: /lib/background/bg14.jpg
---
# new 和 delete

## new 
new operator 是C++的保留关键字，当其成功调用时会调用两个函数：`operator new()` 和 `placement new()` [tips] 这两个函数是可以重载的.
```cpp
string * sp = new string("hello");
```
等价于：
```cpp
// 申请原始空间，类似于malloc
woid * raw = operator new(strlen("hello"));
// 通过 placement new调用string类构造函数，初始化申请空间
new (raw) string("hello");
// 返回对象指针
string * sp = static_cast<string *>(raw);
```
new 这个关键字底层仍然是malloc，区别于malloc的是：new会调用相应的构造函数，虽然我们经常这么说。实际上 new 是由两个步骤的:

1. 调用 `operator new()` / `operator new[]()` 分配内存，这部分相当于malloc
2. 调用对应的构造函数

> 对齐内存分配
> 在 C++17 之后, 可以在 `new` 中指定对齐
> ```Cpp
> void* operator new(std::size_t size, std::align_val_t align); 
> void operator delete(void* ptr, std::size_t size, std::align_val_t align) noexcept;
> ```

## operator new()
new 这个关键字之所以可以发挥作用, 主要是调用了 operator new() 这个函数，所以可以用过重载 `operator new()` 来改变其行为
`operator new()` 用于申请 Heap 空间，功能类似于 C 的 malloc, 尝试从堆上获取一段内存空间，如果成功则直接返回，如果失败则转去调用 new handler，然后抛出一个 `bad_alloc` 异常
其函数原型是：
```cpp
void* operator new(std::size_t size) throw (std::bad::alloc);
```
其具体实现：
```cpp
void* operator new(szie_t size) throw (std::bad_alloc){
	void * p;
	while((p=malloc(size)) == 0)
		if(_callnewh(size) == 0){
			static const std::bad_alloc nomem;
			_RAISE(nomem);      
		// #define _RAISE(x)::std::_Throw(x) 抛出nomen异常
		}
	return (p);
}
```

>   new handler
> new_handler 是一个函数指针, 用于在内存分配时调用. 其定义包含在 `<new>` 中
> ```Cpp
> namespace std {
> using new_handler = void (*)();
> }
> ```
>
> 分配失败时, 触发 new_handler, 然后循环分配并调用 new_handler, 直到(即 new_handler 的必须满足的三种合法行为):
> 
> - 别的内存释放, 分配成功
> - new_handler 抛出异常 `bad_alloc`
> - new_handler 调用 `std::abort`
> 
> 如果没有设置 new_handler, 则直接抛出异常 `bad_alloc`.
> 可以通过 `std::new_handler set_new_handler(new_handler new_p) noexcept;` 设置全局 new_handler, 或者是在局部定义
> ```Cpp
> #include <iostream> #include <new> struct BigObject { 
>     // 静态存储本类专属handler 
>     static std::new_handler class_handler; 
>     // 类专属set_new_handler 
>     static std::new_handler set_new_handler(new_handler h) noexcept { 
>         std::new_handler old = class_handler; 
>         class_handler = h; 
>         return old; 
>      } 
>      // 重载类专属 operator new 
>      static void* operator new(size_t size) { 
>          void* ptr; 
>          // 循环分配，使用本类handler 
>          while ((ptr = ::operator new(size, std::nothrow)) == nullptr) { 
>              if (class_handler == nullptr) throw std::bad_alloc(); 
>              
>              class_handler(); 
>          } 
>          return ptr; 
>      } 
>      char data[1024 * 1024]; 
>  }; 
>  // 静态成员初始化 
>  std::new_handler BigObject::class_handler = nullptr; 
>  // 仅BigObject分配失败触发的回调 
>  void big_obj_oom_handler() { 
>      std::cerr << "分配BigObject内存不足\n"; 
>      throw std::bad_alloc(); 
>  } 
>  int main() { 
>      BigObject::set_new_handler(big_obj_oom_handler); 
>      try { 
>          while (true) { new BigObject; } 
>      } catch (...) { std::cerr << "BigObject内存分配失败\n"; } 
>      return 0; 
> }
> ```
>
> 如果定义 new 为 `noexcept` 则分配失败是不会调用 new_hander, 例如: `char* p = new(nothrow) char[1024];`
>  pmr 的内存耗尽时也会直接抛出 new_hander 不会调用全局 new_hander.
>  但实际上, new_hander 其实很难出发, 因为操作系统往往会做出超量分配承诺, 因为操作系统内部是会维护虚拟内存的, 同时多个进程都在时时刻刻分配和释放, 所以系统即便内存也会给应用程序承诺会分配, 因为可能未来不久就会有新的内存被释放. 同时即便操作系统承诺分配内存, 真正的内存也不会马上分配, 而是在真正被用到时才会分配. 
> 
## placement new()
一般来说，使用new申请空间时，是从系统的"堆"(heap)中分配空间。申请所得的空间的位置时根据当时的内存的实际使用情况决定的。但是, 在某些特殊情况下，可能需要在程序员指定的特定内存创建对象，这就是所谓的"定位放置new"(placement new)操作。

定位放置new操作的语法形式不同于普通的new操作。例如，一般都用如下语句 `A* p=new A;` 申请空间，而定位放置new操作则使用如下语句 `A* p=new (ptr) A;` 申请空间，其中ptr就是程序员指定的内存首地址.

```cpp
int *p=(int*)malloc(sizeof(int)*10);
int *p0 = new(p)int(10);//表示将10放在p的空间的第一位
```
[注意]

1. 用定位放置new操作，既可以在栈(stack)上生成对象，也可以在堆（heap）上生成对象。
2. 使用语句 `A* p=new (mem) A;` 定位生成对象时，指针p和数组名 mem 指向同一片存储区。所以，与其说定位放置 new 操作是申请空间，还不如说是利用已经请好的空间，真正的申请空间的工作是在此之前完成的
3. 使用语句 `A * p=new (mem) A;` 定位生成对象是，会自动调用类A的构造函数，但是由于对象的空间不会自动释放（对象实际上是借用别人的空间），所以必须显示的调用类的析构函数，如本例中的 `p->~A()`.
4. 
```cpp
void * operator new(size_t, void *location){ 
    return location; 
}
```

它也是new操作符的一个使用方法，须要使用一个额外的变量（buffer）。当new操作符隐含调用operator new函数时。把这个变量传递给它。被调用的operator new函数除了带有强制的參数size_t外，还必须接受void* 指针參数。指向构造对象占用的内存空间。如果要将一个元素放在其他下标位置中，可以重载new

```cpp
void* operator new(size_t sz,void *ptr,int pos){
//第1个参数必须但不需要传递，由new自动计算的，第2个参数传递void*指针，第3个参数传递位置
    return &ptr[pos];
}
new(p,3)int(10);    //将10放在下标为3的空间中
```
[ 注意 ]：`operator new()` 和 `operator new[]()` 都是不负责初始化得到的内存的，所有这部分要取决于具体编译器的实现.
在 C++17 之后 placement new 被封装为 `std::construct_at`

## delete
对于每一个 `new` 都有一个对应的 `delete` 来进行释放..
你需要做到 每一种new和delete对应，`new[]` 和 `delete[]` 对应，构造和析构的new delete要对应。但是这些都不是我们所提倡的做法，我们现在更加提倡的是使用智能指针，也就是应该RAII思想。
对应于operator new()，delete关键字也同理于new:
1. 会在调用解构函数
2. 调用 `operator delete()` / `operator delete[]() ()`
所以可以通过重写 `operator delete()` 来改变delete的行为
重载delete：
```cpp
void operator delete[](void *p){
	free(p);
}
void operator delete(void *p){
    free(p);
}
```

# Allocator
在 C++ 的设计中, 标准内存分配器并不是 C 语言中传统的 `malloc` 和 `free`, 而是一种内存安全的类型分配器, 即在使用时需要指定具体类型, 而不是将 `void*` 进行强制类型转换.
即
```Cpp
template <class _Ty>  
class allocator {
    T* allocate(size_t n);
    void deallocate(T* p, size_t n) noexcept;
};
```

在 C++ 中一个标准的内存分配器(无论是否有状态), 都需要包含以下信息:

- `value_type`: 指明分配类型
- `pointer_type`: 对应的指针类型
- `const_pointer`: const pointer版本
- `reference`: 对应的引用类型
- `const_reference`: 对应引用类型的 const 版本
- `size_type`: 内存分配器能表达的最大内存块元素数量, 默认 无符号数字(size_t), 也是用于在 64 位大内存场景溢出时, 无法区分"数量"和"偏差值"的问题.
- `difference_type`: 两个指针之间的差值所返回的类型, 默认 `std::ptrdiff_t` (有符号整数 int). 主要是为了防止 64 位超大数组超出 int 的范围导致标准库算法 `distance`, `advance` 报错.
- `propagate_on_container_move_assignment`: 分配器传播规则

但是对于无状态的内存分配器而言这些都是差不多的, 很多都是在 `value_type` 的基础上预定义的. 所以标准在 `allocator_traits` 中已经提前写好了一份. 所以你可以:

```cpp
template <typename Ty>
class YourAllocator {
    using value_type = Ty;
    YourAllocator() = default;
    // rebind
    template<typename U>
    YourAllocator(const YourAllocator<U>&) noexcept {}
    Ty* allocate(size_t) {}
    void deallocate() {}
};
```

你无需定义其他的东西, `allocator_traits` 会全部补齐.  
同时, 如果你也没有定义该类型应该如何构造和析构, 在 `allocator_traits` 中也会有默认的 `constrcut` 和 `destroy`  
等等你需要的一切都会在 `allocator_traits` 中有默认实现.

在标准库中所有带有显式分配器的容器, 例如 `vector`, `string` 其内部都会通过 `allocator_traits` 来访问对应的内容. 例如:

```cpp
template<typename Ty, class Alloc=std::allocator<Ty>>
class vector{
public:
    using allocator_type = Alloc;
    using size_type = std::allocator_traits<Ty>::size_type;
};
```

来获取对应的静态信息, 所以如果要实现自定义容器同时有希望兼容标准, 实现这里的类型则也是兼容的一环.

为什么标准库要进行一个"舍近求远"的操作, 将问题复杂化呢? 
因为这一切都是为了实现<font color="#c0504d">有状态的内存分配器</font>. 例如: 内存池, 内存追踪分析器, 他们内部不仅要分配内存还要对分配出去的内存做管理和统计, 此时上述的标签就变得至关重要.
其中详细讲述 rebind 和 propagate 规则

## rebind 重绑定规则

对于一个链表对象而言, 外部调用者往往会使用 

```Cpp
std::list<int> l;
```

来进行声明, 但是在 `list` 内部其真正分配并不是一个 `int`, 而是一个 `ListNode<int>` 的类型, 此时在内部就需要将标准内存分配器从 `int` 类型 Rebind 到 `ListNode<int>` 类型, 即

```Cpp
template <class Ty, class Alloc = std::allocator<Ty>>
struct list {
    using NodeAlloc = typename Alloc::template rebind<Node>::other;
};
```

在 C++17 之后的版本, 显示 rebind 操作已经可以通过 [`allocator_traits`](https://cppreference.com/cpp/memory/allocator_traits) 推导得出. 

例如, 对于一个 FixedAllocator:

```Cpp
template<typename T, size_t PoolSize> struct FixedAlloc { 
    char pool[PoolSize]; // 手动自定义rebind，保留第二个模板参数 
    template<typename U> struct rebind { 
        using other = FixedAlloc<U, PoolSize>; 
    }; 
};
```

此时你就需要指定其 rebind, 如果没有这个 rebind, 在 `allocator_traits` 中则会使用默认的 `rebind`, 生成 `FixedAlloc<U>` 缺失了 `PoolSize`, 编译就会报错

## propagate 传播规则

![propagation](/images/propagation in C++.excalidraw.png)
所谓标准库的传播规则, 即如果一个容器内部保存了某个分配器对象时, 当这个对象被拷贝, 移动, 交换时, 改分配器应该采取何种行为.
`propagate_on_container_copy_assignment`: 控制拷贝赋值后, `dst` 是否可以接管 `src` 的分配器.
当其为 `true_type` 时,

1. 用 `dst` 旧分配器释放自身原有所有内存
2. 将 `src` 的分配器完整拷贝一份，赋值给 `dst` 的分配器
3. 使用新拷贝过来的分配器，重新分配内存并拷贝 `src` 全部元素

当其为 `false_type` 时,

1. `dst` 保留自己原本的分配器，不替换
2. 释放 `dst` 旧内存
3. 用 `dst` 自身分配器开辟内存, 拷贝 `src` 元素

如果 dst 和 src 的分配器不相等时, 则会全量拷贝. 对于无状态分配器而言无风险, 因为二者等价. 

[`select_on_container_copy_construction`](https://cppreference.com/cpp/memory/allocator_traits/select_on_container_copy_construction) 在拷贝时(拷贝构造时也会触发)会触发该函数, 其是属于 `allocator_traits` 下的静态成员函数. 当你的分配器没有手动定义这个成员时，`allocator_traits` 提供默认实现:

```Cpp
static Alloc select_on_container_copy_construction(const Alloc& src) { 
    return src; // 直接返回源分配器副本 
}
```

对于无状态的分配器默认即可. 对于有状态的分配器可以自行实现, 例如:

```Cpp
template <typename Ty>
struct YourAlloc {
    YourAlloc select_on_container_copy_construction(const StatefulAlloc& src) const { 
        // 策略B：共享源内存池，但重置分配统计计数 
        YourAlloc new_alloc = src; 
        new_alloc.alloc_cnt = 0; 
        return new_alloc; 
        /* // 策略A：和默认行为一致，完整复制所有状态 
            return src; 
            // 策略C：全新独立内存池，完全隔离 
            YourAlloc separate; separate.pool = std::shared_ptr<char>(new char[4096]);
            return separate; 
        */ 
    }
};
```

如果有自定义实现, 则标准库会使用自定义实现

```Cpp
namespace std { 
template<class Alloc> 
struct allocator_traits { 
    template<class T> static Alloc select_on_container_copy_construction(const Alloc& src) { 
        if constexpr (has_member_select<Alloc>) { 
            // 分配器自定义了函数，优先调用自定义版本 
            return src.select_on_container_copy_construction(src); 
        } else { // 兜底：直接返回源分配器副本 
            return src; 
        } 
    } 
}; 
} // namespace std;
```

`propagate_on_container_move_assignment`: 移动赋值时是否转移源分配器给目标
当其为 `true_type` 时,

1. `dst` 使用自身旧分配器释放原有内存
2. 转移 `src` 的分配器实例给 `dst` (移动语义)
3. 直接窃取 `src` 底层缓冲区指针, 零拷贝
4. `src` 为空容器

当其为 `false_type` 时(默认行为), 不替换 `dst` 的分配器, 分两条子逻辑

1. `dst.get_allocator() == src.get_allocator()`: 分配器等价, 则直接窃取缓冲区, 零开销(无状态分配器永远都是这条, 因为都是等价的)
2. `dst.get_allocator() != src.get_allocator()`: 分配器不等价, 不能直接移交内存(即便是移动语义, 也无法零拷贝).
    1. `dst` 用自身分配器开辟全新缓冲区
    2. 将 `src` 中所有元素移动构造到新内存
    3. `src` 销毁时释放自己原有内存

有状态的有状态分配器：必须手动设为 `true_type`

`propagate_on_container_swap`: 交换两个容器时, 是否同步交换两者的分配器实例
当其为 `true_type` 时: 同时交换容器数据缓冲区, 交换两者分配器内部全部状态. 交换后：a 持有原 b 的分配器与数据, b 持有原 a 的分配器与数据

当其为 `false_type` 时:

- 两个分配器必须相等 `a.get_allocator() == b.get_allocator()`: 交换缓冲区, 分配器各自保留
- 不相等时 UB.

# 多态内存分配器

在C++17中, 标准引入了 PMR (polymorphic memory resource) 多态内存分配器. 原有的内存分配器太难用了, 内存分配器的之间的拷贝太耗时, 本质上还是内存资源和内存分配算法没有解耦.

对于原有的 `vector` 实际上你很难控制内存分配的次数, 即便使用 `reserve` 也会难以避免. 所以一个思路是: 提前分配内存资源, 然后让 `vector` 从这个已经分配好的资源中获取内存, 这样就不会多次分配内存而是统一使用已经分配好的内存资源, 即 PMR, 多态内存资源.
例如:

```Cpp
int main(){
    std::array<std::byte, 8192> buffer;
    std::pmr::monotonic_buffer_resource pool{
        buf.data(), 
        buf.size()
    };
    // 这两个都要使用 pmr, 由于分配器的转播规则.
    std::pmr::vector<std::pmr::string> strs { &pool };
    for (size_t i=0; i<256; ++i){
        strs.emplace_back("hello world");
    }
}
```

相当于上例中的 `vector` 使用了在栈上分配的内存.

而所谓"多态", 则是标准库将内存资源和内存分配算法之间的解耦. 
底层内存资源 `memory_source` 是一个抽象基类, 只负责原始内存分配. 而上层的 `std::pmr::polymorphic_allocator<Ty>` 则是真正的分配器, 内部仅持有内存资源的指针.

既然 memory_source 是一个抽象类, 那自然可以自定义内存资源. 此时需要继承该类, 并重载对应方法

```Cpp
namespace std::pmr { 
class memory_resource { 
public: // 对外公共接口（final，不可重写） 
    void* allocate(size_t bytes, size_t alignment = alignof(max_align_t)); 
    void deallocate(void* p, size_t bytes, size_t alignment = alignof(max_align_t)); 
    bool is_equal(const memory_resource& other) const noexcept;
    
 protected: 
     // 虚函数，由子类实现真实内存逻辑 
     // 分配内存
    virtual void* do_allocate(size_t, size_t) = 0; 
    // 回收内存
    virtual void do_deallocate(void*, size_t, size_t) = 0; 
    // 判断内存资源是否相等
    virtual bool do_is_equal(const memory_resource&) const noexcept = 0;
    memory_resource() = default; 
    virtual ~memory_resource() = default; 
    memory_resource(const memory_resource&) = delete; 
    memory_resource& operator=(const memory_resource&) = delete;
 }; 
 }
```

这里的 `memory_source` 没有对应的模板 `Ty`, 因为内存资源管理的是 bytes 而不在乎什么类型.  标准已经提供了五种内存资源:

- `new_delete_resource`: 每次分配和释放都会调用 `new` 和 `delete`, 相当于原来的 `std::allocator`
- `null_memory_resource`: 返回一个每次分配都会失败的内存资源的指针, 抛出 `std::bad_alloc` 异常.
- `monotonic_buffer_resource`: 线性分配内存, 只增长不局部释放; 仅销毁整体一次性回收
- `synchronized_pool_resource` 和 `unsynchronized_pool_resource`: 分块内存池, 一个线程安全一个线程不安全.

上层的 `std::pmr::polymorphic_allocator<Ty>`, 则符合C++标准对内存分配器的要求

```Cpp
template<class T> class polymorphic_allocator { 
    memory_resource* mr_; // 仅存内存资源指针，无其他状态 
public: 
    // 构造：绑定一个内存资源 
    polymorphic_allocator(memory_resource* r = get_default_resource()) noexcept; 
    // rebind 天然支持，转换后共用同一个 mr_ 
    template<class U> polymorphic_allocator(const polymorphic_allocator<U>& other) noexcept; 
    // 分配T类型对象，底层调用 mr_->allocate 
    T* allocate(size_t n); 
    void deallocate(T* p, size_t n) noexcept; 
    // 获取绑定的内存资源 
    memory_resource* resource() const noexcept; 
    // 内置全套类型别名, allocator_traits 无需兜底 
    using value_type = T; 
    using size_type = size_t; 
    using difference_type = ptrdiff_t; 
    // 传播标签全部 true（有状态分配器标准配置） 
    using propagate_on_container_copy_assignment = true_type;
    using propagate_on_container_move_assignment = true_type;
    using propagate_on_container_swap = true_type; 
    // 拷贝构造自定义函数 select_on_container_copy_construction 
    polymorphic_allocator select_on_container_copy_construction(const polymorphic_allocator&) const; 
};
```

其核心优势就在于, 由于底层的内存资源都是一样的. 所以不存在内存的复制.
