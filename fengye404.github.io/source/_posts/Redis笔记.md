---
title: Redis笔记
typora-root-url: ./Redis笔记
date: 2023-01-24 15:49:03
tags:
---

## 前言

学习后端开发这么久，Redis 是我常用的一个中间件，以往主要是用于做缓存处理和暂存一些值。但用了这么多，却并没有深入地了解过 Redis 底层，并且平时的使用也大多都是通过 SpringData 封装的 RedisTemplate，连 Redis 本身的命令也几乎要忘掉了。因此打算写一篇总结性的博客，包括Redis的基础 + Redis底层 + Redis进阶使用。

## Redis基础

### 基础指令

#### 操作数据库相关指令

- 启动 Redis 客户端: `redis-cli -h host -p port -a password`
- 切换当前数据库: `select 数据库index(0-15)`
- 清空当前的库: `FLUSHDB` ；清空所有库: `FLUSHALL`
- 动态调整 Redis 的配置而不用重启（重启失效）：`CONFIG SET ...`

#### 操作数据类型相关指令

##### String

String 是 Redis 中最简单的存储类型，一个 key 对应一个 value。其 value 是字符串（可以细分为字符串、整数、浮点数）。value 最大值不能超过512mb。

| 命令                             | 说明                                                  |
| -------------------------------- | ----------------------------------------------------- |
| SET key value                    | 设置一个key/value                                     |
| GET key                          | 根据key获得对应的value                                |
| MSET key value [key value ...]   | 一次设置多个key的value                                |
| MGET key1 [key2..]               | 一次获得多个key的value                                |
| GETSET key value                 | 获得原始key的值，同时设置新值                         |
| STRLEN key                       | 获得对应key存储value的长度                            |
| APPEND key value                 | 为对应key的value追加内容                              |
| GETRANGE key start end           | 截取value的内容（索引从0开始）                        |
| SETEX key seconds value          | 设置一个key存活的有效期（秒）                         |
| PSETEX key milliseconds value    | 设置一个key存活的有效期（毫秒）                       |
| SETNX key value                  | key不存在则设置value                                  |
| MSETNX key value [key value ...] | 多个key都不存在则设置多个value                        |
| DECR key                         | 将指定的数值类型-1                                    |
| DECRBY key                       | 将指定的数值类型减去指定的值（二者必须都是整数）      |
| INCR key                         | 将指定的数值类型+1                                    |
| INCRBY key increment             | 将指定的数值类型加上指定的值（二者必须都是整数）      |
| INCRBYFLOAT key increment        | 将指定的数值类型加上指定的值（increment必须是浮点数） |

使用场景：

- 缓存
- 计数器
- 共享Session

##### List

Redis 中的 List 是一个双向链表结构。一个 Key 对应多个有序的 Value，可以添加元素到头部（左边）或者尾部（右边）。一个 List 最多可以包含 `2^32 - 1` 个元素（4294967295）。

| 命令                                 | 说明                                      |
| ------------------------------------ | ----------------------------------------- |
| LPUSH key value1 [value2]            | 将一个或多个值插入到 key list 的左边      |
| LPUSHX key value1 [value2]           | 同LPUSH，但是必须要保证这个 key list 存在 |
| RPUSH key value1 [value2]            | 将某个值加入到一个key列表末尾             |
| RPUSHX key value1 [value2]           | 同RPUSH，但是必须要保证这个 key list 存在 |
| LPOP key                             | 返回并移除列表左边的第一个元素            |
| RPOP key                             | 返回并移除列表右边的第一个元素            |
| LRANGE key start stop                | 获取某一个下标区间内的元素                |
| LLEN key                             | 获取列表元素个数                          |
| LSET key index value                 | 设置某一个指定索引的值（索引必须存在）    |
| LINDEX key index                     | 获取某一个指定索引位置的元素              |
| LREM key count value                 | 删除列表中前 count 值等于 value 的元素    |
| LTRIM key start stop                 | 保留列表中特定区间内的元素                |
| LINSERT key BEFORE/AFTER pivot value | 在某一个元素之前/之后插入新元素           |

通过以上命令组合，List 既可以作为队列，也可以作为栈等数据结构使用。

使用场景：

- 时间轴
- 消息队列

##### Set

Redis 中的 Set 是 String 类型的无序集合，一个 Key 对应多个无序的 Value。Set 是通过哈希表实现的，所以添加、删除、查找的复杂度都是O(1)。集合中不能有重复元素。

| 命令                            | 说明                                               |
| ------------------------------- | -------------------------------------------------- |
| SADD key member1                | 为集合添加元素                                     |
| SMEMBERS key                    | 显示集合中所有元素（无序）                         |
| SCARD key                       | 返回集合中元素的个数                               |
| SPOP key                        | 随机返回并删除一个元素                             |
| SMOVE source destination member | 从一个集合中向另一个集合移动元素  必须是同一种类型 |
| SREM key member                 | 从集合中删除元素                                   |
| SISMEMBER key member            | 判断集合中是否含有这个元素                         |
| SRANDMEMBER key [count]         | 返回一个或多个随机元素                             |
| SDIFF key1 key2                 | 返回两个集合中不同的元素                           |
| SINTER key1 key2]               | 返回交集                                           |
| SUNION key1 key2                | 返回并集                                           |

使用场景：

- tag标签
- 点赞、收藏

##### Zset

Redis 中的 Zset 是 String 类型的有序集合，一个 Key 对应多个有序的 value，每个 Key 同时还会关联一个 double 类型的分数。Zset 排序的依据就是这个分数。Zset底层通过跳表 + hash表实现。

| 命令                         | 说明                             |
| ---------------------------- | -------------------------------- |
| ZADD key score1 member1      | 添加一个有序集合元素，并指定分数 |
| ZCARD key                    | 返回集合的元素个数               |
| ZCOUNT key min max           | 返回指定范围内的元素个数         |
| ZRANGEBYSCORE key min max    | 按照分数查找一个范围内的元素     |
| ZRANK key member             | 返回某个元素的排名               |
| ZREVRANK zrevrank            | 返回某个元素的倒序排名           |
| ZSCORE key mem               | 显示某一个元素的分数             |
| ZREM key member              | 移除某一个元素                   |
| ZINCRBY key increment member | 给某个特定元素加分               |

使用场景：

- 排行榜

##### Hash

Redis 中的 Hash 是 String 类型的键值对（filed/value）映射表。每个Hash可以存储 `2^32 - 1` 个键值对（4294967295）。

| 命令                                    | 说明                              |
| --------------------------------------- | --------------------------------- |
| HSET key field value                    | 设置一个 filed/value 对           |
| HGET key field                          | 获得一个 filed 对应的 value       |
| HGETALL key                             | 获得所有的 filed/value 对         |
| HDEL key field1 [field2]                | 删除一个或多个 filed/value 对     |
| HEXISTS key field                       | 判断一个 filed 是否存在           |
| HKEYS key                               | 获得所有的 filed                  |
| HVALS key                               | 获得所有的 value                  |
| HLEN key                                | 获取 filed/value 对个数           |
| HMSET key field1 value1 [field2 value2] | 设置多个 filed/value              |
| HMGET key field1 [field2]               | 获得多个 filed 的 value           |
| HSETNX key field value                  | field 不存在则添加 field/value 对 |
| HINCRBY key field increment             | 为 value 进行加法运算，同 String  |
| HINCRBYFLOAT key field increment        | 为 value 加入浮点值，同 String    |

使用场景：

- 缓存

#### 操作key相关指令

- del

  - 语法: DEL key [key ...] 
  - 作用: 删除给定的一个或多个 key 。不存在的 key 会被忽略。
  - 返回值: 被删除 key 的数量。 

- exists

  - 语法: EXISTS key
  - 作用: 检查给定 key 是否存在。
  - 返回值: 若 key 存在，返回 1 ，否则返回 0。

- expire

  - 语法: EXPIRE key seconds
  - 作用: 为给定 key 设置生存时间，当 key 过期时，它会被自动删除。
  - 返回值: 设置成功返回1 。

- keys

  - 语法: KEYS pattern
  - 作用: 查找所有符合给定模式 pattern 的key 。
    KEYS * 匹配数据库中所有key 。
    KEYS h?llo 匹配 hello，hallo 和 hxllo 等。
    KEYS h*llo 匹配 hllo 和 heeeeello 等。
    KEYS h[ae]llo 匹配 hello 和 hallo ，但不匹配hillo 。特殊符号用 "\" 隔开
  - 返回值: 符合给定模式的key 列表。

- move

  - 语法: MOVE key db
  - 作用: 将当前数据库的 key 移动到给定的数据库 db 当中。
  - 返回值: 移动成功返回 1 ，失败则返回 0 。

- pexpire

  - 语法: PEXPIRE key milliseconds
  - 作用: 这个命令和 EXPIRE 命令的作用类似，但是它以毫秒为单位设置 key 的生存时间
  - 返回值: 设置成功，返回 1；key不存在或设置失败，返回 0

- ttl

  - 语法: TTL key
  - 作用: 以秒为单位，返回给定 key 的剩余生存时间(time to live)。
  - 返回值: 
    当key 不存在时，返回-2 。
    当key 存在但没有设置剩余生存时间时，返回-1 。
    否则，以秒为单位，返回key 的剩余生存时间。
  - 注意: 在Redis 2.8 以前，当key 不存在，或者key 没有设置剩余生存时间时，命令都返回-1 。

- pttl

  - 语法: PTTL key

  - 作用: 这个命令类似于 TTL 命令，但它以毫秒为单位返回 key 的剩余生存时间

  - 可用版本: >= 2.6.0

  - 返回值: 

    当key 不存在时，返回 -2 。

    当key 存在但没有设置剩余生存时间时，返回 -1 。

    否则，以毫秒为单位，返回 key 的剩余生存时间。

  - 注意: 在Redis 2.8 以前，当 key 不存在，或者 key 没有设置剩余生存时间时，命令都返回-1 。

- randomkey

  - 语法: RANDOMKEY
  - 作用: 从当前数据库中随机返回(不删除) 一个 key 。
  - 返回值: 当数据库不为空时，返回一个 key 。当数据库为空时，返回nil 。

- rename

  - 语法: RENAME key newkey
  - 作用: 将 key 改名为 newkey 。当 key 不存在时，返回一个错误。当 newkey 已经存在时，RENAME 命令将覆盖旧值。
  - 返回值: 改名成功时提示OK ，失败时候返回一个错误。

- type

  - 语法: TYPE key
  - 作用: 返回key 所储存的值的类型。
  - 返回值: 
    none (key 不存在)
    string (字符串)
    list (列表)
    set (集合)
    zset (有序集)
    hash (哈希表)

## Redis底层

> 参考：《Redis设计与实现》（基于Redis 2.9）

### 数据结构与对象

#### 数据结构

Redis 底层中构造了一系列的数据结构。需要注意的是，这些数据结构和前面介绍的数据类型并没有直接的一一对应关系，数据类型实际上是对数据结构的进一层封装（在后续的“对象“部分会提到）。这些数据结构并不只是用于数据类型的底层，其中的大部分数据结构都广泛地应用在 Redis 内部的其他部分。

##### 单动态字符串

Redis是用C语言实现的，但是Redis中的字符串并没有直接使用C语言传统的字符串表示，而是自己构建了一种名为简单动态字符串的抽象类型（simple dynamic string，SDS），并将SDS作为Redis的默认字符串表示。SDS定义在 `src/sds.h` 和 `src/sds.c` 中。

