---
title: UE-Input System
date: 2026-02-24 21:00:31
tags:
---
# UE的输入处理流程
在引擎初始化的时候会初始化其UI系统: Slate, 具体来说: 当玩家通过设备输入某个"键位"的时候, 这个按键首先会被对应操作系统捕获, 例如: `FWindowsApplication` 下的 Window API; `FLinuxApplication` 下的 SDL. 通过这些平台将输入信号传导至 `FSlateApplication` 中的形如 OnXXX 的信号处理函数中, 从而被 Slate 捕获. 然后 Slate 尝试处理这些输入信号(详情见: [[Slate{0}-UI设计的机制#UE的UI框架-Slate]]), 如果 Slate 无法处理这些信号, 这些信号则会穿透 Slate 系统, 进入 PlayerController 中. 进入 `APlayerController::InputKey` (或者 `InputAxis`, 但是还是会调用到 `InputKey` ), 所以如果想模拟虚拟输入只要手动调用 `APlayerController::InputKey` 即可.
在 `APlayerController::InputKey` 中, 输入信号会被转发至 `UPlayerInput::InputKey` 中, 然后将状态写入 `UPlayerInput` 的成员 `TMap<FKey,FKeyState> KeyStateMap;` 中, 由于 `APlayerController::ProcessPlayerInput` 是每帧调用的所以会在下一帧的处理来自玩家的所有输入, 完整的流程如下(省略不必要的性能测量):
```Cpp
void APlayerController::ProcessPlayerInput(const float DeltaTime, const bool bGamePaused)  {  
    static TArray<UInputComponent*> InputStack;  
    // process all input components in the stack, top down 
    BuildInputStack(InputStack);

    // process the desired components  
    PlayerInput->ProcessInputStack(InputStack, DeltaTime, bGamePaused);
    InputStack.Reset();  
}
```


```Cpp
/**
 * @brief 对 InputStack 进行优先级的排序, 这个优先级的大方向是在函数中定死: 
 *     控制器控制的那个 Pawn 的优先级 < 关卡蓝图 ALevelScriptActor < 控制器自己
 *     其中:
 *         - APawn* ControlledPawn 就是走正常的输入: 经典输入, 增强输入
 *         - ULevel* Level : GetWorld()->GetLevels(): 关卡蓝图, 遍历每一个 Level 并 Push 
 *         - InputEnabled(): 控制器自身的输入, 用于各种快捷键或者调试
 *         - CurrentInputStack: 表示手动 Push 的进来的 Input,(手动调用 PushInputComponent(UInputComponent* InInputComponent)) 其拥有最高的优先级
 *     这个之所以叫做 Stack, 是因为其在获取元素时是从尾开始遍历的, 用于模拟真正 Stack 的 Pop,
 *     所以后插入的优先级反而更高    
 */
void APlayerController::BuildInputStack(TArray<UInputComponent*>& InputStack) {  
    // Controlled pawn gets last dibs on the input stack  
    APawn* ControlledPawn = GetPawnOrSpectator();  
    if (ControlledPawn) {  
           if (ControlledPawn->InputEnabled()) {  
                  // Get the explicit input component that is created upon Pawn possession. This one gets last dibs.  
                  if (ControlledPawn->InputComponent)  
                      InputStack.Push(ControlledPawn->InputComponent);  

                  // See if there is another InputComponent that was added to the Pawn's components array (possibly by script).  
                  for (UActorComponent* ActorComponent : ControlledPawn->GetComponents()) {  
                         UInputComponent* PawnInputComponent = Cast<UInputComponent>(ActorComponent);  
                         if (PawnInputComponent && PawnInputComponent != ControlledPawn->InputComponent)  
                             InputStack.Push(PawnInputComponent);    
                  }  
           }  
    }  

    // LevelScriptActors are put on the stack next  
    for (ULevel* Level : GetWorld()->GetLevels()) {  
        ALevelScriptActor* ScriptActor = Level->GetLevelScriptActor();  
        if (ScriptActor)  
            if (ScriptActor->InputEnabled() && ScriptActor->InputComponent)  
                   InputStack.Push(ScriptActor->InputComponent);  
    }  
  
    if (InputEnabled())  
        InputStack.Push(InputComponent);  
  
        // Components pushed on to the stack get priority  
    for (int32 Idx=0; Idx<CurrentInputStack.Num(); ++Idx)  {  
           UInputComponent* IC = CurrentInputStack[Idx].Get();  
           if (IsValid(IC))  
               InputStack.Push(IC);   
           else  
               CurrentInputStack.RemoveAt(Idx--);
    }  
}
```

> 需要注意的是:
> - `UInputComponent` 本身也有 `Priority` 成员
> - 每帧 `BuildInputStack` 是必要的, 因为输入对象的状态 `InputEnabled()` 可能随时都会被改变, 所有每帧接收的输入可能都不一样

在 `PlayerInput->ProcessInputStack(InputStack, DeltaTime, bGamePaused);` 其会
1. 收集所有 Key 的状态: `EvaluateKeyMapState(DeltaTime, bGamePaused, OUT KeysWithEvents);` 
2. 触发所有收集到的 Key 的 Delegate: `EvaluateInputDelegates(InputComponentStack, DeltaTime, bGamePaused, KeysWithEvents);` 逆序地遍历并发送 Delegate
3. 重置 PlayerInput 中的 `KeyStateMap` 

> PlayerController 中的 `InputStack` 的含义是: 本帧谁来处理输入, 按什么优先级. 即表示本帧参与处理输入的 InputComponent 列表
> PlayerInput 中的 `KeyStateMap` 的含义是: 本地设备输入的事实状态库
# 增强输入系统

UE5 引入了增强输入系统, 用于替代原有的输入系统. 增强输入并没有修改底层的输入, 而是从中途接管逻辑输入. 
增强输入在中途接管的方式就是重新定义了新的子类, 核心对象:
- `UEnhancedPlayerInput : public UPlayerInput {};` EPI: 增强输入
    - `UPlayerInput` 将 Key 映射至 ActionName / AxisName; `UEnhancedPlayerInput` 将 Key 映射至 `InputAction`
- `UEnhancedInputComponent : public UInputComponent {};` EIC: 输入组件
    - `UInputComponent`: 将 ActionName / AxisName 映射为 Delegate; `UEnhancedInputComponent` 将 `InputAction` 映射至 Delegate
- `UInputAction` IA: 输入动作, 具体来说, 一个按键如何触发, 触发时执行哪个回调
    - 绑定方式, 例如: `EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AMyPlayerCharacter::Move);`
    - 回调的传递的参数C++: 
        - 回调 type 为 `void()` 例如 Jump
        - 回调 type 为 `void(const FInputActionValue&)`
        - 回调 type 为 `void(const FInputActionInstance&)`
    - 回调的传递的参数BP: `void(FInputActionValue ActionValue, float ElapsedTime, float TriggeredTime)`
- `UInputModifier` IM: 输入修改器
    - DeadZone: 限定范围的值
    - Scalar: 缩放标量
    - Negate: 取反
    - Smooth: 多帧平滑
    - CurveExponential: 指数曲线, XYZ
    - CurveUser: 自定义用户曲线, CurveFloat
    - FOVScaling: FOV缩放
    - ToWorldSpace: 输入设备坐标系向世界坐标系转换 (调换XYZ顺序)
    - SwizzleAxis: 互换轴值
    - Collection: 嵌套子修改器集合
- `UInputTrigger` IT: 输入触发器: [[TriggerState转换自动机.excalidraw]] 同时有若干子类作为Trigger方式
    - `UInputTriggerDown`: 值大于阈值(默认0.5)触发
    - `UInputTriggerPressed`: 不激活到激活
    - `UInputTriggerReleased`: 激活到不激活
    - `UInputTriggerHold`: 按住大于某个时间
    - `UInputTriggerHoldAndRelease`: 按住大于某个时间松开
    - `UInputTriggerTap`: 按下后快速抬起(默认0.2)
    - `UInputTriggerChorded`: 根据别的Action联动触发
- `UInputMappingContext` IMC: 输入映射上下文: Key 到 Action 的映射集合(高优先级的Key会覆盖低优先级的)

![[UML-UE-InputSystem.excalidraw]]
所以优势在于 ActionName / AxisName 只是一个字符串, 而 `InputAction` 作为一个对象, 其能够存储更多的操作和信息.
增强输入的核心设计其分离了按键逻辑和具体按键, 例如: 将 长按某一个键的逻辑 和 实际是哪个键 逻辑进行分离. 
新的输入流程和旧的输入流程几乎一样, 在原来的 `PlayerInput->ProcessInputStack(InputStack, DeltaTime, bGamePaused);` 中, 有两个操作:
1. `EvaluateKeyMapState(DeltaTime, bGamePaused, OUT KeysWithEvents);`: 收集所有 Key 的状态
2. `EvaluateInputDelegates(InputComponentStack, DeltaTime, bGamePaused, KeysWithEvents);`: 触发所有收集到的 Key 的 Delegate:, 逆序地遍历并发送 Delegate
3. 重置 PlayerInput 中的 `KeyStateMap` 

在 EnhancedInput 中, 将 `EvaluateKeyMapState` 和 `EvaluateInputDelegates` 重写, 其中 `EvaluateKeyMapState` 的流程修改不大, 主要是做兼容, 最后还是会调用 `Super::EvaluateKeyMapState`. 
在 `EvaluateInputDelegates` 中的支持了全新的流程: 
- `ProcessActionMappingEvent`
- 处理 Mapping 的 Modifier 和 Trigger
- 处理 Action 的 Modifier 和 Trigger
- `Super::EvaluateInputDelegates(InputComponentStack, DeltaTime, bGamePaused, KeysWithEvents);`

所以局部的(Mapping) 和 全局的(Action) 的 Modifier 会同时触发, 会有负负得正的现象

> [!note] 实践
> - 按照类型使用局部的 `UInputMappingContext` , 不要设置全局的 触发器 和 修改器.
> - 在对应的玩家操控的 Character 或 Pawn 的派生类的 `BeginPlay()` 中调用 AddMappingContext, 例如: `EnhancedInputSubsystem->AddMappingContext(DefaultPlayerMappingContext, 0);`
> - 在 SetupInputComponent 中调用 BindAction, 例如: `EnhancedInputComponent->BindAction(MoveAction, ETriggerEvent::Triggered, this, &AMyPlayerCharacter::Move);`
> - `AMyPawn::UnPossessed()` 中 `RemoveMappingContext(); Super::UnPossessed();`

## UInputTrigger 使用
### UInputTriggerChorded 和弦触发器
要求: 实现按住鼠标左键旋转视角, 松开则无法旋转.
实现: 一个基础的 Look
```Cpp
EnhancedInputComponent->BindAction(LookAction, ETriggerEvent::Triggered, this, &AMyPlayerCharacter::Look);
void AMyPlayerCharacter::Look(const FInputActionValue& Value)  
{  
    FVector2D LookAxisVector = Value.Get<FVector2D>();     
    if (Controller)  
    {  
      AddControllerYawInput(LookAxisVector.X);  
      AddControllerPitchInput(LookAxisVector.Y);  
    }  
}
```
创建一个新的 Action: `IA_LookHold` 值为 `bool`, 在 IMC 中添加鼠标左键的映射, 同时在 `LookAction` 中添加 Trigger: Chorded Action, 并将其设置为 `IA_LookHold`, 即只有在 `IA_LookHold` 触发时 `LookAction` 才能触发
追加绑定:
```Cpp
EnhancedInputComponent->BindAction(LookHoldAction, ETriggerEvent::Started, this, &AMyPlayerCharacter::LookHoldStarted);  
EnhancedInputComponent->BindAction(LookHoldAction, ETriggerEvent::Completed, this, &AMyPlayerCharacter::LookHoldCompleted);
```
其目的是在按下左键的时候同时能做其他处理
## Debug 命令
- `Input.action ActionName Value`: 强制添加某个Action的输入
- `Input.action ActionName`: 移除添加某个Action的输入
- `Input.+key Key Value`: 添加某个 Key 的输入
- `Input.-key Key Value`: 移除某个 Key 的输入
- `ShowDebug EnhancedInput`: 显示调试界面

参考:
- [虚幻引擎倾囊相授计划：增强输入系统教程](https://www.bilibili.com/video/BV1TM41197Dv/?spm_id_from=333.337.search-card.all.click&vd_source=75cdf78dd1707c1077825f0501243c43)
- [知乎: UE5 EnhancedInput(增强输入系统)](https://zhuanlan.zhihu.com/p/470949422)
- [虚化引擎官方: 虎跳龙拿--新一代增强输入框架EnhancedInput](https://www.bilibili.com/video/BV14r4y1r7nz/?spm_id_from=444.41.0.0&vd_source=75cdf78dd1707c1077825f0501243c43)
- [知乎 UE4对玩家输入的处理流程](https://zhuanlan.zhihu.com/p/393346131)
