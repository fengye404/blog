---
title: ElasticSearch笔记
typora-root-url: ./ElasticSearch笔记
date: 2022-04-25 15:44:53
tags:
---

# ElasticSearch

## 安装

### 安装 ES

下载压缩包

```shell
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-7.14.0-linux-x86_64.tar.gz
```

解压

```shell
tar -zxvf elasticsearch-7.14.0-linux-x86_64.tar.gz
```

修改配置文件，开启远程访问

```shell
vim elasticsearch-7.14.0/config

修改
network.host: 0.0.0.0
```

由于 `ElasticSearch` 不能在 `root` 用户下启动，所以需要创建一个新用户：

```shell
useradd temp

passwd temp

su temp
```

启动 `ElasticSearch` 

```
cd elasticsearch-7.14.0/bin

./elasticsearch
```

>port:  http 9200   tcp 9300

可能遇到的问题：

1. 如果启动后 ES 被 `killed` ，可能是服务器内存不够，可以修改分配给 ES 的 JVM 内存

   ```shell
   vim elasticsearch-7.14.0/config/jvm.options
   
   #修改
   -Xms1g
   -Xmx1g
   ```

2. 报错：在 `root` 用户安装了 `JDK` 的情况下，普通用户运行报错 `could not find java in bundled JDK at /home/ElasticSearch`

   这是因为 root 用户安装的 JDK 是局部环境变量，不是全局的。需要在 `/etc/profile` 中配置全局环境变量

   ```shell
   vi  /etc/profile
   
   添加如下内容
   export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-11.0.14.1.1-1.el7_9.x86_64 #安装的jdk的位置
   export CLASSPATH=.:$JAVA_HOME/jre/lib/rt.jar:$JAVA_HOME/lib/dt.jar:$JAVA_HOME/lib/tools.jar
   export PATH=$JAVA_HOME/bin:$PATH
   
   :wq
   
   source /etc/profile
   ```

3. 报错：AccessDeniedException

   ```shell
   chmod -R 777 /home/ElasticSearch/elasticsearch-7.14.0  
   # 修改 ES 目录权限
   ```