`src/sds.h/sdshdr` 定义了SDS的结构：

```c
struct sdshdr {
	//记录buf数组中已使用字节的数量
	//等于SDS所保存字符串的长度
	int len;
	
	//记录buf数组中未使用字节的数量
	int free;
	
	//字节数组，用于保存字符串
	char buf[];
};
```

![image-20230105195656692](./202301051956753.png)

例如有如上SDS示例：

- free属性的值为0，表示这个SDS没有分配任何未使用空间。
- len属性的值为5，表示这个SDS保存了一个五字节长的字符串。
- buf属性是一个char类型的数组，数组的前五个字节分别保存了'R'、'e'、'd'、'i'、's'五个字符，而最后一个字节则保存了空字符'\0'。最后的空字符串不计算入len。

SDS遵循了C字符串以空字符结尾的惯例，因此可以直接复用C语言字符串函数库里的部分函数。

使用SDS而非C字符串的优势：

- C字符串并不能保存自身的长度信息，因此为了获取一个字符串的长度，需要遍历整个字符串直到结尾的空字符串。而SDS保存了字符串的长度，因此可以**常数复杂度获取字符串长度**。
- C字符串容易造成缓冲区溢出。而SDS的API**杜绝了缓冲区的溢出**。
- C字符串底层是字符数组，由于C数组是不可变的，因此每次对C字符串进行修改操作都需要重新分配内存。而SDS的API会预分配一部分未使用的内存给SDS，并且惰性释放空间，**避免了频繁的内存分配**。
- C字符串使用空字符表示字符串结尾，因此无法存储一些带有空字符的数据。而SDS的API会采用处理二进制数据的方式来处理buf中的数据，因此**SDS是二进制安全的**。

##### 链表

链表是一种常用的数据结构，由于C语言中并没有内置这种数据结构，所以Redis构建了自己的链表实现。

###### linkedlist

linkedlist 类似于 Java 中的 LinkedList，是一个双向链表。linkedlist 在 Redis 中应用广泛，例如列表键的底层实现之一就是 linkedlist。当列表键包含较多元素或者列表中的元素大小较长，Redis就会采用链表作为列表键的底层实现。

它的每个链表节点定义在 `adlist.h/listNode` 中：

```c
typedef struct listNode {
	// 前置节点
	struct listNode *prev;
	
	// 后置节点
	struct listNode *next;
	
	// 节点的值
	void *value;
} listNode;
```

多个 listNode 通过 prev 和 next 指针组成双向链表：

![image-20230106043905043](./202301060439086.png)

`adlist.h/list` 中定义了 list 来持有双向链表：

```c
typedef struct list {
	// 表头节点
	listNode * head;
	
	// 表尾节点
	listNode * tail;
	
	// 链表所包含的节点数量
	unsigned long len;
	
	// 节点值复制函数
	void *(*dup)(void *ptr);
	
	// 节点值释放函数
	void (*free)(void *ptr);
	
	// 节点值对比函数
	int (*match)(void *ptr,void *key);
} list;
```

###### ziplist

ziplist 是 Redis 为了节约内存而开发的，是由一系列特殊编码的连续内存块组成的**顺序型数据结构**。

ziplist 是列表键和哈希键的底层实现之一。当一个列表键只包含少量列表项，并且每个列表项都是小整数值或者长度较短的字符串，Redis 就会使用 ziplist 作为列表键的底层实现；当一个哈希表键只包含少量键值对，并且每个键值对的键和值都是小整数值或长度较短的字符串，Redis 就会使用 ziplist 作为哈希表键的底层实现。

**压缩列表的结构**

![image-20230109203249382](./202301092032475.png)

| 属性    | 类型     | 长度  | 作用                                                         |
| ------- | -------- | ----- | ------------------------------------------------------------ |
| zlbytes | uint32_t | 4字节 | 记录整个压缩列表占用的字节数                                 |
| zltail  | uint32_t | 4字节 | 记录压缩列表中末尾节点距离压缩列表起始地址的字节数           |
| zllen   | uint16_t | 2字节 | 记录了压缩列表包含的节点数量（上限是 65535，即当压缩列表节点的数量大于 65535 时，需要遍历整个压缩列表才知道真实节点数量） |
| entryX  | 列表节点 | 不定  | 保存压缩列表的各个节点，节点长度由具体保存的内容决定         |
| zlend   | uint8_t  | 1字节 | 特殊值 0xff，标记压缩列表的末端                              |

例如有如下压缩列表：

![image-20230110030545902](./202301100305945.png)

- zlbytes 为 0x50（十进制8 0），表示压缩列表的总长为80字节。
- zltail 为 0x3C（十进制 60），标识如果有一个指向压缩列表起始地址的指针 p，那么只需要用 p 加上偏移量60，就可以计算出表尾节点 entry3 的地址。
- zllen 为 0x3（十进制 3），标识压缩列表包含三个节点。

**压缩列表节点的结构**

每个压缩列表节点可以保存一个字节数组或者一个整数值。

![image-20230110032029417](./202301100320450.png)

- previous_entry_length：记录前一个节点的字节长度。通过这个属性可以计算出前一个节点的位置，用于帮助程序实现从后向前遍历。
  - 若前一个节点的长度小于 254 字节，则 previous_entry_length 占用一个字节，其中保存的就是前一个结点的长度。
  - 若前一个节点的长度大于等于 254 字节，则 previous_entry_length 占用五个字节，第一个字节的值被固定为 0xFE（十进制 254），后面四个字节用于保存迁移节点的长度。
- encoding：记录 content 保存的数据的类型和长度。
  - 若 encoding 占用一字节并且二进制高位以 11 开头，则说明 content 保存的是整数。content 的类型由 encoding 去掉最高两位之后的其他位记录：
    - encoding 为 11000000，content 类型为 int16_t。
    - encoding 为 11010000，content 类型为 int32_t。
    - encoding 为 11100000，content 类型为 int64_t。
    - encoding 为 11110000，content 类型为 24 位有符号整数。
    - encoding 为 11111110，content 类型为 8 位有符号整数。
    - encoding 为 1111xxxx，由于 encoding 本身的 xxxx 四位已经可以保存一个介于 0 和 12 之间的值，因此没有 content 属性。
  - 若 encoding 占用一字节、两字节、五字节，值的最高位为00、01、10，则说明 content 保存的是字节数组。content 的长度由 encoding 去掉最高两位之后的其他位记录。
    - encoding 为 00bbbbbb，content 保存的是长度小于等于 63 字节的字节数组。
    - encoding 占用两字节时，content 保存的是长度小于等于 16383 字节的字节数组。
    - encoding 占用五字节时，content 保存的是长度小于等于 4294967295 字节的字节数组。
- content：负责保存数据。

##### 字典

###### 字典的实现

Redis中的字典使用哈希表作为底层实现，由三部分组成：dictEntry、dictht、dict。

哈希表由 `dict.h/dictht` 定义：

```c
typedef struct dictht {
	// 哈希表数组
	// 每个元素都是一个指向 dict.h/dictEntry 的指针
	// 每个 dictEntry 结构保存着一个键值对
	dictEntry **table;
	
	// 哈希表大小，即 table 数组大小
	unsigned long size;
	
	// 哈希表大小掩码，用于计算索引
	// 总是等于 size - 1 
	unsigned long sizemask;
	
	// 该哈希表已有节点的数量
	unsigned long used;
} dictht;
```

哈希表节点由 `dict.h/dictEntry` 定义：

```c
typedef struct dictEntry {
	
	// 键
	void *key;
	
	// 值
	// 值可以是指针，
	// 也可以是uint64_tu64或int64_ts64整数
	union{
		void *val;
		uint64_tu64;
		int64_ts64;
	} v;
	
	// 采用链表解决哈希冲突
	// next即指向链表下一个节点的指针
	struct dictEntry *next;
	
} dictEntry;
```

字典由 `dict.h/dict` 定义：

```c
typedef struct dict {
	
	// 类型特定函数
	dictType *type;
	
	// 私有数据
	void *privdata;
	
	// 哈希表
	dictht ht[2];
	
	// rehash 索引
	// 当 rehash 不在进行时，值为-1
	int rehashidx;
}
```

- type属性和privdata属性时针对不同类型的键值对，为创建多态字典而设置的：

  - type属性是一个指向 dictType 结构的指针，每个 dictType 结构保存了一些用于操作特定类型键值对的函数，Redis会为用途不同的字典设置不同类型的特定函数。

    ```c
    typedef struct dictType {
    	//计算哈希值的函数
    	unsigned int (*hashFunction)(const void *key);
    	
    	//复制键的函数
    	void *(*keyDup)(void *privdata, const void *key);
    	
    	//复制值的函数
    	void *(*valDup)(void *privdata, const void *obj);
    	
    	//对比键的函数
    	int (*keyCompare)(void *privdata, const void *key1, const void *key2);
    	
    	//销毁键的函数
    	void (*keyDestructor)(void *privdata, void *key);
    	
    	//销毁值的函数
    	void (*valDestructor)(void *privdata, void *obj);
    } dictType;
    ```

  - privdata属性保存了需要传给那些特定函数的可选参数。

- ht属性是一个包含两个项的数组，数组中的每个项都是一个 dictht 哈希表，一般情况下只会使用 ht[0] 哈希表，ht[1] 只会在对 ht[0] 进行 rehash 时使用。

一个正常情况（没有进行rehash）下的字典结构如图：

![image-20230107063956415](./202301070639470.png)

###### 哈希算法

当要添加一个新的键值对到字典中时，程序会先根据键值对的键计算出哈希值，然后通过哈希值计算出索引值，再将键值对用哈希表节点封装后，存放到哈希表数组的指定索引上。

Redis计算哈希值和索引值的方法如下：

```c
# 使用字典设置的哈希函数，计算键key的哈希值
hash = dict->type->hashFunction(key);

# 使用哈希表的sizemask属性和哈希值，计算出索引值
# 根据情况不同，ht[x]可以是ht[0]或ht[1]
index = hash & dict->ht[x].sizemask;
```

Redis 使用 MurmurHash 算法来计算键的哈希值。

###### 解决哈希冲突

当由两个或以上的键被分配到哈希表的同一个索引上时，就发生了哈希冲突。Redis的哈希表采用链表来解决哈希冲突。每个哈希表节点都有一个next指针，多个哈希表节点可以使用next指针构成一个单向链表。Redis中新节点总是被添加到表头。

###### 调整哈希表容量

和 Java 中的 HashMap 类似，哈希表的底层是一个数组，需要给其定一个初始大小，并且动态地调整容量，以便让其负载因子维持在一个合理的范围内，从而减少哈希冲突的概率。

调整哈希表容量的工作可以通过执行 rehash 操作完成。

Redis 对字典的哈希表执行 rehash 的步骤如下：

1. 为字典的 ht[1] 哈希表分配空间，这个哈希表的空间大小取决于要执行的操作，以及 ht[0] 当前包含的键值对数量（也即是 ht[0].used 属性的值）： 
   - 如果执行的是扩展操作，那么 ht[1] 的大小为第一个大于等于 ht[0].used*2 的2^n。
   - 如果执行的是收缩操作，那么 ht[1] 的大小为第一个大于等于 ht[0].used 的2^n。
