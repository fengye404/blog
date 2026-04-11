---
title: 配置HTTPS
typora-root-url: ./配置HTTPS
date: 2023-01-18 15:48:21
tags:
---

## 前置

由于 HTTP 本身是使用明文通信的，不加密、无法验证通信方的身份、无法证明报文的完整性，因此 HTTPS 出现了。HTTPS 本质上就是 HTTP 与 SSL/TLS 的组合。

**HTTPS要解决的问题：**

- 加密：保证信息不会泄露
- 证明：保证信息来源于目标服务器，并且不被篡改

### 加密

#### 对称加密/共享密钥加密

服务器和客户端使用相同的加密/解密密钥。但是密钥需要传递交给对方，而一旦在互联网上传递，密钥就会泄露，也就失去了加密的意义。

![image-20221118010004817](./202211180100945.png)

#### 非对称加密/公开密钥加密

非对称加密使用的是两把密钥，一把叫私钥（不能公开），一把叫公钥（公开）。信息在经过公钥/私钥加密后，需要用另外一把密钥来解密。

如果两方需要通信，一方可以先将公钥发送给对方，私钥自己保留。需要发送信息时，将待发送信息用自己的密钥进行加密；需要接收信息时，将接收到的信息用自己的密钥进行解密。

![image-20221118204207303](./202211182042388.png)

使用公开密钥加密方式，发送密文的一方使用对方的公开密钥进行加密处理，对方收到被加密的信息后，再使用自己的私有密钥进行解密。利用这种方式，不需要发送用来解密的私有密钥，也不必担心密钥被攻击者窃听而盗走。

#### 混合加密

虽然非对称加密比对称加密要安全，但是处理速度却比对称加密要慢。因此 HTTPS 采用了混合加密机制。

![image-20221118210152453](./202211182101525.png)

即**用非对称加密的方式来传递对称加密的密钥，后续通信通过对称加密**。

### 证明

**为了证明客户端收到的公钥是目标服务器的**，服务器会把公钥放在**数字证书**中发送出去。**数字证书是一串包含服务器公钥并且能够证明服务器身份的字符串**，数字证书一般是有权威的CA机构颁发的。

**为了证明数字证书不被篡改**，需要在数字证书中附带**数字签名**。

CA机构颁发数字证书的流程：

1. CA机构有一套自己的公钥和私钥，CA机构先对证书的明文数据（待颁发服务器的公钥、颁发数字证书的机构、签名算法等内容）进行hash运算，并使用私钥对hash运算的结果加密，生成的值就是**数字签名**。
2. 使用数字证书明文数据和数字签名共同组成数字证书，颁发给目标服务器。

浏览器验证数字证书的流程：

1. 从服务器接收到数字证书，获取其中的明文内容和数字签名。
2. 使用CA机构的公钥（浏览器内置）对数字签名进行解密。
3. 判断解密出来的值是否等于证书明文部分的hash，如果等于，则表示证书未被篡改并且公钥可信。

## 如何给自己的服务器配置数字证书

CA机构有很多，有免费的也有收费的，`Let's Encrypt` 就是其中的一个免费机构。certbot是一个基于 `Let's Encrypt` 的自动化申请证书的工具

### 安装

可以在[官网](https://certbot.eff.org/)选择自己的操作系统和服务器软件自定义安装。我选择的是 Centos7 和 Nginx。

1. 安装snapd

   ```shell
   $ sudo yum install snapd
   ```

2. 配置 snap 链接

   ```shell
   $ sudo ln -s /var/lib/snapd/snap /snap
   ```

3. 通过 snapd 安装 certbot

   ```shell
   $ sudo snap install --classic certbot
   ```

4. 配置 certbot 命令

   ```shell
   $ sudo ln -s /snap/bin/certbot /usr/bin/certbot
   ```

5. 申请并安装证书

   ```shell
   $ sudo certbot certonly --nginx --nginx-server-root=/www/server/nginx/conf
   ```

6. 手动修改配置文件

   ```conf
   server
   {
       # 配置 http 跳转 https
       listen 80;
       server_name www.fengye404.top fengye404.top;
       return 301 https://$server_name$request_uri; 
   }
   server
   {
       listen 443 ssl;
       server_name fengye404.top www.fengye404.top;
       ssl_certificate /etc/letsencrypt/live/fengye404.top/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/fengye404.top/privkey.pem;
       index index.php index.html index.htm default.php default.htm default.html;
       root /wordpress;
   }
   ```

> 参考文章：
>
> [彻底搞懂HTTPS的加密原理 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/43789231)
>
> [CentOS7下使用Certbot+Nginx搭建Https环境 - 禁忌夜色153 - 博客园 (cnblogs.com)](https://www.cnblogs.com/jinjiyese153/p/13396918.html)
>
> [Nginx强制跳转Https - 简书 (jianshu.com)](https://www.jianshu.com/p/116fc2d08165)

