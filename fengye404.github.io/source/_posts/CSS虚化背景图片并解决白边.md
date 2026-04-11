---
title: CSS虚化背景图片并解决白边
typora-root-url: ./CSS虚化背景图片并解决白边
date: 2022-02-14 15:37:14
tags:
---

# CSS虚化背景图片并去掉白边

直接上代码

App.jsx

```js
import {Layout} from "@douyinfe/semi-ui";
import "./App.css";

function App() {
    const {Header, Footer, Content} = Layout;

    return (
        <Layout className={"layout"}>
            <div className={"background"}/>
            <Header>Header</Header>
            <Content>Content</Content>
            <Footer>Footer</Footer>
        </Layout>
    );
}

export default App;
```

App.css

```css
.background{
    width: 100vw;/*设置宽为屏幕宽度*/
    height: 100vh;/*设置高为屏幕高度*/
    position: fixed;/*固定位置*/
    z-index: -1;/*置于下层*/

    background-image: url("../public/枝江往事.jpg");
    background-repeat: no-repeat;
    background-position: center;
    background-attachment: fixed;
    background-size:cover;
    filter: blur(3px);
    transform: scale(1.02);/*放大，去掉白边*/
}
```



参考：[去掉模糊背景或图片的白边 – Clloz ☘️](https://www.clloz.com/programming/front-end/css/2019/05/23/blur-white-border/)