2. 将保存在 ht[0] 中的所有键值对 rehash 到 ht[1] 上面：rehash 指的是重新计算键的哈希值和索引值，然后将键值对放置到 ht[1] 哈希表的指定位置上。 
3. 当 ht[0] 包含的所有键值对都迁移到了 ht[1] 之后（ht[0] 变为空表），释放 ht[0]，将 ht[1] 设置为 ht[0]，并在 ht[1] 新创建一个空白哈希表，为下一次 rehash 做准备。

##### 跳跃表

跳跃表是一种有序数据结构，它通过在每个节点中维持多个指向其他节点的指针，从而达到快速访问节点的目的。

跳跃表支持平均 O(logN)、最坏 O(N) 复杂度的节点查找，还可以通过顺序性操作来批处理节点。

**在大部分情况下，跳跃表的效率可以和平衡树相媲美**，并且跳跃表的实现比平衡树要来的更为简单，所以有不少程序都使用跳跃表来代替平衡树。

Redis使用跳跃表作为有序集合的底层实现之一，并且被用于构建 Redis 集群节点时作为内部数据结构。

Redis中的跳跃表由 `redis.h/zskiplistNode` 和 `redis.h/zskiplist` 两个结构定义。其中 zskiplistNode 结构用于表示跳跃表节点，zskiplist 结构用于保存跳跃表节点的相关信息。一个跳跃表实例如图：

![image-20230107222933229](./202301072229290.png)

- zskiplistNode：

  ```c
  typedef struct zskiplistNode {
  
  	// 层
  	struct zskiplistLevel {
  	
  		// 前进指针
  		struct zskiplistNode *forward;
  		
  		// 跨度，即两个节点之间的距离
  		unsigned int span;
  	} level[];
  	
  	// 后退指针
  	struct zskiplistNode *backward;
  	
  	// 分值
  	double score;
  	
  	// 成员对象
  	robj *obj;
  	
  } zskiplistNode;
  ```

  - level[]：数组中的每个元素都是一个 zskiplistLevel 类型的对象。当新的节点被创建时，会随机生成一个1到32之间的值作为 level 数组的大小。
    - zskiplistLevel 的 forward 指针指向下一个节点。
    - zskiplistLevel 的 span 属性表示跨度，即到下个节点的距离。如果 forward 指向的是null，则 span 为0。span的主要作用是计算 rank，在查找某个节点的过程中，将沿途的所有 span 累加，就可以得到目标节点的 rank。
  - backward：用于向表头访问节点。每个节点只有一个 backward 指针，指向前一个节点。
  - socre：double 类型，跳跃表中的节点按照 score 进行排名。
  - obj：指向一个字符串对象，其中保存着一个 SDS。在一个跳跃表中，obj必须是唯一的。

- zskiplist：

  ```c
  typedef struct zskiplist {
  
  	// 表头节点和表尾节点
  	struct zskiplistNode *header, *tail;
  	
  	// 表中节点的数量
  	unsigned long length;
  	
  	// 表中层数最大的节点的层数
  	int level;
      
  } zskiplist;
  ```

##### 整数集合

整数集合（intset）是 Redis 中用于保存整数值的集合抽象数据结构。它可以保存类型为 int16_t、int32_t、int64_t 的整数值，并且保证集合中不出现重复元素。

intset 由 `intset.h/intset` 定义：

```
typedef struct intset {
	
	// 编码方式
	uint32_t encoding;
	
	// 集合包含的元素数量
	uint32_t length;
	
	// 保存元素的数组
	int8_t contents[];
} intset;
```

- contents[]：整数集合中的每个元素都是 contents 数组中的一个数组项，各项在数组中按值的大小从小到大地排列，并且数组中不包含任何重复项。
- encoding：虽然 contents 的属性被声明为 int8_t 类型的数组，但实际上 contents 数组的真正类型取决于 encoding 的值：
  - 如果 encoding 的属性为 INTSET_ENC_INT16，则数组的真正类型为 int16_t。
  - 如果 encoding 的属性为 INTSET_ENC_INT32，则数组的真正类型为 int32_t。
  - 如果 encoding 的属性为 INTSET_ENC_INT64，则数组的真正类型为 int64_t。

每当需要添加一个新元素到整数集合里面，并且新元素的类型比整数集合现有所有元素的类型都要长时，整数集合需要先对数组进行升级（即给数组重新分配空间，并且移动原来的数据到新的位置），才能将新元素添加到整数集合里。

#### 对象

前面介绍完了 Redis 用到的主要数据结构，但是 Redis 并没有直接使用这些数据结构来实现键值对，而是基于这些数据结构创建了一个对象系统，其中包含了字符串对象、列表对象、哈希对象、集合对象和有序集合对象。每种对象都至少用到了一种数据结构。除此之外，Redis 的对象系统还实现了基于引用计数的内存回收机制和对象共享机制。

Redis使用对象来表示数据库中的键和值，每当我们在 Redis 的数据库中新创建一个键值对时，我们至少会创建两个对象，一个是键对象，一个是值对象。

Redis中的每个对象都由 redisObject 结构表示，该结构中有三个最重要的属性：

```c
typedef struct redisObject{
	
	// 类型
	unsigned type:4;
	
	// 编码
	unsigned encoding:4;
	
	// 指向底层实现数据结构的指针
	void *ptr;

    // 引用计数
    int refcount;
    
    // 最后一次访问时间
    unsigned lru:22;
    
	// ...
} robj;
```

- type记录了对象的类型，这个属性的值可以是：

  | 对象       | type属性的值 | TYPE命令的输出 |
  | ---------- | ------------ | -------------- |
  | 字符串对象 | REDIS_STRING | "string"       |
  | 列表对象   | REDIS_LIST   | "list"         |
  | 哈希对象   | REDIS_HASH   | "hash"         |
  | 集合对象   | REDIS_SET    | "set"          |
  | 有序集对象 | REDIS_ZSET   | "zset"         |

  对于键对象来说，它的值永远是字符串类型，而键对象对应的值对象可以是以上五种。因此，当我们称呼一个键对象为：“字符串键”或“列表键”时，指的都是这个键对象所对应的值对象。

- encoding记录了对象所使用的编码，即底层使用的数据结构：

  | 编码常量                  | 编码对应的底层数据结构     |
  | ------------------------- | -------------------------- |
  | REDIS_ENCODING_INT        | long类型整数               |
  | REDIS_ENCODING_EMBSTR     | smbstr编码的简单动态字符串 |
  | REDIS_ENCODING_RAW        | 简单动态字符串             |
  | REDIS_ENCODING_HT         | 字典                       |
  | REDIS_ENCODING_LINKEDLIST | 双端链表                   |
  | REDIS_ENCODING_ZIPLIST    | 压缩列表                   |
  | REDIS_ENCODING_INTSET     | 整数集合                   |
  | REDIS_ENCODING_SKIPLIST   | 跳跃表和字典               |

  每种对象都至少使用了两种不同的编码：

  | 类型         | 编码                      | 对象                                           |
  | ------------ | ------------------------- | ---------------------------------------------- |
  | REDIS_STRING | REDIS_ENCODING_INT        | 使用整数实现的字符串对象                       |
  | REDIS_STRING | REDIS_ENCODING_EMBSTR     | 使用embstr编码的简单动态字符串实现的字符串对象 |
  | REDIS_STRING | REDIS_ENCODING_RAW        | 使用简单动态字符串实现的字符串对象             |
  | REDIS_LIST   | REDIS_ENCODING_ZIPLIS     | 使用压缩列表实现的列表对象                     |
  | REDIS_LIST   | REDIS_ENCODING_LINKEDLIST | 使用双端链表实现的列表对象                     |
  | REDIS_HASH   | REDIS_ENCODING_ZIPLIST    | 使用压缩列表实现的哈希对象                     |
  | REDIS_HASH   | REDIS_ENCODING_HT         | 使用字典实现的哈希对象                         |
  | REDIS_SET    | REDIS_ENCODING_INTSET     | 使用整数集合实现的集合对象                     |
  | REDIS_SET    | REDIS_ENCODING_HT         | 使用字典实现的集合对象                         |
  | REDIS_ZSET   | REDIS_ENCODING_ZIPLIST    | 使用压缩列表实现的有序集合对象                 |
  | REDIS_ZSET   | REDIS_ENCODING_SKIPLIST   | 使用跳跃表和字典实现的有序集合对象             |

  可以通过 `OBJECT ENCODING key` 查看数据库键的值对象编码。

  Redis使用 type 配合 encoding 来设定某个对象的抽象类型和具体实现类型，极大地提升了 Redis 的灵活性和效率。因为 Redis 可以在不同的场景下为一个对象设置不同的 encoding 来切换它的具体实现，从而优化在某一场景下的效率。

##### 字符串对象

字符串对象对应 Redis 命令中的 String 操作。

字符串对象的 encoding 属性可以是 int、raw、embstr：

- int：字符串对象保存的是一个可以用 long 类型表示的整数值。字符串对象的 ptr 属性会由 void* 转变为 long，然后将值存在 ptr 属性中。
- raw：字符串对象保存的是一个长度大于 32 字节的字符串。字符串对象的 ptr 属性指向这个字符串SDS的地址。
- embstr：字符串对象保存的是一个长度小于等于 32 字节的字符串。字符串对象的 ptr 属性指向这个字符串SDS的地址。

> embstr 是一种专门用于保存短字符串的优化编码方式。这种编码和 raw 编码一样，都使用了 redisObject 结构和 sdshdr 结构。
>
> 但是 raw 编码会调用两次内存分配来分别创建 redisObject 结构和 sdshdr 结构，而 embstr 编码则通过调用一次内存分配函数来分配一块连续的空间，空间中依次包含 redisObject 和 sdshdr 结构。并且 embstr 是只读的，因为 Redis 中并没有提供修改其值的 API。
>
> ![image-20230111012820188](./202301110128268.png)
>
> ![image-20230111012831453](./202301110128491.png)

浮点数在 Redis 中也是作为字符串值来保存的。在保存时会将浮点数先转换为字符串值，然后再保存；在有需要时，会将保存的字符串值转换为浮点数值，再执行某些操作。

**编码转换**

当对 int 编码的字符串对象执行了一些命令（例如 append ）时这个对象对象不再是整数，字符串对象的编码就会变为 raw；由于 embstr 编码是只读的，因此对 embstr 编码的字符串对象执行修改操作时，编码也会变成 raw。

##### 列表对象

列表对象对应 Redis 命令中的 list 操作。

列表对象的 encoding 属性可以是 ziplist、linkedlist：

- ziplist：列表对象使用压缩列表作为底层实现。每个压缩列表的节点（entry）保存了一个列表元素。

  执行代码 `RPUSH numbers 1 "three" 5` 后，将创建如下对象：

  ![image-20230111175717385](./202301120630884.png)

- linkedlist：列表对象使用双向链表作为底层实现。每个双向链表的结点（node）保存了一个**字符串对象**。

  ![image-20230111175730989](./202301120630629.png)

> 图8-6中的 StringObject 表示的是一个字符串对象，即下图的简写。
>
> ![image-20230111175823810](./202301111758851.png)

**编码转换**

当列表对象满足以下条件时，会优先使用 ziplist 编码以节约内存：

- 列表对象所保存的所有字符串元素的长度小于 64 字节。
- 列表对象保存的元素数量小于 512 个。