4. 报错：[关于elasticsearch boostrap checks failed错误类型整理及解决方法 - linzepeng - 博客园 (cnblogs.com)](https://www.cnblogs.com/linzepeng/p/12084734.html)

5. 报错：[(34条消息) ES启动异常：the default discovery settings are unsuitable for production use； at least..._lizz666的博客-CSDN博客](https://blog.csdn.net/lizz861109/article/details/112532473)

 ~~*这tm绝对是我部署过踩坑最多的中间件，太草了*~~

### docker 安装 ES

```shell
docker pull elasticsearch:7.14.0

docker run -d -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e "ES_JAVA_OPTS=-Xms1g -Xmx1g" elasticsearch:7.14.0
```

 ~~*不得不说这种中间件还是docker方便*~~

### 安装 Kibana

```shell
wget https://artifacts.elastic.co/downloads/kibana/kibana-7.14.0-linux-x86_64.tar.gz

tar -xvzf kibana-7.14.0-linux-x86_64/config/kibana.yml

vim kibana-7.14.0-linux-x86_64/config/kibana.yml
# 修改 server.host: "0.0.0.0"
# 修改 elasticsearch.hosts: ["http://localhost:9200"] （默认不用改）

cd kibana-7.14.0-linux-x86_64/bin

./kibana
# kibana也不能运行在 root 用户上
```

>port: 5601

### docker 安装 Kibana

```shell
docker pull kibana:7.14.0

docker run -d --name kibana -p 5601:5601 kibana:7.14.0

docker exec -it kibana bash
# 进入 kibana 的容器

vi config/kibana.yml
# 修改配置文件
# 修改 elasticsearch.hosts: [ "ES运行的地址" ]

exit

docker restart kibana
```

### docker-compose 安装 ES & Kibana

```shell
cd /home

mkdir ES-Kibana

cd ES-Kibana

vim docker-compose.yml
# 内容如下

vim kibana.yml
# 内容如下
```

docker-compose.yml

```dockerfile
version: "3.8"
volumes:
  data:
  config:
  plugin:
networks:
  es:
services:
  elasticsearch:
    image: elasticsearch:7.14.0
    ports:
      - "9200:9200"
      - "9300:9300"
    networks:
      - "es"
    environment:
      - "discovery.type=single-node"
      - "ES_JAVA_OPTS=-Xms512m -Xmx1g"
    volumes:
      - data:/usr/share/elasticsearch/data
      - config:/usr/share/elasticsearch/config
      - plugin:/usr/share/elasticsearch/plugins
    
  kibana:
    image: kibana:7.14.0
    ports:
      - "5601:5601"
    networks:
      - "es"
    depends_on:
      - elasticsearch
    environment:
      I18N_LOCALE: zh-CN  # 7.X  后切换中文
    volumes:
      - ./kibana.yml:/usr/share/kibana/config/kibana.yml
```

kibana.yml

```yaml
server.host: "0"
server.shutdownTimeout: "5s"
elasticsearch.hosts: [ "http://elasticsearch:9200" ]
# 由于 kibana 和 ES 在 docker-compose 文件中指定了处于同一个network
# 因此可以用 ES 的服务名来作为 IP 指定服务
monitoring.ui.container.elasticsearch.enabled: true
```

### 设置用户名密码

在 /usr/share/elasticsearch/config/elasticsearch.yml 中添加

```
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
```

在 /usr/share/kibana/config/kibana.yml 中添加

```
elasticsearch.username: "elastic"
elasticsearch.password: "后面要设置的"
```

重启 ES ，进入 ES 容器，设置用户名密码

```
[root@f42838410089 elasticsearch]# ./bin/elasticsearch-setup-passwords interactive
# 然后依次设置密码


Initiating the setup of passwords for reserved users elastic,apm_system,kibana,kibana_system,logstash_system,beats_system,remote_monitoring_user.
You will be prompted to enter passwords as the process progresses.
Please confirm that you would like to continue [y/N]y


Enter password for [elastic]: 
Reenter password for [elastic]: 
Enter password for [apm_system]: 
Reenter password for [apm_system]: 
Enter password for [kibana_system]: 
Reenter password for [kibana_system]: 
Enter password for [logstash_system]: 
Reenter password for [logstash_system]: 
Enter password for [beats_system]: 
Reenter password for [beats_system]: 
Enter password for [remote_monitoring_user]: 
Reenter password for [remote_monitoring_user]: 
Changed password for user [apm_system]
Changed password for user [kibana_system]
Changed password for user [kibana]
Changed password for user [logstash_system]
Changed password for user [beats_system]
Changed password for user [remote_monitoring_user]
Changed password for user [elastic]
```



## 核心概念

### 索引 index

一群相似的文档的集合，索引由名字来标识（全小写）

相当于 MySQL 的表

#### 索引基础操作

```
# 查看所有索引
GET /_cat/indices    

# 创建索引
PUT /索引名
# 默认创建的索引会在本地创建主数据块和副本数据块，
# 由于主从都在一个服务器上，因此索引的 health 状态会变为 yellow
# 可以暂时设置从索引数量为 0 ，解决这个问题
# PUT /索引名
# {
#	"settings":{
#     	"number_of_shards": 1,
#		"number_of_replicas": 0
#	}
# }

# 删除索引
DELETE /索引名
```

### 文档 document

一条条基础的数据，用 json 表示 

相当于 MySQL 的数据

#### 文档基础操作

```
# 添加文档，手动指定 _id
POST /索引名/_doc/1
{
	"xxx":"xxxx"
}

# 添加文档，自动生成 _id (UUID)
POST /索引名/_doc
{
	"xxx":"xxxx"
}

# 查询文档  基于 _id 查询
GET /索引名/_doc/<id>

# 删除文档  基于 _id 删除
DELETE /索引名/_doc/<id>

# 更新文档  基于 _id 更新 (删除原始文档，重新添加)
PUT /索引名/_doc/<id>
{
	"xxx":"xxxx"
}
# 更新文档  基于 _id 更新 (在原文档的基础上更新)
POST /索引名/_doc/<id>/_update
{
	"xxx":"xxxx"
}
```

### 映射 mapping  

定义一个文档和他所包含的字段如何被存储和索引 

相当于 MySQL 的表结构

#### 映射基础操作

```
# 创建索引的同时创建 mapping 映射
PUT /索引名
{
	"mappings": {
		"properties":{
			"id":{
				"type":"integer"
			},
			"title":{
				"type":"keyword"
			},
			"price":{
				"type":"double"
			},
			"description":{
				"type":"text"
			},
			"created_at":{
				"type":"date"
			}
		}
	}
}

# 查看某个索引的映射信息
GET /索引名/_mapping
```

### ES的基本数据类型

字符串类型：keyword 关键字      text 文本

数字类型：integer long float double

布尔类型：boolean

日期类型：date

## 分词器

推荐 IK 分词器

[medcl/elasticsearch-analysis-ik: The IK Analysis plugin integrates Lucene IK analyzer into elasticsearch, support customized dictionary. (github.com)](https://github.com/medcl/elasticsearch-analysis-ik)

### 安装

-  IK 分词器版本需要与 ES 版本一致
-  Docker 容器运行 ES 安装插件目录为 `/usr/share/elasticsearch/plugins` (docker-compose中已经创建数据卷映射)

```
[root@fengye ~]# docker volume ls
DRIVER    VOLUME NAME
local     es-kibana_config
local     es-kibana_data
local     es-kibana_plugin
[root@fengye ~]# docker volume inspect es-kibana_plugin 
[
    {
        "CreatedAt": "2022-03-29T23:49:42+08:00",
        "Driver": "local",
        "Labels": {
            "com.docker.compose.project": "es-kibana",
            "com.docker.compose.version": "2.2.3",
            "com.docker.compose.volume": "plugin"
        },
        "Mountpoint": "/www/server/docker/volumes/es-kibana_plugin/_data",
        "Name": "es-kibana_plugin",
        "Options": null,
        "Scope": "local"
    }
]
[root@fengye ~]# cd /www/server/docker/volumes/es-kibana_plugin/_data
[root@fengye _data]# wget https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v7.14.0/elasticsearch-analysis-ik-7.14.0.zip
[root@fengye _data]# mkdir ik-7.14.0
[root@fengye _data]# mv elasticsearch-analysis-ik-7.14.0.zip ik-7.14.0/
[root@fengye _data]# cd ik-7.14.0/
[root@fengye _data]# unzip elasticsearch-analysis-ik-7.14.0.zip
```

用kibana进行测试

```
# 请求
POST /_analyze
{
  "analyzer": "ik_max_word",
  "text": "嘉然可爱捏" 
}

# 响应：
{
  "tokens" : [
    {
      "token" : "嘉",
      "start_offset" : 0,
      "end_offset" : 1,
      "type" : "CN_CHAR",
      "position" : 0
    },
    {
      "token" : "然",
      "start_offset" : 1,
      "end_offset" : 2,
      "type" : "CN_CHAR",
      "position" : 1
    },
    {
      "token" : "可爱",
      "start_offset" : 2,
      "end_offset" : 4,
      "type" : "CN_WORD",
      "position" : 2
    },
    {
      "token" : "捏",
      "start_offset" : 4,
      "end_offset" : 5,
      "type" : "CN_CHAR",
      "position" : 3
    }
  ]
}

# ik_max_word 拆分力度比 ik_smart 更细 
```

### 创建索引时使用 IK 分词器

```
PUT /索引名
{
	"mappings":{
		"description":{
			"type":"text",
			"analyzer":"ik_max_word"
		}
	}
}
```

### 扩展|停用词典

修改 ik 解压目录的 config/IKAnalyzer.cfg.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<properties>
        <comment>IK Analyzer 扩展配置</comment>
        <!--用户可以在这里配置自己的扩展字典 -->
        <entry key="ext_dict">test.dic</entry>
         <!--用户可以在这里配置自己的扩展停止词字典-->
        <entry key="ext_stopwords"></entry>
        <!--用户可以在这里配置远程扩展字典 -->
        <!-- <entry key="remote_ext_dict">words_location</entry> -->
        <!--用户可以在这里配置远程扩展停止词字典-->
        <!-- <entry key="remote_ext_stopwords">words_location</entry> -->
</properties>
```

添加拓展词典 test.dic ，创建 test.dic 文件，写入内容（一行一个词）

```
嘉然
```

测试效果：

```
{
  "analyzer": "ik_max_word",
  "text": "嘉然可爱捏" 
}

{
  "tokens" : [
    {
      "token" : "嘉然",
      "start_offset" : 0,
      "end_offset" : 2,
      "type" : "CN_WORD",
      "position" : 0
    },
    {
      "token" : "可爱",
      "start_offset" : 2,
      "end_offset" : 4,
      "type" : "CN_WORD",
      "position" : 1
    },
    {
      "token" : "捏",
      "start_offset" : 4,
      "end_offset" : 5,
      "type" : "CN_CHAR",
      "position" : 2
    }
  ]
}
```

## 查询 Query DSL

通过 rest api 传递 json 数据进行高级查询

语法：

```
GET /索引名/_doc/_search
{
	"xxxx":"xxxx"
}
```

### 常用查询语句

#### 查询一个索引的所有文档 march_all

```
GET /索引名/_search
{
	"query":{
		"match_all":{}
	}
}
```

#### 基于关键词查询 term

```
GET /索引名/_search
{
	"query":{
		"term":{
			"description":{
				"value":"test"
			}
		}
	}
}
# text 默认的分词器是 中文单字，英文单词
# 除了 text ，其余都不分词
```

#### 范围查询 range

```
GET /索引名/_search
{
	"query":{
		"range":{
			"price":{
				"gte":1400,
				"lte":9999
			}
		}
	}
}
# gt 大于  gte 大于等于
# lt 小于  lte 小于等于
```

#### 前缀查询 prefix

```
GET /索引名/_search
{
	"query":{
		"prefix":{
			"title":{
				"value":"ipho"
			}
		}
	}
}
# gt 大于  gte 大于等于
# lt 小于  lte 小于等于
```

#### 通配符查询 wildcard

```
GET /索引名/_search
{
	"query":{
		"wildcard":{
			"description":{
				"value":"ipho*"
			}
		}
	}
}
# ? 匹配任意字符    * 匹配多个字符
```

#### 多id查询 ids

获取多个指定 id 的文档

```
GET /索引名/_search
{
	"query":{
		"ids":{
			"description":{
				"values":["123","124","125"]
			}
		}
	}
}
```

#### 模糊查询 fuzzy

模糊查询含有指定关键字的文档

```
GET /索引名/_search
{
	"query":{
		"fuzzy":{
			"title":"hello"
		}
	}
}
# 搜索关键词长度小于等于 2 不允许模糊 
# 搜索关键词长度为 3-5 允许一次模糊 
# 搜索关键词长度大于 5 允许两次模糊 
```

#### 布尔查询 bool

```
GET /索引名/_search
{
	"query":{
		"bool":{
			"must":[
				{"term":{
					"price":{
						"value":4999
					}
				}}
			]
		}
	}
}
# must 相当于 &&      全真
# should 相当于 ||	   一个真
# must_not 相当于 !   全假
```

#### 多字段查询 multi_match

```
GET /索引名/_search
{
	"query":{
		"multi_match":{
			"query":"iphone",
			"fields":["title","description"]
		}
	}
}
# 如果字段类型 field 分词，那么查询的 query 也会分词后进行查询
```

#### 默认字段分词查询 query_string

```
GET /索引名/_search
{
	"query":{
		"query_string":{
			"default_field":"description",
			"query":"test"
		}
	}
}
# 如果字段分词，查询条件也分词
```

#### 高亮查询 highlight

将指定字段中的关键词高亮显示（只有能分词的字段才可以高亮）

默认使用 `<em>` 标签将关键词包裹

```
GET /索引名/_search
{
	"query":{
		"term":{
			"description":{
				"value":"iphone"
			}
		}
	},
	"highlight":{
		"pre_tags":["<span style='color:red;'>"],
		"post_tags":["</span>"]
		"fields":{
			"*":{}
		}
	}
}
# 如果字段分词，查询条件也分词
```

#### 分页查询 from size

默认查询只返回前十条

size: 每一页多少个数据

from: 起始位置  from = (pageNum-1)*size

```
GET /索引名/_search
{
	"query":{
		"term":{
			"description":{
				"value":"iphone"
			}
		}
	},
	"size":100,
	"from":0
}
```

#### 排序查询 from

```
GET /索引名/_search
{
	"query":{
		"term":{
			"description":{
				"value":"iphone"
			}
		}
	},
	"sort":[
		{
			"price":{
				"order":"desc"
			}
		}
	]
}
# 降序 desc      升序 asc
```

#### 返回指定字段 _source

```
GET /索引名/_search
{
	"query":{
		"term":{
			"description":{
				"value":"iphone"
			}
		}
	},
	"_source":["title","description"]
}
```

### 返回结果样例

```json
{
  "took" : 346,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 3,
      "relation" : "eq"
    },
    "max_score" : 1.0,
    "hits" : [
      {
        "_index" : "products",
        "_type" : "_doc",
        "_id" : "HnOeWYABh7tgu1RN4hRV",
        "_score" : 1.0,
        "_source" : {
          "title" : "test",
          "price" : 123
        }
      }
    ]
  }
}
```

## 过滤查询 filter

ES中有两种查询：query 和 filter 

query 查询出来的结果会根据索引出现的次数、位置等信息进行打分，然后根据得分进行排名后返回结果

filter 则直接返回结果，因此 filter 效率要高于 query（同时 ES 也会缓存常用的 filter ）

一般应用时，应先使用过滤操作过滤数据，然后使用查询匹配数据。

filter 必须配合 bool 查询使用：

```
GET /索引名/_search
{
	"query":{
		"bool":{
			"must":[
				{
					"match_all":{}
				}
			],
			"filter":{
				"term":{
					"description":"iphone"
				}
			}
		}
	}
}
```

过滤类型：term、terms、ranage、exists、ids、bool

## 整合 SpringBoot

引入依赖

```
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-elasticsearch</artifactId>
</dependency>
```

配置客户端

```java
@Configuration
public class ESClientConfig extends AbstractElasticsearchConfiguration {
    @Value("${elasticsearch.host}")
    private String host;

    @Value("${elasticsearch.port}")
    private String port;

    @Override
    @Bean
    public RestHighLevelClient elasticsearchClient() {
        final ClientConfiguration clientConfiguration = ClientConfiguration.builder()
                .connectedTo(host + ":" + port)
                .build();
        return RestClients.create(clientConfiguration).rest();
    }
}
```

客户端对象

- ElasticsearchOperations   通过偏向 oop 的方式操作
- RestHighLevelClient  类似 kibana ，通过rest操作（推荐）

### ElasticsearchOperations

创建映射实体类

```java
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.Document;
import org.springframework.data.elasticsearch.annotations.Field;
import org.springframework.data.elasticsearch.annotations.FieldType;

@Document(indexName = "products")
// 指定文档的索引名称
public class Product {
    @Id
    // 指定字段作为 _id
    private Integer id;
    
    @Field(type = FieldType.Keyword)
    private String title;
    
    @Field(type = FieldType.Float)
    private Double price;
    
    @Field(type = FieldType.Text,analyzer = "ik_max_word")
    // 指定映射类型和分词器
    private String description;
    //get set...
}
```

使用

```java
@SpringBootTest
class DemoApplicationTests {

    @Autowired
    private ElasticsearchOperations elasticsearchOperations;

    @Test
    void contextLoads() {
        Product product = new Product();
        product.setId(1);
        product.setTitle("iphone");
        product.setPrice(9999.0);
        product.setDescription("iphone with IOS");
        
        elasticsearchOperations.save(product);
        // save() 当文档 id 不存在时，创建文档
        // 当文档 id 存在时，更新文档
        
        Product res = elasticsearchOperations.get("1", Product.class);
        
        elasticsearchOperations.delete(product);
    }
}
```

### RestHighLevelClient

#### 创建索引

```java
import org.elasticsearch.action.delete.DeleteRequest;
import org.elasticsearch.action.get.GetRequest;
import org.elasticsearch.action.get.GetResponse;
import org.elasticsearch.action.index.IndexRequest;
import org.elasticsearch.action.search.SearchRequest;
import org.elasticsearch.action.search.SearchResponse;
import org.elasticsearch.action.update.UpdateRequest;
import org.elasticsearch.client.RequestOptions;
import org.elasticsearch.client.RestHighLevelClient;
import org.elasticsearch.client.indices.CreateIndexRequest;
import org.elasticsearch.client.indices.GetIndexRequest;
import org.elasticsearch.common.xcontent.XContentType;
import org.elasticsearch.index.query.QueryBuilder;
import org.elasticsearch.index.query.QueryBuilders;
import org.elasticsearch.search.builder.SearchSourceBuilder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.Map;

/**
 * @author: 風楪fy
 * @create: 2022/4/24 10:47
 **/
@Service
public class ESService {
    @Autowired
    private RestHighLevelClient restHighLevelClient;

    /**
     * 判断索引是否存在
     *
     * @param indexName 索引名称
     * @return
     * @throws IOException
     */
    public boolean isIndexExist(String indexName) throws IOException {
        GetIndexRequest request = new GetIndexRequest(indexName);
        return restHighLevelClient.indices().exists(request, RequestOptions.DEFAULT);
    }

    /**
     * 创建索引
     *
     * @param indexName   索引名
     * @param mappingJson 映射
     * @throws IOException
     */
    public void createIndex(String indexName, String mappingJson) throws IOException {
        CreateIndexRequest createIndexRequest = new CreateIndexRequest(indexName);
        if (mappingJson != null) {
            createIndexRequest.mapping(mappingJson, XContentType.JSON);
        }
        restHighLevelClient.indices().create(createIndexRequest, RequestOptions.DEFAULT);
    }

    /**
     * 向指定索引中添加文档
     *
     * @param indexName 索引名
     * @param document  被添加的 JSON 文档
     * @param id        指定要添加的文档的 id，为 null 时 ES 会自动生成
     * @throws IOException
     */
    public void addDocument(String indexName, String document, String id) throws IOException {
        IndexRequest request = new IndexRequest(indexName);
        request.id(id).source(document, XContentType.JSON);
        restHighLevelClient.index(request, RequestOptions.DEFAULT);
    }

    /**
     * 根据 id 更新文档 (在原文档的基础上更新)
     *
     * @param indexName 索引名
     * @param id        id
     * @param document  更新内容
     */
    public void updateDocument(String indexName, String id, String document) throws IOException {
        UpdateRequest updateRequest = new UpdateRequest(indexName, id);
        updateRequest.doc(document, XContentType.JSON);
        restHighLevelClient.update(updateRequest, RequestOptions.DEFAULT);
    }

    /**
     * 删除指定文档
     *
     * @param indexName
     * @param id
     */
    public void deleteDocument(String indexName, String id) throws IOException {
        DeleteRequest deleteRequest = new DeleteRequest(indexName, id);
        restHighLevelClient.delete(deleteRequest, RequestOptions.DEFAULT);
    }

    /**
     * 根据 id 返回文档
     *
     * @param indexName
     * @param id
     * @return
     * @throws IOException
     */
    public Map<String, Object> getDocumentById(String indexName, String id) throws IOException {
        GetRequest getRequest = new GetRequest(indexName, id);
        GetResponse documentFields = restHighLevelClient.get(getRequest, RequestOptions.DEFAULT);
        return documentFields.getSource();
    }


    /**
     * 封装分页条件查询
     *
     * @param indexName
     * @param queryBuilder
     * @param pageNum      起始位置（从0开始）
     * @param pageSize     每一页的数量
     * @return
     * @throws IOException
     */
    private SearchResponse query(String indexName, QueryBuilder queryBuilder, int pageNum, int pageSize) throws IOException {
        SearchRequest searchRequest = new SearchRequest(indexName);

        SearchSourceBuilder searchSourceBuilder = new SearchSourceBuilder();
        searchSourceBuilder.query(queryBuilder)
                .from((pageNum - 1) * pageSize)
                .size(pageSize);

        searchRequest.source(searchSourceBuilder);
        return restHighLevelClient.search(searchRequest, RequestOptions.DEFAULT);
    }

    /**
     * term 查询
     *
     * @param indexName
     * @param fieldName
     * @param terms
     * @return
     * @throws IOException
     */
    public SearchResponse termQuery(String indexName, String fieldName, String... terms) throws IOException {
        return this.query(indexName, QueryBuilders.termsQuery(fieldName, terms), 0, 10);
    }
}
```