如果不能同时满足以上条件，则使用 linkedlist 编码。

##### 哈希对象

哈希对象对应 Redis 命令中的 hash 操作。

哈希对象的 encoding 属性可以是 ziplist、hashtable：

- ziplist：哈希对象使用压缩列表作为底层实现。每当有新的键值对要加入，程序会先将保存了键的节点推入压缩列表表尾，再将保存了值的节点推入压缩列表表尾。

  执行代码 `HSET profile name "Tom"`、`HSET profile age 25`、`HSET profile career "Programmer"` 后，将创建如下对象：

  ![](./202301112313837.png)

  ![image-20230111231342321](./202301112317659.png)

- hashtable：哈希对象使用字典作为底层实现。哈希对象中的每个键值对都用一个字典键值对来保存。字典中的键和值都是字符串对象。

  ![image-20230111234642471](./202301112346521.png)

**编码转换**

当哈希对象同时满足以下两个条件时，使用 ziplist：

- 哈希对象保存的所有键和值的字符串长度都小于 64 字节。
- 哈希对象保存的键值对数量小于 512 个。

如果不能同时满足以上条件，则使用 hashtable 编码。

##### 集合对象

集合对象对应 Redis 命令中的 set 操作。

集合对象的 encoding 属性可以是 intset、hashtable：

- intset：集合对象使用整数集合作为底层实现。集合对象保存的所有元素都被保存在整数集合中。

  执行代码 `SADD numbers 1 3 5` 后，将创建如下对象：

  ![image-20230111235446411](./202301112354459.png)

- hashtable：集合对象使用字典作为底层实现。字典的每个键都是一个字符串对象，用于保存集合元素，而字典的值全部被设置为 NULL。

  执行代码 `SADD fruits "apple" "banana" "cherry"` 后，将创建如下对象：

  ![image-20230111235822709](./202301112358752.png)

**编码转换**

当集合对象同时满足以下两个条件式，使用 intset：

- 集合对象保存的所有元素都是整数值。
- 集合对象保存的元素数量不超过 512 个。

如果不能同时满足以上条件，则使用 hashtable 编码。

##### 有序集合对象

有序集合对象对应 Redis 命令中的 zset 操作。

有序集合对象的 encoding 属性可以是 ziplist、skiplist：

- ziplist：有序集合对象使用压缩列表作为底层实现。每个有序集合元素占用两个相邻的压缩列表节点，第一个节点用于保存有序集合元素的值，第二个节点用于保存有序集合元素的 score。

  压缩列表内的有序集合元素按照分值从小到大进行排序，分值较小的元素靠近表头，分值较大的元素靠近表尾。

  执行代码 `ZADD price 8.5 apple 5.0 banana 6.0 cherry` 后，将创建如下对象：

  ![image-20230112060641853](./202301120606916.png)

  ![image-20230112060656478](./202301120609250.png)

- skiplist：有序集合对象使用 zset 结构作为底层实现。一个 zset 结构同时包含一个字典和一个跳跃表。

  ```c
  typedef struct zset {
  	
  	zskiplist *zsl;
  	
  	dict *dict;
  } zset;
  ```

  zset 结构中的 zsl 跳跃表按分值从小到大保存了所有集合元素，每个跳跃表节点都保存了一个集合元素。跳跃表节点的 obj 属性保存了元素的值，跳跃表节点的 score 属性保存了元素的 score；zset 结构中的 dict 字典为有序集合创建了一个从值到 score 的映射。同时使用跳跃表和字典，是为了提高有序集合的性能（例如跳跃表可以提供一些范围操作，字典可以提供 O(1) 复杂度的 score 查找）。

  虽然 zset 结构会同时使用字典和跳跃表，但是这两种数据结构会通过指针来共享相同的集合元素值和 score，因此不会浪费内存。

  执行代码 `ZADD price 8.5 apple 5.0 banana 6.0 cherry` 后，将创建如下对象：

  ![image-20230112065940303](./202301120659350.png)

  ![image-20230112065959122](./202301120659181.png)

**编码转换**

当有序集合对象同时满足以下两个条件式，使用 ziplist：

- 有序集合对象保存的元素数量小于 128 个。
- 有序集合对象保存的所有元素的长度都小于 64 字节。

如果不能同时满足以上条件，则使用 hashtable 编码。

##### 类型检查与命令多态

Redis 中的命令基本上可以分为两种类型，一种可以用于操作任何类型的键（例如 DEL、EXPIRE 等），另一种只能针对特定类型的键执行（例如 GET 只能针对字符串键，HGET 只能针对哈希键）。

**类型检查**：对于有类型限制的命令，Redis 执行命令前会先检查键的类型即 redisObject 的 type 属性是否正确。正确就执行，不正确则抛出错误。

**命令多态**：对于某些 redisObject，它的底层实现有很多种，例如列表对象的底层实现有 ziplist 和 linkedlist，而命令的执行本质上是调用底层实现提供的 API。对于这种情况，程序在通过 redisObject 的 type 属性检查完类型后，还需要根据 encoding 属性找出具体实现。

##### 内存回收

因为 C 语言不具备自动内存回收的功能，所以 Redis 在自己的对象系统使用了引用计数的方式实现了内存回收。

每个对象的引用计数信息由 redisObject 的 refcount 属性记录。

对象的引用技术信息会随着对象的使用状态而不断变化：

- 创建的新对象的引用计数值为 1。
- 当一个对象被新程序使用，引用计数值 +1；
- 当一个对象不再被程序使用，引用计数值 -1；
- 当对象的引用计数值变为 0，对象所占用的内存会被释放。 

##### 内存共享

和 Java 的字符串常量池类似，Redis 中需要使用某个字符串对象时，不会优先去创建这个字符串对象，而是会去查找是否有相同的已创建的字符串对象，如果有，则会进行对象复用而不是创建新对象以节省内存。

### 数据库

#### 服务器中的数据库

Redis 服务器将所有数据库都保存在 `redis.h/redisServer` 结构的 `db` 数组中，`db` 数组的每个项都是一个 `redis.h/redisDb` 结构，每个 `redisDb` 结构代表一个数据库。

```c
struct redisServer {
	// ...
	
	// 保存服务器中所有数据库的数组
	redisDb *db;
    
    // 服务器的数据库数量
    int dbnum;
	
	// ...
};
```

服务器初始化时，会根据 `dbnum` 属性来决定创建多少个数据库。`dbnum` 属性的值由服务器配置的 `database` 选项决定，默认情况下，会创建 16 个数据库。

#### 切换数据库

每个 Redis 客户端都有自己的目标数据库，每当客户端执行数据库读写命令时，目标数据库就会称为这些命令的操作对象。默认情况下，客户端的目标数据库为 0 号数据库，但客户端可以通过 `SELECT` 命令来切换目标数据库。

在服务器内部，有一个 `redisClient` 结构用于描述客户端的状态，其中的 db 属性就记录了这个客户端当前的目标数据库。

``` c
typedef struct redisClient {

    // ...
    // 指向当前正在使用的数据库
    redisDb *db;
    
} redisClient;
```

#### 数据库键空间

Redis 中使用 `redis.h/redisDb` 结构来表示数据库，其中的 dict 字典属性保存了这个数据库中保存的所有键值对，这个字典被称为键空间。

```c
typedef struct redisDb {

	// ...
	
	// 数据库键空间，保存着数据库中的所有键值对
	dict *dict;

	// ...
} redisDb;
```

用户通过 Redis 客户端可见的数据库实际上就是键空间：

- 键空间的键是用户可见的数据库的键，每个键都是字符串对象。
- 键空间的值是用户可见的数据库的值，每个值可以是字符串对象、列表对象、哈希表对象、集合对象和有序集合对象等。

![](./202301140705201.png)

所有针对数据库的操作，例如添加一个键值对到数据库中或者从数据库中删除一个键值对，实际上都是通过对键空间字典进行操作来实现的。

#### 键的过期和删除

Redis 中可以给键设置生存时间或给键设置过期时间，服务器会定时自动删除过期的键。

##### 键的过期

四个设置过期时间或者生存时间的命令：

- `EXPIRE key ttl`：将 key 的生存时间设置为 ttl 秒。
- `PEXPIRE key ttl`：将 key 的生存时间设置为 ttl 毫秒。
- `EXPIREAT key timestamp`：将 key 的过期时间设置为 timestamp 所指定的秒数时间戳。
- `PEXPIREAT key timestamp`：将 key 的过期时间设置为 timestamp 所指定的毫秒数时间戳。

以上四个命令最终都会转换成 `PEXPIREAT` 命令来执行。

每个键的过期时间由 `redisDb` 结构中的 `expires` 字典属性保存，这个属性被称为过期字典。

```
typedef struct redisDb {

	// ...
	
	// 过期字典，保存着键的过期时间
	dict *expires;

	// ...
} redisDb;
```

- 过期字典的键是指针，指向键空间的某个键对象（即某个数据库键）。
- 过期字典的值是一个 long long 类型的整数，这个整数保存了键所指向的数据库键的过期时间（毫秒精度的 UNIX 时间戳）。

##### 键的删除

Redis 中使用的是惰性删除和定期删除两种策略：

- 惰性删除：每次从键空间获取键时，都会检查是否过期，如果过期则删除。
- 定期删除：每隔一段时间就对数据库进行一次检查，删除其中的过期键。

###### 惰性删除的实现

过期键的惰性删除策略由 `db.c/expireIfNeeded` 函数实现，所有读写数据库的 Redis 命令在执行前都会调用这个函数对键进行检查：

- 如果键已过期，则 `expireIfNeeded` 函数会将其删除。
- 如果键未过期，则不进行任何操作。

###### 定期删除的实现

过期间的定期删除策略由 `redis.c/activeExpireCycle` 函数实现。此外，Redis 中还有一个定时函数 `redis.c/serverCron`，每隔一段时间就会被调用一次，`serverCron` 会调用 `activeExpireCycle` 函数。`activeExpireCycle` 函数会在规定时间内分多次遍历服务器中的各个数据库，从数据库的 expires 字典中随机检查一部分键的过期时间，并且删除其中的过期键。

### 服务器线程模型与事件

Redis 服务器是一个事件驱动程序，服务器需要处理以下两类事件：

- 文件事件：客户端或者其他服务器与当前服务器通过 socket 进行连接，文件事件就是对 socket 操作的抽象。
- 时间事件：例如定时任务。

#### 文件事件

Redis 基于单 Reactor 模型构建了文件事件处理器。Redis 中的 IO 多路复用通过封装 select、epoll、evport、kqueue 等系统调用实现。

![image-20230117065048290](./202301170650368.png)

- IO 多路复用程序负责监听多个 socket，并且通过队列向文件事件分派器传送产生了事件的 socket（类似 Java NIO 中的 Selector）。

  ![image-20230117065037752](./202301170650825.png)

- 文件事件分派器负责根据 socket 所产生的事件的类型，调用对应的事件处理器。

虽然文件事件处理器以单线程方式运行，但是通过 IO 多路复用来监听多个 socket，文件事件处理器既实现了高性能的网络通信模型，又可以很好地与 Redis 服务器中其他单线程运行的模块进行对接，保持了 Redis 内部单线程设计的简单性。

#### 时间事件

Redis 的时间事件分为两种：

- 定时事件：让程序在指定的时间后执行一次。
- 周期性事件：让程序每隔指定时间就执行一次。

一个时间事件由三个属性组成：

- id：时间事件的全局唯一 ID，ID 从小到大顺序递增，新事件的 ID 比旧事件的 ID 大。
- when：毫秒精度的 UNIX 时间戳，记录了时间事件的到达时间。
- timeProc：时间事件处理函数。当时间事件到达时，服务器就会调用这个函数处理时间事件。

一个时间事件是定时事件还是周期性事件取决于时间事件处理函数的返回值：

- 如果事件处理函数返回值为 `ae.h/AE_NOMORE`，那么这个事件就是定时事件，该事件到达一次之后就会被删除，不会再次到达。
- 如果事件处理函数返回值为非 `ae.h/AE_NOMORE` 的整数值，那么这个事件为周期性时间。该事件到达后，服务器会根据事件处理函数的返回值对时间事件的 when 属性进行更新。

所有的时间事件都存放在一个无序链表中（无序指不按 when 排序），新的事件插入到表头。每当时间事件执行器运行时，就会遍历整个链表，查找所有已到达的时间事件，并调用相应的事件处理函数。

![image-20230117074123448](./202301170741518.png)

>时间事件应用实例：serverCron 函数
>
>持续运行的Redis服务器需要定期对自身的资源和状态进行检查和调整，从而确保服务器可以长期、稳定地运行，这些定期操作由 `redis.c/serverCron` 函数负责执行，它的主要工作包括：
>
>- 更新服务器的各类统计信息，比如时间、内存占用、数据库占用 情况等。
>- 清理数据库中的过期键值对。
>- 关闭和清理连接失效的客户端。
>- 尝试进行AOF或RDB持久化操作。
>- 如果服务器是主服务器，那么对从服务器进行定期同步。
>- 如果处于集群模式，对集群进行定期同步和连接测试。
>
>Redis服务器以周期性事件的方式来运行 serverCron 函数，在服务器运行期间，每隔一段时间，serverCron 就会执行一次，直到服务器关闭为止。 
>
>在Redis2.6版本，服务器默认规定 serverCron 每秒运行10次，平均每间隔100毫秒运行一次。 
>
>从Redis2.8开始，用户可以通过修改hz选项来调整 serverCron 的每秒执行次数

#### 事件的调度与执行

因为服务器中同时存在文件事件和时间事件两种事件类型，所以服务器必须对这两种事件进行调度，决定何时应该处理文件事件，何时又应该处理时间事件，以及花多少时间来处理它们等等。

事件的调度和执行由 `ae.c/aeProcessEvents` 函数负责，以下是该函数的伪代码表示：

```c
def aeProcessEvents():

	#获取到达时间离当前时间最接近的时间事件
	time_event = aeSearchNearestTimer()

	#计算最接近的时间事件距离到达还有多少毫秒
	remaind_ms = time_event.when - unix_ts_now()

	#如果事件已到达，那么remaind_ms的值可能为负数，将它设定为0
	if remaind_ms < 0:
	    remaind_ms = 0

	#根据remaind_ms的值，创建timeval结构
	timeval = create_timeval_with_ms(remaind_ms)

	#阻塞并等待文件事件产生，最大阻塞时间由传入的timeval结构决定
	#如果remaind_ms的值为0，那么aeApiPoll调用之后马上返回，不阻塞
	aeApiPoll(timeval)

	#处理所有已产生的文件事件
	processFileEvents()

	#处理所有已到达的时间事件
	processTimeEvents()
```

将 aeProcessEvents 函数置于一个循环里面，加上初始化和清理函数，这就构成了Redis服务器的主函数，以下是该函数的伪代码表示：

```c
def main():

	#初始化服务器
	init_server()

	#一直处理事件，直到服务器关闭为止
	while server_is_not_shutdown():
	       aeProcessEvents()

	#服务器关闭，执行清理操作
	clean_server()
```

![image-20230117075104979](./202301170751032.png)

### 客户端

Redis 服务器是典型的一对多服务器程序：一个服务器可以与多个客户端建立网络连接，每个客户端可以向服务器发送命令请求，而服务 器则接收并处理客户端发送的命令请求，并向客户端返回命令回复。

Redis 的服务器状态结构中的 clients 属性保存了所有与服务器连接的客户端：

```c
struct redisServer {

	// ...
	
	// 一个链表，保存了所有客户端状态
	list *clients;
	
	// ...
};
```

![image-20230118024444449](./202301180244513.png)

对于每个与服务器进行连接的客户端，服务器都为这些客户端建立了相应的 `redis.h/redisClient` 结构（客户端状态），这个结构保存了客户端当前的状态信息，以及执行相关功能时需要用到的数据结构，其中包括：

```
typedef struct redisClient {

	// ...
	
	// 客户端正在使用的套接字描述符
	int fd;
	
	// 客户端的名字
	robj *name;
	
	// 标志
	int flags;
	
	// 输入缓冲区
	sds querybuf;
	
	// 命令和命令参数
	robj **argv;
	
	// 命令参数个数
	int argc;
	
	// ...
	
} redisClient;
```

- fd：记录客户端正在使用的套接字描述符。伪客户端的 fd 属性为 -1；普通客户端的 fd 属性值为大于 -1 的整数。
- name：默认情况下，客户端没有蜜罐子，可以通过 `CLIENT SETNAME nickname` 命令设置名字。
- flags：记录了客户端的角色以及客户端目前所处的状态。flags 属性的值可以是单个标志，也可以是多个标志的二进制或。
- querybuf：保存客户端发送的命令请求。
- argv：服务器将客户端发送的命令请求保存到 querybuf 后，对命令进行分析。将命令参数存放入 argv 数组。argv[0] 存放的是命令，其余的是命令参数。
- argc：记录 argv 的长度。

## Redis进阶使用

### 持久化

Redis 是一个基于内存的数据库，它将自己的数据库状态（非空数据库和其保存的键值对）存储在内存中，如果不想办法将存储在内存中的数据保存到磁盘中，那么一旦服务器进程退出，服务器中的数据也就消失了。

为了解决这个问题，Redis 提供了持久化的功能，这个功能可以将 Redis 内存中的数据保存到磁盘中，避免数据意外丢失。

Redis 中有两种持久化方式：

- RDB：保存数据库中的键值对。
- AOF：保存服务器所执行的写命令。

#### RDB

RDB 持久化既可以手动执行，也可以根据服务器配置选项定期执行，该功能可以将某个时间点上的数据库状态保存到一个 RDB 文件中，文件名为 `dump.rdb`。

RDB 持久化功能所生成的 RDB 文件是一个经过压缩的二进制文件，通过该文件可以还原生成 RDB 文件时的数据库状态。只要 RDB 文件存在，服务器就可以用它来还原数据库状态。

##### RDB的创建与载入

有两个 Redis 命令可以用于生成 RDB 文件：

- SAVE：阻塞 Redis 服务进程，直到 RDB 创建完成。
- BGSAVE：创建子进程执行 RDB 的创建。

RDB 文件的载入是在服务器启动时自动执行的，Redis 并没有专门用于载入 RDB 文件的命令。当 Redis 服务器启动时检测到有 RDB 文件存在，就会自动载入 RDB 文件。服务器在载入 RDB 文件期间，会一直处于阻塞状态。

> 通常 AOF 文件的更新频率比 RDB 文件的更新频率高，因此如果服务器开启了 AOF 持久化，则服务器会优先使用 AOF 文件来还原数据。

创建 RDB 文件的实际工作由 `rdb.c/rdbSave` 函数完成，载入 RDB 文件的实际工作由 `rdb.c/rdbLoad` 完成。

##### RDB自动保存

用户可以通过在 Redis 的配置文件中配置 save 选项，让服务器在满足条件时自动执行一次 BGSAVE 命令。

Redis 默认的 save 选项是：

```
save 900 1
save 300 10
save 60 10000
```

意思是只要满足以下三个条件的任意一个，就会执行 BGSAVE 命令：

- 在 900 秒内，对数据库进行了至少 1 次修改。
- 在 300 秒内，对数据库进行了至少 10 次修改。
- 在 60 秒内，对数据库进行了至少 10000 次修改。

##### RDB文件

RDB文件生成和载入的位置可以在 Redis 配置文件中通过 dir 选项配置，默认值是 `./` 即 Redis 安装位置。

**RDB 文件的结构**

![image-20230116041414565](./202301160414639.png)

- REDIS：长度为 5 字节。保存着 `REDIS` 这五个字符，用于让 Redis 判断这个文件是否是 RDB 文件。
- db_version：长度为 4 字节，表示 RDB 文件的版本号。
- databases：保存着非空数据库中的键值对。
- EOF：长度为 1 字节。标志着 RDB 文件正文内容结束。
- check_sum：长度为 8 字节。用于校验 RDB 文件。  

#### AOF

被写入 AOF 的所有命令是以 Redis 的命令请求协议格式保存的，因为 Redis 的命令请求协议是纯文本格式，因此可以直接打开一个 AOF 文件，观察其中的内容。

##### AOF文件写入过程

AOF 文件写入过程可以分为：

- 命令追加：Redis 在执行完一个写命令，会先将命令追加到服务器状态的 aof_buf 缓冲区末尾：

  ```c
  struct redisServer {
  	
  	//...
  	
  	// AOF 缓冲区
  	sds aof_buf;
  	
  	//...
  };
  ```

- 文件写入：调用 write 系统调用，将数据写入文件，对于操作系统来说，实际上是将数据写入操作系统的缓冲区。

- 文件同步：将操作系统缓冲区中的数据同步到磁盘中，可以通过调用 fsync 系统调用强制执行。

AOF配置：

```
# 默认配置
appendonly no   # 是否开启AOF
appendfilename "appendonly.aof"  # AOF文件名
appendfsync everysec  # AOF 同步策略
```

appendfsync 策略：

- always：每当触发命令追加，都会同时触发文件写入和文件同步；
- everysec：每当触发命令追加，都会触发文件写入，并且每隔一秒执行一次文件同步；
- no：每当触发命令追加，都会触发文件写入，但是文件同步的具体时间由操作系统决定。

##### AOF文件载入过程

AOF 文件中保存了所有写命令，因此服务器只要读入并重新执行一遍 AOF 文件里保存的写命令，就可以还原服务器关闭之前的数据库状态。

Redis 读取 AOF 文件并且载入数据的过程：

![image-20230116063347363](./202301160633454.png)

##### AOF重写

在 Redis 长期运行的过程中，AOF 文件会变得越来越长，导致载入的速度变得很慢。由于 AOF 只是原封不动地追加写命令，因此会有很多冗余的命令占据 AOF 文件。

为了减小 AOF 文件的大小，Redis 提供了 AOF 重写机制。重写实际上是 Redis 通过当前数据库状态，生成最简短的写命令然后重新生成 AOF 文件的过程。

可以通过手动执行 `BGREWRITEAOF` 命令开始重写 AOF 文件，也可以通过配置文件自动触发：

```
# 默认配置
auto-aof-rewrite-percentage 100 # 触发重写所需要的 aof 文件体积百分比，即当AOF文件的增量比上一次 AOF 重写大多少时，才进行重写
auto-aof-rewrite-min-size 64mb # 表示触发AOF重写的最小文件体积,大于或等于64MB自动触发。
```

#### 对比

| RDB                          | AOF                                                          |
| ---------------------------- | ------------------------------------------------------------ |
| 全量备份，一次保存整个数据库 | 增量备份，只保存从开启 AOF 后的写命令<br>（当重写后，AOF中的数据也是全量的） |
| 每次执行持久化操作间隔较久   | 保存的间隔短，默认文件同步时间为 1 秒                        |
| 数据格式为二进制，还原快     | 数据格式为文本，还原慢                                       |

Redis 中关于 RDB 和 AOF 载入，都是在 Redis 服务器启动时自动执行的，并且这个载入的过程实际上是**覆盖原本的数据**，因此在使用时需要特别注意。

尤其是当原本没有开启 AOF 功能时，如果要开启 AOF 并且要保证数据不丢失，可以通过以下两种方法：

- 通过 Redis 的配置文件开启 AOF，并且执行一遍 `BGREWRITEAOF` 手动重写 AOF，以保证 AOF 文件中的数据是全量的（否则 AOF 文件中还没有数据，此时如果直接重启服务器，服务器从 AOF 文件还原数据，就将数据全部清空了，并且 RDB 也会直接清空）。
- 通过 `redis-cli config set appendonly yes` 命令开启 AOF，这个命令会自动执行一遍 `BGREWRITEAOF`。

### 发布订阅

Redis 中有两种发布订阅模式：

- 基于频道（channel）的发布订阅。
- 基于模式（pattern）的发布订阅。

#### 基于频道

通过执行 `SUBSCRIBE` 命令，客户端可以订阅一个或多个频道。每当有其他客户端通过 `PUBLISH` 向频道发送消息时，频道的所有订阅者都会收到这条消息。

例如客户端 A、B、C 都通过 `SUBCRIBE news.it` 订阅了 news.it 频道。此时有其他客户端通过 `PUBLISH news.it hello` 向 news.it 频道发送了 hello 消息，则客户端 A、B、C 都会收到 hello 消息。

![image-20230118205540586](./202301182055642.png)

当客户端执行完 `SUBSCRIBE` 命令后，会进入订阅状态，处于此状态下的客户端不能使用除 `SUBSCRIBE`、`UNSUBSCRIBE`、`PSUBSCRIBE` 和 `PUNSUBSCRIBE` 这四个属于"发布/订阅"之外的命令。

进入订阅状态后客户端可能收到三种类型的回复，每种类型的回复都包含三个值，第一个值是消息的类型，根据消息类型的不同，第二个和第三个参数的含义也不同。

消息类型的取值可能是以下三个：

- subscribe：表示订阅成功的反馈信息。第二个值是订阅成功的频道名称，第三个是当前客户端订阅的频道数量。
- message：表示接收到的消息，第二个值表示产生消息的频道名称，第三个值是消息的内容。
- unsubscribe：表示成功取消订阅某个频道。第二个值是对应的频道名称，第三个值是当前客户端订阅的频道数量，当此值为0时客户端会退出订阅状态，之后就可以执行其他非"发布/订阅"模式的命令了。

#### 基于模式

通过执行 `PSUBSCRIBE` 命令，客户端可以订阅一个或多个模式。每当有其他客户端通过 `PUBLISH` 向频道发送消息时，除了该频道的订阅者外，所有符合条件的模式也会收到消息（实际上就是通配符）。

![image-20230118234331833](./202301182343893.png)

### 事务

Redis 中一个事务从开始到解树通常会经过以下三个阶段：事务开始、命令入队，事务执行。

#### 事务开始

MULTI 命令的执行标志着事务的开始：

```shell
redis> MULTI
OK
```

MULTI 命令可以将执行该命令的客户端从非事务状态切换到事务状态。这一切换是通过在客户端状态中的 flags 属性中打开 REDIS_MULTI 标识来完成的。

#### 命令入队

当一个客户端处于正常状态时（非事务），客户端发送的命令会立即被服务器执行。

当一个客户端切换到事务状态后，服务器会根据这个客户端发来的不同命令执行不同操作：

- 如果客户端发送的命令为 `EXEC`、`DISCARD`、`WATCH`、`MULTI` 四个命令中的一个，那么服务器会立即执行这个命令。
- 否则，服务器将命令放入事务队列中，然后向客户端返回 QUEUED 回复。

#### 执行事务

当一个处于事务状态的客户端向服务器发送 `EXEC` 命令时，这个 `EXEC` 命令将立即被服务器执行。服务器会遍历这个客户端的事务队列，执行队列中保存的所有命令，最后将执行命令所得的结果全部返回给客户端。

#### WATCH命令

`WATCH` 命令是一个乐观锁，它可以在执行 `EXEC` 命令之前监视任意数量的数据库键。

当执行 `EXEC` 命令时，如果程序发现 `WATCH` 监视的键值对有改动，则 `EXEC` 命令会执行失败。

### 慢查询日志和监视器

#### 慢查询日志

Redis 的慢查询日志功能用于记录执行时间超过给定时长的命令请求，用户可以通过这个功能产生的日志来监视和优化查询速度。

服务器配置有两个和慢查询日志相关的选项： 

- slowlog-log-slower-than：指定执行时间超过多少微秒的命令请求会被记录到日志上。
- slowlog-max-len：指定服务器最多保存多少条慢查询日志。

可以通过 `SLOWLOG GET` 命令获取慢查询日志，也可以加一个参数表示要获取多少条慢查询日志。 

```
> slowlog get 3
1) 1) (integer) 6107
   2) (integer) 1616398930
   3) (integer) 3109
   4) 1) "config"
      2) "rewrite"
2) 1) (integer) 6106
   2) (integer) 1613701788
   3) (integer) 36004
   4) 1) "flushall"
3) 1) (integer) 6105
   2) (integer) 1608722338
   3) (integer) 20449
   4) 1) "scan"
      2) "0"
      3) "MATCH"
      4) "*comment*"
      5) "COUNT"
      6) "10000"
```

每一条慢查询日志都有4个属性组成：

1. 唯一标识ID
2. 命令执行的时间戳
3. 命令执行时长
4. 执行的命名和参数

可以通过 `SLOWLOG LEN` 命令获取慢查询日志的长度，通过 `SLOWLOG RESET` 命令重置慢查询日志。

#### 监视器

通过执行 `MONITOR` 命令，可以让当前的客户端变为监视器，实时地接收并打印出服务器当前处理地命令请求：

```
redis> MONITOR
OK
1378822099.421623 [0 127.0.0.1:56604] "PING"
1378822105.089572 [0 127.0.0.1:56604] "SET" "msg" "hello world"
1378822109.036925 [0 127.0.0.1:56604] "SET" "number" "123"
1378822140.649496 [0 127.0.0.1:56604] "SADD" "fruits" "Apple" "Banana" "Cherry"
1378822154.117160 [0 127.0.0.1:56604] "EXPIRE" "msg" "10086"
1378822257.329412 [0 127.0.0.1:56604] "KEYS" "*"
1378822258.690131 [0 127.0.0.1:56604] "DBSIZE"
```

### 主从复制

虽然 Redis 服务器的性能很高，但是当面对海量数据时，所有的读写压力全部落在一台服务器上，很有可能造成服务器运行效率低下、遇到故障无法快速处理等问题。

因此 Redis 推出了主从复制功能，它可以通过 `REPLICAOF` 命令（Redis 5.0 之前是 `SLAVEOF`）将一台 Redis 服务器的数据，持续地复制到其他的 Redis 服务器。前者称为主节点(master)，后者称为从节点(slave)。一般来说，可以让主节点负责处理写请求，从节点负责处理读取请求，即**读写分离**。

数据的复制是单向的，只能由主节点到从节点。建立连接后，可以通过 `INFO REPLICATION` 命令查看当前服务器的主从复制信息。

主从复制的作用主要包括：

- 数据冗余：主从复制实现了数据的热备份，是持久化之外的一种数据冗余方式。
- 故障恢复：当主节点出现问题时，可以由从节点提供服务，实现快速的故障恢复；实际上是一种服务的冗余。
- 负载均衡：在主从复制的基础上，配合读写分离，可以由主节点提供写服务，由从节点提供读服务（即写 Redis 数据时应用连接主节点，读 Redis 数据时应用连接从节点），分担服务器负载；尤其是在写少读多的场景下，通过多个从节点分担读负载，可以大大提高 Redis 服务器的并发量。
- 高可用基石：除了上述作用以外，主从复制还是哨兵和集群能够实施的基础，因此说主从复制是Redis高可用的基础。

#### 复制功能的实现

Redis 的复制功能分为**同步**和**命令传播**两个操作。

##### 同步

当客户端向服务器发送 `REPLICAOF` 命令，要求从服务器复制主服务器时，从服务器首先要执行同步操作，即将从服务器的数据库状态更新至主服务器当前所处的数据库状态。

从服务器对主服务的同步操作需要通过向主服务器发送 `PSYNC` 命令来完成。`PSYNC` 命令具有完整重同步和部分重同步两种模式：

###### 完整重同步

用于处理初次复制的情况。大致过程如下：

1. 收到 `PSYNC` 命令的主服务器执行 `BGSAVE` 命令，在后台生成一个 RDB 文件，并且使用一个缓冲区记录从现在开始执行的所有写命令。
2. 当主服务器的 `BGSAVE` 命令执行完后，主服务器会将 `BGSAVE` 命令生成的 RDB 文件发送给从服务器，从服务器接收载入这个 RDB 文件。此时从服务器的数据库状态和主服务器执行 BGSAVE 命令时的一致。
3. 主服务器将记录在缓冲区中的所有写命令发送给从服务器，从服务器执行这些命令。此时从服务器的数据库状态更新至主服务器当前所处的状态。

###### 部分重同步

用于处理短线重连后的复制情况。

部分重同步功能由以下三个部分组成：

- 主服务器和从服务器的复制偏移量

  主服务器和从服务器会分别维护一个复制偏移量。主服务器每次向从服务器传播N个字节的数据时，就将自己的复制偏移量的值加上N；从服务器每次收到主服务器传播过来的N个字节的数据时，就将自己的复制偏移量的值加上N。

  ![image-20230120045802098](C:\Users\summer\AppData\Roaming\Typora\typora-user-images\image-20230120045802098.png)

  通过对比主从服务器的复制偏移量，程序可以很容易地知道主从服务器是否处于一致状态。

- 主服务器的复制积压缓冲区。

  复制积压缓冲区是由主服务器维护的一个固定长度队列，默认大小为1MB。当主服务器进行命令传播时，它不仅会将写命令发送给所有从服务器，还会将写命令入队到复制积压缓冲区里面。

  ![image-20230120050016455](./202301200500516.png)

  因此，主服务器的复制积压缓冲区里面会保存着一部分最近传播的写命令，并且复制积压缓冲区会为队列中的每个字节记录相应的复制偏移量。

  ![image-20230120050121243](./202301200501301.png)

  当从服务器重新连上主服务器时，从服务器会通过 `PSYNC` 命令将自己的复制偏移量 offset 发送给主服务器，主服务器会根据这个复制偏移量来决定对从服务器执行何种同步操作：

  - 如果 offset 偏移量之后的数据（也即是偏移量 offset+1 开始的数据）仍然存在于复制积压缓冲区里面，那么主服务器将对从服务器执行部分重同步操作。**即将从服务器断线这段时间，主服务器执行的写命令都传输给从服务器执行，从服务器只需要接收这部分数据即可回到和主服务器一致的状态**。
  - 如果 offset 偏移量之后的数据已经不存在于复制积压缓冲区，那么主服务器将对从服务器执行完整重同步操作。

- 服务器的运行ID

  除了复制偏移量和复制积压缓冲区之外，实现部分重同步还需要用到服务器运行ID。每个Redis服务器，不论主服务器还是从服务，都会有自己的运行ID，运行ID在服务器启动时自动生成，由40个随机的十六进制字符组 成。

  当从服务器断线并重新连上一个主服务器时，从服务器将向当前连接的主服务器发送之前保存的运行ID。如果从服务器保存的运行ID和当前连接的主服务器的运行ID相同，那么说明从服务器断线之前复制的就是当前连接的这个主服务器，主服务器可以继续尝试执行部分重同步操作；否则，主服务器将对从服务器执行完整重同步操作。

##### 命令传播

在同步操作执行完毕之后，主从服务器两者的数据库将达到一致状态，但这种一致并不是一成不变的，每当主服务器执行客户端发送的写命令时，主服务器的数据库就有可能会被修改，并导致主从服务器状态不再一致。

为了让主从服务器再次回到一致状态，主服务器需要对从服务器执行命令传播操作：主服务器会将自己执行的写命令，也即是造成主从服务器不一致的那条写命令，发送给从服务器执行，当从服务器执行了相同的写命令之后，主从服务器将再次回到一致状态。

#### 配置过程

给从服务器设置主服务器的三种方式：

```shell
# 客户端发送命令
127.0.0.1:6379> replicaof 127.0.0.1 6378
OK

# 服务端启动参数
[root@fengye ~] redis-server --replicaof 127.0.0.1 6378

# 配置文件
[root@fengye ~] vim redis.conf
replicaof 127.0.0.1 6378
```

查看当前服务器的主从复制信息：

```
172.17.0.2:6379> info replication
# Replication
role:slave
master_host:172.17.0.1
master_port:6379
master_link_status:down
master_last_io_seconds_ago:-1
master_sync_in_progress:0
slave_read_repl_offset:504
slave_repl_offset:504
master_link_down_since_seconds:-1
slave_priority:100
slave_read_only:1
replica_announced:1
connected_slaves:0
master_failover_state:no-failover
master_replid:606b845f475010a5b558185924dc555616f912b6
master_replid2:0000000000000000000000000000000000000000
master_repl_offset:504
second_repl_offset:-1
repl_backlog_active:1
repl_backlog_size:1048576
repl_backlog_first_byte_offset:1
repl_backlog_histlen:504
```

### 哨兵

当主从复制中的主服务器出现故障，需要把某台从服务器切换为主服务器，代替主服务器工作的过程，叫故障转移（failover）。

在 Redis 主从复制模式中，故障转移的过程是手动的。在这个过程中，不仅需要人为干预，而且还会造成一段时间内服务器处于不可用状态，同时数据安全性也得不到保障。

而 Redis Sentinel 哨兵模式，它弥补了主从模式的不足：哨兵通过发送命令来监控主服务器和从服务器的运行状态。当主服务器宕机时，哨兵会在从服务器中选出一个作为主服务器，并且以发布订阅模式通知其他从服务器，让它们切换主机。

并且多个哨兵之间还可以互相进行监控，保证了哨兵的高可用。

#### 配置过程

配置3哨兵1主2从的 Redis 服务器

| 服务类型 | 是否是主服务器 | IP地址    | 端口  |
| -------- | -------------- | --------- | ----- |
| Redis    | 是             | 127.0.0.1 | 6379  |
| Redis    | 否             | 127.0.0.1 | 6378  |
| Redis    | 否             | 127.0.0.1 | 6377  |
| Sentinel | -              | 127.0.0.1 | 26379 |
| Sentinel | -              | 127.0.0.1 | 26378 |
| Sentinel | -              | 127.0.0.1 | 26377 |

![image-20230121075547425](./202301210755536.png)

##### 配置主从服务器

redis-1.conf：

```
port 6379
requirepass "123456"
```

reids-2.conf：

```
port 6378
replicaof 127.0.0.1 6379
requirepass "123456"

# 主服务器配置了需要密码，这里从服务器就需要配置密码验证
masterauth 123456
```

redis-3.conf：

```
port 6377
replicaof 127.0.0.1 6379
requirepass "123456"

# 主服务器配置了需要密码，这里从服务器就需要配置密码验证
masterauth 123456
```

##### 配置哨兵

sentinel-1.conf：

```
port 26379

# 为哨兵配置需要密码认证
requirepass 123456

# 配置连接其他哨兵时验证的密码
sentinel sentinel-pass 123456

# 修改为后台运行
daemonize yes

# 配置监听的主服务器，mymaster 代表服务器的名称，可以自定义。2代表只有两个或两个以上的哨兵认为主服务器不可用的时候，才会进行 failover 操作。
# 这里 ip 不能用 127.0.0.1
sentinel monitor mymaster 101.35.46.160 6379 2

# 配置主服务器密码
sentinel auth-pass mymaster 123456
```

sentinel-2.conf：

```
port 26378

# 为哨兵配置需要密码认证
requirepass 123456

# 配置连接其他哨兵时验证的密码
sentinel sentinel-pass 123456

# 修改为后台运行
daemonize yes

# 配置监听的主服务器，mymaster 代表服务器的名称，可以自定义。2代表只有两个或两个以上的哨兵认为主服务器不可用的时候，才会进行 failover 操作。
# 这里 ip 不能用 127.0.0.1
sentinel monitor mymaster 101.35.46.160 6379 2

# 配置主服务器密码
sentinel auth-pass mymaster 123456
```

sentinel-3.conf：

```
port 26377

# 为哨兵配置需要密码认证
requirepass 123456

# 配置连接其他哨兵时验证的密码
sentinel sentinel-pass 123456

# 修改为后台运行
daemonize yes

# 配置监听的主服务器，mymaster 代表服务器的名称，可以自定义。2代表只有两个或两个以上的哨兵认为主服务器不可用的时候，才会进行 failover 操作。
# 这里 ip 不能用 127.0.0.1
sentinel monitor mymaster 101.35.46.160 6379 2

# 配置主服务器密码
sentinel auth-pass mymaster 123456
```

##### 启动主从服务器和哨兵

```shell
$ cd /www/server/redis/src

$ ./redis-server ../redis-1.conf
$ ./redis-server ../redis-2.conf
$ ./redis-server ../redis-3.conf

$ ./redis-sentinel ../sentinel-1.conf
$ ./redis-sentinel ../sentinel-2.conf
$ ./redis-sentinel ../sentinel-3.conf
```

##### 整合 Spring Boot

yml配置

```yaml
spring:
  redis:
    sentinel:
      # 主服务器的名称
      master: mymaster
      # 哨兵节点
      nodes:
        - 101.35.46.160:26379
        - 101.35.46.160:26378
        - 101.35.46.160:26377
      # 哨兵的密码
      password: 123456
    database: 0
    # 数据库的密码
    password: xhn200232
```

配置读写分离

```java
@Configuration
public class RedisConfig {
    @Bean
    public LettuceClientConfigurationBuilderCustomizer builder() {
        return builder -> builder.readFrom(ReadFrom.REPLICA);
    }
}
```

#### 实现原理

哨兵本质上只是一个运行在特殊模式下的 Redis 服务器。

##### 启动准备

当一个哨兵启动时，它会根据哨兵配置文件中的配置，创建连向主服务器的网络连接，成为主服务器的客户端。

对于每个被哨兵监视的主服务器，哨兵会创建两个连向主服务器的异步网络连接：

- 一个是命令连接，用于向主服务器发送命令。
- 一个是订阅连接，用于订阅主服务器的 `__sentinel__:hello` 频道。

![image-20230122042210853](./202301220422910.png)

##### 获取主服务器信息

Redis 默认会以每十秒一次的频率，通过命令连接向被监视的主服务器发送 INFO 命令，然后对其分析从而获取主服务器的当前信息。

通过分析主服务器返回的 INFO 命令回复，哨兵可以获取以下信息：                                           

- 主服务器本身的信息，例如服务器运行 id，当前服务器的 role。
- 主服务器属下的所有从服务器的信息，包括从服务器的 ip、port。根据这些信息，哨兵无须用户提供从服务器的地址信息，就可以自动发现从服务器。

当哨兵发现主服务器又新的从服务器出现时，就会与新的从服务器创建命令连接和订阅连接。

当哨兵与从服务器建立命令连接后，会同样以每十秒一次的频率向从服务器发送 INFO 命令。

##### 向发送信息并接收信息

在默认情况下，哨兵会以每两秒一次的频率通过命令连接向所有被监视的主服务器和从服务器发送如下格式的命令：`PUBLISH __sentinel__:hello "<s_ip>,<s_port>,<s_runid>,<s_epoch>,<m_name>,<m_ip>,<m_port>,<m_epoch>"`。

这条命令向服务器的 `__sentinel__:hello` 频道发送了一条信息，信息的内容由多个参数组成：

- s_ip：当前哨兵的 IP 地址
- s_port：当前哨兵的端口号
- s_runid：当前哨兵的运行 ID
- s_epoch：当前哨兵的配置纪元
- m_name：主服务器的名字
- m_ip：主服务器的 IP 地址
- m_port：主服务器的端口号
- m_epoch：主服务器的配置纪元

当哨兵和一个服务器建立起订阅连接后，就会通过订阅连接，向服务器发送以下命令：`SUBSCRIBE __sentinel__:hello`，从而让订阅连接进入订阅模式。

对于每个与哨兵连接的服务器，哨兵既通过命令连接向服务器的 `__sentinel__:hello` 频道发送信息，又通过订阅连接从服务器的 `__sentinel__:hello` 频道接收信息。

![image-20230122061825878](./202301220618943.png)

对于监视同一个服务器的多个哨兵来说，其中一个哨兵发送的信息会被其他几个哨兵接收到，这些信息会被用于更新其他哨兵对于发送信息哨兵的认知，也会被用于更新其他哨兵对被监视服务器的认知。即实现哨兵之间的互相发现和对服务器状态信息的共享。

当哨兵通过频道信息发送一个新的哨兵时，会创建一个连向新哨兵的命令连接，而新哨兵也会同样创建连向这个哨兵的命令连接。最终监视同一个主服务器的多个哨兵之间将形成相互连接的网络。

![image-20230122062226079](./202301220622136.png)

##### 检测下线状态

在默认情况下，哨兵会以每秒一次的频率向所有与它创建了命令连接的实例（主、从服务器和其他哨兵）发送 PING 命令，并通过实例的回复判断对方是否在线。

当实例在一段时间内连续向哨兵返回无效回复，那么哨兵就会标记这个实例为**主观下线**。

当哨兵将一个主服务器判断为主观下线后，为了确认这个主服务器是否真的下线了，它会向同样监视这个主服务器的其他哨兵进行询问。当哨兵从其他哨兵处接收到足够多的主管下线判断时，就会将主服务器判定为**客观下线**。

##### 选举领头哨兵

当一个主服务器被判断为**客观下线**时，监视这个下线主服务器的各个哨兵会通过 Raft 算法，选举出一个领头哨兵，并由领头哨兵对下线主服务器执行故障转移操作。

>选举规则：
>
>- 所有在线的哨兵都有被选为领头哨兵的资格。
>- 每次进行领头哨兵选举之后，不论选举是否成功，所有哨兵的配置纪元的值都会自增一次。配置纪元实际上就是一个计数器。 
>- 在一个配置纪元里面，所有哨兵都有一次将某个哨兵设置为局部领头哨兵的机会，并且局部领头一旦设置，在这个配置纪元里面就不能再更改。 
>- 每个发现主服务器进入客观下线的哨兵都会要求其他哨兵将自己设置为局部领头哨兵。 
>- 哨兵设置局部领头哨兵的规则是先到先得：最先向目标哨兵发送设置要求的源哨兵将成为目标哨兵的局部领头哨兵，而之后接收到的所有设置要求都会被目标哨兵拒绝。  
>- 如果有某个哨兵被半数以上的哨兵设置成了局部领头哨兵，那么这个哨兵成为领头哨兵。
>- 因为领头哨兵的产生需要半数以上哨兵的支持，并且每个哨兵在每个配置纪元里面只能设置一次局部领头哨兵，所以在一个配置纪元里面，只会出现一个领头哨兵。 
>- 如果在给定时限内，没有一个哨兵被选举为领头哨兵，那么各个哨兵将在一段时间之后再次进行选举，直到选出领头哨兵为止。

##### 故障转移

当选举出领头哨兵后，领头哨兵将对已下线的主服务器进行故障转移操作，该操作分为以下三个步骤：

1. 在已下线主服务器属下的所有从服务器里面，挑选出一个状态良好、数据完整的从服务器，向其发送 `REPLICAOF no one` 命令，将其设置为主服务器。
2. 向已下线主服务器属下的所有从服务器发送 `REPLICAOF <ip> <port>` 命令，令其复制新的主服务器。
3. 将已下线主服务器设置为新的主服务器的从服务器，当这个旧的主服务器重新上线时，它就会成为新的主服务器的从服务器。

### 集群

虽然哨兵+主从复制的模式通过读写分离和自动故障转移在大多数情况下满足了高可用的要求，但是这种模式还是存在着一些问题：

- 主从复制虽然实现了读写分离，但是写入操作实际上全部落在了 master 节点上，如果面临同时有大量写请求的高并发场景，很容易造成 master 节点的压力上升。
- 无论是从节点还是主节点，本质上都只是用一台 Redis 服务器存储了所有的数据，数据量太大意味着持久化成本高等问题。

因此 Redis 3.0 正式加入了集群模式，实现了数据的分布式存储，通过对数据进行分片，将不同的数据存储在不同的 master 节点中，从而解决了海量数据的问题。并且集群中也实现了主从复制和自动故障处理。

Redis 集群采用去中心化的思想，没有中心节点的说法，对于客户端来说，整个集群可以看成一个整体，可以连接任意一个节点进行操作，就像操作单一 Redis 实例一样，不需要任何代理中间件。

#### 实现原理

##### 节点

一个 Redis 集群由多个节点（node）组成，一个节点就是一个运行在集群模式下的 Redis 服务器。当 Redis 服务器启动时，如果 `cluster-enabled` 配置的选项为 yes，则会开启服务器的集群模式。另外，节点只能使用 0 号数据库，而单机服务器则没有这一限制。

在刚开始的时候，每个节点都是相互独立的，它们都处于一个只包含自己的集群当中，要组建一个真正可工作的集群，我们必须将各个独立的节点连接起来，构成一个包含多个节点的集群。

连接各个节点的工作可以用 `CLUSTER MEET <ip> <port>` 命令来完成。向一个节点 node 发送 `CLUSTER MEET` 命令，可以让 node 节点与所指定的节点进行握手。当握手成功后，node 节点就会将所指定的节点添加到 node 节点当前所在的集群中。

可以使用 `CLUSTER NODE` 命令查看当前节点所在集群的信息。

##### 槽

Redis 集群通过分片的方式保存数据库中的键值对：集群的整个数据库被分为 16384 个槽（slot），数据库中的每个键都被分配到 16384 个槽中的一个，集群中的每个节点可以处理 0 到 16384 个槽。

当数据库中的 16384 个槽都有节点在处理时，集群处于上线状态（ok）；否则，处于下线状态（fail）。

通过向节点发送 `CLUSTER ADDSLOTS <slot> [slot ...]` 命令，可以将一个或多个槽指派给节点负责。

##### 执行命令

当数据库的 16384 个槽都进行指派后，集群就会进入上线状态，这时客户端就可以向集群中的节点发送数据命令了。

当客户端向节点发送与数据库键有关的命令时，接收命令的节点会计算出命令要处理的数据库键属于哪个槽，并检查这个槽是否指派给了自己：

- 如果键所在的槽正好就指派给了当前节点，那么节点直接执行这个命令。
- 如果键所在的槽并没有指派给当前节点，那么当前节点将客户端重定向到至正确的节点，并再次发送之前想要执行的命令。

![image-20230123094910880](./202301230949998.png)

>计算 key 属于哪个槽的方式：CRC16(key) & 16383

##### 重新分片

Redis 集群的重新分片操作可以将任意数量已经指派给某个节点的槽改为指派给另外一个节点，并且相关槽所属的键值对也会被移动到目标节点。

重新分片的操作是在线进行的，在重新分配的过程中，集群不需要下线，并且源节点和目标节点可以继续处理命令请求。

Redis集群的重新分片操作是由 Redis 的集群管理软件 redis-trib 负责执行的，Redis 提供了进行重新分片所需的所有命令，而 redis-trib 则通过向源节点和目标节点发送命令来进行重新分片操作。

redis-trib 对集群的单个槽 slot 进行重新分片的步骤如下：

1. redis-trib 对目标节点发送 `CLUSTER SETSLOT <slot> IMPORTING <source_id>` 命令，让目标节点准备好从源节点导入（import）属于槽 slot 的键值对。
2. redis-trib 对源节点发送 `CLUSTER SETSLOT <slot> MIGRATING <target_id>` 命令，让源节点准备好将属于槽slot的键值对迁移（migrate）至目标节点。
3. redis-trib 向源节点发送 `CLUSTER GETKEYSINSLOT <slot> <count>` 命令，获得最多count个属于槽slot的键值对的键名（key name）。
4. 对于步骤3获得的每个键名，redis-trib 都向源节点发送一个 `MIGRATE <target_ip> <target_port> <key_name> 0 <timeout>` 命令，将被选中的键原子地从源节点迁移至目标节点。
5. 重复执行步骤3和步骤4，直到源节点保存的所有属于槽 slot 的键 值对都被迁移至目标节点为止。
6. redis-trib 向集群中的任意一个节点发送 `CLUSTER SETSLOT <slot> NODE <target_id>` 命令，将槽 slot 指派给目标节点，这一指派信息会通过消息发送至整个集群，最终集群中的所有节点都会知道槽 slot 已经指派给了目标节点。

![image-20230124021027665](./202301240210749.png)

在重新分片期间，源节点向目标节点迁移槽的过程中，会出现这样一种情况：被迁移槽的一部分键值对保存在源节点中，另一部分键值对则保存在目标节点中。

而此时，如果客户端接收到了一个命令，并且命令所处理的键刚好属于被迁移槽时：

- 源节点会现在自己的数据库中查找指定的键，如果找到则正常执行命令。
- 如果源节点没能在数据库中找到指定的键，那么就返回一个 ASK 错误，并且将客户端重定向到目标节点，再次发送之前的命令。

##### 复制与故障转移

Redis 集群中的节点分为主节点和从节点，主节点用于处理槽，从节点用于复制某个主节点，并且在主节点下线后，接管原来节点负责处理的槽，代替主节点继续执行命令。而原来的主节点重新上线后，会称为新主节点的从节点。可以向一个节点发送 `CLUSTER REPLICATE <node_id>`，让这个节点称为指定节点的从节点。

###### 故障检测

集群中的每个节点都会定期地向集群中地其他节点发送 PING 消息，以此来检测对方是否在线。如果接收 PING 消息地节点没有在规定时间内返回 PONG 消息，那么发送 PING 消息地节点就会将接收 PING 消息的节点标记为疑似下线（PFAIL）。

集群中各个节点会通过互相发送消息的方式来交换集群中各个节点的状态信息。在一个集群中，如果半数以上负责负责处理槽的主节点都将某个主节点报告为疑似下线，那么这个主节点 x 将被标记为已下线。将 x 标记为下线的节点会向集群广播一条关于 x 的下线信息，所有收到这条信息的节点都会立即将 x 标记为下线。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              

###### 故障转移

故障转移过程：

- 下线的主节点的所有从节点中，会有一个从节点通过 Raft 算法被选中。
- 被选中的从节点会执行 `REPLICAOF no one` 命令，成为新的主节点。
- 新的主节点将原主节点的所有槽都重新指派给自己
- 新主节点向集群中的所有节点广播一条 PONG 消息，通知其他节点，这个节点已经成为了新的主节点。
- 新主节点开始接收和自己负责处理的槽有关的命令请求，故障转移完成。

#####  消息

集群中各个节点通过发送和接收消息来进行通信。称发送消息的节点为发送者，接收消息的节点为接收者。

节点发送的消息主要有以下五种：

- MEET 消息：当发送者接到客户端发送的 `CLUSTER MEET` 命令时，发送者会向接收者发送 MEET 消息，请求接收者加入到发送者当前所处的集群里面。 
- PING 消息：集群里的每个节点默认每隔一秒钟就会从已知节点中随机选出五个节点，然后对这五个节点中最长时间没有发送过 PING 消息的节点发送 PING 消息，以此来检测被选中的节点是否在线。除此之外，如果节点 A 最后一次收到节点 B 发送的 PONG 消息的时间距离当前时间已经超过了节点 A 的 `cluster-node-timeout` 选项设置时长的一半，那么节点 A 也会向节点 B 发送 PING 消息，这可以防止节点 A 因为长时间没有随机选中节点 B 作为 PING 消息的发送对象而导致对节点 B 的信息更新滞后。 
- PONG 消息：当接收者收到发送者发来的 MEET 消息或者 PING 消息时，为了向发送者确认这条 MEET 消息或者 PING 消息已到达，接收者会向发送者返回一条 PONG 消息。另外，一个节点也可以通过向集群广播自己的 PONG 消息来让集群中的其他节点立即刷新关于这个节点的认识，例如当一次故障转移操作成功执行之后，新的主节点会向集群广播一条 PONG 消息，以此来让集群中的其他节点立即知道这个节点已经变成了主节点，并且接管了已下线节点负责的槽。 
- FAIL 消息：当一个主节点 A 判断另一个主节点 B 已经进入 FAIL 状态时，节点 A 会向集群广播一条关于节点 B 的 FAIL 消息，所有收到这条消息的节点都会立即将节点 B 标记为已下线。 
- PUBLISH 消息：当节点接收到一个 PUBLISH 命令时，节点会执行 这个命令，并向集群广播一条 PUBLISH 消息，所有接收到这条 PUBLISH 消息的节点都会执行相同的 PUBLISH 命令。

#### 配置过程

搭建集群有两种方法：手动搭建和自动搭建。主要介绍自动搭建。

在 Redis 5.0 之前，自动搭建集群通过 src 目录下的 `redis-trib.rb` 实现。Redis 5.0 之后，自动搭建集群可以直接通过 `redis-cli` 实现。

参考：[spring - 深入理解Redis系列之集群环境搭建 - 后端系列进阶 - SegmentFault 思否](https://segmentfault.com/a/1190000017151802)

